// Enhanced form interactions
document.addEventListener("DOMContentLoaded", function () {
  const inputs = document.querySelectorAll(".form-input");

  inputs.forEach((input) => {
    // Add focus animation
    input.addEventListener("focus", function () {
      this.parentElement.style.transform = "scale(1.02)";
    });

    input.addEventListener("blur", function () {
      this.parentElement.style.transform = "scale(1)";
    });

    // Auto-focus first input
    if (input === inputs[0]) {
      input.focus();
    }
  });

  // Form validation
  const form = document.querySelector("form");
  form.addEventListener("submit", function (e) {
    const username = document.getElementById("user_ID").value.trim();
    const password = document.getElementById("password").value;

    if (!username || !password) {
      e.preventDefault();
      alert("Please fill in all fields.");
      return;
    }

    // Add loading state
    const submitBtn = document.querySelector(".btn-submit");
    submitBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> Signing In...';
    submitBtn.disabled = true;
  });
});
