// ============================================================================
// ADVANCED MEAL PLANNING PAGE FUNCTIONALITY
// ============================================================================

let chatbotState = {
  pantryItems: [],
  filteredPantryItems: [],
  selectedPantryItems: [],
  foodRestrictions: [''],
  isLoading: false,
  searchTimeout: null,
  currentConversationId: null,
  conversations: []
};

// Initialize page functionality
document.addEventListener("DOMContentLoaded", function () {
  initializeChatbot();
});

// ============================================================================
// CHATBOT FUNCTIONALITY
// ============================================================================

function initializeChatbot() {
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSendBtn');
  
  if (!chatInput || !sendBtn) return;

  // Chat input functionality
  chatInput.addEventListener('input', updateSendButton);
  chatInput.addEventListener('keypress', handleChatKeyPress);
  sendBtn.addEventListener('click', sendChatMessage);
  
  // Auto-resize textarea
  chatInput.addEventListener('input', autoResizeTextarea);
  
  // Suggestion buttons
  initializeSuggestionButtons();
  
  // Sidebar functionality
  initializeSidebar();
  
  // Sidebar toggle functionality
  initializeSidebarToggle();
  
  // Load pantry items
  loadPantryItems();
  
  // Load conversation history
  loadConversations();
}

function updateSendButton() {
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('chatSendBtn');
  
  if (chatInput && sendBtn) {
    const hasText = chatInput.value.trim().length > 0;
    sendBtn.disabled = !hasText || chatbotState.isLoading;
  }
}

function handleChatKeyPress(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
}

function autoResizeTextarea() {
  const chatInput = document.getElementById('chatInput');
  if (!chatInput) return;
  
  chatInput.style.height = 'auto';
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
}

function sendChatMessage() {
  const chatInput = document.getElementById('chatInput');
  const message = chatInput?.value.trim();
  
  if (!message || chatbotState.isLoading) return;
  
  // Add user message to chat
  addMessageToChat(message, 'user');
  
  // Clear input
  chatInput.value = '';
  updateSendButton();
  autoResizeTextarea();
  
  // Set loading state
  chatbotState.isLoading = true;
  updateSendButton();
  
  // Show typing indicator
  showTypingIndicator();
  
  // Send message to backend
  sendMessageToAPI(message)
    .then(response => {
      hideTypingIndicator();
      
      if (response.success) {
        addMessageToChat(response.response, 'assistant');
        
        // Update conversation ID if this was a new conversation
        if (response.conversation_id && !chatbotState.currentConversationId) {
          chatbotState.currentConversationId = response.conversation_id;
          // Reload conversations list to show the new conversation
          loadConversations();
        }
        
        // Update suggestions if provided
        if (response.suggestions && response.suggestions.length > 0) {
          updateSuggestionButtons(response.suggestions);
        }
        
        // Handle action required (e.g., ready to generate meal plan)
        if (response.action_required && response.meal_plan_data) {
          handleMealPlanGeneration(response.meal_plan_data);
        }
      } else {
        addMessageToChat(response.message || "Sorry, I encountered an error. Please try again.", 'assistant');
      }
      
      chatbotState.isLoading = false;
      updateSendButton();
    })
    .catch(error => {
      hideTypingIndicator();
      console.error('Chat API error:', error);
      addMessageToChat("Sorry, I'm having trouble connecting right now. Please check your connection and try again.", 'assistant');
      chatbotState.isLoading = false;
      updateSendButton();
    });
}

