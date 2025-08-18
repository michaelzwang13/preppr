// Global variables
let shoppingLists = [];

// Initialize the page
document.addEventListener("DOMContentLoaded", function () {
  loadShoppingLists();
  initializeEventListeners();
  initializeDropdowns();
  handleDropdownResize();
});

// Event listeners
function initializeEventListeners() {
  // Create list form
  document
    .getElementById("createListForm")
    .addEventListener("submit", handleCreateList);
}

// Load shopping lists from backend
async function loadShoppingLists() {
  try {
    const response = await fetch("/api/shopping-lists");
    const data = await response.json();
    shoppingLists = data.lists || [];
    renderShoppingLists();
  } catch (error) {
    console.error("Error loading shopping lists:", error);
    // Show mock data for demonstration
    showMockData();
  }
}

// Handle create new list
async function handleCreateList(event) {
  event.preventDefault();

  const formData = new FormData(event.target);
  const listData = {
    name: formData.get("listName"),
    description: formData.get("listDescription") || "",
  };

  try {
    const response = await fetch("/api/shopping-lists", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(listData),
    });

    const result = await response.json();

    if (response.ok) {
      // Add new list to the array
      shoppingLists.push(result.list);
      renderShoppingLists();

      // Reset form
      event.target.reset();

      // Show success message
      showNotification("List created successfully!", "success");
    } else {
      showNotification(result.error || "Failed to create list", "error");
    }
  } catch (error) {
    console.error("Error creating list:", error);
    showNotification("Failed to create list", "error");
  }
}

// Render shopping lists
function renderShoppingLists() {
  const listsGrid = document.getElementById("listsGrid");
  const emptyState = document.getElementById("emptyState");

  if (shoppingLists.length === 0) {
    listsGrid.style.display = "none";
    emptyState.style.display = "block";
    return;
  }

  listsGrid.style.display = "grid";
  emptyState.style.display = "none";

  listsGrid.innerHTML = shoppingLists
    .map(
      (list) => `
    <div class="list-card" data-list-id="${list.id}" onclick="openListModal(${
        list.id
      }, event)">
        <div class="list-header">
        <div>
            <div class="list-header-top">
            <h3 class="list-name">${escapeHtml(list.name)}</h3>
            <div class="list-actions">
                <button class="btn-icon btn-edit" onclick="editList(${
                  list.id
                })" title="Rename list">
                <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon btn-delete" onclick="deleteList(${
                  list.id
                })" title="Delete list">
                <i class="fas fa-trash"></i>
                </button>
            </div>
            </div>
            ${
              list.description
                ? `<div class="list-description">${escapeHtml(
                    list.description
                  )}</div>`
                : ""
            }
        </div>
        <div class="list-meta">
            <div class="list-stats">
            <i class="fas fa-shopping-basket" style="color: var(--primary-color);"></i>
            <span>${list.items ? list.items.length : 0} items</span>
            </div>
            <div class="list-stats">
            <i class="fas fa-calendar" style="color: var(--text-muted);"></i>
            <span>${formatDate(list.created_at || new Date())}</span>
            </div>
        </div>
        </div>
    </div>
    `
    )
    .join("");
}

