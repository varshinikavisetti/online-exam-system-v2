// Handles Previous/Next navigation between question cards without page reload.
(function () {
  const cards = document.querySelectorAll(".question-card");
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  const submitBtn = document.getElementById("submitBtn");
  const progressLabel = document.getElementById("progressLabel");
  let current = 0;

  function show(index) {
    cards.forEach((c, i) => c.classList.toggle("d-none", i !== index));
    prevBtn.disabled = index === 0;

    const isLast = index === cards.length - 1;
    nextBtn.classList.toggle("d-none", isLast);
    submitBtn.classList.toggle("d-none", !isLast);

    progressLabel.textContent = `Question ${index + 1} of ${cards.length}`;
  }

  prevBtn.addEventListener("click", () => {
    if (current > 0) {
      current -= 1;
      show(current);
    }
  });

  nextBtn.addEventListener("click", () => {
    if (current < cards.length - 1) {
      current += 1;
      show(current);
    }
  });

  show(current);
})();