function addMessageToChat(message, sender, metadata = null) {
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${sender}-message`;
  
  messageDiv.innerHTML = `
    <div class="message-content">
      <p>${message}</p>
    </div>
  `;
  
  chatMessages.appendChild(messageDiv);
  
  // Handle metadata (for loaded conversations)
  if (metadata && sender === 'assistant') {
    if (metadata.suggestions && metadata.suggestions.length > 0) {
      updateSuggestionButtons(metadata.suggestions);
    }
  }
  
  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
  
  // Add entrance animation
  messageDiv.style.opacity = '0';
  messageDiv.style.transform = 'translateY(20px)';
  setTimeout(() => {
    messageDiv.style.transition = 'all 0.3s ease';
    messageDiv.style.opacity = '1';
    messageDiv.style.transform = 'translateY(0)';
  }, 50);
}

function showTypingIndicator() {
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) return;
  
  const typingDiv = document.createElement('div');
  typingDiv.id = 'typingIndicator';
  typingDiv.className = 'message assistant-message';
  typingDiv.innerHTML = `
    <div class="message-content">
      <p style="opacity: 0.6;">
        <i class="fas fa-circle" style="animation: pulse 1.5s ease-in-out infinite;"></i>
        <i class="fas fa-circle" style="animation: pulse 1.5s ease-in-out 0.5s infinite;"></i>
        <i class="fas fa-circle" style="animation: pulse 1.5s ease-in-out 1s infinite;"></i>
      </p>
    </div>
  `;
  
  chatMessages.appendChild(typingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
  const typingIndicator = document.getElementById('typingIndicator');
  typingIndicator?.remove();
}

function initializeSuggestionButtons() {
  const suggestionBtns = document.querySelectorAll('.suggestion-btn');
  
  suggestionBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const text = btn.getAttribute('data-text');
      const chatInput = document.getElementById('chatInput');
      
      if (chatInput && text) {
        chatInput.value = text;
        updateSendButton();
        autoResizeTextarea();
        chatInput.focus();
      }
    });
  });
}

// ============================================================================
// SIDEBAR FUNCTIONALITY
// ============================================================================

function initializeSidebar() {
  initializePantrySection();
  initializeFoodRestrictions();
  initializeDietaryPreferences();
}

function initializeSidebarToggle() {
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.chatbot-sidebar');
  
  if (!toggleBtn || !sidebar) return;
  
  toggleBtn.addEventListener('click', () => {
    sidebar.classList.toggle('hidden');
  });
}

function initializePantrySection() {
  // Initialize search functionality
  const searchInput = document.getElementById('pantrySearchInput');
  searchInput?.addEventListener('input', handlePantrySearch);
  searchInput?.addEventListener('focus', handleSearchFocus);
  searchInput?.addEventListener('blur', handleSearchBlur);
  
  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    const searchWrapper = document.querySelector('.pantry-search-wrapper');
    if (!searchWrapper?.contains(e.target)) {
      hideSearchDropdown();
    }
  });
}

function loadPantryItems() {
  // Load all pantry items initially (no search query)
  fetch('/api/pantry/items')
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        chatbotState.pantryItems = data.items || [];
      }
    })
    .catch(error => {
      console.error('Error loading pantry items:', error);
    });
}

function searchPantryItems(searchQuery) {
  if (!searchQuery.trim()) {
    hideSearchDropdown();
    return;
  }
  
  const url = `/api/pantry/items?search=${encodeURIComponent(searchQuery)}`;
  
  fetch(url)
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        chatbotState.filteredPantryItems = data.items || [];
        renderSearchResults(data.items || []);
      } else {
        chatbotState.filteredPantryItems = [];
        renderSearchResults([]);
      }
    })
    .catch(error => {
      console.error('Error searching pantry items:', error);
      chatbotState.filteredPantryItems = [];
      renderSearchResults([]);
    });
}

function renderSearchResults(items) {
  const resultsContainer = document.getElementById('pantrySearchResults');
  if (!resultsContainer) return;
  
  if (items.length === 0) {
    resultsContainer.innerHTML = '<div style="padding: var(--spacing-sm); text-align: center; color: var(--text-muted); font-size: 0.875rem;">No items found</div>';
    showSearchDropdown();
    return;
  }
  
  const itemsHTML = items
    .slice(0, 8) // Limit to 8 items in dropdown
    .map(item => {
      const isSelected = chatbotState.selectedPantryItems.some(selected => selected.pantry_item_id === item.pantry_item_id);
      
      return `
        <div class="search-result-item" data-item-id="${item.pantry_item_id}" style="display: flex; justify-content: space-between; align-items: center; padding: var(--spacing-sm); border-bottom: 1px solid var(--border-light); cursor: pointer; transition: background 0.2s ease;" onmouseover="this.style.background='var(--bg-secondary)'" onmouseout="this.style.background='transparent'">
          <div>
            <div style="font-weight: 500; font-size: 0.875rem; color: var(--text-primary);">${item.item_name}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted);">${item.quantity} ${item.unit || ''}</div>
          </div>
          <button class="add-item-btn" data-item-id="${item.pantry_item_id}" style="background: none; border: none; color: ${isSelected ? 'var(--primary-color)' : 'var(--text-muted)'}; cursor: pointer; padding: 4px; border-radius: 50%; transition: all 0.2s ease;" ${isSelected ? 'disabled' : ''} title="${isSelected ? 'Already selected' : 'Add to selection'}">
            <i class="fas ${isSelected ? 'fa-check' : 'fa-plus'}"></i>
          </button>
        </div>
      `;
    }).join('');
  
  resultsContainer.innerHTML = itemsHTML;
  
  // Add event listeners to add buttons
  resultsContainer.querySelectorAll('.add-item-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const itemId = parseInt(btn.getAttribute('data-item-id'));

      selectPantryItem(itemId);
      
      // Update this specific button to show selected state
      btn.innerHTML = '<i class="fas fa-check"></i>';
      btn.style.color = 'var(--primary-color)';
      btn.disabled = true;
      btn.title = 'Already selected';
    });
  });
  
  showSearchDropdown();
}


function initializeFoodRestrictions() {
  const addRestrictionBtn = document.getElementById('addRestrictionBtn');
  addRestrictionBtn?.addEventListener('click', addFoodRestriction);
  
  // Initialize existing restriction inputs
  updateRestrictionEventListeners();
}

function addFoodRestriction() {
  const restrictionsContainer = document.getElementById('foodRestrictions');
  if (!restrictionsContainer) return;
  
  const restrictionDiv = document.createElement('div');
  restrictionDiv.className = 'restriction-item';
  restrictionDiv.innerHTML = `
    <input type="text" placeholder="Block ingredients..." class="restriction-input" />
    <button class="btn-remove-restriction">
      <i class="fas fa-times"></i>
    </button>
  `;
  
  restrictionsContainer.appendChild(restrictionDiv);
  updateRestrictionEventListeners();
  
  // Focus on new input
  const newInput = restrictionDiv.querySelector('.restriction-input');
  newInput?.focus();
}

function updateRestrictionEventListeners() {
  const removeButtons = document.querySelectorAll('.btn-remove-restriction');
  
  removeButtons.forEach(btn => {
    btn.onclick = (e) => {
      const restrictionItem = e.target.closest('.restriction-item');
      const restrictionsContainer = document.getElementById('foodRestrictions');
      
      // Always keep at least one restriction input
      if (restrictionsContainer?.children.length > 1) {
        restrictionItem?.remove();
      } else {
        // Clear the input instead of removing it
        const input = restrictionItem?.querySelector('.restriction-input');
        if (input) input.value = '';
      }
    };
  });
}

function initializeDietaryPreferences() {
  const dietarySelect = document.getElementById('chatDietaryPreference');
  if (!dietarySelect) return;
  
  // Set default value
  dietarySelect.value = 'none';
}

function getFoodRestrictions() {
  const restrictionInputs = document.querySelectorAll('.restriction-input');
  const restrictions = [];
  
  restrictionInputs.forEach(input => {
    const value = input.value.trim();
    if (value) restrictions.push(value);
  });
  
  return restrictions;
}

function getDietaryPreference() {
  const dietarySelect = document.getElementById('chatDietaryPreference');
  return dietarySelect?.value || 'none';
}

// ============================================================================
// CONVERSATION MANAGEMENT
// ============================================================================

function loadConversations() {
  fetch('/api/conversations')
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        chatbotState.conversations = data.conversations || [];
        renderConversationsList();
      } else {
        console.error('Failed to load conversations:', data.message);
        renderConversationsList([]); // Render empty state
      }
    })
    .catch(error => {
      console.error('Error loading conversations:', error);
      renderConversationsList([]); // Render empty state
    });
}

function renderConversationsList() {
  const conversationsList = document.getElementById('conversationsList');
  if (!conversationsList) return;
  
  if (chatbotState.conversations.length === 0) {
    conversationsList.innerHTML = `
      <div class="empty-conversations" style="text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: var(--spacing-sm);">
        No conversations yet
      </div>
    `;
    return;
  }
  
  const conversationsHTML = chatbotState.conversations.map(conv => {
    const isActive = conv.conversation_id === chatbotState.currentConversationId;
    const lastMessageDate = conv.last_message_at ? new Date(conv.last_message_at).toLocaleDateString() : '';
    
    return `
      <div class="conversation-item ${isActive ? 'active' : ''}" data-conversation-id="${conv.conversation_id}" style="display: flex; justify-content: space-between; align-items: center; padding: var(--spacing-sm); border: 1px solid var(--border-light); border-radius: var(--radius-sm); margin-bottom: var(--spacing-xs); cursor: pointer; transition: all 0.2s ease; ${isActive ? 'background: var(--primary-color); color: white;' : 'background: var(--bg-primary);'}" onmouseover="if (!this.classList.contains('active')) this.style.background='var(--bg-secondary)'" onmouseout="if (!this.classList.contains('active')) this.style.background='var(--bg-primary)'">
        <div style="flex: 1; min-width: 0;">
          <div class="conv-title" style="font-size: 0.85rem; font-weight: 500; margin-bottom: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${conv.title}</div>
          <div class="conv-meta" style="font-size: 0.7rem; opacity: 0.7;">${conv.message_count} messages • ${lastMessageDate}</div>
        </div>
        <button class="btn-delete-conversation" data-conversation-id="${conv.conversation_id}" style="background: none; border: none; color: ${isActive ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)'}; cursor: pointer; padding: 4px; opacity: 0.7; transition: opacity 0.2s;" title="Delete conversation">
          <i class="fas fa-trash fa-xs"></i>
        </button>
      </div>
    `;
  }).join('');
  
  conversationsList.innerHTML = conversationsHTML;
  
  // Add event listeners
  conversationsList.querySelectorAll('.conversation-item').forEach(item => {
    item.addEventListener('click', (e) => {
      if (!e.target.closest('.btn-delete-conversation')) {
        const conversationId = parseInt(item.getAttribute('data-conversation-id'));
        loadConversation(conversationId);
      }
    });
  });
  
  conversationsList.querySelectorAll('.btn-delete-conversation').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const conversationId = parseInt(btn.getAttribute('data-conversation-id'));
      deleteConversation(conversationId);
    });
  });
  
  // Add new chat button listener
  const newChatBtn = document.getElementById('newChatBtn');
  if (newChatBtn) {
    newChatBtn.onclick = startNewConversation;
  }
}

function loadConversation(conversationId) {
  if (conversationId === chatbotState.currentConversationId) return;
  
  fetch(`/api/conversations/${conversationId}`)
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        chatbotState.currentConversationId = conversationId;
        
        // Clear current chat and load messages
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
          chatMessages.innerHTML = '';
          
          // Add messages to chat
          if (data.conversation.messages && data.conversation.messages.length > 0) {
            data.conversation.messages.forEach(msg => {
              addMessageToChat(msg.message, msg.sender, msg.metadata);
            });
          } else {
            // Add welcome message if no messages
            addMessageToChat("Hi! I'm your meal planning assistant. I can help you create personalized meal plans based on your pantry items, dietary preferences, and specific requirements. What kind of meal plan would you like me to create for you?", 'assistant');
          }
        }
        
        // Update conversation list to show active state
        renderConversationsList();
        
        // Load context data if available
        if (data.conversation.context) {
          const context = data.conversation.context;
          
          // Update dietary preference
          if (context.dietary_preference && context.dietary_preference !== 'none') {
            const dietarySelect = document.getElementById('chatDietaryPreference');
            if (dietarySelect) {
              dietarySelect.value = context.dietary_preference;
            }
          }
          
          // Update food restrictions
          if (context.food_restrictions && context.food_restrictions.length > 0) {
            const restrictionsContainer = document.getElementById('foodRestrictions');
            if (restrictionsContainer) {
              // Clear existing restrictions
              restrictionsContainer.innerHTML = '';
              
              // Add saved restrictions
              context.food_restrictions.forEach(restriction => {
                if (restriction.trim()) {
                  const restrictionDiv = document.createElement('div');
                  restrictionDiv.className = 'restriction-item';
                  restrictionDiv.innerHTML = `
                    <input type="text" value="${restriction}" class="restriction-input" />
                    <button class="btn-remove-restriction">
                      <i class="fas fa-times"></i>
                    </button>
                  `;
                  restrictionsContainer.appendChild(restrictionDiv);
                }
              });
              
              // Add one empty restriction if none exist
              if (context.food_restrictions.length === 0 || context.food_restrictions.every(r => !r.trim())) {
                addFoodRestriction();
              }
              
              updateRestrictionEventListeners();
            }
          }
        }
        
      } else {
        console.error('Failed to load conversation:', data.message);
        showMessage('Failed to load conversation', 'error');
      }
    })
    .catch(error => {
      console.error('Error loading conversation:', error);
      showMessage('Error loading conversation', 'error');
    });
}

function startNewConversation() {
  // Reset current conversation
  chatbotState.currentConversationId = null;
  
  // Clear chat messages and show welcome message
  const chatMessages = document.getElementById('chatMessages');
  if (chatMessages) {
    chatMessages.innerHTML = '';
    addMessageToChat("Hi! I'm your meal planning assistant. I can help you create personalized meal plans based on your pantry items, dietary preferences, and specific requirements. What kind of meal plan would you like me to create for you?", 'assistant');
  }
  
  // Reset sidebar inputs
  const dietarySelect = document.getElementById('chatDietaryPreference');
  if (dietarySelect) {
    dietarySelect.value = 'none';
  }
  
  // Clear selected pantry items
  chatbotState.selectedPantryItems = [];
  renderSelectedItems();
  
  // Reset food restrictions to one empty input
  const restrictionsContainer = document.getElementById('foodRestrictions');
  if (restrictionsContainer) {
    restrictionsContainer.innerHTML = `
      <div class="restriction-item">
        <input type="text" placeholder="Block ingredients..." class="restriction-input" />
        <button class="btn-remove-restriction">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;
    updateRestrictionEventListeners();
  }
  
  // Update conversation list to show no active conversation
  renderConversationsList();
}

