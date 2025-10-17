// Recipe management functionality

let currentRecipes = [];
let filteredRecipes = [];
let currentRecipeId = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadRecipes();
    loadStats();
    setupEventListeners();
});

function setupEventListeners() {
    // Filter controls
    document.getElementById('searchFilter').addEventListener('input', applyFilters);
    document.getElementById('mealTypeFilter').addEventListener('change', applyFilters);
    document.getElementById('favoritesFilter').addEventListener('change', applyFilters);
    document.getElementById('sortFilter').addEventListener('change', applyFilters);
    document.getElementById('clearFiltersBtn').addEventListener('click', clearAllFilters);

    // Modal controls
    document.getElementById('closeRecipeDetailBtn').addEventListener('click', closeRecipeDetailModal);
    document.getElementById('closeUseRecipeBtn').addEventListener('click', closeUseRecipeModal);
    document.getElementById('cancelUseRecipeBtn').addEventListener('click', closeUseRecipeModal);

    // Button actions
    document.getElementById('createRecipeBtn').addEventListener('click', createNewRecipe);
    document.getElementById('createFirstRecipeBtn').addEventListener('click', createNewRecipe);
    document.getElementById('editRecipeBtn').addEventListener('click', editCurrentRecipe);
    document.getElementById('favoriteRecipeBtn').addEventListener('click', toggleCurrentRecipeFavorite);
    document.getElementById('deleteRecipeBtn').addEventListener('click', deleteCurrentRecipe);
    document.getElementById('useRecipeBtn').addEventListener('click', showUseRecipeModal);

    // Form submission
    document.getElementById('useRecipeForm').addEventListener('submit', handleUseRecipe);

    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('useMealDate').value = today;
}

async function loadRecipes() {
    try {
        const response = await fetch('/api/saved-recipes');
        const data = await response.json();
        
        if (data.success) {
            currentRecipes = data.recipes;
            filteredRecipes = [...currentRecipes];
            renderRecipes();
        } else {
            showError('Failed to load recipes: ' + data.message);
        }
    } catch (error) {
        showError('Error loading recipes: ' + error.message);
    }
}

