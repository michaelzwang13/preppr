// Dynamic greeting based on time of day
function updateWelcomeMessage() {
  const now = new Date();
  const hour = now.getHours();
  const welcomeTimeEl = document.getElementById("welcomeTime");

  let greeting = "";
  let message = "";

  if (hour < 12) {
    greeting = "Good morning";
    message = "Ready to start your day with meal prepping?";
  } else if (hour < 17) {
    greeting = "Good afternoon";
    message = "Perfect time for some smart shopping!";
  } else {
    greeting = "Good evening";
    message = "Plan ahead for tomorrow's meal prep needs!";
  }

  welcomeTimeEl.textContent = `${greeting}! ${message}`;
}

// Load daily tip
async function loadDailyTip() {
  const tipText = document.getElementById("tipText");
  const dailyTip = document.getElementById("dailyTip");

  try {
    const response = await fetch("/api/tips/daily");
    const data = await response.json();

    if (data.success && data.tip) {
      // Update tip text with "Tip: " prefix
      tipText.textContent = `Tip: ${data.tip.text}`;
    } else {
      // Hide tip entirely if no tip available
      dailyTip.style.display = "none";
    }
  } catch (error) {
    console.error("Error loading daily tip:", error);
    // Hide tip on error
    dailyTip.style.display = "none";
  }
}

// Animate stats on page load
function animateStats() {
  const statValues = document.querySelectorAll(".stat-value");

  statValues.forEach((stat, index) => {
    setTimeout(() => {
      stat.style.animation = "pulse 0.6s ease";
    }, index * 200);
  });
}


// Header scroll effect
function initializeScrollEffects() {
  const header = document.querySelector(".header");

  window.addEventListener("scroll", function () {
    if (window.scrollY > 100) {
      header.style.background = "rgba(255, 255, 255, 0.98)";
      header.style.borderBottom = "1px solid var(--border-medium)";
    } else {
      header.style.background = "rgba(255, 255, 255, 0.95)";
      header.style.borderBottom = "1px solid var(--border-light)";
    }
  });
}

// Mobile menu toggle (placeholder for future implementation)
function initializeMobileMenu() {
  const mobileMenuBtn = document.querySelector(".mobile-menu-btn");
  const navLinks = document.querySelector(".nav-links");

  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener("click", function () {
      // Future mobile menu implementation
      console.log("Mobile menu toggle");
    });
  }
}

// Dropdown menu functionality
function initializeDropdowns() {
  const dropdownToggles = document.querySelectorAll(".dropdown-toggle");

  dropdownToggles.forEach((toggle) => {
    // Prevent default link behavior
    toggle.addEventListener("click", function (e) {
      e.preventDefault();
    });

    // Handle mobile click behavior
    if (window.innerWidth <= 768) {
      toggle.addEventListener("click", function (e) {
        e.preventDefault();
        const dropdown = this.closest(".nav-dropdown");
        const menu = dropdown.querySelector(".dropdown-menu");

        // Close other dropdowns
        document.querySelectorAll(".nav-dropdown").forEach((otherDropdown) => {
          if (otherDropdown !== dropdown) {
            otherDropdown.classList.remove("active");
          }
        });

        // Toggle current dropdown
        dropdown.classList.toggle("active");
      });
    }
  });

  // Close dropdowns when clicking outside
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".nav-dropdown")) {
      document.querySelectorAll(".nav-dropdown").forEach((dropdown) => {
        dropdown.classList.remove("active");
      });
    }
  });
}

// Handle window resize for dropdown behavior
function handleDropdownResize() {
  window.addEventListener("resize", function () {
    // Remove active class when switching to desktop
    if (window.innerWidth > 768) {
      document.querySelectorAll(".nav-dropdown").forEach((dropdown) => {
        dropdown.classList.remove("active");
      });
    }
  });
}