function deleteConversation(conversationId) {
  if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
    return;
  }
  
  fetch(`/api/conversations/${conversationId}`, {
    method: 'DELETE'
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        // Remove from local state
        chatbotState.conversations = chatbotState.conversations.filter(
          conv => conv.conversation_id !== conversationId
        );
        
        // If this was the current conversation, start a new one
        if (chatbotState.currentConversationId === conversationId) {
          startNewConversation();
        }
        
        // Re-render conversation list
        renderConversationsList();
        
        showMessage('Conversation deleted', 'success');
      } else {
        console.error('Failed to delete conversation:', data.message);
        showMessage('Failed to delete conversation', 'error');
      }
    })
    .catch(error => {
      console.error('Error deleting conversation:', error);
      showMessage('Error deleting conversation', 'error');
    });
}

// ============================================================================
// CHAT API INTEGRATION
// ============================================================================

function sendMessageToAPI(message) {
  const chatMessages = document.getElementById('chatMessages');
  const conversationHistory = [];
  
  // Build conversation history from current chat
  const messages = chatMessages.querySelectorAll('.message');
  messages.forEach(msg => {
    const isUser = msg.classList.contains('user-message');
    const content = msg.querySelector('.message-content p')?.textContent;
    if (content) {
      conversationHistory.push({
        sender: isUser ? 'user' : 'assistant',
        message: content
      });
    }
  });

  const payload = {
    message: message,
    pantry_items: chatbotState.pantryItems,
    selected_pantry_items: chatbotState.selectedPantryItems,
    food_restrictions: getFoodRestrictions(),
    dietary_preference: getDietaryPreference(),
    conversation_history: conversationHistory,
    conversation_id: chatbotState.currentConversationId
  };
  
  return fetch('/api/advanced-meal-planning/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload)
  })
  .then(response => response.json());
}

