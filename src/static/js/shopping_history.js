// Shopping Details Modal Functions
async function openShoppingDetails(cartId) {
  console.log("Opening shopping details for cart:", cartId);

  const modal = document.getElementById("shoppingModal");
  const itemsContainer = document.getElementById("itemsContainer");

  // Show modal with loading state
  showModal();
  resetModalContent();

  try {
    const response = await fetch(
      `/api/shopping-trip/details?cart_id=${cartId}`
    );

    if (response.ok) {
      const data = await response.json();
      console.log("Received data:", data);
      populateModal(data);
    } else {
      console.error("Failed to load shopping details:", response.status);
      showErrorState("Failed to load shopping trip details. Please try again.");
    }
  } catch (error) {
    console.error("Error loading shopping details:", error);
    showErrorState(
      "Unable to connect to server. Please check your connection and try again."
    );
  }
}

function showModal() {
  const modal = document.getElementById("shoppingModal");
  modal.style.display = "flex";
  // Trigger animation
  setTimeout(() => {
    modal.classList.add("show");
  }, 10);

  // Prevent body scroll
  document.body.style.overflow = "hidden";

  // Close modal when clicking overlay
  modal.onclick = function (e) {
    if (e.target === modal) {
      closeShoppingModal();
    }
  };

  // Close modal with Escape key
  document.addEventListener("keydown", handleEscapeKey);
}

function closeShoppingModal() {
  const modal = document.getElementById("shoppingModal");
  modal.classList.remove("show");

  // Wait for animation to complete before hiding
  setTimeout(() => {
    modal.style.display = "none";
    document.body.style.overflow = "";
  }, 300);

  // Remove event listener
  document.removeEventListener("keydown", handleEscapeKey);
}

function handleEscapeKey(e) {
  if (e.key === "Escape") {
    closeShoppingModal();
  }
}

function resetModalContent() {
  document.getElementById("modalTitle").textContent = "Shopping Trip Details";
  document.getElementById("modalDate").textContent = "";
  document.getElementById("modalStoreName").textContent = "-";
  document.getElementById("modalTotalAmount").textContent = "$0.00";
  document.getElementById("modalTotalItems").textContent = "0";

  const itemsContainer = document.getElementById("itemsContainer");
  itemsContainer.innerHTML = `
    <div class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        <p>Loading shopping trip details...</p>
    </div>
    `;
}

function populateModal(data) {
  // Format date
  const date = new Date(data.created_at);
  const formattedDate = date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
  const formattedTime = date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
  });

  // Update modal content
  document.getElementById(
    "modalTitle"
  ).textContent = `${data.store_name} Shopping Trip`;
  document.getElementById(
    "modalDate"
  ).textContent = `${formattedDate} at ${formattedTime}`;
  document.getElementById("modalStoreName").textContent = data.store_name;
  document.getElementById("modalTotalAmount").textContent = `$${Number(
    data.total_amount
  ).toFixed(2)}`;
  document.getElementById(
    "modalTotalItems"
  ).textContent = `${data.total_items}`;

  // Populate items
  const itemsContainer = document.getElementById("itemsContainer");

  if (!data.items || data.items.length === 0) {
    itemsContainer.innerHTML = `
        <div class="empty-state">
        <i class="fas fa-shopping-cart"></i>
        <h3>No Items Found</h3>
        <p>This shopping trip doesn't have any recorded items.</p>
        </div>
    `;
    return;
  }

  itemsContainer.innerHTML = "";

  data.items.forEach((item) => {
    const itemCard = document.createElement("div");
    itemCard.className = "item-card";

    const itemTotal = Number(item.price * item.quantity).toFixed(2);
    const imageUrl =
      item.image_url ||
      "https://images.unsplash.com/photo-1523294587484-bae6cc870010?w=60&h=60&fit=crop&crop=center";

    itemCard.innerHTML = `
        <img src="${imageUrl}" 
            alt="${item.item_name}" 
            class="item-image" 
            onerror="this.src='https://images.unsplash.com/photo-1523294587484-bae6cc870010?w=60&h=60&fit=crop&crop=center'">
        <div class="item-details">
        <div class="item-name" title="${item.item_name}">${item.item_name}</div>
        <div class="item-quantity">Qty: ${item.quantity}</div>
        <div class="item-price">$${item.price} each</div>
        </div>
        <div class="item-total">$${itemTotal}</div>
    `;

    itemsContainer.appendChild(itemCard);
  });
}

function showErrorState(message) {
  const itemsContainer = document.getElementById("itemsContainer");
  itemsContainer.innerHTML = `
    <div class="error-state">
        <i class="fas fa-exclamation-triangle"></i>
        <h3>Unable to Load Details</h3>
        <p>${message}</p>
    </div>
    `;
}

