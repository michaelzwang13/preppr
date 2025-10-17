document.addEventListener("DOMContentLoaded", function () {
  // Get configuration from global object set by template
  const config = window.PANTRY_TRANSFER_CONFIG || {};

  const form = document.getElementById("pantryTransferForm");
  const selectAllBtn = document.getElementById("selectAllBtn");
  const selectNoneBtn = document.getElementById("selectNoneBtn");
  const transferBtn = document.getElementById("transferBtn");
  const loadingModal = document.getElementById("loadingModal");

  // Select all/none functionality
  selectAllBtn.addEventListener("click", function () {
    document
      .querySelectorAll('input[name="include_item"]')
      .forEach((cb) => (cb.checked = true));
  });

  selectNoneBtn.addEventListener("click", function () {
    document
      .querySelectorAll('input[name="include_item"]')
      .forEach((cb) => (cb.checked = false));
  });

  // Form submission
  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const selectedItems = [];
    const formData = new FormData(form);

    // Gather selected items and their data
    document
      .querySelectorAll('input[name="include_item"]:checked')
      .forEach((checkbox) => {
        const itemId = checkbox.value;
        selectedItems.push({
          item_id: itemId,
          quantity: formData.get(`quantity_${itemId}`),
          unit: formData.get(`unit_${itemId}`),
          storage_type: formData.get(`storage_${itemId}`),
          category: formData.get(`category_${itemId}`),
          expiration_date: formData.get(`expiry_${itemId}`) || null,
          ai_predict_expiry: formData.get(`ai_predict_${itemId}`) === "on",
          notes: formData.get(`notes_${itemId}`) || null,
        });
      });

    if (selectedItems.length === 0) {
      alert("Please select at least one item to add to your pantry.");
      return;
    }

    // Show loading modal
    loadingModal.style.display = "flex";

    try {
      const response = await fetch("/api/pantry/transfer-from-trip", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          cart_id: config.cartId || 0,
          items: selectedItems,
        }),
      });

      const result = await response.json();

      if (result.success) {
        // Success - redirect to pantry or home
        window.location.href = config.urls?.pantry || "/pantry";
      } else {
        alert("Error adding items to pantry: " + result.message);
        loadingModal.style.display = "none";
      }
    } catch (error) {
      console.error("Transfer error:", error);
      alert("Error adding items to pantry. Please try again.");
      loadingModal.style.display = "none";
    }
  });
});
