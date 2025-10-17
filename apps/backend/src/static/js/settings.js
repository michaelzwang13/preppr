// Form validation and interactions
document.addEventListener("DOMContentLoaded", function () {
  const forms = document.querySelectorAll("form");

  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      const submitBtn = this.querySelector('button[type="submit"]');

      // Add loading state
      if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML =
          '<i class="fas fa-spinner fa-spin"></i> Saving...';
        submitBtn.disabled = true;

        // Re-enable after 3 seconds in case of issues
        setTimeout(() => {
          submitBtn.innerHTML = originalText;
          submitBtn.disabled = false;
        }, 3000);
      }
    });
  });

  // Enhanced input focus effects
  const inputs = document.querySelectorAll(".form-input");
  inputs.forEach((input) => {
    input.addEventListener("focus", function () {
      this.parentElement.style.transform = "scale(1.02)";
    });

    input.addEventListener("blur", function () {
      this.parentElement.style.transform = "scale(1)";
    });
  });

  // Load user preferences
  loadUserPreferences();

  // Handle preferences save button
  const savePreferencesBtn = document.getElementById("savePreferencesBtn");
  if (savePreferencesBtn) {
    savePreferencesBtn.addEventListener("click", saveUserPreferences);
  }

  // Handle theme preference change
  const themePreference = document.getElementById("themePreference");
  if (themePreference) {
    themePreference.addEventListener("change", function() {
      // Apply theme immediately when changed
      if (typeof window.applyThemeFromPreference === 'function') {
        window.applyThemeFromPreference(this.value);
      }
    });
  }
});

// Load user preferences from API
async function loadUserPreferences() {
  try {
    const response = await fetch("/api/user/preferences");
    if (response.ok) {
      const data = await response.json();
      if (data.success && data.preferences) {
        // Set toggle switches
        const nutritionToggle = document.getElementById("nutritionTrackingToggle");
        if (nutritionToggle) {
          nutritionToggle.checked = data.preferences.nutrition_tracking_enabled !== false;
        }

        const emailToggle = document.getElementById("emailNotificationsToggle");
        if (emailToggle) {
          emailToggle.checked = data.preferences.email_notifications !== false;
        }

        // Set measurement unit
        const measurementUnit = document.getElementById("measurementUnit");
        if (measurementUnit && data.preferences.measurement_unit) {
          measurementUnit.value = data.preferences.measurement_unit;
        }

        // Set theme preference
        const themePreference = document.getElementById("themePreference");
        if (themePreference && data.preferences.theme_preference) {
          themePreference.value = data.preferences.theme_preference;
        }
      }
    }
  } catch (error) {
    console.error("Error loading preferences:", error);
  }
}

// Save user preferences
async function saveUserPreferences() {
  const saveBtn = document.getElementById("savePreferencesBtn");
  const originalText = saveBtn.innerHTML;
  
  try {
    // Show loading state
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
    saveBtn.disabled = true;

    // Get form values
    const preferences = {
      nutrition_tracking_enabled: document.getElementById("nutritionTrackingToggle").checked,
      email_notifications: document.getElementById("emailNotificationsToggle").checked,
      measurement_unit: document.getElementById("measurementUnit").value,
      theme_preference: document.getElementById("themePreference").value
    };

    const response = await fetch("/api/user/preferences", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(preferences),
    });

    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        // Show success message
        showMessage("Preferences saved successfully!", "success");
        
        // Scroll to top to show the success message
        window.scrollTo({
          top: 0,
          behavior: 'smooth'
        });
        
        // Apply theme preference immediately after saving
        if (typeof window.applyThemeFromPreference === 'function') {
          window.applyThemeFromPreference(preferences.theme_preference);
        }
        
        window.lastNutritionState = preferences.nutrition_tracking_enabled;
      } else {
        showMessage("Failed to save preferences: " + data.message, "error");
      }
    } else {
      showMessage("Failed to save preferences. Please try again.", "error");
    }
  } catch (error) {
    console.error("Error saving preferences:", error);
    showMessage("An error occurred while saving preferences.", "error");
  } finally {
    // Restore button state
    saveBtn.innerHTML = originalText;
    saveBtn.disabled = false;
  }
}

// Toggle feature comparison dropdown
function toggleFeatureComparison() {
  const content = document.getElementById('featureComparisonContent');
  const icon = document.getElementById('featureToggleIcon');
  
  if (content.style.display === 'none' || content.style.display === '') {
    content.style.display = 'block';
    icon.style.transform = 'rotate(180deg)';
  } else {
    content.style.display = 'none';
    icon.style.transform = 'rotate(0deg)';
  }
}

// Show message to user
function showMessage(message, type) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll('.temp-message');
  existingMessages.forEach(msg => msg.remove());

  // Create message element
  const messageDiv = document.createElement('div');
  messageDiv.className = `message temp-message ${type === 'success' ? 'success' : 'error'}`;
  messageDiv.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-triangle'}"></i> ${message}`;
  
  // Insert at top of settings container
  const settingsContainer = document.querySelector('.settings-container');
  const header = settingsContainer.querySelector('.settings-header');
  header.insertAdjacentElement('afterend', messageDiv);

  // Remove message after 5 seconds
  setTimeout(() => {
    messageDiv.remove();
  }, 5000);
}
