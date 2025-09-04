// Initialize dropdown functionality
function initializeDropdowns() {
  // Get all dropdown toggles
  const dropdownToggles = document.querySelectorAll(".dropdown-toggle");

  dropdownToggles.forEach((toggle) => {
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

// Calendar functionality
let currentDate = new Date();
let currentView = "week";
let mealPlanData = [];
let mealsData = [];

// Load existing meal plans on page load
// Goals functionality
function initializeGoals() {
  // Set current month
  const currentDate = new Date();
  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];
  // Calculate and display current week
  const weekStart = getWeekStartDate(currentDate);
  const weekEnd = new Date(weekStart);
  weekEnd.setDate(weekStart.getDate() + 6);
  const weekStartFormatted = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const weekEndFormatted = weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  document.getElementById("currentWeek").textContent = `${weekStartFormatted} - ${weekEndFormatted}`;

  // Load saved goals from localStorage
  loadGoals();

  // Update progress displays
  updateGoalsProgress();

  // Setup event listeners
  setupGoalsEventListeners();
}

// Helper function to get week start date (Monday)
function getWeekStartDate(date) {
  const daysFromMonday = date.getDay() === 0 ? 6 : date.getDay() - 1;
  const weekStart = new Date(date);
  weekStart.setDate(date.getDate() - daysFromMonday);
  weekStart.setHours(0, 0, 0, 0);
  return weekStart;
}

async function loadGoals() {
  console.log("Loading weekly goals...");
  try {
    const response = await fetch(`/api/meal-goals/weekly`);
    console.log("Goals API response status:", response.status);
    const data = await response.json();
    console.log("Goals API data:", data);

    if (data.success) {
      const goals = data.goals;
      document.getElementById("mealPlansGoal").value = goals.meal_plans_goal;
      document.getElementById("mealsCompletedGoal").value =
        goals.meals_completed_goal;
      document.getElementById("newRecipesGoal").value = goals.new_recipes_goal;
      console.log("Loaded goals:", goals);
    } else {
      console.warn("Failed to load weekly goals:", data.message);
    }

    updateGoalTargets();
  } catch (error) {
    console.error("Error loading weekly goals:", error);
    // Set default weekly values on error
    document.getElementById("mealPlansGoal").value = 2;
    document.getElementById("mealsCompletedGoal").value = 15;
    document.getElementById("newRecipesGoal").value = 3;
    updateGoalTargets();
  }
}

async function saveGoals() {
  console.log("Saving weekly goals...");
  try {
    const goalsData = {
      meal_plans_goal: parseInt(document.getElementById("mealPlansGoal").value),
      meals_completed_goal: parseInt(
        document.getElementById("mealsCompletedGoal").value
      ),
      new_recipes_goal: parseInt(
        document.getElementById("newRecipesGoal").value
      ),
    };

    console.log("Goals data to save:", goalsData);

    const response = await fetch("/api/meal-goals/weekly", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(goalsData),
    });

    console.log("Save goals API response status:", response.status);
    const data = await response.json();
    console.log("Save goals API data:", data);

    if (data.success) {
      updateGoalTargets();
      updateGoalsProgress();

      // Show success message
      const saveBtn = document.getElementById("saveGoalsBtn");
      const originalText = saveBtn.innerHTML;
      saveBtn.innerHTML = '<i class="fas fa-check"></i> Saved!';
      saveBtn.style.background = "var(--success-gradient)";

      setTimeout(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.style.background = "var(--primary-gradient)";
      }, 2000);
    } else {
      console.error("Save goals failed:", data);
      alert("Failed to save weekly goals: " + data.message);
    }
  } catch (error) {
    console.error("Error saving weekly goals:", error);
    alert("Failed to save weekly goals. Please try again.");
  }
}

function resetGoals() {
  document.getElementById("mealPlansGoal").value = 2;
  document.getElementById("mealsCompletedGoal").value = 15;
  document.getElementById("newRecipesGoal").value = 3;

  updateGoalTargets();
  updateGoalsProgress();
}

function updateGoalTargets() {
  document.getElementById("mealPlansTarget").textContent =
    document.getElementById("mealPlansGoal").value;
  document.getElementById("mealsCompletedTarget").textContent =
    document.getElementById("mealsCompletedGoal").value;
  document.getElementById("newRecipesTarget").textContent =
    document.getElementById("newRecipesGoal").value;
}

async function updateGoalsProgress() {
  try {
    // Calculate current week range
    const now = new Date();
    const weekStart = getWeekStartDate(now);
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);
    
    const startDateStr = weekStart.toISOString().split('T')[0];
    const endDateStr = weekEnd.toISOString().split('T')[0];

    // Get weekly progress data from the API
    const response = await fetch(
      `/api/meal-goals/progress/weekly?start_date=${startDateStr}&end_date=${endDateStr}`
    );
    const data = await response.json();

    if (data.success) {
      const progress = data.progress;

      // Update displays with real data from backend
      updateGoalProgress("mealPlans", progress.meal_plans_count, "plans");
      updateGoalProgress(
        "mealsCompleted",
        progress.completed_meals_count,
        "meals"
      );
      updateGoalProgress("newRecipes", progress.new_recipes_count, "recipes");
    } else {
      console.warn("Failed to load weekly progress:", data.message);
      // Set zero values on error
      updateGoalProgress("mealPlans", 0, "plans");
      updateGoalProgress("mealsCompleted", 0, "meals");
      updateGoalProgress("newRecipes", 0, "recipes");
    }
  } catch (error) {
    console.error("Error updating weekly goals progress:", error);
    // Set zero values on error
    updateGoalProgress("mealPlans", 0, "plans");
    updateGoalProgress("mealsCompleted", 0, "meals");
    updateGoalProgress("newRecipes", 0, "recipes");
  }
}

function updateGoalProgress(goalType, current, unit, isBudget = false) {
  const target = parseInt(document.getElementById(`${goalType}Goal`).value);
  const percentage = Math.min((current / target) * 100, 100);

  // Update progress bar
  document.getElementById(`${goalType}Progress`).style.width = `${percentage}%`;

  // Update current count
  const currentText = isBudget ? `$${current}` : `${current} ${unit}`;
  document.getElementById(`${goalType}Count`).textContent = currentText;
}

function setupGoalsEventListeners() {
  // Input change listeners
  document
    .getElementById("mealPlansGoal")
    .addEventListener("input", updateGoalTargets);
  document
    .getElementById("mealsCompletedGoal")
    .addEventListener("input", updateGoalTargets);
  document
    .getElementById("newRecipesGoal")
    .addEventListener("input", updateGoalTargets);

  // Button listeners
  document.getElementById("saveGoalsBtn").addEventListener("click", saveGoals);
  document
    .getElementById("resetGoalsBtn")
    .addEventListener("click", resetGoals);
}

document.addEventListener("DOMContentLoaded", function () {
  initializeDropdowns();
  handleDropdownResize();

  // Set default start date to today and prevent past dates and future dates beyond one month
  const today = new Date();
  const todayString = today.toISOString().split("T")[0];
  const oneMonthFromToday = new Date(today);
  oneMonthFromToday.setMonth(today.getMonth() + 1);
  const maxDateString = oneMonthFromToday.toISOString().split("T")[0];

  const startDateInput = document.getElementById("start_date");
  startDateInput.value = todayString;
  startDateInput.min = todayString;
  startDateInput.max = maxDateString;

  loadMealPlans();
  initializeCalendar();
  initializeGoals();

  // Initialize form handlers for slider and calendar preview
  initializeFormHandlers();


  // Setup generate button
  document
    .getElementById("generateBtn")
    .addEventListener("click", generateMealPlan);

  // Setup show more button for active plans
  const showMoreActiveBtn = document.getElementById("showMoreActiveBtn");
  if (showMoreActiveBtn) {
    showMoreActiveBtn.addEventListener("click", toggleShowAllActive);
  }

  // Setup info popup functionality
  setupInfoPopup();
  
  // Setup meal selection popup event listeners
  setupMealSelectionPopup();
});

function initializeCalendar() {
  // Setup calendar navigation with limits
  document.getElementById("prevMonth").addEventListener("click", async () => {
    const today = new Date();
    const twelveMonthsAgo = new Date(today);
    twelveMonthsAgo.setMonth(today.getMonth() - 12);

    let potentialDate = new Date(currentDate);
    
    if (currentView === "week") {
      // Move back by 7 days (1 week)
      potentialDate.setDate(currentDate.getDate() - 7);
    } else {
      // Move back by 1 month
      potentialDate.setMonth(currentDate.getMonth() - 1);
    }

    if (potentialDate >= twelveMonthsAgo) {
      if (currentView === "week") {
        currentDate.setDate(currentDate.getDate() - 7);
      } else {
        currentDate.setMonth(currentDate.getMonth() - 1);
      }
      clearMealPlanPreview();
      await loadMealsForCalendar();
      updateNavigationButtons();
    }
  });

  document.getElementById("nextMonth").addEventListener("click", async () => {
    const today = new Date();
    const twoMonthsFromNow = new Date(today);
    twoMonthsFromNow.setMonth(today.getMonth() + 2);

    let potentialDate = new Date(currentDate);
    
    if (currentView === "week") {
      // Move forward by 7 days (1 week)
      potentialDate.setDate(currentDate.getDate() + 7);
    } else {
      // Move forward by 1 month
      potentialDate.setMonth(currentDate.getMonth() + 1);
    }

    if (potentialDate <= twoMonthsFromNow) {
      if (currentView === "week") {
        currentDate.setDate(currentDate.getDate() + 7);
      } else {
        currentDate.setMonth(currentDate.getMonth() + 1);
      }
      clearMealPlanPreview();
      await loadMealsForCalendar();
      updateNavigationButtons();
    }
  });

  // Initial button state update
  updateNavigationButtons();

  // Setup view toggle
  document.querySelectorAll(".calendar-view-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      document
        .querySelectorAll(".calendar-view-btn")
        .forEach((b) => b.classList.remove("active"));
      e.target.classList.add("active");
      currentView = e.target.dataset.view;
      updateCalendarTitle();
      renderCalendar();
    });
  });

  renderCalendar();
}

