// Lightweight tab-switch / focus-loss detection during an active exam.
// - First 2 switches: warns the student with a toast.
// - 3rd switch: auto-submits the exam immediately.
(function () {
  const MAX_ALLOWED_SWITCHES = 3;
  let switchCount = 0;

  const hiddenInput = document.getElementById("tabSwitchCount");
  const warningBanner = document.getElementById("proctorWarning");
  const form = document.getElementById("examForm");

  function updateHiddenCount() {
    if (hiddenInput) hiddenInput.value = switchCount;
  }

  function showWarning(message) {
    if (!warningBanner) return;
    warningBanner.textContent = message;
    warningBanner.classList.remove("d-none");
  }

  function handleVisibilityChange() {
    if (document.visibilityState !== "hidden") return; // only count when leaving

    switchCount += 1;
    updateHiddenCount();

    if (switchCount >= MAX_ALLOWED_SWITCHES) {
      showWarning(
        `Exam auto-submitted: you switched tabs/windows ${switchCount} times, which exceeds the allowed limit.`
      );
      if (form) form.submit();
    } else {
      showWarning(
        `Warning ${switchCount}/${MAX_ALLOWED_SWITCHES - 1}: switching tabs or minimizing the window during the exam is recorded. ` +
        `The exam will auto-submit if this happens ${MAX_ALLOWED_SWITCHES} times.`
      );
    }
  }

  document.addEventListener("visibilitychange", handleVisibilityChange);
  updateHiddenCount();
})();
