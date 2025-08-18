// Get configuration from global object set by template
const config = window.SHOPPING_TRIP_CONFIG || {};
const ALLOCATED_BUDGET = config.allocatedBudget || 1000;
const REMAINING_BUDGET = config.remainingBudget || 1000;
const CART_SESSION_EXISTS = config.cartSessionExists || false;

// Removed barcode scanner for testing UPC input

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  if (CART_SESSION_EXISTS) {
    loadCartItems();
    // Add a small delay to ensure cart ID is properly initialized
    setTimeout(() => {
      loadShoppingListStatus();
    }, 100);
  }

  const form = document.getElementById("addItemForm");
  if (form) {
    form.addEventListener("submit", handleFormSubmit);
  }

  // Setup price input auto-formatting
  setupPriceInputFormatting();

  // Setup cart controls event listeners
  setupCartEventListeners();

  // Setup shopping list functionality
  setupShoppingListEventListeners();
});

// Load cart items from API
async function loadCartItems() {
  try {
    const response = await fetch(
      config.urls?.getCartItems || "/api/shopping-trip/get-cart-items",
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );
    const data = await response.json();

    if (data.items) {
      updateCartDOM(data.items);
    }

    // Update budget if available
    if (data.total_items !== undefined) {
      const defaultBudget = ALLOCATED_BUDGET;
      const defaultRemaining = REMAINING_BUDGET;
      updateBudgetOverview(
        data.allocated_budget || defaultBudget,
        data.total_spent || 0,
        data.total_items || 0,
        data.remaining || defaultRemaining
      );
    }
  } catch (err) {
    console.error("Error loading cart items:", err);
  }
}

// Update cart items in DOM
function updateCartDOM(items) {
  const container = document.getElementById("cart-items-container");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `
        <div class="empty-cart">
        <div class="empty-cart-icon">
            <i class="fas fa-shopping-cart" aria-hidden="true"></i>
        </div>
        <h4 class="empty-cart-title">Your cart is empty</h4>
        <p class="empty-cart-description">Start adding items to see them here</p>
        </div>
    `;
    return;
  }

  container.innerHTML = items
    .map((item) => {
      const subtotal = (item.price * item.quantity).toFixed(2);
      const imgHtml = item.image_url
        ? `<img src="${item.image_url}" alt="${item.item_name}" class="item-image">`
        : `<div class="item-image"><i class="fas fa-image" aria-hidden="true"></i></div>`;

      return `
        <div class="cart-item" data-item-id="${item.item_ID}">
        ${imgHtml}
        <div class="item-details">
            <div class="item-name">${escapeHtml(item.item_name)}</div>
            <div class="item-price">$${parseFloat(item.price).toFixed(
              2
            )} each</div>
        </div>
        <div class="quantity-controls">
            <button class="qty-btn qty-decrease" data-item-id="${
              item.item_ID
            }" data-action="decrease" ${item.quantity <= 1 ? "disabled" : ""}>
            <i class="fas fa-minus"></i>
            </button>
            <input type="number" class="qty-input" value="${
              item.quantity
            }" min="1" max="999" 
                    data-item-id="${item.item_ID}" 
                    onblur="this.value = Math.max(1, parseInt(this.value) || 1)">
            <button class="qty-btn qty-increase" data-item-id="${
              item.item_ID
            }" data-action="increase">
            <i class="fas fa-plus"></i>
            </button>
        </div>
        <div class="item-subtotal">$${subtotal}</div>
        <div class="item-actions">
            <button class="delete-btn" data-item-id="${
              item.item_ID
            }" title="Remove item">
            <i class="fas fa-trash"></i>
            </button>
        </div>
        </div>
    `;
    })
    .join("");
}