function updateNavigationButtons() {
  const today = new Date();
  const twelveMonthsAgo = new Date(today);
  twelveMonthsAgo.setMonth(today.getMonth() - 12);
  const twoMonthsFromNow = new Date(today);
  twoMonthsFromNow.setMonth(today.getMonth() + 2);

  const prevButton = document.getElementById("prevMonth");
  const nextButton = document.getElementById("nextMonth");

  let potentialPrevDate = new Date(currentDate);
  let potentialNextDate = new Date(currentDate);

  if (currentView === "week") {
    // For week view, check one week back/forward
    potentialPrevDate.setDate(currentDate.getDate() - 7);
    potentialNextDate.setDate(currentDate.getDate() + 7);
  } else {
    // For month view, check one month back/forward
    potentialPrevDate.setMonth(currentDate.getMonth() - 1);
    potentialNextDate.setMonth(currentDate.getMonth() + 1);
  }

  // Disable/enable previous button
  if (potentialPrevDate < twelveMonthsAgo) {
    prevButton.disabled = true;
    prevButton.style.opacity = "0.4";
    prevButton.style.cursor = "not-allowed";
    prevButton.title = currentView === "week" ? 
      "Cannot go back more than 12 months" : 
      "Cannot go back more than 12 months";
  } else {
    prevButton.disabled = false;
    prevButton.style.opacity = "1";
    prevButton.style.cursor = "pointer";
    prevButton.title = currentView === "week" ? "Previous week" : "Previous month";
  }

  // Disable/enable next button
  if (potentialNextDate > twoMonthsFromNow) {
    nextButton.disabled = true;
    nextButton.style.opacity = "0.4";
    nextButton.style.cursor = "not-allowed";
    nextButton.title = currentView === "week" ? 
      "Cannot go forward more than 2 months" : 
      "Cannot go forward more than 2 months";
  } else {
    nextButton.disabled = false;
    nextButton.style.opacity = "1";
    nextButton.style.cursor = "pointer";
    nextButton.title = currentView === "week" ? "Next week" : "Next month";
  }
}

function updateCalendarTitle() {
  const titleElement = document.getElementById("calendarTitle");
  if (currentView === "month") {
    titleElement.textContent = "Your Month at a Glance";
  } else {
    titleElement.textContent = "Your Week at a Glance";
  }
}

function renderCalendar() {
  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  // Update month/year display
  document.getElementById("monthYear").textContent = `${
    monthNames[currentDate.getMonth()]
  } ${currentDate.getFullYear()}`;

  const calendarGrid = document.getElementById("calendarGrid");
  calendarGrid.innerHTML = "";

  // Add day headers
  dayNames.forEach((day) => {
    const dayHeader = document.createElement("div");
    dayHeader.className = "calendar-day-header";
    dayHeader.textContent = day;
    calendarGrid.appendChild(dayHeader);
  });

  if (currentView === "month") {
    renderMonthView(calendarGrid);
  } else {
    renderWeekView(calendarGrid);
  }

  // Update navigation button states after rendering
  updateNavigationButtons();
}

function renderMonthView(container) {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Get first day of month and number of days
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const startDate = new Date(firstDay);
  startDate.setDate(startDate.getDate() - firstDay.getDay());

  // Generate 6 weeks (42 days)
  for (let i = 0; i < 42; i++) {
    const cellDate = new Date(startDate);
    cellDate.setDate(startDate.getDate() + i);

    const dayCell = createDayCell(cellDate, month);
    container.appendChild(dayCell);
  }
}

function renderWeekView(container) {
  // Use same date calculation logic as month view for consistency
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const day = currentDate.getDate();
  
  // Create a date object for the current date being viewed
  const viewingDate = new Date(year, month, day);
  
  // Calculate start of week (Sunday = 0) - same logic as month view
  const startDate = new Date(viewingDate);
  startDate.setDate(viewingDate.getDate() - viewingDate.getDay());

  // Generate 7 days for the week containing currentDate
  for (let i = 0; i < 7; i++) {
    const cellDate = new Date(startDate);
    cellDate.setDate(startDate.getDate() + i);

    const dayCell = createWeekDayCell(cellDate);
    container.appendChild(dayCell);
  }
}

function createWeekDayCell(date) {
  const dayCell = document.createElement("div");
  dayCell.className = "calendar-day week-view";
  dayCell.setAttribute("data-date", date.toISOString().split("T")[0]);

  // Use timezone-aware today detection
  const serverToday = window.serverToday;
  const isToday = serverToday ? 
    date.toISOString().split("T")[0] === serverToday : 
    date.toDateString() === new Date().toDateString();

  if (isToday) {
    dayCell.classList.add("today");
  }

  // Day number
  const dayNumber = document.createElement("div");
  dayNumber.className = "calendar-day-number";
  dayNumber.textContent = date.getDate();
  dayCell.appendChild(dayNumber);

  // Meals container
  const mealsContainer = document.createElement("div");
  mealsContainer.className = "calendar-meals";

  // Find meals for this date
  const dayMeals = getMealsForDate(date);

  // Group meals by type
  const mealsByType = {
    breakfast: [],
    lunch: [],
    dinner: [],
    snack: [],
  };

  dayMeals.forEach((meal) => {
    if (mealsByType[meal.type]) {
      mealsByType[meal.type].push(meal);
    }
  });

  // Create fixed slots for each meal type
  const mealTypes = ["breakfast", "lunch", "dinner"];

  console.log('Creating meal slots for date:', date, 'with meals:', mealsByType);

  mealTypes.forEach((type) => {
    const mealSlot = document.createElement("div");
    mealSlot.className = `calendar-meal-slot ${type}`;

    const meals = mealsByType[type];
    
    if (meals.length > 0) {
      mealSlot.classList.add("has-meal");

      // Get the dish name from the first meal (or combine if multiple)
      const dishName =
        meals.length === 1
          ? getDishName(meals[0])
          : `${getDishName(meals[0])} +${meals.length - 1} more`;

      // Use server-provided future check (timezone-aware)
      const isFuture = meals[0].is_future;

      mealSlot.innerHTML = `
        <div class="calendar-meal-type">${type}</div>
        <div class="meal-completion">
            <input type="checkbox" class="meal-checkbox" ${
              meals[0].is_completed ? "checked" : ""
            } ${
        isFuture ? "disabled" : ""
      } onclick="event.stopPropagation(); toggleMealCompletion(${
        meals[0].meal_id
      }, this.checked, '${date.toISOString().split("T")[0]}')">
            <div class="calendar-meal-name">${dishName}</div>
        </div>
        `;

      if (meals[0].is_completed) {
        mealSlot.classList.add("completed");
      }

      mealSlot.title = meals
        .map((meal) => `${type}: ${getDishName(meal)}`)
        .join("\n");

      // Add click handler for individual meal selection
      mealSlot.addEventListener("click", (e) => {
        e.stopPropagation(); // Prevent day click handler
        if (meals.length === 1) {
          showMealDetails(meals[0]);
        } else {
          showMealSelectionModal(date, meals);
        }
      });

      // Add hover effect for clickable meals
      mealSlot.style.cursor = "pointer";
    } else {
      // Empty slot - invisible but maintains spacing
      mealSlot.classList.add("empty-slot");
      // No content - completely blank
    }

    mealsContainer.appendChild(mealSlot);
  });

  console.log(`Total meal slots appended: ${mealTypes.length}, container children: ${mealsContainer.children.length}`);

  if (dayMeals.length > 0) {
    dayCell.classList.add("has-meals");
  }

  dayCell.appendChild(mealsContainer);

  // Click handler for day details
  dayCell.addEventListener("click", () => showDayDetails(date, dayMeals));

  return dayCell;
}

function getDishName(meal) {
  // Extract actual dish name from meal name
  // Meal names might be in format "Day X Breakfast: Dish Name" or just "Dish Name"
  if (meal.name.includes(":")) {
    return meal.name.split(":").slice(1).join(":").trim();
  }
  return meal.name;
}