// Add item to list
async function addItemToList(event, listId) {
  event.preventDefault();

  const form = event.target;
  const itemName = form.querySelector(".add-item-input").value.trim();
  const quantity = parseInt(form.querySelector(".add-item-qty").value);

  if (!itemName) return;

  // Check 25 item limit
  const list = shoppingLists.find((list) => list.id === listId);
  if (list && list.items && list.items.length >= 25) {
    showNotification(
      "Cannot add more items. Maximum 25 items per list.",
      "error"
    );
    return;
  }

  try {
    const response = await fetch(`/api/shopping-lists/${listId}/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: itemName, quantity: quantity }),
    });

    const result = await response.json();

    if (response.ok) {
      // Update the list in our array
      const listIndex = shoppingLists.findIndex((list) => list.id === listId);
      if (listIndex !== -1) {
        if (!shoppingLists[listIndex].items) {
          shoppingLists[listIndex].items = [];
        }
        shoppingLists[listIndex].items.push(result.item);
        renderShoppingLists();
      }

      // Reset form
      form.reset();
      form.querySelector(".add-item-qty").value = 1;

      showNotification("Item added successfully!", "success");

      // Update modal if it's open for this list
      if (currentModalListId === listId) {
        openListModal(listId, { target: { closest: () => null } });
      }
    } else {
      showNotification(result.error || "Failed to add item", "error");
    }
  } catch (error) {
    console.error("Error adding item:", error);
    showNotification("Failed to add item", "error");
  }
}

// Global variable to track current modal list
let currentModalListId = null;

// Open list modal
function openListModal(listId, event) {
  // Don't open modal if clicking on buttons
  if (
    event.target.closest(".list-actions") ||
    event.target.closest(".btn-icon")
  ) {
    event.stopPropagation();
    return;
  }

  const list = shoppingLists.find((l) => l.id === listId);
  if (!list) return;

  currentModalListId = listId;

  // Populate modal content
  document.getElementById("modalTitle").textContent = list.name;

  const modalDescription = document.getElementById("modalDescription");
  if (list.description) {
    modalDescription.textContent = list.description;
    modalDescription.style.display = "block";
  } else {
    modalDescription.style.display = "none";
  }

  // Populate meta information
  document.getElementById("modalMeta").innerHTML = `
    <div class="list-stats">
        <i class="fas fa-shopping-basket" style="color: var(--primary-color);"></i>
        <span>${list.items ? list.items.length : 0} items</span>
    </div>
    <div class="list-stats">
        <i class="fas fa-calendar" style="color: var(--text-muted);"></i>
        <span>${formatDate(list.created_at || new Date())}</span>
    </div>
    `;

  // Populate items
  document.getElementById("modalContent").innerHTML = `
    <ul class="list-items">
        ${(list.items || [])
          .map(
            (item) => `
        <li class="list-item">
            <div class="item-checkbox ${item.is_completed ? "completed" : ""}" 
                onclick="toggleItem(${list.id}, ${item.id})"></div>
            <input type="text" class="item-text-input ${
              item.is_completed ? "completed" : ""
            }" 
                    value="${escapeHtml(item.name)}" 
                    onblur="updateItemNameInline(${list.id}, ${
              item.id
            }, this.value)" 
                    onkeypress="handleItemNameKeypress(event, ${list.id}, ${
              item.id
            })" 
                    title="Edit item name directly">
            <div class="item-controls">
            <div class="quantity-controls">
                <button class="qty-btn qty-decrease" onclick="changeQuantity(${
                  list.id
                }, ${item.id}, -1)" title="Decrease quantity">
                <i class="fas fa-minus"></i>
                </button>
                <span class="item-quantity">${item.quantity}</span>
                <button class="qty-btn qty-increase" onclick="changeQuantity(${
                  list.id
                }, ${item.id}, 1)" title="Increase quantity">
                <i class="fas fa-plus"></i>
                </button>
            </div>
            <button class="btn-delete-item" onclick="deleteItem(${list.id}, ${
              item.id
            })" title="Delete item">
                <i class="fas fa-times"></i>
            </button>
            </div>
        </li>
        `
          )
          .join("")}
    </ul>
    
    ${
      (list.items || []).length < 25
        ? `
        <form class="add-item-form" onsubmit="addItemToList(event, ${list.id})">
        <input type="text" class="add-item-input" placeholder="Add item..." required>
        <input type="number" class="add-item-qty" value="1" min="1" required>
        <button type="submit" class="btn-add-item">
            <i class="fas fa-plus"></i>
        </button>
        </form>
    `
        : `
        <div class="item-limit-message">
        <i class="fas fa-info-circle" style="color: var(--warning-color); margin-right: 8px;"></i>
        Maximum 25 items per list reached
        </div>
    `
    }
    `;

  // Show modal
  document.getElementById("listModal").classList.add("active");
  document.body.style.overflow = "hidden"; // Prevent background scrolling
}

// Close list modal
function closeListModal() {
  document.getElementById("listModal").classList.remove("active");
  document.body.style.overflow = ""; // Restore scrolling
  currentModalListId = null;
}

// Close modal when clicking on overlay
document
  .getElementById("listModal")
  .addEventListener("click", function (event) {
    if (event.target === this) {
      closeListModal();
    }
  });

// Toggle item completion
async function toggleItem(listId, itemId) {
  try {
    const response = await fetch(
      `/api/shopping-lists/${listId}/items/${itemId}/toggle`,
      {
        method: "PATCH",
      }
    );

    if (response.ok) {
      // Update the item in our array
      const list = shoppingLists.find((list) => list.id === listId);
      if (list && list.items) {
        const item = list.items.find((item) => item.id === itemId);
        if (item) {
          item.is_completed = !item.is_completed;
          renderShoppingLists();
          // Update modal if it's open for this list
          if (currentModalListId === listId) {
            openListModal(listId, { target: { closest: () => null } });
          }
        }
      }
    }
  } catch (error) {
    console.error("Error toggling item:", error);
  }
}

// Handle inline item name editing on Enter key
function handleItemNameKeypress(event, listId, itemId) {
  if (event.key === "Enter") {
    event.target.blur(); // This will trigger the onblur event
  }
}

// Update item name inline without confirmation
async function updateItemNameInline(listId, itemId, newName) {
  const trimmedName = newName.trim();

  // Find current item to compare
  const list = shoppingLists.find((list) => list.id === listId);
  if (!list || !list.items) return;

  const item = list.items.find((item) => item.id === itemId);
  if (!item) return;

  // Don't update if name is empty or unchanged
  if (!trimmedName || trimmedName === item.name) {
    // Reset to original value if empty
    if (!trimmedName) {
      renderShoppingLists();
    }
    return;
  }

  try {
    const response = await fetch(
      `/api/shopping-lists/${listId}/items/${itemId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: trimmedName }),
      }
    );

    if (response.ok) {
      // Update the item in our array
      item.name = trimmedName;
      renderShoppingLists();
      // Update modal if it's open for this list
      if (currentModalListId === listId) {
        openListModal(listId, { target: { closest: () => null } });
      }
    } else {
      showNotification("Failed to update item", "error");
      renderShoppingLists(); // Reset to original value
      // Update modal if it's open for this list
      if (currentModalListId === listId) {
        openListModal(listId, { target: { closest: () => null } });
      }
    }
  } catch (error) {
    console.error("Error updating item:", error);
    showNotification("Failed to update item", "error");
    renderShoppingLists(); // Reset to original value
  }
}