// Update budget overview
function updateBudgetOverview(allocated, spent, totalItems, remaining) {
  const budgetEl = document.getElementById("budget-overview");
  if (budgetEl) {
    budgetEl.innerHTML = `
        <div class="budget-stat">
        <div class="budget-stat-value">$${allocated}</div>
        <div class="budget-stat-label">Allocated Budget</div>
        </div>
        <div class="budget-stat">
        <div class="budget-stat-value">$${spent}</div>
        <div class="budget-stat-label">Total Spent</div>
        </div>
        <div class="budget-stat">
        <div class="budget-stat-value">${totalItems}</div>
        <div class="budget-stat-label">Items in Cart</div>
        </div>
        <div class="budget-stat">
        <div class="budget-stat-value">$${remaining}</div>
        <div class="budget-stat-label">Remaining</div>
        </div>
    `;
  }
}

// Handle form submission
async function handleFormSubmit(event) {
  event.preventDefault();

  const form = event.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn.innerHTML;

  // Add loading state
  submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
  submitBtn.disabled = true;
  form.classList.add("loading");

  const itemName = document.getElementById("itemName").value.trim();
  const itemPriceInput = document.getElementById("itemPrice").value.trim();
  const itemPrice = itemPriceInput ? parseFloat(itemPriceInput) : 0;
  const itemQty = parseInt(document.getElementById("itemQty").value, 10);

  if (!itemName || isNaN(itemQty) || itemQty <= 0) {
    alert("Please enter valid item name and quantity.");
    resetForm();
    return;
  }

  // Validate price only if provided
  if (itemPriceInput && isNaN(itemPrice)) {
    alert("Please enter a valid price or leave it empty.");
    resetForm();
    return;
  }

  try {
    // Show processing message
    showNotification(`🔍 Looking up UPC: ${itemName}...`, "info");

    // 1) Search for item by UPC using Nutritionix API
    const searchResponse = await fetch(
      `${
        config.urls?.searchItem || "/api/shopping-trip/searchitem"
      }?upc=${encodeURIComponent(itemName)}`
    );
    const searchData = await searchResponse.json();

    // 2) Extract food data with improved fallback handling
    let brandName = "Unknown Brand";
    let foodName = "Unknown Item";
    let imageUrl =
      "https://t4.ftcdn.net/jpg/02/51/95/53/360_F_251955356_FAQH0U1y1TZw3ZcdPGybwUkH90a3VAhb.jpg";
    let carbs = 0,
      sugar = 0,
      sodium = 0,
      fat = 0;

    console.log("Nutritionix API Response:", searchData);

    // Check if we found data in Nutritionix API
    if (searchData.foods && searchData.foods.length > 0) {
      const firstItem = searchData.foods[0];
      brandName = firstItem.brand_name || brandName;
      foodName = firstItem.food_name || foodName;
      imageUrl = firstItem.photo?.thumb || imageUrl;
      carbs = firstItem.nf_total_carbohydrate || 0;
      sugar = firstItem.nf_sugars || 0;
      sodium = firstItem.nf_sodium || 0;
      fat = firstItem.nf_saturated_fat || 0;

      // Show success message if found
      console.log("Product found in Nutritionix database:", searchData.message);
      showNotification(`✅ Found: ${brandName} - ${foodName}`, "success");
    } else if (searchData.fallback) {
      // Use fallback data if API failed or item not found
      const fallbackItem = searchData.fallback;
      brandName = fallbackItem.brand_name || brandName;
      foodName = fallbackItem.food_name || foodName;
      imageUrl = fallbackItem.photo?.thumb || imageUrl;
      carbs = fallbackItem.nf_total_carbohydrate || 0;
      sugar = fallbackItem.nf_sugars || 0;
      sodium = fallbackItem.nf_sodium || 0;
      fat = fallbackItem.nf_saturated_fat || 0;

      // Show warning about fallback data
      console.warn(
        "Using fallback data:",
        searchData.message || searchData.error
      );
      showNotification(
        "⚠️ Product not found in database. Using generic data.",
        "warning"
      );
    } else {
      // Last resort - completely manual entry
      foodName = `Manual Entry (${itemName})`;
      console.warn("No product data available, using manual entry");
      showNotification(
        "⚠️ No product data available. Adding as manual entry.",
        "warning"
      );
    }

    const combinedName = `${brandName} - ${foodName}`;

    // 3) Add item to cart
    const requestBody = {
      upc: itemName,
      price: itemPrice,
      quantity: itemQty,
      itemName: combinedName,
      imageUrl: imageUrl,
    };

    // Check if this is linked to a shopping list item
    let nameInput = document.getElementById("itemName");
    if (nameInput && nameInput.dataset.listItemId) {
      requestBody.list_item_id = parseInt(nameInput.dataset.listItemId);
    }

    const addItemResponse = await fetch(
      config.urls?.addItem || "/api/shopping-trip/add-item",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      }
    );

    const resultData = await addItemResponse.json();

    if (addItemResponse.ok && resultData.items) {
      updateCartDOM(resultData.items);

      // Update budget
      const totalSpent = resultData.items.reduce(
        (sum, item) => sum + item.price * item.quantity,
        0
      );
      const totalItems = resultData.items.reduce(
        (sum, item) => sum + item.quantity,
        0
      );
      const allocatedBudget = ALLOCATED_BUDGET;
      updateBudgetOverview(
        allocatedBudget,
        totalSpent,
        totalItems,
        allocatedBudget - totalSpent
      );

      showNotification(`✅ Added to cart: ${combinedName}`, "success");
    } else {
      showNotification(
        `❌ Failed to add item: ${resultData.error || "Unknown error"}`,
        "error"
      );
    }

    // 4) Check for impulse purchase if we have nutritional data
    if (carbs > 0 || sugar > 0 || sodium > 0 || fat > 0) {
      try {
        const predictResponse = await fetch(
          `${
            config.urls?.predict || "/api/shopping-trip/predict"
          }?carbs=${carbs}&sugar=${sugar}&sodium=${sodium}&fat=${fat}`
        );
        const predictData = await predictResponse.json();

        if (predictData.prediction == 1) {
          showImpulsePopup(carbs, sugar, sodium, fat);
        }
      } catch (predictError) {
        console.warn("Impulse prediction failed:", predictError);
      }
    }

    // Clear form and list item linking
    form.reset();
    nameInput = document.getElementById("itemName");
    if (nameInput && nameInput.dataset.listItemId) {
      delete nameInput.dataset.listItemId;
    }

    // Refresh shopping list status to show updated progress
    if (currentCartId) {
      loadShoppingListStatus();
    }
  } catch (err) {
    console.error("Error adding item:", err);
    showNotification(`❌ Error: ${err.message}`, "error");
  } finally {
    resetForm();
  }

  function resetForm() {
    submitBtn.innerHTML = originalText;
    submitBtn.disabled = false;
    form.classList.remove("loading");
  }
}