async function loadStats() {
    try {
        const response = await fetch('/api/saved-recipes/stats');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('totalRecipes').textContent = data.stats.total_recipes;
            document.getElementById('favoriteRecipes').textContent = data.stats.favorite_recipes;
            document.getElementById('totalUses').textContent = data.stats.total_uses;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function applyFilters() {
    const searchTerm = document.getElementById('searchFilter').value.toLowerCase();
    const mealType = document.getElementById('mealTypeFilter').value;
    const favoritesOnly = document.getElementById('favoritesFilter').value === 'favorites';
    const sortBy = document.getElementById('sortFilter').value;

    // Filter recipes
    filteredRecipes = currentRecipes.filter(recipe => {
        const matchesSearch = !searchTerm || 
            recipe.recipe_name.toLowerCase().includes(searchTerm) ||
            (recipe.description && recipe.description.toLowerCase().includes(searchTerm));
        
        const matchesMealType = !mealType || recipe.meal_type === mealType;
        const matchesFavorites = !favoritesOnly || recipe.is_favorite;

        return matchesSearch && matchesMealType && matchesFavorites;
    });

    // Sort recipes
    filteredRecipes.sort((a, b) => {
        switch (sortBy) {
            case 'name':
                return a.recipe_name.localeCompare(b.recipe_name);
            case 'times_used':
                return b.times_used - a.times_used;
            case 'last_used':
                if (!a.last_used_date && !b.last_used_date) return 0;
                if (!a.last_used_date) return 1;
                if (!b.last_used_date) return -1;
                return new Date(b.last_used_date) - new Date(a.last_used_date);
            case 'created_at':
            default:
                return new Date(b.created_at) - new Date(a.created_at);
        }
    });

    renderRecipes();
}

function renderRecipes() {
    const grid = document.getElementById('recipesGrid');
    const emptyState = document.getElementById('emptyState');
    
    if (filteredRecipes.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    grid.style.display = 'grid';
    emptyState.style.display = 'none';
    
    grid.innerHTML = filteredRecipes.map(recipe => createRecipeCard(recipe)).join('');
}

function createRecipeCard(recipe) {
    const totalTime = (recipe.prep_time || 0) + (recipe.cook_time || 0);
    const timeDisplay = totalTime > 0 ? `${totalTime} min` : 'N/A';
    
    const favoriteIcon = recipe.is_favorite ? 
        '<i class="fas fa-heart recipe-favorite" title="Favorite"></i>' : '';
    
    const tags = recipe.custom_tags || [];
    const tagsHtml = tags.map(tag => `<span class="recipe-tag">${tag}</span>`).join('');

    const lastUsed = recipe.last_used_date ? 
        new Date(recipe.last_used_date).toLocaleDateString() : 'Never';

    return `
        <div class="recipe-card ${recipe.is_favorite ? 'favorite' : ''}" data-recipe-id="${recipe.saved_recipe_id}">
            <div class="recipe-header">
                <h3 class="recipe-title">${recipe.recipe_name}</h3>
                ${favoriteIcon}
            </div>
            
            <div class="recipe-meta">
                <div class="meta-item">
                    <i class="fas fa-utensils"></i>
                    ${recipe.meal_type}
                </div>
                <div class="meta-item">
                    <i class="fas fa-clock"></i>
                    ${timeDisplay}
                </div>
                <div class="meta-item">
                    <i class="fas fa-users"></i>
                    ${recipe.servings} serving${recipe.servings > 1 ? 's' : ''}
                </div>
                ${recipe.difficulty ? `
                <div class="meta-item">
                    <i class="fas fa-signal"></i>
                    ${recipe.difficulty}
                </div>
                ` : ''}
            </div>

            ${recipe.description ? `
            <div class="recipe-description">
                ${recipe.description.length > 100 ? 
                    recipe.description.substring(0, 100) + '...' : 
                    recipe.description}
            </div>
            ` : ''}

            ${tags.length > 0 ? `
            <div class="recipe-tags">
                ${tagsHtml}
            </div>
            ` : ''}

            <div class="recipe-actions">
                <div class="left">
                    <button onclick="viewRecipeDetails(${recipe.saved_recipe_id})">
                        <i class="fas fa-eye"></i> View
                    </button>
                    <button onclick="editRecipe(${recipe.saved_recipe_id})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button onclick="deleteRecipe(${recipe.saved_recipe_id}, '${recipe.recipe_name.replace(/'/g, "\\'")}')">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
                <div class="recipe-usage-info">
                    Used ${recipe.times_used} time${recipe.times_used !== 1 ? 's' : ''}
                    <br><small>Last used: ${lastUsed}</small>
                </div>
            </div>
        </div>
    `;
}

async function viewRecipeDetails(recipeId) {
    try {
        const response = await fetch(`/api/saved-recipes/${recipeId}`);
        const data = await response.json();
        
        if (data.success) {
            currentRecipeId = recipeId;
            displayRecipeDetails(data.recipe);
            showRecipeDetailModal();
        } else {
            showError('Failed to load recipe details: ' + data.message);
        }
    } catch (error) {
        showError('Error loading recipe details: ' + error.message);
    }
}

function displayRecipeDetails(recipe) {
    document.getElementById('recipeDetailTitle').textContent = recipe.recipe_name;
    
    const content = document.getElementById('recipeDetailContent');
    const totalTime = (recipe.prep_time || 0) + (recipe.cook_time || 0);
    
    const ingredientsHtml = recipe.ingredients.map(ing => `
        <li>
            <span class="ingredient-name">${ing.name}</span>
            <span class="ingredient-amount">${ing.quantity} ${ing.unit}${ing.notes ? ` (${ing.notes})` : ''}</span>
        </li>
    `).join('');

    const instructionsHtml = recipe.instructions.split('\n').filter(step => step.trim()).map(step => `
        <li>${step.replace(/^\d+\.\s*/, '').trim()}</li>
    `).join('');

    const tagsHtml = recipe.custom_tags.map(tag => `<span class="recipe-tag">${tag}</span>`).join('');

    content.innerHTML = `
        <div class="recipe-detail-section">
            <div class="recipe-meta">
                <div class="meta-item">
                    <i class="fas fa-utensils"></i> ${recipe.meal_type}
                </div>
                ${recipe.prep_time ? `<div class="meta-item">
                    <i class="fas fa-clock"></i> Prep: ${recipe.prep_time} min
                </div>` : ''}
                ${recipe.cook_time ? `<div class="meta-item">
                    <i class="fas fa-fire"></i> Cook: ${recipe.cook_time} min
                </div>` : ''}
                ${totalTime > 0 ? `<div class="meta-item">
                    <i class="fas fa-hourglass-half"></i> Total: ${totalTime} min
                </div>` : ''}
                <div class="meta-item">
                    <i class="fas fa-users"></i> ${recipe.servings} serving${recipe.servings > 1 ? 's' : ''}
                </div>
                ${recipe.difficulty ? `<div class="meta-item">
                    <i class="fas fa-signal"></i> ${recipe.difficulty}
                </div>` : ''}
            </div>
        </div>

        ${recipe.description ? `
        <div class="recipe-detail-section">
            <h3>Description</h3>
            <p>${recipe.description}</p>
        </div>
        ` : ''}

        ${recipe.custom_tags.length > 0 ? `
        <div class="recipe-detail-section">
            <h3>Tags</h3>
            <div class="recipe-tags">${tagsHtml}</div>
        </div>
        ` : ''}

        ${recipe.ingredients.length > 0 ? `
        <div class="recipe-detail-section">
            <h3>Ingredients</h3>
            <ul class="ingredients-list">
                ${ingredientsHtml}
            </ul>
        </div>
        ` : ''}

        <div class="recipe-detail-section">
            <h3>Instructions</h3>
            <ol class="instructions-list">
                ${instructionsHtml}
            </ol>
        </div>

        ${recipe.notes ? `
        <div class="recipe-detail-section">
            <h3>Notes</h3>
            <p>${recipe.notes}</p>
        </div>
        ` : ''}

        <div class="recipe-detail-section">
            <h3>Usage</h3>
            <p>Used ${recipe.times_used} time${recipe.times_used !== 1 ? 's' : ''}. 
            ${recipe.last_used_date ? `Last used: ${new Date(recipe.last_used_date).toLocaleDateString()}` : 'Never used'}</p>
        </div>
    `;

    // Update favorite button
    const favoriteBtn = document.getElementById('favoriteRecipeBtn');
    const favoriteSpan = favoriteBtn.querySelector('span');
    if (recipe.is_favorite) {
        favoriteBtn.innerHTML = '<i class="fas fa-heart-broken"></i> <span>Remove from Favorites</span>';
    } else {
        favoriteBtn.innerHTML = '<i class="fas fa-heart"></i> <span>Add to Favorites</span>';
    }
}

function showRecipeDetailModal() {
    document.getElementById('recipeDetailModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeRecipeDetailModal() {
    document.getElementById('recipeDetailModal').style.display = 'none';
    document.body.style.overflow = 'auto';
    currentRecipeId = null;
}

function showUseRecipeModal() {
    document.getElementById('useRecipeModal').style.display = 'flex';
}

function closeUseRecipeModal() {
    document.getElementById('useRecipeModal').style.display = 'none';
    // Reset form
    document.getElementById('useRecipeForm').reset();
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('useMealDate').value = today;
}

async function handleUseRecipe(event) {
    event.preventDefault();
    
    if (!currentRecipeId) {
        showError('No recipe selected');
        return;
    }

    const formData = new FormData(event.target);
    const mealDate = document.getElementById('useMealDate').value;
    const mealType = document.getElementById('useMealType').value;
    const replaceExisting = document.getElementById('replaceExistingMeal').checked;
    const notes = document.getElementById('useRecipeNotes').value;

    try {
        const response = await fetch(`/api/saved-recipes/${currentRecipeId}/use`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                meal_date: mealDate,
                meal_type: mealType,
                replace_existing: replaceExisting,
                usage_context: 'meal_plan',
                notes: notes
            })
        });

        const data = await response.json();
        
        if (data.success) {
            showSuccess(`Recipe added to your ${mealType} for ${new Date(mealDate).toLocaleDateString()}`);
            closeUseRecipeModal();
            closeRecipeDetailModal();
            // Reload recipes to update usage counts
            loadRecipes();
            loadStats();
        } else {
            if (data.requires_confirmation) {
                if (confirm(data.message + ' Do you want to replace it?')) {
                    // Retry with replace_existing = true
                    document.getElementById('replaceExistingMeal').checked = true;
                    handleUseRecipe(event);
                    return;
                }
            } else if (data.requires_upgrade && typeof showUpgradeModal === 'function') {
                showUpgradeModal(
                    data.limit_type, 
                    data.current_limit, 
                    data.message
                );
            } else {
                showError(data.message);
            }
        }
    } catch (error) {
        showError('Error using recipe: ' + error.message);
    }
}

async function toggleCurrentRecipeFavorite() {
    if (!currentRecipeId) return;

    try {
        const response = await fetch(`/api/saved-recipes/${currentRecipeId}/favorite`, {
            method: 'POST'
        });

        const data = await response.json();
        
        if (data.success) {
            showSuccess(data.message);
            // Reload recipes to update favorite status
            loadRecipes();
            loadStats();
            // Update the current recipe details if modal is still open
            viewRecipeDetails(currentRecipeId);
        } else {
            showError(data.message);
        }
    } catch (error) {
        showError('Error updating favorite status: ' + error.message);
    }
}

function createNewRecipe() {
    // For now, redirect to meal plans to save recipes from meals
    // In the future, this could open a recipe creation modal
    window.location.href = '/meal-plans';
}

function editRecipe(recipeId) {
    // TODO: Implement recipe editing modal
    showInfo('Recipe editing coming soon! For now, you can create a new recipe from your meal plans.');
}

function editCurrentRecipe() {
    if (currentRecipeId) {
        editRecipe(currentRecipeId);
    }
}

function deleteCurrentRecipe() {
    if (currentRecipeId) {
        // Get the recipe name from the modal title
        const recipeName = document.getElementById('recipeDetailTitle').textContent;
        deleteRecipe(currentRecipeId, recipeName);
    }
}

function clearAllFilters() {
    // Reset all filter inputs to their default values
    document.getElementById('searchFilter').value = '';
    document.getElementById('mealTypeFilter').value = '';
    document.getElementById('favoritesFilter').value = '';
    document.getElementById('sortFilter').value = 'created_at';
    
    // Apply filters to refresh the display
    applyFilters();
    
    showSuccess('All filters cleared');
}

async function deleteRecipe(recipeId, recipeName) {
    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the recipe "${recipeName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/saved-recipes/${recipeId}`, {
            method: 'DELETE'
        });

        const data = await response.json();
        
        if (data.success) {
            showSuccess(data.message);
            // Reload recipes and stats to update the display
            loadRecipes();
            loadStats();
            
            // Close modal if it's currently open for this recipe
            if (currentRecipeId === recipeId) {
                closeRecipeDetailModal();
            }
        } else {
            showError(data.message);
        }
    } catch (error) {
        showError('Error deleting recipe: ' + error.message);
    }
}

// Utility functions for showing messages
function showSuccess(message) {
    showMessage(message, 'success');
}

function showError(message) {
    showMessage(message, 'error');
}

function showInfo(message) {
    showMessage(message, 'info');
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
    switch (type) {
        case 'success':
            messageDiv.style.background = '#10b981';
            break;
        case 'error':
            messageDiv.style.background = '#ef4444';
            break;
        case 'info':
        default:
            messageDiv.style.background = '#3b82f6';
            break;
    }

    messageDiv.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-triangle' : 'fa-info-circle'}"></i>
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