// Change item quantity
async function changeQuantity(listId, itemId, change) {
  const list = shoppingLists.find((list) => list.id === listId);
  if (!list || !list.items) return;

  const item = list.items.find((item) => item.id === itemId);
  if (!item) return;

  const newQuantity = item.quantity + change;

  // Don't allow quantity to go below 1
  if (newQuantity < 1) return;

  try {
    const response = await fetch(
      `/api/shopping-lists/${listId}/items/${itemId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quantity: newQuantity }),
      }
    );

    if (response.ok) {
      // Update the item in our array
      item.quantity = newQuantity;
      renderShoppingLists();
      // Update modal if it's open for this list
      if (currentModalListId === listId) {
        openListModal(listId, { target: { closest: () => null } });
      }
    } else {
      showNotification("Failed to update quantity", "error");
    }
  } catch (error) {
    console.error("Error updating quantity:", error);
    showNotification("Failed to update quantity", "error");
  }
}

// Delete item without confirmation
async function deleteItem(listId, itemId) {
  try {
    const response = await fetch(
      `/api/shopping-lists/${listId}/items/${itemId}`,
      {
        method: "DELETE",
      }
    );

    if (response.ok) {
      // Remove the item from our array
      const list = shoppingLists.find((list) => list.id === listId);
      if (list && list.items) {
        list.items = list.items.filter((item) => item.id !== itemId);
        renderShoppingLists();
        showNotification("Item deleted", "success");
        // Update modal if it's open for this list
        if (currentModalListId === listId) {
          openListModal(listId, { target: { closest: () => null } });
        }
      }
    } else {
      showNotification("Failed to delete item", "error");
    }
  } catch (error) {
    console.error("Error deleting item:", error);
    showNotification("Failed to delete item", "error");
  }
}

// Edit list
function editList(listId) {
  const list = shoppingLists.find((list) => list.id === listId);
  if (list) {
    const newName = prompt("Enter new list name:", list.name);
    if (newName && newName.trim() !== "") {
      updateListName(listId, newName.trim());
    }
  }
}

// Update list name
async function updateListName(listId, newName) {
  try {
    const response = await fetch(`/api/shopping-lists/${listId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName }),
    });

    if (response.ok) {
      const listIndex = shoppingLists.findIndex((list) => list.id === listId);
      if (listIndex !== -1) {
        shoppingLists[listIndex].name = newName;
        renderShoppingLists();
        showNotification("List updated successfully!", "success");
      }
    } else {
      showNotification("Failed to update list", "error");
    }
  } catch (error) {
    console.error("Error updating list:", error);
    showNotification("Failed to update list", "error");
  }
}

// Delete list
async function deleteList(listId) {
  if (
    !confirm(
      "Are you sure you want to delete this list? This action cannot be undone."
    )
  ) {
    return;
  }

  try {
    const response = await fetch(`/api/shopping-lists/${listId}`, {
      method: "DELETE",
    });

    if (response.ok) {
      shoppingLists = shoppingLists.filter((list) => list.id !== listId);
      renderShoppingLists();
      showNotification("List deleted successfully!", "success");
    } else {
      showNotification("Failed to delete list", "error");
    }
  } catch (error) {
    console.error("Error deleting list:", error);
    showNotification("Failed to delete list", "error");
  }
}

// Utility functions
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(date) {
  const d = new Date(date);
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: d.getFullYear() !== new Date().getFullYear() ? "numeric" : undefined,
  });
}

function showNotification(message, type = "info") {
  // Simple notification system - you can enhance this
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
        : "var(--primary-color)"
    };
    color: white;
    padding: 1rem 1.5rem;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-lg);
    z-index: 9999;
    animation: fadeInUp 0.3s ease;
    `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.remove();
  }, 3000);
}

// Mock data for demonstration (remove when backend is ready)
function showMockData() {
  shoppingLists = [
    {
      id: 1,
      name: "Weekly Groceries",
      description: "Regular weekly shopping",
      created_at: new Date("2025-01-15"),
      items: [
        { id: 1, name: "Milk", quantity: 2, is_completed: false },
        { id: 2, name: "Bread", quantity: 1, is_completed: true },
        { id: 3, name: "Eggs", quantity: 12, is_completed: false },
        { id: 4, name: "Cheese", quantity: 1, is_completed: false },
      ],
    },
    {
      id: 2,
      name: "Party Supplies",
      description: "Birthday party this weekend",
      created_at: new Date("2025-01-18"),
      items: [
        { id: 5, name: "Balloons", quantity: 20, is_completed: false },
        { id: 6, name: "Cake Mix", quantity: 1, is_completed: true },
      ],
    },
  ];
  renderShoppingLists();
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