// Show impulse purchase popup
function showImpulsePopup(carbs, sugar, sodium, fat) {
  const popup = document.createElement("div");
  popup.className = "impulse-popup";
  popup.innerHTML = `
    <div class="impulse-popup-content">
        <div class="impulse-icon">
        <i class="fas fa-exclamation-triangle" aria-hidden="true"></i>
        </div>
        <h3 class="impulse-title">Impulse Purchase Detected!</h3>
        <p class="impulse-description">
        Our AI detected this might be an impulse purchase based on the nutritional content. 
        Are you sure you want to keep this item?
        </p>
        <div class="impulse-actions">
        <button class="btn-impulse-no" onclick="handleImpulseResponse(false, ${carbs}, ${sugar}, ${sodium}, ${fat})">
            Keep It
        </button>
        <button class="btn-impulse-yes" onclick="handleImpulseResponse(true, ${carbs}, ${sugar}, ${sodium}, ${fat})">
            Remove It
        </button>
        </div>
    </div>
    `;

  document.body.appendChild(popup);

  // Remove on outside click
  popup.addEventListener("click", (e) => {
    if (e.target === popup) {
      document.body.removeChild(popup);
    }
  });
}

// Handle impulse purchase response
async function handleImpulseResponse(wasImpulse, carbs, sugar, sodium, fat) {
  const popup = document.querySelector(".impulse-popup");
  if (popup) {
    document.body.removeChild(popup);
  }

  // Send feedback to ML model
  const label = wasImpulse ? 1 : 0;
  fetch(
    `${
      config.urls?.learn || "/api/shopping-trip/learn"
    }?carbs=${carbs}&sugar=${sugar}&sodium=${sodium}&fat=${fat}&label=${label}`
  ).catch((error) => console.error("ML feedback failed:", error));

  if (wasImpulse) {
    // Remove the last added item
    try {
      const response = await fetch("/api/shopping-trip/remove-last-item", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const data = await response.json();
      if (data.items) {
        updateCartDOM(data.items);

        // Update budget
        const totalSpent = data.items.reduce(
          (sum, item) => sum + item.price * item.quantity,
          0
        );
        const totalItems = data.items.reduce(
          (sum, item) => sum + item.quantity,
          0
        );
        const allocatedBudget = ALLOCATED_BUDGET;
        updateBudgetOverview(
          allocatedBudget,
          totalSpent,
          totalItems,
          allocatedBudget - totalSpent
        );
      }
    } catch (error) {
      console.error("Error removing item:", error);
    }
  }
}

// Update item quantity
async function updateQuantity(itemId, newQuantity) {
  try {
    newQuantity = Math.max(1, parseInt(newQuantity) || 1);

    const response = await fetch("/api/shopping-trip/update-item", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        item_id: itemId,
        quantity: newQuantity,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      updateCartDOM(data.items);
      updateBudgetOverview(
        data.allocated_budget,
        data.total_spent,
        data.total_items,
        data.remaining
      );
    } else {
      const errorData = await response.json();
      console.error("Failed to update quantity:", errorData.error);
      alert("Failed to update item quantity. Please try again.");
    }
  } catch (error) {
    console.error("Error updating quantity:", error);
    alert("An error occurred while updating the quantity. Please try again.");
  }
}

// Update quantity from input field
function updateQuantityFromInput(input) {
  const itemId = parseInt(input.dataset.itemId);
  const newQuantity = parseInt(input.value);
  updateQuantity(itemId, newQuantity);
}

// Setup event listeners for cart controls
function setupCartEventListeners() {
  document.addEventListener("click", function (e) {
    // Handle quantity buttons
    if (e.target.closest(".qty-btn")) {
      const button = e.target.closest(".qty-btn");
      const itemId = parseInt(button.dataset.itemId);
      const action = button.dataset.action;

      if (action === "increase") {
        const currentQty = parseInt(
          button.parentElement.querySelector(".qty-input").value
        );
        updateQuantity(itemId, currentQty + 1);
      } else if (action === "decrease") {
        const currentQty = parseInt(
          button.parentElement.querySelector(".qty-input").value
        );
        updateQuantity(itemId, currentQty - 1);
      }
    }

    // Handle delete buttons
    if (e.target.closest(".delete-btn")) {
      const button = e.target.closest(".delete-btn");
      const itemId = parseInt(button.dataset.itemId);
      deleteItem(itemId);
    }
  });

  // Handle quantity input changes
  document.addEventListener("change", function (e) {
    if (e.target.classList.contains("qty-input")) {
      updateQuantityFromInput(e.target);
    }
  });
}

// Delete an item from cart
async function deleteItem(itemId) {
  if (!confirm("Are you sure you want to remove this item from your cart?")) {
    return;
  }

  try {
    const response = await fetch("/api/shopping-trip/delete-item", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        item_id: itemId,
      }),
    });

    if (response.ok) {
      const data = await response.json();
      updateCartDOM(data.items);
      updateBudgetOverview(
        data.allocated_budget,
        data.total_spent,
        data.total_items,
        data.remaining
      );
    } else {
      const errorData = await response.json();
      console.error("Failed to delete item:", errorData.error);
      alert("Failed to remove item. Please try again.");
    }
  } catch (error) {
    console.error("Error deleting item:", error);
    alert("An error occurred while removing the item. Please try again.");
  }
}