function createDayCell(date, currentMonth, isWeekView = false) {
  const dayCell = document.createElement("div");
  dayCell.className = "calendar-day";
  dayCell.setAttribute("data-date", date.toISOString().split("T")[0]);

  const isCurrentMonth = date.getMonth() === currentMonth;
  
  // Get timezone-aware today info from server data
  const serverToday = window.mealsData && window.mealsData.length > 0 ? 
    window.serverToday : null;
  const isToday = serverToday ? 
    date.toISOString().split("T")[0] === serverToday : 
    date.toDateString() === new Date().toDateString();

  if (isToday) {
    dayCell.classList.add("today");
  }

  if (!isCurrentMonth && !isWeekView) {
    dayCell.classList.add("other-month");
  }

  // Day number
  const dayNumber = document.createElement("div");
  dayNumber.className = "calendar-day-number";
  dayNumber.textContent = date.getDate();
  dayCell.appendChild(dayNumber);

  // Meals container
  const mealsContainer = document.createElement("div");
  mealsContainer.className = "calendar-meals";

  // Find meals for this date
  const dayMeals = getMealsForDate(date);

  // Group meals by type for consistent positioning
  const mealsByType = {
    breakfast: [],
    lunch: [],
    dinner: [],
    snack: [],
  };

  dayMeals.forEach((meal) => {
    if (mealsByType[meal.type]) {
      mealsByType[meal.type].push(meal);
    }
  });

  // Create fixed slots for each meal type (month view)
  const mealTypes = ["breakfast", "lunch", "dinner"];
  let hasAnyMeals = false;

  mealTypes.forEach((type) => {
    const meals = mealsByType[type];
    
    if (meals.length > 0) {
      hasAnyMeals = true;
      
      // Show first meal for this type
      const meal = meals[0];
      const mealElement = document.createElement("div");
      mealElement.className = `calendar-meal ${meal.type} ${
        meal.is_completed ? "completed" : ""
      }`;

      // Create checkbox
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.className = "meal-checkbox";
      checkbox.checked = meal.is_completed;
      checkbox.disabled = meal.is_future;
      checkbox.addEventListener("click", (e) => {
        e.stopPropagation();
        if (!checkbox.disabled) {
          toggleMealCompletion(meal.meal_id, checkbox.checked, date.toISOString().split("T")[0]);
        }
      });

      // Create meal name text
      const mealNameText = document.createElement("span");
      mealNameText.className = "meal-name-text";
      
      // Show count if multiple meals of same type
      const displayName = meals.length === 1 ? 
        getDishName(meal) : 
        `${getDishName(meal)} +${meals.length - 1}`;
        
      mealNameText.textContent = displayName;
      mealNameText.title = `${meal.type}: ${meal.name}`;

      // Make meal name clickable for details
      mealNameText.style.cursor = "pointer";
      mealNameText.addEventListener("click", (e) => {
        e.stopPropagation();
        if (meals.length === 1) {
          showMealDetails(meal);
        } else {
          showMealSelectionModal(date, meals);
        }
      });

      // Create meal header (checkbox + name)
      const mealHeader = document.createElement("div");
      mealHeader.className = "meal-header";
      mealHeader.appendChild(checkbox);
      mealHeader.appendChild(mealNameText);

      mealElement.appendChild(mealHeader);
      mealsContainer.appendChild(mealElement);
    } else {
      // Create invisible empty slot for month view (maintains spacing)
      const mealElement = document.createElement("div");
      mealElement.className = `calendar-meal ${type} empty-meal-slot`;
      // Empty content - completely blank but maintains height
      mealsContainer.appendChild(mealElement);
    }
  });

  if (hasAnyMeals) {
    dayCell.classList.add("has-meals");
  }

  dayCell.appendChild(mealsContainer);

  // Add click handler
  dayCell.addEventListener("click", () => {
    showDayDetails(date, dayMeals);
  });

  return dayCell;
}

function getMealsForDate(date) {
  const dateStr = date.toISOString().split("T")[0];

  // Return meals from the global mealsData for this date
  return (window.mealsData || mealsData || []).filter(
    (meal) => meal.date === dateStr
  );
}

function getDayName(dayNumber) {
  const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  if (dayNumber <= 7) {
    return dayNames[dayNumber - 1];
  }
  return `Day ${dayNumber}`;
}

function showDayDetails(date, meals) {
  if (meals.length === 0) {
    showEmptyDayPopup(date);
    return;
  }

  // Show meal selection modal if multiple meals, or direct meal view if one meal
  if (meals.length === 1) {
    showMealDetails(meals[0]);
  } else {
    showMealSelectionModal(date, meals);
  }
}

async function loadMealPlans() {
  try {
    console.log("Loading meal plans...");
    const response = await fetch("/api/meal-plans");
    const data = await response.json();

    console.log("Meal plans response:", data);

    if (data.success && data.plans && data.plans.length > 0) {
      console.log(`Found ${data.plans.length} meal plans`);

      // Store meal plan data for plan management
      mealPlanData = data.plans;

      displayMealPlans(data.plans);
      document.getElementById("emptyState").style.display = "none";
    } else {
      console.log("No meal plans found or error:", data);
      mealPlanData = [];
      document.getElementById("emptyState").style.display = "block";
    }

    // Load meals for calendar regardless of meal plans
    await loadMealsForCalendar();
  } catch (error) {
    console.error("Error loading meal plans:", error);
    mealPlanData = [];
    document.getElementById("emptyState").style.display = "block";
    await loadMealsForCalendar();
  }
}

async function loadMealsForCalendar() {
  try {
    // Get date range for current calendar view
    const startDate = new Date(
      currentDate.getFullYear(),
      currentDate.getMonth(),
      1
    );
    const endDate = new Date(
      currentDate.getFullYear(),
      currentDate.getMonth() + 1,
      0
    );

    // Extend range to cover full weeks
    const calendarStart = new Date(startDate);
    calendarStart.setDate(startDate.getDate() - startDate.getDay());
    const calendarEnd = new Date(endDate);
    calendarEnd.setDate(endDate.getDate() + (6 - endDate.getDay()));

    const startDateStr = calendarStart.toISOString().split("T")[0];
    const endDateStr = calendarEnd.toISOString().split("T")[0];

    console.log("Loading meals for calendar:", startDateStr, "to", endDateStr);

    const response = await fetch(
      `/api/meals?start_date=${startDateStr}&end_date=${endDateStr}`
    );
    const data = await response.json();

    if (data.success) {
      console.log(`Found ${data.meals.length} meals for calendar`);

      // Store meals data globally for calendar
      window.mealsData = data.meals || [];
      window.serverToday = data.user_today || null; // Store timezone-aware "today"
      mealsData = data.meals || [];

      // Update calendar with new meal data
      if (typeof renderCalendar === "function") {
        renderCalendar();
      }
    } else {
      console.log("No meals found or error:", data);
      window.mealsData = [];
      mealsData = [];
      if (typeof renderCalendar === "function") {
        renderCalendar();
      }
    }
  } catch (error) {
    console.error("Error loading meals for calendar:", error);
    window.mealsData = [];
    mealsData = [];
    if (typeof renderCalendar === "function") {
      renderCalendar();
    }
  }
}

// Global state for plan categorization
let allPlans = [];
let showingAllActive = false;

function displayMealPlans(plans) {
  console.log("Displaying meal plans:", plans);
  allPlans = plans;
  
  // Categorize plans by status
  const activePlans = plans.filter(plan => plan.status === 'active');
  const completedPlans = plans.filter(plan => plan.status === 'completed');
  const expiredPlans = plans.filter(plan => plan.status === 'expired');
  
  console.log("Categorized plans:", { activePlans, completedPlans, expiredPlans });
  
  // Display categorized plans
  displayCategorizedPlans('active', activePlans);
  displayCategorizedPlans('completed', completedPlans);
  displayCategorizedPlans('expired', expiredPlans);
  
  // Update plan counts
  updatePlanCounts(activePlans.length, completedPlans.length, expiredPlans.length);
  
  // Show/hide empty state
  const emptyState = document.getElementById("emptyState");
  if (plans.length === 0) {
    emptyState.style.display = "block";
  } else {
    emptyState.style.display = "none";
  }
}

function displayCategorizedPlans(category, plans) {
  const gridId = `${category}PlansGrid`;
  const grid = document.getElementById(gridId);
  
  if (!grid) {
    console.error(`Grid not found: ${gridId}`);
    return;
  }
  
  grid.innerHTML = "";
  
  // For active plans, show only first 3 initially
  let plansToShow = plans;
  if (category === 'active' && !showingAllActive && plans.length > 3) {
    plansToShow = plans.slice(0, 3);
    // Show the "show more" button
    const showMoreBtn = document.getElementById("showMoreActiveBtn");
    if (showMoreBtn) {
      showMoreBtn.style.display = "block";
      showMoreBtn.classList.remove("expanded");
      showMoreBtn.querySelector("span").textContent = "Show All Active Plans";
    }
  } else if (category === 'active') {
    // Handle button state for showing all or 3 or fewer plans
    const showMoreBtn = document.getElementById("showMoreActiveBtn");
    if (showMoreBtn) {
      if (plans.length > 3 && showingAllActive) {
        // Showing all plans - display "Show Fewer" button
        showMoreBtn.style.display = "block";
        showMoreBtn.classList.add("expanded");
        showMoreBtn.querySelector("span").textContent = "Show Fewer Plans";
      } else {
        // 3 or fewer plans total - hide button
        showMoreBtn.style.display = "none";
        showMoreBtn.classList.remove("expanded");
      }
    }
  }
  
  plansToShow.forEach((plan) => {
    const planCard = createPlanCard(plan);
    grid.appendChild(planCard);
  });
}

function updatePlanCounts(activeCount, completedCount, expiredCount) {
  const activeCountEl = document.getElementById("activePlansCount");
  const completedCountEl = document.getElementById("completedPlansCount");
  const expiredCountEl = document.getElementById("expiredPlansCount");
  
  if (activeCountEl) activeCountEl.textContent = `(${activeCount})`;
  if (completedCountEl) completedCountEl.textContent = `(${completedCount})`;
  if (expiredCountEl) expiredCountEl.textContent = `(${expiredCount})`;
}

