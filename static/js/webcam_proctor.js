// Webcam proctoring for exams that have it enabled.
//
// Two checks run on the webcam feed every couple of seconds, both built on
// the SAME TensorFlow.js runtime (important: mixing tfjs-based libraries
// that bundle different internal tfjs versions — e.g. face-api.js — causes
// silent runtime conflicts where detection just stops working):
//   1. FACE check (BlazeFace, Google's official TF.js face detector) — must
//      see at least one human face. Zero faces (blocked/away from desk) is
//      a violation. A SECOND (or third+) face is intentionally NOT treated
//      as a violation on its own — real exam settings often have an
//      invigilator walking the room, and terminating on that would make
//      proctoring unusable in a supervised hall. Face count is only ever
//      used to catch an EMPTY seat, never to catch extra people.
//   2. OBJECT check (COCO-SSD) — flags ANY detected object that isn't a
//      person (phone, book, remote, cup, bottle, laptop... anything), not
//      just a fixed whitelist. This is the only check that can terminate
//      for "something/someone extra" being present.
//
// Either the no-face or the object violation terminates and auto-submits
// the exam. Multiple faces never does.
(function () {
  if (typeof WEBCAM_PROCTORING_ENABLED === "undefined" || !WEBCAM_PROCTORING_ENABLED) {
    return;
  }

  const CHECK_INTERVAL_MS = 2000;

  // Scores build up on bad frames and decay on clean frames so a single
  // missed/false-negative frame doesn't erase progress — detection is noisy
  // frame-to-frame, but sustained violations still terminate quickly.
  const OBJECT_SCORE_TO_TERMINATE = 4;
  const OBJECT_SCORE_PER_HIT = 3;
  const OBJECT_SCORE_DECAY = 1;

  const NO_FACE_SCORE_TO_TERMINATE = 5;
  const NO_FACE_SCORE_PER_HIT = 2;
  const NO_FACE_SCORE_DECAY = 1;

  const OBJECT_SCORE_THRESHOLD = 0.5;
  const FACE_PROBABILITY_THRESHOLD = 0.8;

  const form = document.getElementById("examForm");
  const violationInput = document.getElementById("proctorViolation");
  const violationReasonInput = document.getElementById("proctorViolationReason");
  const warningBanner = document.getElementById("proctorWarning");
  const video = document.getElementById("proctorVideo");
  const statusEl = document.getElementById("proctorStatus");

  let objectScore = 0;
  let noFaceScore = 0;
  let terminated = false;
  let objectModel = null;
  let faceModel = null;

  function log(...args) {
    console.log("[proctor]", ...args);
  }

  function showWarning(message) {
    if (!warningBanner) return;
    warningBanner.textContent = message;
    warningBanner.classList.remove("d-none");
  }

  function hideWarning() {
    if (warningBanner) warningBanner.classList.add("d-none");
  }

  function setStatus(text, ok) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.classList.toggle("text-success", ok);
    statusEl.classList.toggle("text-danger", !ok);
  }

  function terminateExam(reason, message) {
    if (terminated) return;
    terminated = true;
    log("TERMINATING:", reason);

    if (violationInput) violationInput.value = "1";
    if (violationReasonInput) violationReasonInput.value = reason;

    showWarning(message);
    setStatus("Exam terminated — submitting...", false);

    // Disable answer inputs so the student can't keep interacting while the
    // termination submit goes through — but NOT the hidden control fields
    // (csrf_token, tab_switch_count, proctor_violation...): disabled fields
    // are excluded from form submission entirely, which would silently
    // strip the CSRF token and make the submit fail.
    document.querySelectorAll("#examForm input, #examForm button").forEach((el) => {
      if (el.type === "hidden") return;
      el.disabled = true;
    });

    if (form) form.submit();
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 320, height: 240 },
      });
      if (video) {
        video.srcObject = stream;
        await video.play();
      }
      setStatus("Starting proctoring...", true);
      return true;
    } catch (err) {
      log("camera error:", err);
      terminateExam(
        "no_face_detected",
        "Camera access is required for this proctored exam and could not be started. Your exam has been terminated."
      );
      return false;
    }
  }

  // Model weights are fetched by blazeface/coco-ssd from
  // storage.googleapis.com — a DIFFERENT host than the jsdelivr CDN the
  // library scripts load from. That fetch is what was silently failing on
  // deploy (slow/unreliable egress on some hosts' free tiers), which the
  // old code only logged and then carried on without protection. This
  // retries with backoff and gives up loudly instead of quietly.
  async function withRetry(loadFn, label, attempts = 3) {
    let lastErr;
    for (let i = 1; i <= attempts; i++) {
      try {
        const model = await loadFn();
        log(`${label} loaded (attempt ${i})`);
        return model;
      } catch (err) {
        lastErr = err;
        log(`${label} load failed (attempt ${i}/${attempts}):`, err);
        if (i < attempts) await new Promise((r) => setTimeout(r, 1500 * i));
      }
    }
    log(`${label} gave up after ${attempts} attempts:`, lastErr);
    return null;
  }

  async function loadModels() {
    setStatus("Loading proctoring models...", true);

    faceModel = await withRetry(() => blazeface.load(), "blazeface");
    objectModel = await withRetry(
      () => cocoSsd.load({ base: "mobilenet_v2" }),
      "coco-ssd (mobilenet_v2)"
    );
    if (!objectModel) {
      objectModel = await withRetry(() => cocoSsd.load(), "coco-ssd (lite fallback)");
    }

    // Fail CLOSED only on the OBJECT model — that's the one that actually
    // catches phones/books/etc, which is the core anti-cheating feature.
    // Requiring BOTH models to succeed made the exam unstartable on any
    // network hiccup (including sometimes on localhost), which is worse
    // than the bug we were fixing. The face model is best-effort: if it
    // fails, the "empty seat" check is simply skipped (runCheck() already
    // guards on `if (faceModel)`) rather than blocking the whole exam —
    // students still get real object-detection proctoring.
    if (!objectModel) {
      setStatus("Proctoring failed to start — see message below", false);
      showWarning(
        "Proctoring could not start (detection models failed to load, likely a network issue). " +
          "The exam cannot begin until this is fixed."
      );
      document.querySelectorAll("#examForm input, #examForm button").forEach((el) => {
        if (el.type === "hidden") return;
        el.disabled = true;
      });
      if (warningBanner) {
        const retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "btn btn-sm btn-warning ms-2";
        retryBtn.textContent = "Retry";
        retryBtn.onclick = () => window.location.reload();
        warningBanner.appendChild(retryBtn);
      }
      return false;
    }

    if (!faceModel) {
      log("blazeface never loaded — continuing with object detection only (no empty-seat check).");
      setStatus("Camera active — monitoring (face check unavailable)", true);
    } else {
      setStatus("Camera active — monitoring", true);
    }
    return true;
  }

  async function runCheck() {
    if (terminated || !video || video.readyState < 2) return;

    let faceCount = null;
    if (faceModel) {
      try {
        const predictions = await faceModel.estimateFaces(video, false);
        faceCount = predictions.filter((p) => {
          const prob = Array.isArray(p.probability) ? p.probability[0] : p.probability;
          return prob === undefined || prob >= FACE_PROBABILITY_THRESHOLD;
        }).length;
        log("faces detected:", faceCount);
      } catch (err) {
        log("face detect() error:", err);
      }
    }

    let nonPersonObjects = [];
    if (objectModel) {
      try {
        const predictions = await objectModel.detect(video);
        log("objects:", predictions.map((p) => `${p.class} (${p.score.toFixed(2)})`));
        nonPersonObjects = predictions.filter(
          (p) => p.class !== "person" && p.score > OBJECT_SCORE_THRESHOLD
        );
      } catch (err) {
        log("object detect() error:", err);
      }
    }

    // --- Any object other than the person/face ---
    if (nonPersonObjects.length > 0) {
      objectScore = Math.min(OBJECT_SCORE_TO_TERMINATE, objectScore + OBJECT_SCORE_PER_HIT);
      const names = [...new Set(nonPersonObjects.map((o) => o.class))].join(", ");
      showWarning(
        `Warning: something other than your face (${names}) is visible to the camera. The exam will be terminated if this continues.`
      );
      if (objectScore >= OBJECT_SCORE_TO_TERMINATE) {
        terminateExam(
          "phone_or_object_detected",
          `Exam terminated: an object other than your face (${names}) was detected in front of the screen.`
        );
        return;
      }
    } else {
      objectScore = Math.max(0, objectScore - OBJECT_SCORE_DECAY);
    }

    // --- Face presence (only an EMPTY seat is a violation) ---
    if (faceCount !== null) {
      if (faceCount === 0) {
        noFaceScore = Math.min(NO_FACE_SCORE_TO_TERMINATE, noFaceScore + NO_FACE_SCORE_PER_HIT);
        showWarning("Warning: no face detected in the camera. The exam will be terminated if your face isn't visible.");
        if (noFaceScore >= NO_FACE_SCORE_TO_TERMINATE) {
          terminateExam(
            "no_face_detected",
            "Exam terminated: your face was not visible to the camera for too long during this proctored exam."
          );
          return;
        }
      } else {
        // One or more faces present (an invigilator or bystander walking
        // into frame is expected in a supervised hall) — this counts as
        // "student present", full stop. Not a violation, never terminates.
        noFaceScore = Math.max(0, noFaceScore - NO_FACE_SCORE_DECAY);
      }
    }

    if (objectScore === 0 && noFaceScore === 0) {
      hideWarning();
    }
  }

  (async function init() {
    const cameraOk = await startCamera();
    if (!cameraOk) return;
    const modelsOk = await loadModels();
    if (!modelsOk) return;
    setInterval(runCheck, CHECK_INTERVAL_MS);
  })();
})();