// Barcode scanner functions temporarily disabled for UPC testing

// Notification system
function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.textContent = message;
  notification.style.cssText = `
    position: fixed;
    top: 100px;
    right: 20px;
    background: ${
      type === "success"
        ? "var(--success-color)"
        : type === "error"
        ? "var(--error-color)"
        : type === "warning"
        ? "var(--warning-color)"
        : "var(--primary-color)"
    };
    color: white;
    padding: 1rem 1.5rem;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    z-index: 9999;
    animation: fadeInUp 0.3s ease;
    max-width: 300px;
    word-wrap: break-word;
    `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 5000); // Show warning messages a bit longer
}

// Utility function
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
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

// Initialize dropdowns when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  initializeDropdowns();
  handleDropdownResize();
});

// Shopping List Integration Functions
let currentCartId = null;

// Setup shopping list event listeners
function setupShoppingListEventListeners() {
  // Load lists button
  const loadListsBtn = document.getElementById("loadListsBtn");
  if (loadListsBtn) {
    loadListsBtn.addEventListener("click", loadAvailableLists);
  }

  // Start shopping button
  const startShoppingBtn = document.getElementById("startShoppingBtn");
  if (startShoppingBtn) {
    startShoppingBtn.addEventListener("click", handleStartShopping);
  }

  // List selection change
  const listSelect = document.getElementById("availableListsSelect");
  if (listSelect) {
    listSelect.addEventListener("change", function () {
      const startBtn = document.getElementById("startShoppingBtn");

      // Update button text based on selection
      if (this.value) {
        startBtn.innerHTML =
          '<i class="fas fa-play" aria-hidden="true"></i> Start Shopping with List';
        showNotification(
          '💡 List selected - click "Start Shopping with List" to begin',
          "info"
        );
      } else {
        startBtn.innerHTML =
          '<i class="fas fa-play" aria-hidden="true"></i> Start Shopping';
      }
    });
  }

  // Get cart ID from session
  if (CART_SESSION_EXISTS && config.cartId) {
    currentCartId = config.cartId;
  }

  // Debug log to help troubleshoot
  console.log("Current cart ID initialized:", currentCartId);
  console.log("Cart session exists:", CART_SESSION_EXISTS);
}