// Load More History Functionality
let currentOffset = 0; // Start from 0 since we're loading all history
const config = window.SHOPPING_HISTORY_CONFIG || {};
const maxTrips = config.totalTrips || 0;

async function loadMoreHistory() {
  const showMoreBtn = document.getElementById("showMoreBtn");
  const showLessBtn = document.getElementById("showLessBtn");
  const tableBody = document.getElementById("historyTableBody");

  // Show loading state
  showMoreBtn.disabled = true;
  showMoreBtn.innerHTML =
    '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Loading...';

  try {
    const response = await fetch(
      `/api/shopping-history?offset=${currentOffset}&limit=35`
    );

    if (response.ok) {
      const data = await response.json();

      // Add new rows to the table with a class to identify them as additional
      data.history.forEach((cart) => {
        const row = document.createElement("tr");
        row.className = "clickable-row additional-history";
        row.setAttribute("data-cart-id", cart.cart_ID);

        // Format the date
        const date = new Date(cart.created_at);
        const formattedDate = date.toLocaleDateString("en-US", {
          month: "2-digit",
          day: "2-digit",
          year: "2-digit",
        });

        row.innerHTML = `
            <td>
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-store" style="color: var(--primary-color);"></i>
                ${cart.store_name}
            </div>
            </td>
            <td>
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-calendar-alt" style="color: var(--text-secondary);"></i>
                ${formattedDate}
            </div>
            </td>
            <td>
            <span class="cart-badge">
                <i class="fas fa-shopping-basket" aria-hidden="true"></i>
                ${cart.total_items} items
            </span>
            </td>
            <td>
            <span class="amount">$${cart.total_spent}</span>
            </td>
        `;

        // Add click handler to the new row
        row.addEventListener("click", function () {
          const cartId = this.getAttribute("data-cart-id");
          if (cartId) {
            openShoppingDetails(cartId);
          }
        });

        tableBody.appendChild(row);
      });

      currentOffset += data.history.length;

      // Show the "Show Less" button
      if (showLessBtn) {
        showLessBtn.style.display = "inline-flex";
      }

      // Update or hide the "Show More" button
      if (currentOffset >= maxTrips) {
        showMoreBtn.style.display = "none";
      } else {
        showMoreBtn.disabled = false;
        showMoreBtn.innerHTML = `
            <i class="fas fa-chevron-down" aria-hidden="true"></i>
            Show More
        `;
      }
    } else {
      console.error("Failed to load more history");
      showMoreBtn.disabled = false;
      showMoreBtn.innerHTML =
        '<i class="fas fa-chevron-down" aria-hidden="true"></i> Show More';
    }
  } catch (error) {
    console.error("Error loading more history:", error);
    showMoreBtn.disabled = false;
    showMoreBtn.innerHTML =
      '<i class="fas fa-chevron-down" aria-hidden="true"></i> Show More';
  }
}

function showLessHistory() {
  const showMoreBtn = document.getElementById("showMoreBtn");
  const showLessBtn = document.getElementById("showLessBtn");
  const tableBody = document.getElementById("historyTableBody");

  // Remove all additional history rows
  const additionalRows = tableBody.querySelectorAll(".additional-history");
  additionalRows.forEach((row) => row.remove());

  // Reset the offset to initial value
  currentOffset = 0;

  // Hide the "Show Less" button
  if (showLessBtn) {
    showLessBtn.style.display = "none";
  }

  // Show and reset the "Show More" button
  showMoreBtn.style.display = "inline-flex";
  showMoreBtn.disabled = false;
  showMoreBtn.innerHTML = `
    <i class="fas fa-chevron-down" aria-hidden="true"></i>
    Show More
    `;
}

// Initialize Shopping History Click Handlers
function initializeShoppingHistory() {
  // Add click handlers to existing rows
  document.querySelectorAll(".clickable-row").forEach((row) => {
    row.addEventListener("click", function () {
      const cartId = this.getAttribute("data-cart-id");
      if (cartId) {
        openShoppingDetails(cartId);
      }
    });
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

// Animate stats on page load
function animateStats() {
  const statValues = document.querySelectorAll(".stat-value");

  statValues.forEach((stat, index) => {
    setTimeout(() => {
      stat.style.animation = "pulse 0.6s ease";
    }, index * 200);
  });
}

// Initialize all functionality
document.addEventListener("DOMContentLoaded", function () {
  animateStats();
  initializeScrollEffects();
  initializeMobileMenu();
  initializeDropdowns();
  handleDropdownResize();
  initializeShoppingHistory();
});