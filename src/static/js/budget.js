// Initialize charts and functionality
let spendingChart;

// Initialize spending chart
function initSpendingChart() {
  const ctx = document.getElementById("spendingChart").getContext("2d");

  spendingChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Daily Spending",
          data: [],
          backgroundColor: "#667eea",
          borderColor: "#667eea",
          borderWidth: 1,
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        x: {
          grid: {
            display: false,
          },
          border: {
            display: false,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: "rgba(0, 0, 0, 0.1)",
          },
          border: {
            display: false,
          },
          ticks: {
            callback: function (value) {
              return "$" + value.toFixed(2);
            },
          },
        },
      },
      interaction: {
        intersect: false,
        mode: "index",
      },
      onClick: handleChartClick,
    },
  });
}

// Update budget stats
function updateBudgetStats(budget, spent) {
  const remaining = budget - spent;
  const dailyAvg = spent / new Date().getDate();

  document.getElementById("monthlyBudget").textContent =
    "$" + budget.toLocaleString();
  document.getElementById("totalSpent").textContent = "$" + spent.toFixed(2);
  document.getElementById("remaining").textContent = "$" + remaining.toFixed(2);
  document.getElementById("avgDaily").textContent = "$" + dailyAvg.toFixed(2);

  // Update stat card colors based on remaining budget
  const remainingCard = document
    .querySelector("#remaining")
    .closest(".stat-card");
  remainingCard.className =
    "stat-card " + (remaining > 0 ? "warning" : "error");
}

// Handle budget settings form
function handleBudgetSettings(event) {
  event.preventDefault();

  const budget = parseFloat(
    document.getElementById("monthlyBudgetInput").value
  );
  const period = document.getElementById("budgetPeriod").value;
  const threshold = parseInt(document.getElementById("alertThreshold").value);
  const categoryLimits = document.getElementById("categoryLimit").value;

  // In production, send this to your API
  console.log("Budget settings updated:", {
    budget,
    period,
    threshold,
    categoryLimits,
  });

  // Update the display
  updateBudgetStats(budget, 743.5); // Use current spent amount

  // Show success message (you could implement a toast notification)
  alert("Budget settings saved successfully!");
}

// Load real data from API
async function loadBudgetData() {
  try {
    const response = await fetch("/api/budget/overview");
    if (response.ok) {
      const data = await response.json();
      updateBudgetStats(data.monthly_budget, data.total_spent);

      // Update settings form with current values
      document.getElementById("monthlyBudgetInput").value = data.monthly_budget;
      document.getElementById("alertThreshold").value = data.alert_threshold;
      document.getElementById("budgetPeriod").value = data.budget_period;
    }
  } catch (error) {
    console.error("Error loading budget data:", error);
  }
}

// Load spending trends from API
async function loadSpendingTrends(period = "7d") {
  console.log("DEBUG: Loading spending trends for period:", period);
  try {
    const response = await fetch(
      `/api/budget/spending-trends?period=${period}`
    );
    console.log("DEBUG: Response status:", response.status);
    if (response.ok) {
      const data = await response.json();
      console.log("DEBUG: Received data:", data);

      if (data.trends && data.trends.length > 0) {
        // Store trends data globally for chart click handler
        window.currentTrendsData = data.trends;

        // Update labels and data for bar chart
        const labels = data.trends.map((item) => item.label || item.date);
        const amounts = data.trends.map((item) => item.amount);

        spendingChart.data.labels = labels;
        spendingChart.data.datasets[0].data = amounts;

        // Update label based on period
        let label = "Daily Spending";
        if (period === "1m" || period === "3m") {
          label = "Weekly Spending";
        } else if (period === "1y") {
          label = "Monthly Spending";
        }

        spendingChart.data.datasets[0].label = label;
        console.log("DEBUG: Updated chart with", amounts.length, "data points");
        spendingChart.update("active");
      } else {
        console.log("DEBUG: No trends data received");
      }
    } else {
      console.error("DEBUG: Response not OK:", response.status);
    }
  } catch (error) {
    console.error("Error loading spending trends:", error);
  }
}

// Handle budget settings form
async function handleBudgetSettings(event) {
  event.preventDefault();

  const budget = parseFloat(
    document.getElementById("monthlyBudgetInput").value
  );
  const period = document.getElementById("budgetPeriod").value;
  const threshold = parseInt(document.getElementById("alertThreshold").value);
  const categoryLimits = document.getElementById("categoryLimit").value;

  try {
    const response = await fetch("/api/budget/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        monthly_budget: budget,
        budget_period: period,
        alert_threshold: threshold,
        category_limits: categoryLimits,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      alert("Budget settings saved successfully!");

      // Reload budget data to reflect changes
      loadBudgetData();
    } else {
      const errorData = await response.json();
      alert("Failed to save budget settings: " + errorData.error);
    }
  } catch (error) {
    console.error("Error saving budget settings:", error);
    alert("An error occurred while saving budget settings.");
  }
}