// Show more/fewer active plans functionality
function toggleShowAllActive() {
  showingAllActive = !showingAllActive;
  const activePlans = allPlans.filter(plan => plan.status === 'active');
  displayCategorizedPlans('active', activePlans);
}

// Toggle plan category visibility
function togglePlanCategory(category) {
  const categorySection = document.querySelector(`.${category}-plans`);
  const toggleBtn = document.getElementById(`toggle${category.charAt(0).toUpperCase() + category.slice(1)}Btn`);
  
  if (!categorySection || !toggleBtn) return;
  
  const isHidden = categorySection.style.display === 'none';
  
  if (isHidden) {
    categorySection.style.display = 'block';
    toggleBtn.classList.add('active');
    toggleBtn.querySelector('span').textContent = `Hide ${category.charAt(0).toUpperCase() + category.slice(1)} Plans`;
  } else {
    categorySection.style.display = 'none';
    toggleBtn.classList.remove('active');
    toggleBtn.querySelector('span').textContent = `Show ${category.charAt(0).toUpperCase() + category.slice(1)} Plans`;
  }
}

function formatDateString(dateString) {
  // Parse YYYY-MM-DD format manually
  const [year, month, day] = dateString.split('-');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[parseInt(month) - 1]} ${parseInt(day)}`;
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

function createPlanCard(plan) {
  const card = document.createElement("div");
  card.className = "plan-card";
  card.onclick = () => viewPlanDetails(plan.plan_id);

  // Format dates manually from YYYY-MM-DD string
  const startDate = formatDateString(plan.start_date);
  const endDate = formatDateString(plan.end_date);
  
  // If it's a single day plan, only show the date once
  const dateDisplay = plan.start_date === plan.end_date ? startDate : `${startDate} - ${endDate}`;

  // Create fuzzy matching summary HTML if available
  let fuzzyMatchingHtml = '';
  if (plan.fuzzy_matching_summary) {
    const summary = plan.fuzzy_matching_summary;
    const utilizationRate = summary.pantry_utilization_rate || 0;
    const utilizationColor = utilizationRate >= 70 ? 'success' : utilizationRate >= 50 ? 'warning' : 'error';
    
    fuzzyMatchingHtml = `
      <div class="fuzzy-summary">
        <div class="fuzzy-header">
          <i class="fas fa-brain"></i>
          <span>Pantry Analysis</span>
        </div>
        <div class="fuzzy-stats">
          <span class="stat success">
            <i class="fas fa-check"></i> ${summary.auto_matched}
          </span>
          <span class="stat warning">
            <i class="fas fa-question"></i> ${summary.confirm_needed}
          </span>
          <span class="stat error">
            <i class="fas fa-exclamation"></i> ${summary.missing}
          </span>
        </div>
        <div class="utilization-bar">
          <div class="utilization-fill ${utilizationColor}" style="width: ${utilizationRate}%"></div>
          <span class="utilization-text">${utilizationRate.toFixed(1)}% utilized</span>
        </div>
      </div>
    `;
  } else {
    // Show placeholder for meal plans without pantry analysis
    fuzzyMatchingHtml = `
      <div class="fuzzy-summary no-analysis">
        <div class="fuzzy-header">
          <i class="fas fa-info-circle"></i>
          <span>Pantry Analysis</span>
        </div>
        <div class="fuzzy-placeholder">
          <span class="placeholder-text">Pantry analysis not enabled for this meal plan</span>
        </div>
      </div>
    `;
  }

  card.innerHTML = `
    <div class="plan-header">
        <div>
        <h3 class="plan-name">${plan.plan_name}</h3>
        <p class="plan-dates">${dateDisplay}</p>
        </div>
        <span class="plan-status status-${plan.status}">${plan.status}</span>
    </div>
    
    <div class="plan-details">
        <div class="plan-detail">
        <i class="fas fa-calendar-alt"></i>
        <span>${plan.total_days} days</span>
        </div>
        <div class="plan-detail">
        <i class="fas fa-leaf"></i>
        <span>${plan.dietary_preference || "No restrictions"}</span>
        </div>
        <div class="plan-detail">
        <i class="fas fa-dollar-sign"></i>
        <span>${
          plan.budget_limit ? "$" + plan.budget_limit : "No budget limit"
        }</span>
        </div>
        <div class="plan-detail">
        <i class="fas fa-clock"></i>
        <span>${plan.max_cooking_time} min/day</span>
        </div>
    </div>
    
    ${fuzzyMatchingHtml}
    
    <div class="plan-actions">
        <button class="btn-view" onclick="event.stopPropagation(); viewPlanDetails(${
          plan.plan_id
        })">
        <i class="fas fa-eye"></i> View Details
        </button>
        <button class="btn-smart-list" onclick="event.stopPropagation(); generateSmartShoppingList(${
          plan.plan_id
        })" ${plan.fuzzy_matching_summary ? '' : 'disabled title="No pantry analysis available"'}>
        <i class="fas fa-brain"></i> Smart List
        </button>
    </div>
    `;

  return card;
}

async function generateSmartShoppingList(planId) {
  try {
    // Show loading state
    const button = document.querySelector(`button[onclick*="generateSmartShoppingList(${planId})"]`);
    const originalContent = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    button.disabled = true;

    // Generate smart shopping list
    const response = await fetch('/api/shopping/smart-generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        meal_plan_session_id: planId,
        auto_confirm_threshold: 85.0
      })
    });

    const result = await response.json();

    if (result.success) {
      // Show confirmation modal with results
      showSmartListModal(result);
    } else {
      throw new Error(result.message || 'Failed to generate smart shopping list');
    }

  } catch (error) {
    console.error('Error generating smart shopping list:', error);
    showNotification('Failed to generate smart shopping list: ' + error.message, 'error');
  } finally {
    // Restore button
    const button = document.querySelector(`button[onclick*="generateSmartShoppingList(${planId})"]`);
    if (button) {
      button.innerHTML = originalContent;
      button.disabled = false;
    }
  }
}

function showSmartListModal(result) {
  const { shopping_items, confirmed_matches, matching_summary, cost_analysis, recommendations } = result;

  const modalHtml = `
    <div id="smartListModal" class="modal-overlay">
      <div class="modal-content smart-list-modal">
        <div class="modal-header">
          <h3><i class="fas fa-brain"></i> Smart Shopping List Generated</h3>
          <button class="modal-close" onclick="closeSmartListModal()">&times;</button>
        </div>
        
        <div class="modal-body">
          <!-- Cost Analysis Summary -->
          <div class="cost-analysis">
            <h4><i class="fas fa-dollar-sign"></i> Cost Analysis</h4>
            <div class="cost-stats">
              <div class="cost-stat">
                <span class="label">Recipe Total:</span>
                <span class="value">$${cost_analysis.total_recipe_cost.toFixed(2)}</span>
              </div>
              <div class="cost-stat">
                <span class="label">Shopping Needed:</span>
                <span class="value">$${cost_analysis.shopping_list_cost.toFixed(2)}</span>
              </div>
              <div class="cost-stat savings">
                <span class="label">Pantry Savings:</span>
                <span class="value">$${cost_analysis.estimated_savings.toFixed(2)}</span>
              </div>
            </div>
          </div>

          <!-- Matching Summary -->
          <div class="matching-summary">
            <h4><i class="fas fa-chart-pie"></i> Pantry Matching Results</h4>
            <div class="summary-grid">
              <div class="summary-item success">
                <i class="fas fa-check"></i>
                <span>${matching_summary.auto_matched} Auto-matched</span>
              </div>
              <div class="summary-item warning">
                <i class="fas fa-question"></i>
                <span>${matching_summary.confirm_needed} Need Confirmation</span>
              </div>
              <div class="summary-item error">
                <i class="fas fa-exclamation"></i>
                <span>${matching_summary.missing} Missing from Pantry</span>
              </div>
            </div>
            <div class="utilization-display">
              <span>Pantry Utilization: <strong>${cost_analysis.pantry_utilization_rate.toFixed(1)}%</strong></span>
            </div>
          </div>

          <!-- Items that need confirmation -->
          ${matching_summary.confirm_needed > 0 ? createConfirmationSection(shopping_items) : ''}

          <!-- Recommendations -->
          ${recommendations.length > 0 ? createRecommendationsSection(recommendations) : ''}

          <!-- Shopping Items List -->
          <div class="shopping-preview">
            <h4><i class="fas fa-shopping-cart"></i> Items to Buy (${shopping_items.length})</h4>
            <div class="items-list">
              ${shopping_items.map(item => `
                <div class="item-preview ${item.match_type}">
                  <div class="item-indicator">
                    <i class="fas fa-${item.match_type === 'auto' ? 'check' : item.match_type === 'confirm' ? 'question' : 'exclamation'}"></i>
                  </div>
                  <div class="item-info">
                    <span class="item-name">${item.quantity_needed} ${item.unit} ${item.ingredient_name}</span>
                    <span class="item-cost">$${item.estimated_cost || '0.00'}</span>
                  </div>
                  ${item.pantry_match ? `
                    <div class="pantry-match-info">
                      <i class="fas fa-warehouse"></i>
                      <span>Found ${item.pantry_match.available} in pantry (${(item.pantry_match.confidence || 0).toFixed(1)}% match)</span>
                    </div>
                  ` : ''}
                </div>
              `).join('')}
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="closeSmartListModal()">
            <i class="fas fa-times"></i> Close
          </button>
          <button class="btn btn-primary" onclick="createShoppingTrip(${result.generation_id})">
            <i class="fas fa-cart-plus"></i> Create Shopping Trip
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.insertAdjacentHTML('beforeend', modalHtml);

  // Show modal with animation
  setTimeout(() => {
    document.getElementById('smartListModal').classList.add('show');
  }, 10);

  // Close on outside click
  const modal = document.getElementById('smartListModal');
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeSmartListModal();
    }
  });
}

