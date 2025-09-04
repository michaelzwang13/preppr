// Shared meal modal functionality
// Used by home.js and meal_plan_details.js to avoid code duplication

function convertToMixedFraction(decimal) {
  if (!decimal || decimal === 0) return '0';
  
  const num = parseFloat(decimal);
  const wholeNumber = Math.floor(num);
  const fractionalPart = num - wholeNumber;
  
  // If no fractional part, return whole number
  if (fractionalPart === 0) {
    return wholeNumber.toString();
  }
  
  // Round to nearest common fraction
  let fraction = '';
  const tolerance = 0.04; // Tolerance for rounding
  
  // Check for halves
  if (Math.abs(fractionalPart - 0.5) < tolerance) {
    fraction = '1/2';
  }
  // Check for quarters
  else if (Math.abs(fractionalPart - 0.25) < tolerance) {
    fraction = '1/4';
  }
  else if (Math.abs(fractionalPart - 0.75) < tolerance) {
    fraction = '3/4';
  }
  // Check for thirds
  else if (Math.abs(fractionalPart - 0.333) < tolerance || Math.abs(fractionalPart - 0.33) < tolerance) {
    fraction = '1/3';
  }
  else if (Math.abs(fractionalPart - 0.667) < tolerance || Math.abs(fractionalPart - 0.66) < tolerance) {
    fraction = '2/3';
  }
  // If doesn't match common fractions, round to nearest quarter
  else {
    const rounded = Math.round(fractionalPart * 4) / 4;
    if (rounded === 0.25) fraction = '1/4';
    else if (rounded === 0.5) fraction = '1/2';
    else if (rounded === 0.75) fraction = '3/4';
    else if (rounded === 0) return wholeNumber.toString();
    else if (rounded === 1) return (wholeNumber + 1).toString();
  }
  
  // Return formatted result
  if (wholeNumber === 0) {
    return fraction;
  } else {
    // For meal plan details, use HTML formatting, for home use plain text
    if (typeof window !== 'undefined' && window.MEAL_PLAN_DETAILS_CONFIG) {
      return `${wholeNumber}&nbsp;<span class="mixed-fraction">${fraction}</span>`;
    } else {
      return `${wholeNumber} ${fraction}`;
    }
  }
}

// Function to load and display detailed nutrition data
async function loadMealNutritionData(mealId, sectionId) {
  try {
    const response = await fetch(`/api/nutrition/${mealId}`);
    const data = await response.json();

    console.log("Data")
    console.log(data)

    const nutritionSection = document.getElementById(sectionId);

    console.log(nutritionSection)
    console.log("test")
    if (!nutritionSection) return;

    if (data.success && data.nutrition) {
      const nutrition = data.nutrition;

      let nutritionHTML = '<div class="nutrition-details-grid">';

      // Main macros
      if (nutrition.calories) {
        nutritionHTML += `<div class="nutrition-detail-item">
          <span class="nutrition-label">Calories</span>
          <span class="nutrition-value">${Math.round(nutrition.calories)}</span>
        </div>`;
      }

      if (nutrition.macros.protein) {
        nutritionHTML += `<div class="nutrition-detail-item">
          <span class="nutrition-label">Protein</span>
          <span class="nutrition-value">${Math.round(nutrition.macros.protein)}g</span>
        </div>`;
      }

      if (nutrition.macros.carbs) {
        nutritionHTML += `<div class="nutrition-detail-item">
          <span class="nutrition-label">Carbohydrates</span>
          <span class="nutrition-value">${Math.round(nutrition.macros.carbs)}g</span>
        </div>`;
      }

      if (nutrition.macros.fat) {
        nutritionHTML += `<div class="nutrition-detail-item">
          <span class="nutrition-label">Fat</span>
          <span class="nutrition-value">${Math.round(nutrition.macros.fat)}g</span>
        </div>`;
      }

      if (nutrition.macros.fiber) {
        nutritionHTML += `<div class="nutrition-detail-item">
          <span class="nutrition-label">Fiber</span>
          <span class="nutrition-value">${Math.round(nutrition.macros.fiber)}g</span>
        </div>`;
      }

      if (nutrition.macros.sodium) {
        nutritionHTML += `<div class="nutrition-detail-item">
          <span class="nutrition-label">Sodium</span>
          <span class="nutrition-value">${Math.round(nutrition.macros.sodium)}mg</span>
        </div>`;
      }

      nutritionHTML += "</div>";

      // Add serving info if available
      if (nutrition.servings || nutrition.serving_size) {
        nutritionHTML += '<div class="nutrition-serving-info">';
        if (nutrition.servings) {
          nutritionHTML += `<span class="serving-info">Servings: ${nutrition.servings}</span>`;
        }
        if (nutrition.serving_size) {
          nutritionHTML += `<span class="serving-info">Serving Size: ${nutrition.serving_size}</span>`;
        }
        nutritionHTML += "</div>";
      }

      // Check if this is for meal plan details (has section label)
      if (typeof window !== 'undefined' && window.MEAL_PLAN_DETAILS_CONFIG) {
        nutritionSection.innerHTML = `
          <div class="section-label">
            <i class="fas fa-chart-bar"></i>
            Nutrition Information
          </div>
          ${nutritionHTML}
        `;
      } else {
        // For home page modal
        nutritionSection.innerHTML = `
          <h4><i class="fas fa-chart-bar"></i> Nutrition Information</h4>
          ${nutritionHTML}
        `;
      }
    } else {
      const noDataHTML = `
        <div style="color: var(--text-muted); font-style: italic; padding: var(--spacing-sm) 0;">
          No nutrition data available for this meal.
        </div>
      `;
      
      if (typeof window !== 'undefined' && window.MEAL_PLAN_DETAILS_CONFIG) {
        nutritionSection.innerHTML = `
          <div class="section-label">
            <i class="fas fa-chart-bar"></i>
            Nutrition Information
          </div>
          ${noDataHTML}
        `;
      } else {
        nutritionSection.innerHTML = `
          <h4><i class="fas fa-chart-bar"></i> Nutrition Information</h4>
          ${noDataHTML}
        `;
      }
    }
  } catch (error) {
    console.error("Failed to load nutrition data:", error);
    const nutritionSection = document.getElementById(sectionId);
    if (nutritionSection) {
      const errorHTML = `
        <div style="color: var(--error-color); font-style: italic; padding: var(--spacing-sm) 0;">
          Failed to load nutrition data.
        </div>
      `;
      
      if (typeof window !== 'undefined' && window.MEAL_PLAN_DETAILS_CONFIG) {
        nutritionSection.innerHTML = `
          <div class="section-label">
            <i class="fas fa-chart-bar"></i>
            Nutrition Information
          </div>
          ${errorHTML}
        `;
      } else {
        nutritionSection.innerHTML = `
          <h4><i class="fas fa-chart-bar"></i> Nutrition Information</h4>
          ${errorHTML}
        `;
      }
    }
  }
}

// Wrapper functions for backward compatibility
function loadMealNutritionForDetails(mealId) {
  loadMealNutritionData(mealId, `mealNutritionSection-${mealId}`);
}

function loadMealNutritionForPlanDetails(mealId) {
  loadMealNutritionData(mealId, `nutritionSection-${mealId}`);
}