// Load available shopping lists
async function loadAvailableLists() {
  try {
    showNotification("Loading your shopping lists...", "info");

    const response = await fetch("/api/shopping-trip/available-lists");
    const data = await response.json();

    if (response.ok && data.lists) {
      displayAvailableLists(data.lists);
    } else {
      showNotification("❌ Failed to load shopping lists", "error");
    }
  } catch (error) {
    console.error("Error loading lists:", error);
    showNotification("❌ Error loading shopping lists", "error");
  }
}

// Display available shopping lists
function displayAvailableLists(lists) {
  const container = document.getElementById("availableListsContainer");
  const select = document.getElementById("availableListsSelect");
  const loadBtn = document.getElementById("loadListsBtn");

  // Clear existing options
  select.innerHTML = '<option value="">Select a shopping list...</option>';

  // Filter out lists with 0 items
  const listsWithItems = lists.filter(list => list.item_count > 0);

  if (listsWithItems.length === 0) {
    if (lists.length === 0) {
      showNotification(
        "📝 No shopping lists found. Create one first!",
        "warning"
      );
    } else {
      showNotification(
        "📝 No shopping lists with items found. Add items to your lists first!",
        "warning"
      );
    }
    return;
  }

  // Populate select with lists that have items
  listsWithItems.forEach((list) => {
    const option = document.createElement("option");
    option.value = list.id;
    option.textContent = `${list.name} (${list.completed_count}/${list.item_count} items)`;
    select.appendChild(option);
  });

  // Show the container and hide load button
  container.style.display = "block";
  loadBtn.style.display = "none";
}