function createConfirmationSection(shoppingItems) {
  const itemsNeedingConfirmation = shoppingItems.filter(item => item.match_type === 'confirm');
  
  if (itemsNeedingConfirmation.length === 0) return '';

  return `
    <div class="confirmation-section">
      <h4><i class="fas fa-question-circle"></i> Items Need Your Confirmation</h4>
      <div class="confirmation-items">
        ${itemsNeedingConfirmation.map(item => `
          <div class="confirmation-item" data-ingredient="${item.ingredient_name}">
            <div class="item-question">
              <i class="fas fa-question"></i>
              <span>Use <strong>${item.pantry_match.available} ${item.pantry_match.item_name}</strong> for <strong>${item.ingredient_name}</strong>?</span>
              <span class="confidence">(${(item.pantry_match.confidence || 0).toFixed(1)}% match)</span>
            </div>
            <div class="confirmation-buttons">
              <button class="btn btn-sm btn-success" onclick="confirmPantryMatch('${item.ingredient_name}', true)">
                <i class="fas fa-check"></i> Yes
              </button>
              <button class="btn btn-sm btn-danger" onclick="confirmPantryMatch('${item.ingredient_name}', false)">
                <i class="fas fa-times"></i> No
              </button>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function createRecommendationsSection(recommendations) {
  return `
    <div class="recommendations-section">
      <h4><i class="fas fa-lightbulb"></i> Recommendations</h4>
      <ul class="recommendations-list">
        ${recommendations.map(rec => `<li><i class="fas fa-check"></i> ${rec}</li>`).join('')}
      </ul>
    </div>
  `;
}

function closeSmartListModal() {
  const modal = document.getElementById('smartListModal');
  if (modal) {
    modal.classList.remove('show');
    setTimeout(() => modal.remove(), 300);
  }
}

async function confirmPantryMatch(ingredientName, isConfirmed) {
  const confirmationItem = document.querySelector(`[data-ingredient="${ingredientName}"]`);
  
  if (isConfirmed) {
    confirmationItem.innerHTML = `
      <div class="confirmed-item success">
        <i class="fas fa-check"></i>
        <span>Confirmed: Will use pantry item for <strong>${ingredientName}</strong></span>
      </div>
    `;
  } else {
    confirmationItem.innerHTML = `
      <div class="confirmed-item error">
        <i class="fas fa-times"></i>
        <span>Rejected: Will buy new <strong>${ingredientName}</strong></span>
      </div>
    `;
  }
}

async function createShoppingTrip(generationId) {
  try {
    // You can implement this to integrate with your shopping trip system
    // For now, just redirect to shopping trip page with a notification
    showNotification('Smart shopping list ready! Create a new shopping trip to use it.', 'success');
    closeSmartListModal();
    
    // Optional: redirect to shopping trip page
    // window.location.href = '/shopping-trip';
  } catch (error) {
    console.error('Error creating shopping trip:', error);
    showNotification('Failed to create shopping trip', 'error');
  }
}

function showNotification(message, type = 'info') {
  // Create notification element (reuse from meal plan details)
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.innerHTML = `
    <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'exclamation-triangle' : 'info'}"></i>
    <span>${message}</span>
  `;
  
  // Add to page
  document.body.appendChild(notification);
  
  // Show notification
  setTimeout(() => notification.classList.add('show'), 100);
  
  // Auto-hide after 3 seconds
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => {
      if (document.body.contains(notification)) {
        document.body.removeChild(notification);
      }
    }, 300);
  }, 3000);
}

function highlightMealPlanDates(startDate, days) {
  // Clear any existing preview highlights
  clearMealPlanPreview();

  const startDateObj = new Date(startDate);

  // Highlight each day in the range
  for (let i = 0; i < days; i++) {
    const currentDate = new Date(startDateObj);
    currentDate.setDate(startDateObj.getDate() + i);

    const dateStr = currentDate.toISOString().split("T")[0];
    const calendarCell = document.querySelector(`[data-date="${dateStr}"]`);

    if (calendarCell) {
      calendarCell.classList.add("meal-plan-preview");

      // Add day number indicator
      if (i === 0) {
        calendarCell.classList.add("preview-start");
      } else if (i === days - 1) {
        calendarCell.classList.add("preview-end");
      } else {
        calendarCell.classList.add("preview-middle");
      }
    }
  }
}

function clearMealPlanPreview() {
  // Remove all preview classes from calendar cells
  const previewCells = document.querySelectorAll(".meal-plan-preview");
  previewCells.forEach((cell) => {
    cell.classList.remove(
      "meal-plan-preview",
      "preview-start",
      "preview-end",
      "preview-middle"
    );
  });
}

async function checkForMealConflicts(startDate, days) {
  try {
    const startDateObj = new Date(startDate);
    const endDateObj = new Date(startDateObj);
    endDateObj.setDate(startDateObj.getDate() + days - 1);

    const startDateStr = startDateObj.toISOString().split("T")[0];
    const endDateStr = endDateObj.toISOString().split("T")[0];

    const response = await fetch(
      `/api/meals?start_date=${startDateStr}&end_date=${endDateStr}`
    );
    const data = await response.json();

    if (data.success && data.meals && data.meals.length > 0) {
      // Group meals by date and type
      const conflictsByDate = {};
      let lockedMeals = [];
      let unlockedMeals = [];

      data.meals.forEach((meal) => {
        if (!conflictsByDate[meal.date]) {
          conflictsByDate[meal.date] = [];
        }
        conflictsByDate[meal.date].push(meal);

        const mealInfo = `${meal.date} (${meal.type})`;
        if (meal.is_locked) {
          lockedMeals.push(mealInfo);
        } else {
          unlockedMeals.push(mealInfo);
        }
      });

      return {
        hasConflicts: true,
        conflictsByDate,
        lockedMeals,
        unlockedMeals,
        conflictingDates: Object.keys(conflictsByDate),
        totalConflicts: data.meals.length
      };
    }

    return { hasConflicts: false };
  } catch (error) {
    console.error("Error checking for meal conflicts:", error);
    return { hasConflicts: false };
  }
}

function resetGenerateButton(btn, spinner, icon, text) {
  btn.disabled = false;
  spinner.style.display = "none";
  icon.style.display = "block";
  text.textContent = "Generate Meal Plan";
}

function showMealConflictWarning(conflicts) {
  const conflictDates = conflicts.conflictingDates
    .map(date => new Date(date).toLocaleDateString())
    .join(', ');

  let conflictDetails = [];
  if (conflicts.lockedMeals.length > 0) {
    conflictDetails.push(`Locked meals: ${conflicts.lockedMeals.join(', ')}`);
  }
  if (conflicts.unlockedMeals.length > 0) {
    conflictDetails.push(`Existing meals: ${conflicts.unlockedMeals.join(', ')}`);
  }

  const detailText = conflictDetails.length > 0 ? `\n\n${conflictDetails.join('\n')}` : '';

  const popupHTML = `
    <div id="mealConflictWarning" class="modal-overlay">
        <div class="modal-content date-limit-popup">
        <div class="modal-body">
            <div class="warning-content">
            <div class="warning-icon">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <h3 class="warning-title">Meal Plan Conflict Detected</h3>
            <p class="warning-message">
                Cannot generate meal plan because there are existing meals on the selected dates: <strong>${conflictDates}</strong>.
                <br><br>
                You have ${conflicts.totalConflicts} existing meal(s) in this date range. Please choose a different date range or delete the conflicting meals first.
            </p>
            <div class="warning-actions">
                <button class="btn btn-secondary" onclick="closeMealConflictWarning(); navigateToConflictDate('${conflicts.conflictingDates[0]}')">
                <i class="fas fa-calendar-alt"></i> View Conflicts
                </button>
                <button class="btn btn-primary" onclick="closeMealConflictWarning()">
                <i class="fas fa-check"></i> Got It
                </button>
            </div>
            </div>
        </div>
        </div>
    </div>
    `;

  document.body.insertAdjacentHTML("beforeend", popupHTML);

  // Show popup with animation
  setTimeout(() => {
    document.getElementById("mealConflictWarning").classList.add("show");
  }, 10);

  // Close popup when clicking outside
  const popup = document.getElementById("mealConflictWarning");
  popup.addEventListener("click", (e) => {
    if (e.target === popup) {
      closeMealConflictWarning();
    }
  });

  // Close popup with Escape key
  document.addEventListener("keydown", handleMealConflictEscape);
}

function handleMealConflictEscape(e) {
  if (e.key === "Escape") {
    const popup = document.getElementById("mealConflictWarning");
    if (popup) {
      closeMealConflictWarning();
    }
  }
}

function closeMealConflictWarning() {
  const popup = document.getElementById("mealConflictWarning");
  if (popup) {
    popup.classList.remove("show");
    document.removeEventListener("keydown", handleMealConflictEscape);
    setTimeout(() => {
      popup.remove();
    }, 300);
  }
}

