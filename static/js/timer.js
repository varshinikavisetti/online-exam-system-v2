// Countdown timer with auto-submit when time runs out.
(function () {
  let remaining = typeof DURATION_SECONDS !== "undefined" ? DURATION_SECONDS : 1800;
  const timerEl = document.getElementById("timer");

  function render() {
    const m = Math.floor(remaining / 60).toString().padStart(2, "0");
    const s = (remaining % 60).toString().padStart(2, "0");
    timerEl.textContent = `${m}:${s}`;
    if (remaining <= 60) {
      timerEl.classList.add("blink-warning");
    }
  }

  render();
  const interval = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(interval);
      timerEl.textContent = "00:00";
      const form = document.getElementById("examForm");
      if (form) form.submit();
      return;
    }
    render();
  }, 1000);
})();