// Handle start shopping button click
async function handleStartShopping() {
  const select = document.getElementById("availableListsSelect");
  const storeNameInput = document.getElementById("storeName");
  const listId = select ? select.value : null;

  if (!storeNameInput || !storeNameInput.value.trim()) {
    showNotification("❌ Please enter a store name first", "error");
    storeNameInput.focus();
    return;
  }

  try {
    if (listId) {
      // Create shopping trip with imported list
      showNotification("Creating shopping trip with imported list...", "info");

      const cartResponse = await fetch("/api/shopping-trip/create-cart", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          store_name: storeNameInput.value.trim(),
          import_list_id: parseInt(listId),
        }),
      });

      const cartData = await cartResponse.json();

      if (cartResponse.ok) {
        showNotification(
          `✅ Shopping trip created with imported list!`,
          "success"
        );
        currentCartId = cartData.cart_id;
        setTimeout(() => {
          window.location.href = "/shopping-trip";
        }, 500);
      } else {
        showNotification(
          `❌ Failed to create trip: ${cartData.error}`,
          "error"
        );
      }
    } else {
      // Regular shopping trip without list
      const form = document.getElementById("startShoppingForm");
      const formData = new FormData(form);

      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        window.location.href = "/shopping-trip";
      } else {
        showNotification("❌ Failed to start shopping trip", "error");
      }
    }
  } catch (error) {
    console.error("Error starting shopping trip:", error);
    showNotification("❌ Error starting shopping trip", "error");
  }
}

// Load shopping list status for active trip
async function loadShoppingListStatus(retryCount = 0) {
  if (!currentCartId) {
    console.log("No currentCartId found, shopping list status not available");

    // Retry up to 3 times with increasing delays if cart ID might still be initializing
    if (retryCount < 3 && CART_SESSION_EXISTS) {
      console.log(
        `Retrying loadShoppingListStatus in ${(retryCount + 1) * 500}ms...`
      );
      setTimeout(() => {
        loadShoppingListStatus(retryCount + 1);
      }, (retryCount + 1) * 500);
    }
    return;
  }

  try {
    const response = await fetch(
      `/api/shopping-trip/list-status?cart_id=${currentCartId}`
    );
    const data = await response.json();

    if (response.ok) {
      if (data.has_list) {
        displayShoppingListProgress(data);
      } else {
        // Hide shopping list section if no list is imported
        const section = document.getElementById("shoppingListSection");
        if (section) section.style.display = "none";
      }
    }
  } catch (error) {
    console.error("Error loading shopping list status:", error);
  }
}

// Display shopping list progress
function displayShoppingListProgress(data) {
  const section = document.getElementById("shoppingListSection");
  const content = document.getElementById("shoppingListContent");

  if (!section || !content) return;

  section.style.display = "block";

  // Update section title
  const title = section.querySelector(".section-title");
  if (title) {
    title.textContent = `${data.list_name}`;
  }

  // Update progress bar
  const progressBar = document.getElementById("shoppingListProgressBar");
  if (progressBar && data.items) {
    const totalItems = data.items.length;
    const completedItems = data.items.filter(
      (item) => item.is_found || item.in_cart
    ).length;
    const progressPercent =
      totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

    progressBar.innerHTML = `
        <span>${completedItems}/${totalItems} found</span>
        <div class="progress-bar">
        <div class="progress-fill" style="width: ${progressPercent}%"></div>
        </div>
        <span>${progressPercent}%</span>
    `;
  }

  // Create items HTML
  const itemsHtml = data.items
    .map((item) => {
      const isFound = item.is_found;
      const inCart = item.in_cart;

      return `
        <div class="shopping-list-item ${
          isFound ? "found" : ""
        }" data-list-item-id="${item.list_item_id}">
        <input type="checkbox" class="list-item-checkbox" 
                ${isFound ? "checked" : ""} 
                onchange="toggleItemFound(${item.list_item_id}, this.checked)">
        
        <div class="list-item-details">
            <div class="list-item-name">${escapeHtml(item.name)}</div>
            <div class="list-item-quantity">Qty: ${item.quantity}</div>
            ${
              item.notes
                ? `<div class="list-item-notes">${escapeHtml(item.notes)}</div>`
                : ""
            }
        </div>
        
        <div class="list-item-status ${isFound ? "found" : "not-found"}">
            ${
              inCart
                ? `<i class="fas fa-shopping-cart"></i> In Cart`
                : isFound
                ? `<i class="fas fa-check-circle"></i> Found`
                : `<i class="fas fa-circle"></i> Not Found`
            }
        </div>
        
        <div class="list-item-actions">
            ${
              !inCart
                ? `
            <button class="btn-list-action btn-add-to-cart" 
                    onclick="quickAddToCart('${escapeHtml(item.name)}', ${
                    item.quantity
                  }, ${item.list_item_id})">
                <i class="fas fa-plus"></i> Add
            </button>
            `
                : ""
            }
            ${
              !isFound
                ? `
            <button class="btn-list-action btn-mark-found" 
                    onclick="toggleItemFound(${item.list_item_id}, true)">
                <i class="fas fa-check"></i> Found
            </button>
            `
                : ""
            }
        </div>
        </div>
    `;
    })
    .join("");

  content.innerHTML = `
    <div class="shopping-list-items">
        ${itemsHtml}
    </div>
    `;

  // Initialize collapse state (expanded by default)
  const toggle = section.querySelector(".shopping-list-toggle");
  const contentEl = section.querySelector(".shopping-list-content");
  if (toggle && contentEl) {
    toggle.classList.remove("collapsed");
    contentEl.classList.remove("collapsed");
  }
}