function navigateToConflictDate(dateStr) {
  // Update calendar to show the conflict date
  const conflictDate = new Date(dateStr);
  currentDate = new Date(conflictDate.getFullYear(), conflictDate.getMonth(), 1);
  renderCalendar();
  updateNavigationButtons();

  // Scroll to calendar
  const calendarSection = document.querySelector(".calendar-section");
  if (calendarSection) {
    calendarSection.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
}

async function generateMealPlan() {
  const btn = document.getElementById("generateBtn");
  const spinner = document.getElementById("spinner");
  const icon = document.getElementById("generateIcon");
  const text = document.getElementById("generateText");

  // Show loading state for validation
  btn.disabled = true;
  spinner.style.display = "block";
  icon.style.display = "none";
  text.textContent = "Validating...";

  try {
    const formData = new FormData(document.getElementById("generateForm"));

    // Validate required fields
    const startDate = formData.get("start_date");
    if (!startDate) {
      alert("Please select a start date for your meal plan.");
      resetGenerateButton(btn, spinner, icon, text);
      return;
    }

    const days = parseInt(formData.get("days"));
    
    // Check for existing meals in the date range before proceeding
    const conflictCheck = await checkForMealConflicts(startDate, days);
    if (conflictCheck.hasConflicts) {
      showMealConflictWarning(conflictCheck);
      resetGenerateButton(btn, spinner, icon, text);
      return;
    }

    // Validate that start date is not more than one month in the future
    const selectedDate = new Date(startDate);
    const today = new Date();
    const oneMonthFromToday = new Date(today);
    oneMonthFromToday.setMonth(today.getMonth() + 1);

    if (selectedDate > oneMonthFromToday) {
      showDateLimitWarning();
      resetGenerateButton(btn, spinner, icon, text);
      return;
    }

    // Reset button state and show meal selection popup
    resetGenerateButton(btn, spinner, icon, text);
    showMealSelectionPopup(formData, days);

  } catch (error) {
    console.error("Validation error:", error);
    alert("An error occurred during validation. Please try again.");
    resetGenerateButton(btn, spinner, icon, text);
  }
}

// Meal Selection Popup Functions
function showMealSelectionPopup(formData, days) {
  const overlay = document.getElementById('mealSelectionOverlay');
  const grid = document.getElementById('mealSelectionGrid');
  
  // Generate day selection grid
  grid.innerHTML = '';
  const startDate = new Date(formData.get('start_date'));
  
  for (let i = 0; i < days; i++) {
    const currentDate = new Date(startDate);
    currentDate.setDate(startDate.getDate() + i);
    
    const dayDiv = document.createElement('div');
    dayDiv.className = 'day-selection';
    dayDiv.innerHTML = `
      <div class="day-header">
        <span class="day-title">Day ${i + 1} - ${currentDate.toLocaleDateString('en-US', { 
          weekday: 'short', 
          month: 'short', 
          day: 'numeric' 
        })}</span>
        <span class="day-select-all" data-day="${i + 1}">Select All</span>
      </div>
      <div class="meal-checkboxes">
        ${['breakfast', 'lunch', 'dinner'].map(mealType => `
          <div class="meal-checkbox-item ${mealType}">
            <input type="checkbox" id="meal_${i + 1}_${mealType}" 
                   data-day="${i + 1}" data-meal="${mealType}" checked>
            <label for="meal_${i + 1}_${mealType}">${mealType}</label>
          </div>
        `).join('')}
      </div>
    `;
    grid.appendChild(dayDiv);
  }
  
  // Store form data for later use
  window.pendingMealPlanData = formData;
  console.log('Stored pendingMealPlanData:', window.pendingMealPlanData);
  
  // Show popup
  overlay.classList.add('active');
  
  // Update summary
  updateMealSelectionSummary();
}

function updateMealSelectionSummary() {
  const checkboxes = document.querySelectorAll('#mealSelectionGrid input[type="checkbox"]:checked');
  const selectedCount = checkboxes.length;
  
  let cookingTime = 60; // default
  if (window.pendingMealPlanData && typeof window.pendingMealPlanData.get === 'function') {
    cookingTime = parseInt(window.pendingMealPlanData.get('cooking_time') || 60);
  }
  
  const estimatedTime = selectedCount * (cookingTime / 3); // Rough estimate
  
  document.getElementById('selectedMealCount').textContent = selectedCount;
  document.getElementById('estimatedTime').textContent = Math.round(estimatedTime);
  
  // Enable/disable confirm button
  const confirmBtn = document.getElementById('confirmMealSelection');
  confirmBtn.disabled = selectedCount === 0;
}

async function confirmMealSelection() {
  const checkboxes = document.querySelectorAll('#mealSelectionGrid input[type="checkbox"]:checked');
  
  if (checkboxes.length === 0) {
    alert('Please select at least one meal to generate.');
    return;
  }
  
  // Collect selected meals
  const selectedMeals = [];
  const dayMeals = {};
  
  checkboxes.forEach(checkbox => {
    const day = parseInt(checkbox.dataset.day);
    const meal = checkbox.dataset.meal;
    
    if (!dayMeals[day]) {
      dayMeals[day] = [];
    }
    dayMeals[day].push(meal);
  });
  
  // Convert to array format
  for (const [day, meals] of Object.entries(dayMeals)) {
    selectedMeals.push({
      day: parseInt(day),
      meals: meals
    });
  }
  
  // Store data before closing popup (which clears the global variable)
  const formDataToUse = window.pendingMealPlanData;
  
  console.log('About to generate with:', {
    formData: formDataToUse,
    selectedMeals: selectedMeals
  });
  
  // Close popup and start generation
  closeMealSelectionPopup();
  
  // Call the actual generation function
  await generateMealPlanWithSelection(formDataToUse, selectedMeals);
}

async function generateMealPlanWithSelection(formData, selectedMeals) {
  const btn = document.getElementById("generateBtn");
  const spinner = document.getElementById("spinner");
  const icon = document.getElementById("generateIcon");
  const text = document.getElementById("generateText");

  // Show loading state
  btn.disabled = true;
  spinner.style.display = "block";
  icon.style.display = "none";
  text.textContent = "Generating...";

  try {
    if (!formData) {
      throw new Error("Form data is missing");
    }

    const data = {
      start_date: formData.get('start_date'),
      days: parseInt(formData.get("days")),
      dietary_preference: formData.get("dietary_preference"),
      budget: formData.get("budget") ? parseFloat(formData.get("budget")) : null,
      cooking_time: parseInt(formData.get("cooking_time")),
      minimal_cooking_sessions: formData.has("minimal_cooking_sessions"),
      selected_meals: selectedMeals
    };

    console.log('Sending data:', data);
    
    const response = await fetch("/api/generate-meal-plan", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    const result = await response.json();
    console.log('Result:', result);

    if (result.success) {
      alert(`Meal plan generated successfully! Created ${result.created_meals.length} meals.`);
      await loadMealPlans();
      
      if (result.session_id) {
        viewPlanDetails(result.session_id);
      }
    } else {
      // Check if this is a subscription limit error
      if (result.requires_upgrade && typeof showUpgradeModal === 'function') {
        showUpgradeModal(
          result.limit_type, 
          result.current_limit, 
          result.message
        );
      } else {
        alert("Error generating meal plan: " + result.message);
      }
    }
  } catch (error) {
    console.error("Error generating meal plan:", error);
    alert("Failed to generate meal plan. Please try again.");
  } finally {
    resetGenerateButton(btn, spinner, icon, text);
    clearMealPlanPreview();
  }
}

function closeMealSelectionPopup() {
  const overlay = document.getElementById('mealSelectionOverlay');
  overlay.classList.remove('active');
  window.pendingMealPlanData = null;
}

function setupMealSelectionPopup() {
  // Close button
  document.getElementById('closeMealSelection').addEventListener('click', closeMealSelectionPopup);
  
  // Cancel button
  document.getElementById('cancelMealSelection').addEventListener('click', closeMealSelectionPopup);
  
  // Confirm button
  document.getElementById('confirmMealSelection').addEventListener('click', confirmMealSelection);
  
  // Quick select buttons
  document.querySelectorAll('.btn-quick-select').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const mode = e.currentTarget.dataset.mode;
      const checkboxes = document.querySelectorAll('#mealSelectionGrid input[type="checkbox"]');
      
      switch (mode) {
        case 'all':
          checkboxes.forEach(cb => cb.checked = true);
          break;
        case 'lunch-dinner':
          checkboxes.forEach(cb => {
            cb.checked = cb.dataset.meal === 'lunch' || cb.dataset.meal === 'dinner';
          });
          break;
        case 'clear':
          checkboxes.forEach(cb => cb.checked = false);
          break;
      }
      
      updateMealSelectionSummary();
    });
  });
  
  // Close on overlay click
  document.getElementById('mealSelectionOverlay').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
      closeMealSelectionPopup();
    }
  });
  
  // Delegate event for day select all and checkboxes (since they're dynamically created)
  document.getElementById('mealSelectionGrid').addEventListener('click', (e) => {
    if (e.target.classList.contains('day-select-all')) {
      const day = e.target.dataset.day;
      const dayCheckboxes = document.querySelectorAll(`input[data-day="${day}"]`);
      const allChecked = Array.from(dayCheckboxes).every(cb => cb.checked);
      
      dayCheckboxes.forEach(cb => cb.checked = !allChecked);
      updateMealSelectionSummary();
    }
  });
  
  // Listen for checkbox changes
  document.getElementById('mealSelectionGrid').addEventListener('change', (e) => {
    if (e.target.type === 'checkbox') {
      updateMealSelectionSummary();
    }
  });
}