// Shopping Details Modal Functions
let currentPeriod = "1m";

function handleChartClick(event, elements) {
  if (elements.length > 0) {
    const element = elements[0];
    const dataIndex = element.index;

    // We need to get the actual date, not the label
    // The date is stored in the trends data when we load it
    let clickedDate = null;

    // Get the date from our stored trends data
    if (window.currentTrendsData && window.currentTrendsData[dataIndex]) {
      clickedDate = window.currentTrendsData[dataIndex].date;
    }

    if (clickedDate) {
      // Show loading state
      showShoppingModal(
        "Loading...",
        "Loading shopping details...",
        [],
        0,
        0,
        0
      );

      // Fetch detailed spending data for this period
      loadShoppingDetails(currentPeriod, clickedDate);
    } else {
      console.error("Could not determine clicked date");
    }
  }
}

async function loadShoppingDetails(period, date) {
  console.log("DEBUG: Loading shopping details for", period, date);
  try {
    const response = await fetch(
      `/api/budget/spending-details?period=${period}&date=${date}`
    );
    console.log("DEBUG: Shopping details response status:", response.status);

    if (response.ok) {
      const data = await response.json();
      console.log("DEBUG: Shopping details data:", data);

      showShoppingModal(
        data.period_label,
        `Shopping Summary for ${data.period_label}`,
        data.trips,
        data.total_amount,
        data.total_trips,
        data.total_items
      );
    } else {
      console.error("DEBUG: Failed to load shopping details:", response.status);
      showShoppingModal(
        "Error",
        "Failed to load shopping details",
        [],
        0,
        0,
        0
      );
    }
  } catch (error) {
    console.error("Error loading shopping details:", error);
    showShoppingModal("Error", "Failed to load shopping details", [], 0, 0, 0);
  }
}

function showShoppingModal(
  title,
  subtitle,
  trips,
  totalAmount,
  totalTrips,
  totalItems
) {
  // Update modal title and summary
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalTotalAmount").textContent =
    "$" + totalAmount.toFixed(2);
  document.getElementById("modalTotalTrips").textContent = totalTrips;
  document.getElementById("modalTotalItems").textContent = totalItems;

  // Clear and populate trips container
  const tripsContainer = document.getElementById("tripsContainer");
  tripsContainer.innerHTML = "";

  if (trips.length === 0) {
    tripsContainer.innerHTML =
      '<p style="text-align: center; color: var(--text-secondary); padding: 2rem;">No shopping trips found for this period.</p>';
  } else {
    trips.forEach((trip) => {
      const tripCard = document.createElement("div");
      tripCard.className = "trip-card";

      // Simplified version - just store name and item count
      tripCard.innerHTML = `
        <div class="trip-header">
            <div class="trip-info">
            <h4>${trip.store_name}</h4>
            <div class="trip-meta">${trip.datetime}</div>
            </div>
            <div class="trip-stats">
            <div class="trip-total">$${trip.trip_total.toFixed(2)}</div>
            <div class="trip-items">${trip.items.length} items</div>
            </div>
        </div>
        `;

      tripsContainer.appendChild(tripCard);
    });
  }

  // Show modal
  document.getElementById("shoppingModal").style.display = "flex";

  // Close modal when clicking overlay
  document.getElementById("shoppingModal").onclick = function (e) {
    if (e.target === this) {
      closeShoppingModal();
    }
  };
}

function closeShoppingModal() {
  document.getElementById("shoppingModal").style.display = "none";
}

// Update current period when chart data changes
function updateCurrentPeriod(period) {
  currentPeriod = period;
}

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

// Initialize everything when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  initializeDropdowns();
  handleDropdownResize();
  initSpendingChart();

  // Chart period controls
  document.querySelectorAll(".chart-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const period = btn.dataset.period;
      loadSpendingTrends(period);
      updateCurrentPeriod(period);

      // Update active button
      document
        .querySelectorAll(".chart-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
  });

  // Budget settings form
  document
    .getElementById("budgetSettingsForm")
    .addEventListener("submit", handleBudgetSettings);

  // Load real data
  loadBudgetData();
  loadSpendingTrends("1m");
});
