document.addEventListener("DOMContentLoaded", function () {
  const inputs = document.querySelectorAll(".form-input");
  const passwordInput = document.getElementById("password");
  const confirmPasswordInput = document.getElementById("confirmPassword");
  const passwordStrength = document.getElementById("passwordStrength");
  const passwordStrengthText = document.getElementById("passwordStrengthText");
  const passwordMatch = document.getElementById("passwordMatch");
  const submitBtn = document.getElementById("submitBtn");
  const form = document.getElementById("registerForm");

  // Enhanced form interactions
  inputs.forEach((input) => {
    input.addEventListener("focus", function () {
      this.parentElement.style.transform = "scale(1.02)";
    });

    input.addEventListener("blur", function () {
      this.parentElement.style.transform = "scale(1)";
    });
  });

  // Password strength checker
  function checkPasswordStrength(password) {
    let strength = 0;
    let feedback = "";

    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;

    passwordStrength.className = "password-strength";

    if (strength === 0) {
      feedback = "";
    } else if (strength <= 2) {
      passwordStrength.classList.add("weak");
      feedback = "Weak password";
    } else if (strength <= 3) {
      passwordStrength.classList.add("medium");
      feedback = "Medium strength";
    } else {
      passwordStrength.classList.add("strong");
      feedback = "Strong password";
    }

    passwordStrengthText.textContent = feedback;
    return strength;
  }

  // Password match checker
  function checkPasswordMatch() {
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (confirmPassword === "") {
      passwordMatch.textContent = "";
      passwordMatch.className = "password-match";
    } else if (password === confirmPassword) {
      passwordMatch.innerHTML = '<i class="fas fa-check"></i> Passwords match';
      passwordMatch.className = "password-match match";
    } else {
      passwordMatch.innerHTML =
        '<i class="fas fa-times"></i> Passwords do not match';
      passwordMatch.className = "password-match no-match";
    }
  }

  // Email validation function
  function checkEmailValidity() {
    const email = document.getElementById("email_address").value;
    const emailInput = document.getElementById("email_address");
    let emailFeedback = document.getElementById("emailFeedback");
    
    // Create feedback element if it doesn't exist
    if (!emailFeedback) {
      emailFeedback = document.createElement("div");
      emailFeedback.id = "emailFeedback";
      emailFeedback.className = "input-feedback";
      emailInput.parentElement.parentElement.appendChild(emailFeedback);
    }
    
    if (email === "") {
      emailFeedback.textContent = "";
      emailFeedback.className = "input-feedback";
      emailInput.style.borderColor = "";
      return true; // Allow empty email during typing
    }
    
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    const isValid = emailPattern.test(email);
    
    if (isValid) {
      emailFeedback.textContent = "";
      emailFeedback.className = "input-feedback";
      emailInput.style.borderColor = "";
    } else {
      emailFeedback.innerHTML = '<i class="fas fa-times"></i> Please enter a valid email address';
      emailFeedback.className = "input-feedback invalid";
      emailInput.style.borderColor = "var(--error-color)";
    }
    
    return isValid;
  }

  // Form validation
  function validateForm() {
    const firstName = document.getElementById("first_name").value;
    const lastName = document.getElementById("last_name").value;
    const email = document.getElementById("email_address").value;
    const username = document.getElementById("user_ID").value;
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    const emailValid = email === "" || /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
    const emailRequired = email !== "";
    const usernameValid = username.length >= 3;
    const passwordValid = checkPasswordStrength(password) >= 3;
    const passwordsMatch = password === confirmPassword && password !== "";

    const isValid =
      emailValid && emailRequired && usernameValid && passwordValid && passwordsMatch;

    submitBtn.disabled = !isValid;
    return isValid;
  }

  // Event listeners
  passwordInput.addEventListener("input", function () {
    checkPasswordStrength(this.value);
    checkPasswordMatch();
    validateForm();
  });

  confirmPasswordInput.addEventListener("input", function () {
    checkPasswordMatch();
    validateForm();
  });

  // Email validation listener
  document.getElementById("email_address").addEventListener("input", function () {
    checkEmailValidity();
    validateForm();
  });

  // Blur event for email to ensure validation on field exit
  document.getElementById("email_address").addEventListener("blur", function () {
    if (this.value !== "") {
      checkEmailValidity();
    }
  });

  inputs.forEach((input) => {
    input.addEventListener("input", validateForm);
  });

  // Form submission
  form.addEventListener("submit", function (e) {
    const email = document.getElementById("email_address").value;
    const username = document.getElementById("user_ID").value;
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    // Validate email format
    if (!checkEmailValidity() && email !== "") {
      e.preventDefault();
      alert("Please enter a valid email address.");
      document.getElementById("email_address").focus();
      return;
    }

    if (!validateForm()) {
      e.preventDefault();
      
      // Provide specific error messages
      if (email === "") {
        alert("Please enter your email address.");
        document.getElementById("email_address").focus();
      } else if (username.length < 3) {
        alert("Username must be at least 3 characters long.");
        document.getElementById("user_ID").focus();
      } else if (checkPasswordStrength(password) < 3) {
        alert("Please choose a stronger password.");
        passwordInput.focus();
      } else if (password !== confirmPassword) {
        alert("Passwords do not match.");
        confirmPasswordInput.focus();
      } else {
        alert("Please fill in all fields correctly.");
      }
      return;
    }

    // Add loading state
    submitBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> Creating Account...';
    submitBtn.disabled = true;
  });

  // Auto-focus first input
  document.getElementById("email_address").focus();
});