function viewPlanDetails(planId) {
  // Navigate to plan details page
  window.location.href = `/meal-plans/${planId}`;
}

function showMealSelectionModal(date, meals) {
  const dateStr = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  const modalHTML = `
    <div id="mealSelectionModal" class="modal-overlay">
        <div class="modal-content">
        <div class="modal-header">
            <h3>Select a Meal - ${dateStr}</h3>
            <button class="modal-close" onclick="closeMealSelectionModal()">
            <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            <div class="meals-list">
            ${meals
              .map(
                (meal) => `
                <div class="meal-row" onclick="showMealDetails(${JSON.stringify(
                  meal
                ).replace(/"/g, "&quot;")})">
                    <div class="meal-row-type">
                        <div class="meal-type-badge ${meal.type}">
                            <i class="fas fa-${getMealIcon(meal.type)}"></i>
                            ${meal.type.charAt(0).toUpperCase() + meal.type.slice(1)}
                        </div>
                    </div>
                    <div class="meal-row-content">
                        <div class="meal-row-name">${meal.name}</div>
                        ${
                          meal.prep_time
                            ? `<div class="meal-row-time">
                                <i class="fas fa-clock"></i>
                                ${meal.prep_time + (meal.cook_time || 0)} min total
                               </div>`
                            : ""
                        }
                    </div>
                    <div class="meal-row-action">
                        <i class="fas fa-chevron-right"></i>
                    </div>
                </div>
            `
              )
              .join("")}
            </div>
        </div>
        </div>
    </div>
    `;

  document.body.insertAdjacentHTML("beforeend", modalHTML);

  // Show modal with animation
  setTimeout(() => {
    document.getElementById("mealSelectionModal").classList.add("show");
  }, 10);
}

function closeMealSelectionModal() {
  const modal = document.getElementById("mealSelectionModal");
  if (modal) {
    modal.classList.remove("show");
    setTimeout(() => {
      modal.remove();
    }, 300);
  }
}

async function showMealDetails(meal) {
  // Close meal selection modal if it exists
  closeMealSelectionModal();

  console.log(meal.meal_id)

  try {
    // Fetch detailed meal information
    const response = await fetch(`/api/meals/${meal.meal_id}`);
    const data = await response.json();

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

function getMealIcon(mealType) {
  const icons = {
    breakfast: "coffee",
    lunch: "hamburger",
    dinner: "utensils",
    snack: "cookie-bite",
  };
  return icons[mealType] || "utensils";
}

function editMeal(mealId) {
  // Placeholder for meal editing functionality
  alert(
    `Meal editing functionality will be implemented here for meal ID: ${mealId}`
  );
  // This could open an edit modal or navigate to an edit page
}

async function toggleMealCompletion(mealId, isCompleted, mealDate = null) {
  // Server-side validation will handle timezone-aware future date checking
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
      // Update the meal data in memory
      if (window.mealsData) {
        const meal = window.mealsData.find((m) => m.meal_id === mealId);
        if (meal) {
          meal.is_completed = isCompleted;
        }
      }

      // Refresh calendar view to show updated completion status
      renderCalendar();

      // Update goals progress if we're on the goals section
      if (typeof updateGoalsProgress === "function") {
        updateGoalsProgress();
      }
    } else {
      alert("Failed to update meal completion: " + data.message);
      // Revert checkbox state on error
      const checkbox = document.querySelector(`input[onclick*="${mealId}"]`);
      if (checkbox) {
        checkbox.checked = !isCompleted;
      }
    }
  } catch (error) {
    console.error("Error updating meal completion:", error);
    alert("Failed to update meal completion. Please try again.");
    // Revert checkbox state on error
    const checkbox = document.querySelector(`input[onclick*="${mealId}"]`);
    if (checkbox) {
      checkbox.checked = !isCompleted;
    }
  }
}

function showEmptyDayPopup(date) {
  const dateStr = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  // Store the selected date globally for use when navigating
  window.selectedEmptyDate = date.toISOString().split("T")[0];

  // Check if date is in the past using timezone-aware today
  const selectedDateStr = date.toISOString().split("T")[0];
  const serverToday = window.serverToday; // This should be set from the meals API
  const isPastDate = serverToday && selectedDateStr < serverToday;

  const generateButtonClass = isPastDate ? "btn btn-secondary" : "btn btn-primary";
  const generateButtonDisabled = isPastDate ? "disabled" : "";
  const generateButtonTitle = isPastDate ? "Cannot generate meal plans for past dates" : "";
  const generateButtonOnClick = isPastDate ? "" : "onclick=\"closeEmptyDayPopupAndNavigate()\"";
  const generateButtonIcon = isPastDate ? "fas fa-ban" : "fas fa-magic";
  const generateButtonText = isPastDate ? "Cannot Generate" : "Generate Meal Plan";

  const popupHTML = `
    <div id="emptyDayPopup" class="modal-overlay">
        <div class="modal-content empty-day-popup">
        <div class="modal-body">
            <div class="empty-day-content">
            <div class="empty-day-icon">
                <i class="fas fa-calendar-plus"></i>
            </div>
            <h3 class="empty-day-title">No meals planned for ${dateStr}</h3>
            <p class="empty-day-message">
                ${isPastDate 
                  ? "This date is in the past. You can only generate meal plans for today or future dates."
                  : "Generate a meal plan to see your meals for this day and start planning your delicious week ahead!"
                }
            </p>
            <div class="empty-day-actions">
                <button class="${generateButtonClass}" ${generateButtonDisabled} title="${generateButtonTitle}" ${generateButtonOnClick}>
                <i class="${generateButtonIcon}"></i> ${generateButtonText}
                </button>
                <button class="btn btn-secondary" onclick="closeEmptyDayPopup()">
                <i class="fas fa-times"></i> Close
                </button>
            </div>
            </div>
        </div>
        </div>
    </div>
    `;

  document.body.insertAdjacentHTML("beforeend", popupHTML);

  // Show popup with animation
  setTimeout(() => {
    document.getElementById("emptyDayPopup").classList.add("show");
  }, 10);

  // Auto-close after 4 seconds if user doesn't interact
  setTimeout(() => {
    const popup = document.getElementById("emptyDayPopup");
    if (popup && !popup.classList.contains("user-interacted")) {
      closeEmptyDayPopupAndNavigate();
    }
  }, 4000);

  // Mark as user-interacted when they hover or click
  const popup = document.getElementById("emptyDayPopup");
  popup.addEventListener("mouseenter", () => {
    popup.classList.add("user-interacted");
  });

  // Close popup when clicking outside
  popup.addEventListener("click", (e) => {
    if (e.target === popup) {
      closeEmptyDayPopup();
    }
  });

  // Close popup with Escape key
  document.addEventListener("keydown", handleEmptyDayEscape);
}

function handleEmptyDayEscape(e) {
  if (e.key === "Escape") {
    const popup = document.getElementById("emptyDayPopup");
    if (popup) {
      closeEmptyDayPopup();
      document.removeEventListener("keydown", handleEmptyDayEscape);
    }
  }
}

function closeEmptyDayPopup() {
  const popup = document.getElementById("emptyDayPopup");
  if (popup) {
    popup.classList.remove("show");
    document.removeEventListener("keydown", handleEmptyDayEscape);
    setTimeout(() => {
      popup.remove();
    }, 300);
  }
}

function closeEmptyDayPopupAndNavigate() {
  closeEmptyDayPopup();

  // Wait for popup to close, then scroll to generate section
  setTimeout(() => {
    const generateSection = document.querySelector(".generate-section");
    if (generateSection) {
      generateSection.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });

      // Set the start date to the selected empty date
      if (window.selectedEmptyDate) {
        const startDateInput = document.getElementById("start_date");
        if (startDateInput) {
          startDateInput.value = window.selectedEmptyDate;

          // Trigger calendar preview update
          const event = new Event("change");
          startDateInput.dispatchEvent(event);
        }
      }

      // Optional: Focus on the form for better UX
      setTimeout(() => {
        const daysInput = document.getElementById("days");
        if (daysInput) {
          daysInput.focus();
        }
      }, 800);
    }
  }, 300);
}

function showDateLimitWarning() {
  const today = new Date();
  const oneMonthFromToday = new Date(today);
  oneMonthFromToday.setMonth(today.getMonth() + 1);

  const maxDateStr = oneMonthFromToday.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const popupHTML = `
    <div id="dateLimitWarning" class="modal-overlay">
        <div class="modal-content date-limit-popup">
        <div class="modal-body">
            <div class="warning-content">
            <div class="warning-icon">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <h3 class="warning-title">Date Too Far in Future</h3>
            <p class="warning-message">
                You can only plan meals up to one month in advance. Please select a date on or before <strong>${maxDateStr}</strong>.
            </p>
            <div class="warning-actions">
                <button class="btn btn-primary" onclick="closeDateLimitWarning()">
                <i class="fas fa-check"></i> Got It
                </button>
            </div>
            </div>
        </div>
        </div>
    </div>
    `;

  document.body.insertAdjacentHTML("beforeend", popupHTML);

  // Show popup with animation
  setTimeout(() => {
    document.getElementById("dateLimitWarning").classList.add("show");
  }, 10);

  // Close popup when clicking outside
  const popup = document.getElementById("dateLimitWarning");
  popup.addEventListener("click", (e) => {
    if (e.target === popup) {
      closeDateLimitWarning();
    }
  });

  // Close popup with Escape key
  document.addEventListener("keydown", handleDateLimitEscape);
}