// Toggle shopping list section collapse/expand
function toggleShoppingListSection() {
  const section = document.getElementById("shoppingListSection");
  if (!section) return;

  const toggle = section.querySelector(".shopping-list-toggle");
  const content = section.querySelector(".shopping-list-content");

  if (toggle && content) {
    const isCollapsed = toggle.classList.contains("collapsed");

    if (isCollapsed) {
      // Expand
      toggle.classList.remove("collapsed");
      content.classList.remove("collapsed");
    } else {
      // Collapse
      toggle.classList.add("collapsed");
      content.classList.add("collapsed");
    }
  }
}

// Toggle item found status
async function toggleItemFound(listItemId, isFound) {
  if (!currentCartId) return;

  try {
    const response = await fetch("/api/shopping-trip/mark-found", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        list_item_id: listItemId,
        cart_id: parseInt(currentCartId),
        is_found: isFound,
      }),
    });

    if (response.ok) {
      loadShoppingListStatus(); // Refresh the display
    } else {
      const data = await response.json();
      showNotification(`❌ Failed to update item: ${data.error}`, "error");
    }
  } catch (error) {
    console.error("Error updating item status:", error);
    showNotification("❌ Error updating item status", "error");
  }
}

// Quick add item from shopping list to cart
async function quickAddToCart(itemName, quantity, listItemId) {
  // Pre-fill the add item form
  const nameInput = document.getElementById("itemName");
  const qtyInput = document.getElementById("itemQty");

  if (nameInput && qtyInput) {
    // Clear the UPC field and suggest manual entry
    nameInput.value = "";
    qtyInput.value = quantity;

    // Scroll to add item form
    const addItemSection = document.querySelector(".add-item-section");
    if (addItemSection) {
      addItemSection.scrollIntoView({ behavior: "smooth" });
    }

    // Store the list item ID for linking when item is added
    nameInput.dataset.listItemId = listItemId;

    showNotification(`📝 Fill in UPC for "${itemName}" (price is optional)`, "info");
  }
}

// Setup price input formatting to convert integers to decimal (499 -> 4.99)
function setupPriceInputFormatting() {
  const priceInput = document.getElementById("itemPrice");
  if (!priceInput) return;

  priceInput.addEventListener('input', function(e) {
    let value = e.target.value.replace(/[^0-9]/g, ''); // Remove non-numeric characters
    
    if (value === '') {
      e.target.value = '';
      return;
    }
    
    // Convert to integer and divide by 100 to get decimal
    let numericValue = parseInt(value);
    let formattedValue = (numericValue / 100).toFixed(2);
    
    e.target.value = formattedValue;
  });

  priceInput.addEventListener('blur', function(e) {
    let value = e.target.value.trim();
    
    if (value === '' || value === '0.00') {
      e.target.value = '';
      return;
    }
    
    // Ensure proper decimal formatting on blur
    let numericValue = parseFloat(value);
    if (!isNaN(numericValue)) {
      e.target.value = numericValue.toFixed(2);
    }
  });

  priceInput.addEventListener('focus', function(e) {
    // Clear placeholder behavior - if it's empty, keep it empty
    if (e.target.value === '0.00') {
      e.target.value = '';
    }
  });
}