// Load and display today's meals
async function loadTodaysMeals() {
  try {
    const response = await fetch('/api/meals/today');
    const data = await response.json();

    const loadingDiv = document.getElementById("mealsLoading");
    const noMealsDiv = document.getElementById("noMealsToday");
    const mealsGrid = document.getElementById("todaysMealsGrid");

    loadingDiv.style.display = "none";

    if (data.success && data.meals && data.meals.length > 0) {
      displayTodaysMeals(data.meals);
      noMealsDiv.style.display = "none";
      mealsGrid.style.display = "grid";
    } else {
      noMealsDiv.style.display = "block";
      mealsGrid.style.display = "none";
    }
  } catch (error) {
    console.error("Error loading today's meals:", error);
    document.getElementById("mealsLoading").style.display = "none";
    document.getElementById("noMealsToday").style.display = "block";
    document.getElementById("todaysMealsGrid").style.display = "none";
  }
}

function displayTodaysMeals(meals) {
  const grid = document.getElementById("todaysMealsGrid");
  grid.innerHTML = "";

  // Sort meals by meal type order
  const mealTypeOrder = { breakfast: 1, lunch: 2, dinner: 3, snack: 4 };
  meals.sort(
    (a, b) => (mealTypeOrder[a.type] || 5) - (mealTypeOrder[b.type] || 5)
  );

  meals.forEach((meal) => {
    const mealItem = document.createElement("div");
    mealItem.className = `meal-item ${meal.type} ${
      meal.is_completed ? "completed" : ""
    }`;

    const dishName = getDishName(meal);
    const totalTime = (meal.prep_time || 0) + (meal.cook_time || 0);

    mealItem.innerHTML = `
        <div class="meal-single-row">
          <span class="meal-type-badge ${meal.type}">${meal.type}</span>
          <div class="meal-name" onclick="showMealDetails(${
            meal.meal_id
          })">${dishName}</div>
          <div class="meal-info">
            ${
              totalTime > 0
                ? `<span><i class="fas fa-clock"></i> ${totalTime} min</span>`
                : ""
            }
            ${
              meal.servings
                ? `<span><i class="fas fa-users"></i> ${meal.servings} servings</span>`
                : ""
            }
            ${
              meal.difficulty
                ? `<span><i class="fas fa-chart-line"></i> ${meal.difficulty}</span>`
                : ""
            }
          </div>
          <label class="meal-completion-checkbox">
            <input type="checkbox" ${meal.is_completed ? "checked" : ""} 
                    onchange="toggleMealCompletion(${
                      meal.meal_id
                    }, this.checked, this, '${meal.date}')">
          </label>
        </div>
    `;

    grid.appendChild(mealItem);
  });
}

function getDishName(meal) {
  // Extract actual dish name from meal name
  if (meal.name && meal.name.includes(":")) {
    return meal.name.split(":").slice(1).join(":").trim();
  }
  return meal.name || `Custom ${meal.type}`;
}