function updateSuggestionButtons(suggestions) {
  const suggestionContainer = document.querySelector('.chat-suggestions');
  if (!suggestionContainer || !suggestions.length) return;
  
  // Clear existing suggestions
  suggestionContainer.innerHTML = '';
  
  // Add new suggestions
  suggestions.forEach(suggestion => {
    const btn = document.createElement('button');
    btn.className = 'suggestion-btn';
    btn.textContent = suggestion;
    btn.setAttribute('data-text', suggestion);
    
    btn.addEventListener('click', () => {
      const chatInput = document.getElementById('chatInput');
      if (chatInput) {
        chatInput.value = suggestion;
        updateSendButton();
        autoResizeTextarea();
        chatInput.focus();
      }
    });
    
    suggestionContainer.appendChild(btn);
  });
}

function handleMealPlanGeneration(mealPlanData) {
  // Show confirmation dialog
  const confirmed = confirm('I have enough information to generate your meal plan. Would you like me to create it now?');
  
  if (confirmed) {
    // Redirect to meal plans page with parameters
    const params = new URLSearchParams();
    if (mealPlanData.start_date) params.set('start_date', mealPlanData.start_date);
    if (mealPlanData.days) params.set('days', mealPlanData.days);
    if (mealPlanData.dietary_preference) params.set('dietary_preference', mealPlanData.dietary_preference);
    if (mealPlanData.budget) params.set('budget', mealPlanData.budget);
    if (mealPlanData.cooking_time) params.set('cooking_time', mealPlanData.cooking_time);
    
    // Store additional context
    if (mealPlanData.food_restrictions || mealPlanData.ingredients) {
      sessionStorage.setItem('chatbotMealPlanContext', JSON.stringify({
        food_restrictions: mealPlanData.food_restrictions || [],
        preferred_ingredients: mealPlanData.ingredients || []
      }));
    }
    
    const url = `/meal-plans?${params.toString()}&auto_generate=true`;
    window.location.href = url;
  } else {
    addMessageToChat("No problem! Feel free to ask me any other questions about your meal plan.", 'assistant');
  }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

// ============================================================================
// PANTRY SEARCH AND SELECTION FUNCTIONALITY
// ============================================================================

function handlePantrySearch(e) {
  const searchQuery = e.target.value.trim();
  
  // Clear existing timeout
  if (chatbotState.searchTimeout) {
    clearTimeout(chatbotState.searchTimeout);
  }
  
  // Debounce search with 300ms delay
  chatbotState.searchTimeout = setTimeout(() => {
    searchPantryItems(searchQuery);
  }, 300);
}

function handleSearchFocus() {
  const searchInput = document.getElementById('pantrySearchInput');
  if (searchInput?.value.trim()) {
    showSearchDropdown();
  }
}

function handleSearchBlur() {
  // Delay hiding to allow clicks on dropdown items
  setTimeout(() => {
    hideSearchDropdown();
  }, 200);
}

function showSearchDropdown() {
  const dropdown = document.getElementById('pantrySearchResults');
  
  if (dropdown) {
    dropdown.style.display = 'block';
  }
}

function hideSearchDropdown() {
  const dropdown = document.getElementById('pantrySearchResults');
  if (dropdown) {
    dropdown.style.display = 'none';
  }
}

function selectPantryItem(itemId) {
  // Find item in filtered search results
  const item = chatbotState.filteredPantryItems.find(i => i.pantry_item_id === itemId);

  console.log("SJEIHSEGHSEOGHOSEHG")
  
  if (item && !chatbotState.selectedPantryItems.some(selected => selected.pantry_item_id === itemId)) {
    chatbotState.selectedPantryItems.push(item);
    renderSelectedItems();
  }
}

function removePantryItem(itemId) {
  chatbotState.selectedPantryItems = chatbotState.selectedPantryItems.filter(
    item => item.pantry_item_id !== itemId
  );
  renderSelectedItems();
  
  // If search results are visible, refresh them to update the + buttons
  const searchInput = document.getElementById('pantrySearchInput');
  const dropdown = document.getElementById('pantrySearchResults');
  if (dropdown?.style.display !== 'none' && searchInput?.value.trim()) {
    searchPantryItems(searchInput.value.trim());
  }
}

function renderSelectedItems() {
  const selectedList = document.getElementById('selectedItemsList');
  if (!selectedList) return;

  console.log(selectedList);
  
  if (chatbotState.selectedPantryItems.length === 0) {
    selectedList.innerHTML = `
      <div class="empty-state" style="text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: var(--spacing-sm);">
        No items selected yet
      </div>
    `;
    return;
  }
  
  const itemsHTML = chatbotState.selectedPantryItems.map(item => `
    <div class="selected-item" style="display: flex; justify-content: space-between; align-items: center; padding: var(--spacing-xs); background: var(--bg-secondary); border-radius: var(--radius-sm);">
      <span style="font-size: 0.875rem; color: var(--text-primary);">${item.item_name} (${item.quantity} ${item.unit || ''})</span>
      <button class="btn-remove-selected" data-item-id="${item.pantry_item_id}" style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 2px; transition: color 0.2s ease;" title="Remove from selection">
        <i class="fas fa-times"></i>
      </button>
    </div>
  `).join('');
  
  selectedList.innerHTML = itemsHTML;
  
  // Add event listeners to remove buttons
  selectedList.querySelectorAll('.btn-remove-selected').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const itemId = parseInt(btn.getAttribute('data-item-id'));
      removePantryItem(itemId);
    });
    
    // Hover effect
    btn.addEventListener('mouseenter', () => {
      btn.style.color = 'var(--error-color)';
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.color = 'var(--text-muted)';
    });
  });
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