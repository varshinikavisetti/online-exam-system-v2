// Animates any element with class "count-up" from 0 to its target number.
// Target number is read from the element's own text content at page load.
(function () {
  function animateCount(el) {
    const target = parseFloat(el.textContent.replace(/[^0-9.]/g, ""));
    if (isNaN(target)) return;

    const suffix = el.textContent.trim().endsWith("%") ? "%" : "";
    const duration = 700;
    const start = performance.now();

    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const current = target * eased;
      el.textContent = (target % 1 === 0 ? Math.round(current) : current.toFixed(2)) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".count-up").forEach(animateCount);
  });
})();