async function toggleMealCompletion(
  mealId,
  isCompleted,
  checkbox,
  mealDate = null
) {
  // Prevent completing future meals
  if (mealDate) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const checkDate = new Date(mealDate);
    checkDate.setHours(0, 0, 0, 0);

    if (checkDate > today) {
      alert("You can only complete meals for today or past dates.");
      checkbox.checked = !isCompleted;
      return;
    }
  }
  try {
    const response = await fetch(`/api/meals/${mealId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        is_completed: isCompleted,
      }),
    });

    const data = await response.json();

    if (data.success) {
      // Update the meal item appearance
      const mealItem = checkbox.closest(".meal-item");
      if (isCompleted) {
        mealItem.classList.add("completed");
      } else {
        mealItem.classList.remove("completed");
      }

      // Update the weekly progress wheel
      if (typeof loadWeeklyProgress === "function") {
        loadWeeklyProgress();
      }
    } else {
      // Revert checkbox on error
      checkbox.checked = !isCompleted;
      alert("Failed to update meal completion: " + data.message);
    }
  } catch (error) {
    console.error("Error updating meal completion:", error);
    checkbox.checked = !isCompleted;
    alert("Failed to update meal completion. Please try again.");
  }
}

async function showMealDetails(mealId) {
  try {
    const response = await fetch(`/api/meals/${mealId}`);
    const data = await response.json();

    console.log(data)

    if (data.success) {
      displayMealDetailsModal(data.meal);
    } else {
      alert("Failed to load meal details: " + data.message);
    }
  } catch (error) {
    console.error("Error loading meal details:", error);
    alert("Failed to load meal details. Please try again.");
  }
}

function displayMealDetailsModal(meal) {
  console.log("displaying meal details modal")
  const modalHTML = `
    <div id="mealDetailsModal" class="modal-overlay">
        <div class="modal-content meal-details-modal ${meal.type}">
        <div class="modal-header">
            <div>
            <h3>${meal.name}</h3>
            <p class="meal-meta">${
              meal.type.charAt(0).toUpperCase() + meal.type.slice(1)
            } • ${new Date(meal.date).toLocaleDateString()}</p>
            </div>
            <button class="modal-close" onclick="closeMealDetailsModal()">
            <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            <div class="meal-details-content">
            
            <div class="meal-info-grid">
                ${
                  meal.prep_time
                    ? `<div class="info-item"><i class="fas fa-clock"></i> Prep: ${meal.prep_time} min</div>`
                    : ""
                }
                ${
                  meal.cook_time
                    ? `<div class="info-item"><i class="fas fa-fire"></i> Cook: ${meal.cook_time} min</div>`
                    : ""
                }
                ${
                  meal.servings
                    ? `<div class="info-item"><i class="fas fa-users"></i> Serves: ${meal.servings}</div>`
                    : ""
                }
                ${
                  meal.difficulty
                    ? `<div class="info-item"><i class="fas fa-chart-line"></i> ${
                        meal.difficulty.charAt(0).toUpperCase() +
                        meal.difficulty.slice(1)
                      }</div>`
                    : ""
                }
                ${
                  meal.estimated_cost
                    ? `<div class="info-item"><i class="fas fa-dollar-sign"></i> ${meal.estimated_cost}</div>`
                    : ""
                }
                ${
                  meal.calories_per_serving
                    ? `<div class="info-item"><i class="fas fa-fire-alt"></i> ${meal.calories_per_serving} cal</div>`
                    : ""
                }
            </div>
            ${window.NUTRITION_TRACKING_ENABLED ? `
            <div class="meal-nutrition-section" id="mealNutritionSection-${meal.meal_id}">
                <h4><i class="fas fa-chart-bar"></i> Nutrition Information</h4>
                <div class="nutrition-loading" style="color: var(--text-muted); font-style: italic;">Loading nutrition data...</div>
            </div>
            ` : ''}
            ${
              meal.ingredients && meal.ingredients.length > 0
                ? `
                <div class="meal-section">
                <h4><i class="fas fa-list-ul"></i> Ingredients</h4>
                <div class="ingredients-list">
                    ${meal.ingredients
                      .map(
                        (ingredient) => `
                    <div class="ingredient-item ${
                      ingredient.is_custom ? "custom" : ""
                    }">
                        <span class="ingredient-name">${
                          ingredient.ingredient_name
                        }${
                          ingredient.notes
                            ? ` (${ingredient.notes})`
                            : ""
                        }</span>
                        <span class="ingredient-amount">${
                          convertToMixedFraction(ingredient.quantity)
                        } ${ingredient.unit === 'pcs' || ingredient.unit === 'pc' ? '' : ingredient.unit}</span>
                    </div>
                    `
                      )
                      .join("")}
                </div>
                </div>
            `
                : ""
            }
            ${
              meal.instructions
                ? `
                <div class="meal-section">
                <h4><i class="fas fa-clipboard-list"></i> Instructions</h4>
                <div class="instructions-content">${meal.instructions.replace(
                  /\\n/g,
                  "<br>"
                )}</div>
                </div>
            `
                : ""
            }
            ${
              meal.notes
                ? `
                <div class="meal-section">
                <h4><i class="fas fa-sticky-note"></i> Notes</h4>
                <div class="notes-content">${meal.notes}</div>
                </div>
            `
                : ""
            }
            </div>
            
            <div class="meal-actions">
            ${
              meal.session_id
                ? `
                <button class="btn btn-secondary" onclick="viewPlanDetails(${meal.session_id})">
                <i class="fas fa-calendar-alt"></i> View Full Meal Plan
                </button>
            `
                : ""
            }
            <button class="btn btn-secondary" onclick="saveRecipeFromMeal(${meal.meal_id}, '${meal.name}')">
                <i class="fas fa-bookmark"></i> Save Recipe
            </button>
            <button class="btn btn-primary" onclick="editMeal(${meal.meal_id})">
                <i class="fas fa-edit"></i> Edit Meal
            </button>
            </div>
        </div>
        </div>
    </div>
    `;
  document.body.insertAdjacentHTML("beforeend", modalHTML);
  // Show modal with animation
  setTimeout(() => {
    document.getElementById("mealDetailsModal").classList.add("show");
    // Load nutrition data for the meal if nutrition tracking is enabled
    if (window.NUTRITION_TRACKING_ENABLED) {
      loadMealNutritionForDetails(meal.meal_id);
    }
  }, 10);
}

function closeMealDetailsModal() {
  const modal = document.getElementById("mealDetailsModal");
  if (modal) {
    modal.classList.remove("show");
    setTimeout(() => {
      modal.remove();
    }, 300);
  }
}

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
    return `${wholeNumber} ${fraction}`;
  }
}

// Helper functions for meal modal actions
function viewPlanDetails(sessionId) {
  // Navigate to meal plans page with specific session
  window.location.href = window.HOME_CONFIG?.urls?.mealPlans || "/meal-plans";
}

function saveRecipeFromMeal(mealId, mealName) {
  // Placeholder for save recipe functionality
  alert(`Save recipe functionality will be implemented for: ${mealName}`);
}

function editMeal(mealId) {
  // Placeholder for meal editing functionality
  alert(`Meal editing functionality will be implemented for meal ID: ${mealId}`);
}

function loadMealNutritionForDetails(mealId) {
  // Placeholder for nutrition loading functionality
  console.log(`Loading nutrition data for meal ${mealId}`);
}

// Weekly Meals Progress Wheel Functionality
async function loadWeeklyProgress() {
  console.log("Loading weekly progress...");
  try {
    const now = new Date();
    
    // Calculate current week start (Monday)
    const currentDay = now.getDay();
    const daysFromMonday = currentDay === 0 ? 6 : currentDay - 1; // Handle Sunday as 0
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - daysFromMonday);
    weekStart.setHours(0, 0, 0, 0);
    
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);
    weekEnd.setHours(23, 59, 59, 999);

    // Format week display
    const weekStartFormatted = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    const weekEndFormatted = weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    
    document.getElementById("progressWeek").textContent = `${weekStartFormatted} - ${weekEndFormatted}`;

    // Get goals and progress data for the week
    const startDateStr = weekStart.toISOString().split('T')[0];
    const endDateStr = weekEnd.toISOString().split('T')[0];
    
    console.log("Fetching weekly goals and progress:", { startDateStr, endDateStr });
    
    const [goalsResponse, progressResponse] = await Promise.all([
      fetch(`/api/meal-goals/weekly`),
      fetch(`/api/meal-goals/progress/weekly?start_date=${startDateStr}&end_date=${endDateStr}`),
    ]);

    console.log("API responses:", { 
      goalsStatus: goalsResponse.status, 
      progressStatus: progressResponse.status 
    });

    const goalsData = await goalsResponse.json();
    const progressData = await progressResponse.json();

    console.log("API data:", { goalsData, progressData });

    if (goalsData.success && progressData.success) {
      const goal = goalsData.goals.meals_completed_goal;
      const completed = progressData.progress.completed_meals_count;

      console.log("Updating progress wheel:", { completed, goal });
      updateProgressWheel(completed, goal);
    } else {
      console.warn("API calls failed, using defaults:", { goalsData, progressData });
      // Use default values if API fails (more reasonable for weekly)
      updateProgressWheel(0, 15);
    }
  } catch (error) {
    console.error("Error loading weekly progress:", error);
    // Use default values on error
    updateProgressWheel(0, 15);
  }
}

function updateProgressWheel(completed, goal) {
  const percentage = Math.min((completed / goal) * 100, 100);
  const remaining = Math.max(goal - completed, 0);

  // Update the progress circle
  const circle = document.getElementById("progressCircle");
  const circumference = 2 * Math.PI * 90; // radius = 90
  const dashArray = (percentage / 100) * circumference;
  circle.style.strokeDasharray = `${dashArray} ${circumference}`;

  // Update text elements
  document.getElementById("progressPercentage").textContent = `${Math.round(
    percentage
  )}%`;
  document.getElementById("completedMeals").textContent = completed;
  document.getElementById("goalTarget").textContent = goal;
  document.getElementById("remainingMeals").textContent = remaining;

  // Update progress circle color based on completion
  if (percentage >= 100) {
    circle.style.stroke = "var(--success-color)";
    document.getElementById("progressPercentage").style.color =
      "var(--success-color)";
  } else if (percentage >= 75) {
    circle.style.stroke = "var(--primary-color)";
    document.getElementById("progressPercentage").style.color =
      "var(--primary-color)";
  } else if (percentage >= 50) {
    circle.style.stroke = "var(--warning-color)";
    document.getElementById("progressPercentage").style.color =
      "var(--warning-color)";
  } else {
    circle.style.stroke = "var(--error-color)";
    document.getElementById("progressPercentage").style.color =
      "var(--error-color)";
  }
}

// Initialize all functionality
document.addEventListener("DOMContentLoaded", function () {
  loadDailyTip();
  animateStats();
  initializeScrollEffects();
  initializeMobileMenu();
  initializeDropdowns();
  handleDropdownResize();
  loadTodaysMeals();
  loadWeeklyProgress();
  initializeDailyNutrition();

  // Update time-based greeting every minute
  // setInterval(updateWelcomeMessage, 60000);
});

// Daily nutrition summary variables
let currentNutritionDate = new Date();
let userNutritionGoals = null;

// Initialize daily nutrition summary
function initializeDailyNutrition() {
  const prevBtn = document.getElementById('prevNutritionDate');
  const nextBtn = document.getElementById('nextNutritionDate');
  
  if (prevBtn && nextBtn) {
    prevBtn.addEventListener('click', () => {
      currentNutritionDate.setDate(currentNutritionDate.getDate() - 1);
      loadDailyNutritionSummary();
    });
    
    nextBtn.addEventListener('click', () => {
      currentNutritionDate.setDate(currentNutritionDate.getDate() + 1);
      loadDailyNutritionSummary();
    });
  }
  
  // Load nutrition goals and current date nutrition
  loadNutritionGoals().then(() => {
    loadDailyNutritionSummary();
  });
}

// Load daily nutrition summary
async function loadDailyNutritionSummary() {
  try {
    const dateString = currentNutritionDate.toISOString().split('T')[0];
    const dateDisplay = currentNutritionDate.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
    
    const currentDateElement = document.getElementById('currentNutritionDate');
    if (currentDateElement) {
      currentDateElement.textContent = dateDisplay;
    }
    
    const response = await fetch(`/api/nutrition/daily/${dateString}`);
    const data = await response.json();
    
    const contentElement = document.getElementById('nutritionContent');
    if (!contentElement) return;
    
    if (data.success) {
      const totals = data.daily_totals;
      const meals = data.meals;
      
      let contentHTML = `
        <div class="nutrition-overview">
          <div class="nutrition-stat">
            <span class="nutrition-stat-value">${Math.round(totals.calories)}</span>
            <span class="nutrition-stat-label">Calories</span>
          </div>
          <div class="nutrition-stat">
            <span class="nutrition-stat-value">${Math.round(totals.protein)}<span class="nutrition-stat-unit">g</span></span>
            <span class="nutrition-stat-label">Protein</span>
          </div>
          <div class="nutrition-stat">
            <span class="nutrition-stat-value">${Math.round(totals.carbs)}<span class="nutrition-stat-unit">g</span></span>
            <span class="nutrition-stat-label">Carbs</span>
          </div>
          <div class="nutrition-stat">
            <span class="nutrition-stat-value">${Math.round(totals.fat)}<span class="nutrition-stat-unit">g</span></span>
            <span class="nutrition-stat-label">Fat</span>
          </div>
        </div>
        
        <div class="nutrition-breakdown">
          <div class="nutrition-category">
            <div class="nutrition-category-title">
              <i class="fas fa-dumbbell"></i>
              Macronutrients
            </div>
            <div class="nutrition-category-meals">
              <div class="nutrition-meal-item">
                <span class="nutrition-meal-name">Daily Target</span>
                <div class="nutrition-meal-macros">
                  <div style="font-weight: 600; color: var(--success-color);">Goal: ${userNutritionGoals?.daily_calories || 2000} cal</div>
                  <div style="font-size: 0.7rem; color: var(--text-muted);">${userNutritionGoals?.daily_protein || 150}p/${userNutritionGoals?.daily_carbs || 250}c/${userNutritionGoals?.daily_fat || 70}f</div>
                </div>
              </div>
              <div class="nutrition-meal-item">
                <span class="nutrition-meal-name">Progress</span>
                <div class="nutrition-meal-macros">
                  <div style="font-weight: 600; color: var(--primary-color);">${Math.round((totals.calories / (userNutritionGoals?.daily_calories || 2000)) * 100)}% complete</div>
                  <div style="font-size: 0.7rem; color: var(--text-muted);">Calories consumed</div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="nutrition-category">
            <div class="nutrition-category-title">
              <i class="fas fa-utensils"></i>
              Meal Breakdown
            </div>
            <div class="nutrition-category-meals">
              ${meals.map(meal => `
                <div class="nutrition-meal-item">
                  <div>
                    <div class="nutrition-meal-name">${meal.meal_name}</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted); text-transform: capitalize;">${meal.meal_type}</div>
                  </div>
                  <div class="nutrition-meal-macros">
                    <div style="font-weight: 600; color: var(--primary-color);">${Math.round(meal.nutrition.calories)} cal</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">${Math.round(meal.nutrition.protein)}p/${Math.round(meal.nutrition.carbs)}c/${Math.round(meal.nutrition.fat)}f</div>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
      
      contentElement.innerHTML = contentHTML;
    } else {
      contentElement.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 2rem;">No nutrition data available</div>';
    }
  } catch (error) {
    console.error('Failed to load daily nutrition:', error);
    const contentElement = document.getElementById('nutritionContent');
    if (contentElement) {
      contentElement.innerHTML = '<div style="text-align: center; color: var(--error-color); padding: 2rem;">Failed to load nutrition data</div>';
    }
  }
}

// Load user nutrition goals
async function loadNutritionGoals() {
  try {
    const response = await fetch('/api/nutrition/goals');
    const data = await response.json();
    
    if (data.success) {
      userNutritionGoals = data.goals;
      console.log('Loaded nutrition goals:', userNutritionGoals);
    } else {
      console.warn('Failed to load nutrition goals, using defaults');
      userNutritionGoals = {
        daily_calories: 2000,
        daily_protein: 150,
        daily_carbs: 250,
        daily_fat: 70,
      };
    }
  } catch (error) {
    console.error('Error loading nutrition goals:', error);
    userNutritionGoals = {
      daily_calories: 2000,
      daily_protein: 150,
      daily_carbs: 250,
      daily_fat: 70,
    };
  }
}
