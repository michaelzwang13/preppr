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

document.addEventListener("DOMContentLoaded", function () {
  initializeDropdowns();
  handleDropdownResize();

  const addItemBtn = document.getElementById("addItemBtn");
  const addFirstItemBtn = document.getElementById("addFirstItemBtn");
  const deleteExpiredBtn = document.getElementById("deleteExpiredBtn");
  const addItemModal = document.getElementById("addItemModal");
  const addItemForm = document.getElementById("addItemForm");
  const editItemModal = document.getElementById("editItemModal");
  const editItemForm = document.getElementById("editItemForm");
  const pantryItems = document.getElementById("pantryItems");
  const emptyState = document.getElementById("emptyState");

  // Modal controls
  addItemBtn.addEventListener(
    "click",
    () => (addItemModal.style.display = "flex")
  );
  addFirstItemBtn.addEventListener(
    "click",
    () => (addItemModal.style.display = "flex")
  );

  // Delete expired items
  deleteExpiredBtn.addEventListener("click", deleteAllExpiredItems);

  // Handle custom unit functionality for Add Item modal
  const unitSelect = document.getElementById("unitSelect");
  const customUnitInput = document.getElementById("customUnitInput");

  unitSelect.addEventListener("change", function () {
    if (this.value === "custom") {
      customUnitInput.style.display = "block";
      customUnitInput.required = true;
    } else {
      customUnitInput.style.display = "none";
      customUnitInput.required = false;
      customUnitInput.value = "";
    }
  });

  // Handle custom unit functionality for Edit Item modal
  const editUnitSelect = document.getElementById("editUnit");
  const editCustomUnitInput = document.getElementById("editCustomUnitInput");

  editUnitSelect.addEventListener("change", function () {
    if (this.value === "custom") {
      editCustomUnitInput.style.display = "block";
      editCustomUnitInput.required = true;
    } else {
      editCustomUnitInput.style.display = "none";
      editCustomUnitInput.required = false;
      editCustomUnitInput.value = "";
    }
  });

  document.querySelectorAll(".close-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      addItemModal.style.display = "none";
      editItemModal.style.display = "none";
      // Reset custom unit inputs when closing modals
      resetCustomUnitInputs();
    });
  });

  // Function to reset custom unit inputs
  function resetCustomUnitInputs() {
    // Reset Add Item modal
    unitSelect.value = "pcs";
    customUnitInput.style.display = "none";
    customUnitInput.required = false;
    customUnitInput.value = "";

    // Reset Edit Item modal
    editUnitSelect.value = "pcs";
    editCustomUnitInput.style.display = "none";
    editCustomUnitInput.required = false;
    editCustomUnitInput.value = "";
  }

  // Load pantry items on page load
  loadPantryItems();

  // Filter event listeners
  document
    .getElementById("searchFilter")
    .addEventListener("input", loadPantryItems);
  document
    .getElementById("storageFilter")
    .addEventListener("change", loadPantryItems);
  document
    .getElementById("categoryFilter")
    .addEventListener("change", loadPantryItems);
  document
    .getElementById("tagFilter")
    .addEventListener("change", loadPantryItems);
  document
    .getElementById("expiryFilter")
    .addEventListener("change", loadPantryItems);

  // Clear filters button
  document
    .getElementById("clearFiltersBtn")
    .addEventListener("click", clearAllFilters);

  // Add item form submission
  addItemForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(addItemForm);
    const unitValue = formData.get("unit");
    const finalUnit =
      unitValue === "custom" ? formData.get("custom_unit") : unitValue;

    const itemData = {
      item_name: formData.get("item_name"),
      quantity: parseFloat(formData.get("quantity")),
      unit: finalUnit,
      storage_type: formData.get("storage_type"),
      category: formData.get("category"),
      tag_ids: getSelectedTagIds("selectedTags"),
      expiration_date: formData.get("expiration_date") || null,
      ai_predict_expiry: formData.get("ai_predict_expiry") === "on",
      notes: formData.get("notes") || null,
    };

    try {
      const response = await fetch("/api/pantry/items", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(itemData),
      });

      const result = await response.json();

      if (result.success) {
        addItemModal.style.display = "none";
        addItemForm.reset();
        resetCustomUnitInputs();
        resetTagSelection("selectedTags");
        // Pass the newly added item ID to highlight it
        const newItemId = result.item.pantry_item_id;
        loadPantryItems(newItemId);
      } else {
        alert("Error adding item: " + result.message);
      }
    } catch (error) {
      console.error("Add item error:", error);
      alert("Error adding item. Please try again.");
    }
  });

  // Edit item form submission
  editItemForm.addEventListener("submit", async function (e) {
    e.preventDefault();

    const formData = new FormData(editItemForm);
    const itemId = formData.get("item_id");
    const unitValue = formData.get("unit");
    const finalUnit =
      unitValue === "custom" ? formData.get("custom_unit") : unitValue;

    const itemData = {
      item_name: formData.get("item_name"),
      quantity: parseFloat(formData.get("quantity")),
      unit: finalUnit,
      storage_type: formData.get("storage_type"),
      category: formData.get("category"),
      tag_ids: getSelectedTagIds("editSelectedTags"),
      expiration_date: formData.get("expiration_date") || null,
      ai_predict_expiry: formData.get("ai_predict_expiry") === "on",
      notes: formData.get("notes") || null,
    };

    try {
      const response = await fetch(`/api/pantry/items/${itemId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(itemData),
      });

      const result = await response.json();

      if (result.success) {
        editItemModal.style.display = "none";
        editItemForm.reset();
        resetCustomUnitInputs();
        resetTagSelection("editSelectedTags");
        loadPantryItems();
      } else {
        alert("Error updating item: " + result.message);
      }
    } catch (error) {
      console.error("Edit item error:", error);
      alert("Error updating item. Please try again.");
    }
  });

  async function loadPantryItems(highlightItemId = null) {
    try {
      const searchFilter = document
        .getElementById("searchFilter")
        .value.toLowerCase()
        .trim();
      const storageFilter = document.getElementById("storageFilter").value;
      const categoryFilter = document.getElementById("categoryFilter").value;
      const tagFilter = document.getElementById("tagFilter").value;
      const expiryFilter = document.getElementById("expiryFilter").value;

      const params = new URLSearchParams();
      if (storageFilter) params.append("storage_type", storageFilter);
      if (categoryFilter) params.append("category", categoryFilter);
      if (expiryFilter) params.append("expiry_status", expiryFilter);

      const response = await fetch(`/api/pantry/items?${params}`);
      const result = await response.json();

      if (result.success) {
        let filteredItems = result.items;

        // Load and populate tag filter
        await loadAndPopulateTagFilter();

        // Apply client-side search filter
        if (searchFilter) {
          filteredItems = filteredItems.filter(
            (item) =>
              item.item_name.toLowerCase().includes(searchFilter) ||
              (item.notes && item.notes.toLowerCase().includes(searchFilter))
          );
        }

        // Apply client-side tag filter
        if (tagFilter) {
          filteredItems = filteredItems.filter((item) => {
            return item.tags && item.tags.some((tag) => tag.name === tagFilter);
          });
        }

        displayPantryItems(filteredItems, highlightItemId);
        updateStats(filteredItems);
      } else {
        console.error("Error loading pantry items:", result.message);
      }
    } catch (error) {
      console.error("Load items error:", error);
    }
  }

  function displayPantryItems(items, highlightItemId = null) {
    if (items.length === 0) {
      pantryItems.style.display = "none";
      emptyState.style.display = "block";

      const searchFilter = document.getElementById("searchFilter").value.trim();
      const storageFilter = document.getElementById("storageFilter").value;
      const categoryFilter = document.getElementById("categoryFilter").value;
      const tagFilter = document.getElementById("tagFilter").value;
      const expiryFilter = document.getElementById("expiryFilter").value;
      const emptyStateElement = document.getElementById("emptyState");

      // Check if any filters are active
      const hasActiveFilters = searchFilter || storageFilter || categoryFilter || tagFilter || expiryFilter;

      if (hasActiveFilters) {
        let filterDescription = "your current filters";
        if (searchFilter) {
          filterDescription = `your search for "${searchFilter}"`;
        } else if (categoryFilter) {
          filterDescription = `the category "${categoryFilter}"`;
        } else if (storageFilter) {
          filterDescription = `the storage type "${storageFilter}"`;
        } else if (tagFilter) {
          filterDescription = `the tag "${tagFilter}"`;
        } else if (expiryFilter) {
          const expiryLabels = {
            "expired": "expired items",
            "expiring_soon": "items expiring soon",
            "fresh": "fresh items"
          };
          filterDescription = expiryLabels[expiryFilter] || expiryFilter;
        }

        emptyStateElement.innerHTML = `
                    <h3>No items found</h3>
                    <p>No pantry items match ${filterDescription}. Try adjusting your filters or search terms.</p>
                `;
      } else {
        emptyStateElement.innerHTML = `
                    <h3>Your pantry is empty</h3>
                    <p>Start by completing a shopping trip or adding items manually.</p>
                    <button id="addFirstItemBtn" class="btn-primary">Add Your First Item</button>
                `;
        // Re-add event listener for the new button
        document
          .getElementById("addFirstItemBtn")
          .addEventListener("click", () => {
            document.getElementById("addItemModal").style.display = "flex";
          });
      }
      return;
    }

    pantryItems.style.display = "block";
    emptyState.style.display = "none";

    const searchFilter = document.getElementById("searchFilter").value.trim();
    const storageFilter = document.getElementById("storageFilter").value;
    const categoryFilter = document.getElementById("categoryFilter").value;
    const tagFilter = document.getElementById("tagFilter").value;

    // If filtering by specific category, storage, tag, or search, use simple grid layout
    if (categoryFilter || storageFilter || tagFilter || searchFilter) {
      pantryItems.innerHTML = `<div class="pantry-grid">${items
        .map((item) => createItemHTML(item))
        .join("")}</div>`;
      
      // After rendering, scroll to and highlight the newly added item if specified
      if (highlightItemId) {
        scrollToAndHighlightItem(highlightItemId);
      }
      return;
    }

    // Group items by category for "All Locations" view
    const groupedItems = groupItemsByCategory(items);
    pantryItems.innerHTML = createCategorizedHTML(groupedItems);
    
    // After rendering, scroll to and highlight the newly added item if specified
    if (highlightItemId) {
      scrollToAndHighlightItem(highlightItemId);
    }
  }

  function groupItemsByCategory(items) {
    const groups = {};

    items.forEach((item) => {
      const category = item.category || "Other";
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(item);
    });

    // Sort categories alphabetically, but put 'Other' at the end
    const sortedCategories = Object.keys(groups).sort((a, b) => {
      if (a === "Other") return 1;
      if (b === "Other") return -1;
      return a.localeCompare(b);
    });

    const sortedGroups = {};
    sortedCategories.forEach((category) => {
      sortedGroups[category] = groups[category];
    });

    return sortedGroups;
  }

  function createCategorizedHTML(groupedItems) {
    const categoryIcons = {
      Produce: { icon: "fas fa-apple-alt", color: "var(--success-gradient)" },
      Meat: { icon: "fas fa-drumstick-bite", color: "var(--error-gradient)" },
      Dairy: { icon: "fas fa-cheese", color: "var(--warning-gradient)" },
      Grains: { icon: "fas fa-wheat", color: "var(--secondary-gradient)" },
      "Canned Goods": {
        icon: "fas fa-can-food",
        color: "var(--accent-gradient)",
      },
      "Frozen Foods": {
        icon: "fas fa-snowflake",
        color: "#06b6d4",
      },
      Beverages: {
        icon: "fas fa-glass-water",
        color: "#3b82f6",
      },
      Snacks: {
        icon: "fas fa-cookie-bite",
        color: "#f97316",
      },
      Condiments: {
        icon: "fas fa-pepper-hot",
        color: "#dc2626",
      },
      Spices: {
        icon: "fas fa-mortar-pestle",
        color: "#7c3aed",
      },
      Bread: {
        icon: "fas fa-bread-slice",
        color: "#92400e",
      },
      Other: { icon: "fas fa-box", color: "var(--text-secondary)" },
    };

    let html = "";

    Object.entries(groupedItems).forEach(([category, items]) => {
      const categoryInfo = categoryIcons[category] || categoryIcons["Other"];
      const expiredCount = items.filter((item) => {
        const status = getExpiryStatus(item.expiration_date);
        return status.status === "expired";
      }).length;
      const expiringSoonCount = items.filter((item) => {
        const status = getExpiryStatus(item.expiration_date);
        return status.status === "expiring_soon";
      }).length;

      html += `
                <div class="category-section">
                    <div class="category-header">
                        <div class="category-icon" style="background: ${
                          categoryInfo.color
                        };">
                            <i class="${categoryInfo.icon}"></i>
                        </div>
                        <h3 class="category-title">${category}</h3>
                        <div class="category-count">${items.length} items</div>
                        ${
                          expiredCount > 0
                            ? `<div class="category-count" style="background: var(--error-color); color: white;">${expiredCount} expired</div>`
                            : ""
                        }
                        ${
                          expiringSoonCount > 0
                            ? `<div class="category-count" style="background: var(--warning-color); color: white;">${expiringSoonCount} expiring soon</div>`
                            : ""
                        }
                    </div>
                    <div class="category-grid">
                        ${items.map((item) => createItemHTML(item)).join("")}
                    </div>
                </div>
            `;
    });

    return html;
  }

  function createItemHTML(item) {
    const expiryStatus = getExpiryStatus(item.expiration_date);
    const expiryClass =
      expiryStatus.status === "expired"
        ? "expired"
        : expiryStatus.status === "expiring_soon"
        ? "expiring-soon"
        : "";

    return `
            <div class="pantry-item ${expiryClass}" data-item-id="${item.pantry_item_id}">
                <div class="item-header">
                    <h4 class="item-name">${item.item_name}</h4>
                    <div class="item-actions">
                        <button onclick="editItem(${
                          item.pantry_item_id
                        })" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="deleteItem(${
                          item.pantry_item_id
                        })" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="item-content">
                    <div class="item-details">
                        <p><strong>Quantity:</strong> ${
                          item.quantity
                        } ${item.unit}</p>
                        <p><strong>Storage:</strong> ${item.storage_type}</p>
                        <p><strong>Category:</strong> ${item.category}</p>
                        ${
                          item.expiration_date
                            ? `<p><strong>Expires:</strong> <span class="expiry-status ${expiryStatus.status}">${expiryStatus.text}</span></p>`
                            : "<p><strong>Expires:</strong> No expiry date</p>"
                        }
                        <p><strong>Added:</strong> ${new Date(
                          item.date_added
                        ).toLocaleDateString()}</p>
                        ${
                          item.notes
                            ? `<p><strong>Notes:</strong> ${item.notes}</p>`
                            : ""
                        }
                    </div>
                    ${
                      item.tags && item.tags.length > 0
                        ? `<div class="item-tags-container">
                            ${item.tags
                              .slice(0, 5)
                              .map(
                                (tag) =>
                                  `<span class="item-tag" style="background-color: ${
                                    tag.color || "#3B82F6"
                                  }">${tag.name}</span>`
                              )
                              .join("")}
                            ${
                              item.tags.length > 5
                                ? `<span class="item-tag-overflow">+${
                                    item.tags.length - 5
                                  }</span>`
                                : ""
                            }
                        </div>`
                        : ""
                    }
                </div>
            </div>
        `;
  }

  function getExpiryStatus(expirationDate) {
    if (!expirationDate) return { status: "none", text: "No expiry date" };

    const today = new Date();
    const expiry = new Date(expirationDate);
    const diffDays = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
      const absDays = Math.abs(diffDays);
      if (absDays >= 365) {
        const years = Math.floor(absDays / 365);
        return { status: "expired", text: `Expired ${years}+ years ago` };
      }
      return { status: "expired", text: `Expired ${absDays} days ago` };
    } else if (diffDays <= 3) {
      return { status: "expiring_soon", text: `Expires in ${diffDays} days` };
    } else {
      if (diffDays >= 365) {
        const years = Math.floor(diffDays / 365);
        return { status: "fresh", text: `Expires in ${years}+ years` };
      }
      return { status: "fresh", text: `Expires in ${diffDays} days` };
    }
  }

  function updateStats(items) {
    const totalItems = items.length;
    let expiredItems = 0;
    let expiringSoonItems = 0;

    items.forEach((item) => {
      const status = getExpiryStatus(item.expiration_date);
      if (status.status === "expired") expiredItems++;
      else if (status.status === "expiring_soon") expiringSoonItems++;
    });

    document.getElementById("totalItems").textContent = totalItems;
    document.getElementById("expiredItems").textContent = expiredItems;
    document.getElementById("expiringSoonItems").textContent =
      expiringSoonItems;
  }

  async function deleteAllExpiredItems() {
    try {
      // First get all current items to find expired ones
      const response = await fetch("/api/pantry/items");
      const result = await response.json();

      if (!result.success) {
        alert("Error fetching pantry items");
        return;
      }

      const expiredItems = result.items.filter((item) => {
        const status = getExpiryStatus(item.expiration_date);
        return status.status === "expired";
      });

      if (expiredItems.length === 0) {
        alert("No expired items found to delete.");
        return;
      }

      const confirmDelete = confirm(
        `Are you sure you want to delete ${expiredItems.length} expired item(s)? This action cannot be undone.`
      );

      if (!confirmDelete) return;

      // Delete each expired item
      let deletedCount = 0;
      for (const item of expiredItems) {
        const deleteResponse = await fetch(
          `/api/pantry/items/${item.pantry_item_id}`,
          {
            method: "DELETE",
          }
        );

        const deleteResult = await deleteResponse.json();
        if (deleteResult.success) {
          deletedCount++;
        }
      }

      if (deletedCount > 0) {
        alert(`Successfully deleted ${deletedCount} expired item(s).`);
        loadPantryItems(); // Refresh the display
      } else {
        alert("Error deleting expired items. Please try again.");
      }
    } catch (error) {
      console.error("Delete expired items error:", error);
      alert("Error deleting expired items. Please try again.");
    }
  }

  function clearAllFilters() {
    // Reset all filter inputs to their default values
    document.getElementById("searchFilter").value = "";
    document.getElementById("storageFilter").value = "";
    document.getElementById("categoryFilter").value = "";
    document.getElementById("tagFilter").value = "";
    document.getElementById("expiryFilter").value = "";

    // Refresh the pantry items to show all items
    loadPantryItems();
  }

  // Global functions for item actions
  window.editItem = async function (itemId) {
    try {
      // Fetch the current item data
      const response = await fetch(`/api/pantry/items/${itemId}`, {
        method: "GET",
      });

      const result = await response.json();

      if (result.success && result.item) {
        const item = result.item;

        // Populate the edit form
        document.getElementById("editItemId").value = item.pantry_item_id;
        document.getElementById("editItemName").value = item.item_name;
        document.getElementById("editQuantity").value = item.quantity;

        // Handle unit selection - check if it's a predefined unit or custom
        const editUnitSelect = document.getElementById("editUnit");
        const editCustomUnitInput = document.getElementById(
          "editCustomUnitInput"
        );
        const predefinedUnits = ["pcs", "g", "kg", "ml", "l", "oz", "lbs"];

        if (predefinedUnits.includes(item.unit)) {
          editUnitSelect.value = item.unit;
          editCustomUnitInput.style.display = "none";
          editCustomUnitInput.required = false;
          editCustomUnitInput.value = "";
        } else {
          editUnitSelect.value = "custom";
          editCustomUnitInput.style.display = "block";
          editCustomUnitInput.required = true;
          editCustomUnitInput.value = item.unit;
        }

        document.getElementById("editStorageType").value = item.storage_type;
        document.getElementById("editCategory").value = item.category;

        // Populate tags
        editSelectedTags = [];
        if (item.tags && item.tags.length > 0) {
          editSelectedTags = item.tags.map((tag) => ({
            id: tag.id,
            name: tag.name,
            color: tag.color,
          }));
        }
        updateSelectedTagsDisplay("editSelectedTags");
        populateTagSuggestions("editTagSuggestions", "editSelectedTags");

        document.getElementById("editExpirationDate").value =
          item.expiration_date || "";
        document.getElementById("editAiPredict").checked = false; // Reset AI prediction
        document.getElementById("editNotes").value = item.notes || "";

        // Show the edit modal
        editItemModal.style.display = "flex";
      } else {
        alert(
          "Error loading item details: " + (result.message || "Item not found")
        );
      }
    } catch (error) {
      console.error("Error loading item for edit:", error);
      alert("Error loading item details. Please try again.");
    }
  };

  window.deleteItem = async function (itemId) {
    if (!confirm("Are you sure you want to delete this item?")) return;

    try {
      const response = await fetch(`/api/pantry/items/${itemId}`, {
        method: "DELETE",
      });

      const result = await response.json();

      if (result.success) {
        loadPantryItems();
      } else {
        alert("Error deleting item: " + result.message);
      }
    } catch (error) {
      console.error("Delete item error:", error);
      alert("Error deleting item. Please try again.");
    }
  };

  // Tag Management Functions
  let allTags = [];
  let selectedTags = [];
  let editSelectedTags = [];

  async function loadAndPopulateTagFilter() {
    try {
      const response = await fetch("/api/pantry/tags");
      const result = await response.json();

      if (result.success) {
        allTags = result.tags;
        populateTagFilter();
        populateTagSuggestions("tagSuggestions", "selectedTags");
        populateTagSuggestions("editTagSuggestions", "editSelectedTags");
      }
    } catch (error) {
      console.error("Error loading tags:", error);
    }
  }

  function populateTagFilter() {
    const tagSelect = document.getElementById("tagFilter");
    const currentValue = tagSelect.value;

    tagSelect.innerHTML = '<option value="">All Tags</option>';

    allTags.forEach((tag) => {
      const option = document.createElement("option");
      option.value = tag.tag_name;
      option.textContent = `${tag.tag_name} (${tag.usage_count})`;
      tagSelect.appendChild(option);
    });

    if (currentValue) {
      tagSelect.value = currentValue;
    }
  }

  function populateTagSuggestions(containerId, selectedTagsId) {
    const container = document.getElementById(containerId);
    const selectedTagsList =
      selectedTagsId === "selectedTags" ? selectedTags : editSelectedTags;

    container.innerHTML = "";

    // Check if 5-tag limit reached
    if (selectedTagsList.length >= 5) {
      container.innerHTML =
        '<p style="color: var(--warning-color); font-size: 0.8em; padding: 8px;">Maximum 5 tags reached. Remove a tag to add more.</p>';
      return;
    }

    if (allTags.length === 0) {
      container.innerHTML =
        '<p style="color: var(--text-secondary); font-size: 0.8em; padding: 8px;">No tags created yet. Type above to create your first tag.</p>';
      return;
    }

    const availableTags = allTags.filter(
      (tag) => !selectedTagsList.find((selected) => selected.id === tag.tag_id)
    );

    if (availableTags.length === 0) {
      container.innerHTML =
        '<p style="color: var(--text-secondary); font-size: 0.8em; padding: 8px;">All tags selected</p>';
      return;
    }

    availableTags.forEach((tag) => {
      const suggestion = document.createElement("div");
      suggestion.className = "tag-suggestion";
      suggestion.innerHTML = `
                <div class="tag-suggestion-info">
                    <div class="tag-suggestion-color" style="background-color: ${tag.tag_color}"></div>
                    <span>${tag.tag_name}</span>
                </div>
                <span class="tag-suggestion-usage">${tag.usage_count} uses</span>
            `;
      suggestion.addEventListener("click", () =>
        addExistingTag(tag, selectedTagsId)
      );
      container.appendChild(suggestion);
    });
  }

  function addExistingTag(tag, selectedTagsId) {
    const targetList =
      selectedTagsId === "selectedTags" ? selectedTags : editSelectedTags;

    // Check if already selected
    if (targetList.find((selected) => selected.id === tag.tag_id)) {
      return;
    }

    // Check 5-tag limit
    if (targetList.length >= 5) {
      alert("Maximum 5 tags allowed per item");
      return;
    }

    targetList.push({
      id: tag.tag_id,
      name: tag.tag_name,
      color: tag.tag_color,
    });
    updateSelectedTagsDisplay(selectedTagsId);
    populateTagSuggestions(
      selectedTagsId === "selectedTags"
        ? "tagSuggestions"
        : "editTagSuggestions",
      selectedTagsId
    );
  }

  window.removeTag = function (tagId, selectedTagsId) {
    const targetList =
      selectedTagsId === "selectedTags" ? selectedTags : editSelectedTags;
    const index = targetList.findIndex((tag) => tag.id === tagId);

    if (index > -1) {
      targetList.splice(index, 1);
      updateSelectedTagsDisplay(selectedTagsId);
      populateTagSuggestions(
        selectedTagsId === "selectedTags"
          ? "tagSuggestions"
          : "editTagSuggestions",
        selectedTagsId
      );
    }
  };

  function updateSelectedTagsDisplay(selectedTagsId) {
    const container = document.getElementById(selectedTagsId);
    const targetList =
      selectedTagsId === "selectedTags" ? selectedTags : editSelectedTags;

    container.innerHTML = "";

    targetList.forEach((tag) => {
      const badge = document.createElement("div");
      badge.className = "tag-badge";
      badge.style.backgroundColor = tag.color;
      badge.innerHTML = `
                ${tag.name}
                <button class="remove-tag" onclick="removeTag(${tag.id}, '${selectedTagsId}')" type="button">×</button>
            `;
      container.appendChild(badge);
    });

    // Update button and input states based on limit
    const inputId =
      selectedTagsId === "selectedTags" ? "tagInput" : "editTagInput";
    const buttonId =
      selectedTagsId === "selectedTags" ? "addTagBtn" : "editAddTagBtn";

    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);

    if (targetList.length >= 5) {
      input.disabled = true;
      input.placeholder = "Maximum 5 tags reached";
      button.disabled = true;
    } else {
      input.disabled = false;
      input.placeholder = "Type to add or search tags...";
      button.disabled = false;
    }
  }

  function getSelectedTagIds(selectedTagsId) {
    const targetList =
      selectedTagsId === "selectedTags" ? selectedTags : editSelectedTags;
    return targetList.map((tag) => tag.id);
  }

  function resetTagSelection(selectedTagsId) {
    if (selectedTagsId === "selectedTags") {
      selectedTags = [];
      document.getElementById("tagInput").value = "";
    } else {
      editSelectedTags = [];
      document.getElementById("editTagInput").value = "";
    }
    updateSelectedTagsDisplay(selectedTagsId);
    populateTagSuggestions(
      selectedTagsId === "selectedTags"
        ? "tagSuggestions"
        : "editTagSuggestions",
      selectedTagsId
    );
  }

  async function createNewTag(tagName) {
    try {
      const response = await fetch("/api/pantry/tags", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tag_name: tagName,
          tag_color: generateRandomColor(),
        }),
      });

      const result = await response.json();

      if (result.success) {
        allTags.push(result.tag);
        return result.tag;
      } else {
        alert(result.message);
        return null;
      }
    } catch (error) {
      console.error("Error creating tag:", error);
      alert("Error creating tag. Please try again.");
      return null;
    }
  }

  function generateRandomColor() {
    const colors = [
      "#3B82F6",
      "#10B981",
      "#F59E0B",
      "#EF4444",
      "#8B5CF6",
      "#06B6D4",
      "#84CC16",
      "#F97316",
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  // Tag input event listeners
  document
    .getElementById("addTagBtn")
    .addEventListener("click", async function () {
      const input = document.getElementById("tagInput");
      const tagName = input.value.trim();

      if (tagName) {
        // Check 5-tag limit
        if (selectedTags.length >= 5) {
          alert("Maximum 5 tags allowed per item");
          return;
        }

        // Check if tag already exists
        let existingTag = allTags.find(
          (tag) => tag.tag_name.toLowerCase() === tagName.toLowerCase()
        );

        if (!existingTag) {
          // Create new tag
          existingTag = await createNewTag(tagName);
          if (!existingTag) return;
        }

        addExistingTag(existingTag, "selectedTags");
        input.value = "";
      }
    });

  document
    .getElementById("editAddTagBtn")
    .addEventListener("click", async function () {
      const input = document.getElementById("editTagInput");
      const tagName = input.value.trim();

      if (tagName) {
        // Check 5-tag limit
        if (editSelectedTags.length >= 5) {
          alert("Maximum 5 tags allowed per item");
          return;
        }

        // Check if tag already exists
        let existingTag = allTags.find(
          (tag) => tag.tag_name.toLowerCase() === tagName.toLowerCase()
        );

        if (!existingTag) {
          // Create new tag
          existingTag = await createNewTag(tagName);
          if (!existingTag) return;
        }

        addExistingTag(existingTag, "editSelectedTags");
        input.value = "";
      }
    });

  // Tag input enter key support
  document
    .getElementById("tagInput")
    .addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        document.getElementById("addTagBtn").click();
      }
    });

  document
    .getElementById("editTagInput")
    .addEventListener("keypress", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        document.getElementById("editAddTagBtn").click();
      }
    });

  // Load tags when page loads
  loadAndPopulateTagFilter();


  // Function to scroll to and highlight a newly added item
  function scrollToAndHighlightItem(itemId) {
    // Use setTimeout to ensure DOM is fully rendered
    setTimeout(() => {
      const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
      if (itemElement) {
        // Scroll to the item with smooth scrolling
        itemElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
        
        // Add highlight class for animation
        itemElement.classList.add('newly-added-item');
        
        // Remove highlight class after animation completes
        setTimeout(() => {
          itemElement.classList.remove('newly-added-item');
        }, 3000); // 3 seconds highlight duration
      }
    }, 100); // Small delay to ensure DOM rendering
  }
});