function handleDateLimitEscape(e) {
  if (e.key === "Escape") {
    const popup = document.getElementById("dateLimitWarning");
    if (popup) {
      closeDateLimitWarning();
      document.removeEventListener("keydown", handleDateLimitEscape);
    }
  }
}

function closeDateLimitWarning() {
  const popup = document.getElementById("dateLimitWarning");
  if (popup) {
    popup.classList.remove("show");
    document.removeEventListener("keydown", handleDateLimitEscape);
    setTimeout(() => {
      popup.remove();
    }, 300);
  }
}

// Handle range input for number of days and calendar preview
function initializeFormHandlers() {
  const daysRange = document.getElementById("days");
  const daysValue = document.getElementById("daysValue");
  const startDateInput = document.getElementById("start_date");

  function updateCalendarPreview() {
    const startDate = startDateInput?.value;
    const days = parseInt(daysRange?.value || 7);

    if (startDate && days) {
      highlightMealPlanDates(startDate, days);
    } else {
      clearMealPlanPreview();
    }
  }

  if (daysRange && daysValue) {
    daysRange.addEventListener("input", function () {
      const value = parseInt(this.value);
      daysValue.textContent = value;
      updateCalendarPreview();
    });
  }

  if (startDateInput) {
    startDateInput.addEventListener("change", updateCalendarPreview);
  }
}

function setupInfoPopup() {
  const infoIcon = document.getElementById('cookingSessionsInfo');
  const popup = document.getElementById('cookingSessionsPopup');
  let isPopupVisible = false;

  if (!infoIcon || !popup) return;

  // Show popup on click
  infoIcon.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (isPopupVisible) {
      hidePopup();
    } else {
      showPopup();
    }
  });

  // Hide popup when clicking outside
  document.addEventListener('click', (e) => {
    if (isPopupVisible && !popup.contains(e.target) && !infoIcon.contains(e.target)) {
      hidePopup();
    }
  });

  // Hide popup on escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && isPopupVisible) {
      hidePopup();
    }
  });

  function showPopup() {
    popup.classList.add('show');
    isPopupVisible = true;
  }

  function hidePopup() {
    popup.classList.remove('show');
    isPopupVisible = false;
  }
}

// Function to load and display nutrition data for a meal
async function loadMealNutrition(mealId) {
  try {
    const response = await fetch(`/api/nutrition/${mealId}`);
    const data = await response.json();
    
    const nutritionElement = document.getElementById(`nutrition-${mealId}`);
    if (!nutritionElement) return;
    
    if (data.success && data.nutrition) {
      const nutrition = data.nutrition;
      let nutritionHTML = '';
      
      // Add calories if available
      if (nutrition.calories) {
        nutritionHTML += `<span class="nutrition-item nutrition-calories">${Math.round(nutrition.calories)} cal</span>`;
      }
      
      // Add macros if available
      const macros = [];
      if (nutrition.macros.protein) {
        macros.push(`${Math.round(nutrition.macros.protein)}p`);
      }
      if (nutrition.macros.carbs) {
        macros.push(`${Math.round(nutrition.macros.carbs)}c`);
      }
      if (nutrition.macros.fat) {
        macros.push(`${Math.round(nutrition.macros.fat)}f`);
      }
      
      if (macros.length > 0) {
        nutritionHTML += `<span class="nutrition-item nutrition-macros">${macros.join('/')}</span>`;
      }
      
      if (nutritionHTML) {
        nutritionElement.innerHTML = nutritionHTML;
      } else {
        nutritionElement.innerHTML = '<span style="opacity: 0.5; font-size: 0.5rem; font-style: italic;">No nutrition</span>';
      }
    } else {
      nutritionElement.innerHTML = '<span style="opacity: 0.5; font-size: 0.5rem; font-style: italic;">No nutrition</span>';
    }
  } catch (error) {
    console.error('Failed to load nutrition:', error);
    const nutritionElement = document.getElementById(`nutrition-${mealId}`);
    if (nutritionElement) {
      nutritionElement.innerHTML = '<span style="opacity: 0.5; font-size: 0.5rem;">-</span>';
    }
  }
}

// Function to load and display detailed nutrition data for meal details modal
async function loadMealNutritionForDetails(mealId) {
  try {
    const response = await fetch(`/api/nutrition/${mealId}`);
    const data = await response.json();
    
    const nutritionSection = document.getElementById(`mealNutritionSection-${mealId}`);
    if (!nutritionSection) return;
    
    if (data.success && data.nutrition) {
      const nutrition = data.nutrition;
      
      let nutritionHTML = '<h4><i class="fas fa-chart-bar"></i> Nutrition Information</h4>';
      nutritionHTML += '<div class="nutrition-details-grid">';
      
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
      
      nutritionHTML += '</div>';
      
      // Add serving info if available
      if (nutrition.servings || nutrition.serving_size) {
        nutritionHTML += '<div class="nutrition-serving-info">';
        if (nutrition.servings) {
          nutritionHTML += `<span class="serving-info">Servings: ${nutrition.servings}</span>`;
        }
        if (nutrition.serving_size) {
          nutritionHTML += `<span class="serving-info">Serving Size: ${nutrition.serving_size}</span>`;
        }
        nutritionHTML += '</div>';
      }
      
      nutritionSection.innerHTML = nutritionHTML;
    } else {
      nutritionSection.innerHTML = `
        <h4><i class="fas fa-chart-bar"></i> Nutrition Information</h4>
        <div style="color: var(--text-muted); font-style: italic; padding: 1rem 0;">
          No nutrition data available for this meal.
        </div>
      `;
    }
  } catch (error) {
    console.error('Failed to load nutrition for details:', error);
    const nutritionSection = document.getElementById(`mealNutritionSection-${mealId}`);
    if (nutritionSection) {
      nutritionSection.innerHTML = `
        <h4><i class="fas fa-chart-bar"></i> Nutrition Information</h4>
        <div style="color: var(--error-color); font-style: italic; padding: 1rem 0;">
          Failed to load nutrition data.
        </div>
      `;
    }
  }
}

// Save recipe from meal functionality
async function saveRecipeFromMeal(mealId, mealName) {
  try {
    const response = await fetch(`/api/saved-recipes/save-from-meal/${mealId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        recipe_name: mealName,
        notes: `Saved from meal plan on ${new Date().toLocaleDateString()}`
      })
    });

    const data = await response.json();
    
    if (data.success) {
      showSuccessMessage(`Recipe "${data.recipe_name}" saved successfully!`);
      // Close meal details modal
      closeMealDetailsModal();
    } else {
      if (data.existing_recipe_id) {
        const userConfirm = confirm(`${data.message} Would you like to view your saved recipes instead?`);
        if (userConfirm) {
          window.location.href = '/recipes';
        }
      } else {
        showErrorMessage(data.message);
      }
    }
  } catch (error) {
    console.error('Error saving recipe:', error);
    showErrorMessage('Failed to save recipe. Please try again.');
  }
}

// Utility functions for showing messages
function showSuccessMessage(message) {
  showMessage(message, 'success');
}

function showErrorMessage(message) {
  showMessage(message, 'error');
}

function showMessage(message, type) {
  // Remove existing messages
  const existingMessages = document.querySelectorAll('.temp-message');
  existingMessages.forEach(msg => msg.remove());

  // Create message element
  const messageDiv = document.createElement('div');
  messageDiv.className = `temp-message ${type}`;
  messageDiv.style.cssText = `
    position: fixed;
    top: 100px;
    left: 50%;
    transform: translateX(-50%);
    padding: 15px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    z-index: 10000;
    max-width: 400px;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  `;

  // Set background color based on type
  if (type === 'success') {
    messageDiv.style.background = '#10b981';
  } else if (type === 'info') {
    messageDiv.style.background = '#3b82f6';
  } else {
    messageDiv.style.background = '#ef4444';
  }

  let icon = 'fa-exclamation-triangle';
  if (type === 'success') icon = 'fa-check-circle';
  if (type === 'info') icon = 'fa-info-circle';

  messageDiv.innerHTML = `
    <i class="fas ${icon}"></i>
    ${message}
  `;

  document.body.appendChild(messageDiv);

  // Animate in
  messageDiv.style.opacity = '0';
  messageDiv.style.transform = 'translateX(-50%) translateY(-20px)';
  setTimeout(() => {
    messageDiv.style.transition = 'all 0.3s ease';
    messageDiv.style.opacity = '1';
    messageDiv.style.transform = 'translateX(-50%) translateY(0)';
  }, 10);

  // Remove after 5 seconds
  setTimeout(() => {
    messageDiv.style.opacity = '0';
    messageDiv.style.transform = 'translateX(-50%) translateY(-20px)';
    setTimeout(() => {
      messageDiv.remove();
    }, 300);
  }, 5000);
}


// Add pulse animation for typing indicator
const style = document.createElement('style');
style.textContent = `
  @keyframes pulse {
    0%, 100% { opacity: 0.3; transform: scale(0.8); }
    50% { opacity: 1; transform: scale(1); }
  }
`;
document.head.appendChild(style);

