/**
 * Subscription and upgrade utilities for frontend
 */

// Show upgrade modal when user hits subscription limits
// Set redirectOnly to true to go directly to upgrade page instead of showing modal
function showUpgradeModal(limitType, currentLimit, message, redirectOnly = false) {
    if (redirectOnly) {
        window.location.href = '/upgrade';
        return;
    }
    // Remove existing modal if any
    const existingModal = document.getElementById('upgrade-modal');
    if (existingModal) {
        existingModal.remove();
    }

    // Create modal HTML
    const modalHTML = `
    <div id="upgrade-modal" class="modal" style="display: block; z-index: 10000;">
        <div class="modal-content upgrade-modal-content">
            <div class="upgrade-header">
                <div class="upgrade-icon">
                    <i class="fas fa-star"></i>
                </div>
                <h2>Upgrade to Preppr Premium</h2>
                <button class="close-modal" onclick="closeUpgradeModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            
            <div class="upgrade-body">
                <div class="upgrade-message">
                    <p>${message}</p>
                </div>
                
                <div class="upgrade-benefits">
                    <h3>Premium Benefits:</h3>
                    <ul>
                        <li><i class="fas fa-check text-green-500"></i> Unlimited meal plans and advanced planning</li>
                        <li><i class="fas fa-check text-green-500"></i> Unlimited pantry storage</li>
                        <li><i class="fas fa-check text-green-500"></i> Unlimited shopping list generation</li>
                        <li><i class="fas fa-check text-green-500"></i> Full macro tracking with history</li>
                        <li><i class="fas fa-check text-green-500"></i> Advanced shopping optimization</li>
                        <li><i class="fas fa-check text-green-500"></i> Bulk recipe import</li>
                        <li><i class="fas fa-check text-green-500"></i> Smart pantry AI suggestions</li>
                        <li><i class="fas fa-check text-green-500"></i> Priority AI speed</li>
                    </ul>
                </div>
                
                <div class="upgrade-pricing">
                    <div class="pricing-options">
                        <div class="pricing-card popular">
                            <div class="pricing-badge">Most Popular</div>
                            <h4>Annual Plan</h4>
                            <div class="price">
                                <span class="amount">$59.99</span>
                                <span class="period">/year</span>
                            </div>
                            <div class="savings">Save 37% • Just $5/month</div>
                            <button class="btn btn-primary upgrade-btn" onclick="redirectToUpgrade()">
                                Choose Annual
                            </button>
                        </div>
                        
                        <div class="pricing-card">
                            <h4>Monthly Plan</h4>
                            <div class="price">
                                <span class="amount">$7.99</span>
                                <span class="period">/month</span>
                            </div>
                            <div class="savings">Flexible billing</div>
                            <button class="btn btn-secondary upgrade-btn" onclick="redirectToUpgrade()">
                                Choose Monthly
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="upgrade-footer">
                <p><i class="fas fa-shield-alt"></i> 30-day money-back guarantee</p>
            </div>
        </div>
    </div>
    `;

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Add CSS for modal styling
    addUpgradeModalStyles();
    
    // Prevent background scrolling
    document.body.style.overflow = 'hidden';
}

function closeUpgradeModal() {
    const modal = document.getElementById('upgrade-modal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}

function upgradeToPremium(plan) {
    // Redirect to upgrade page instead of handling payment here
    window.location.href = '/upgrade';
    closeUpgradeModal();
}

// Direct redirect to upgrade page (for use in buttons and links)
function redirectToUpgrade() {
    window.location.href = '/upgrade';
}

function addUpgradeModalStyles() {
    // Check if styles already added
    if (document.getElementById('upgrade-modal-styles')) return;
    
    const styles = `
    <style id="upgrade-modal-styles">
    .modal {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        box-sizing: border-box;
    }
    
    .upgrade-modal-content {
        background: var(--bg-primary);
        border-radius: 16px;
        max-width: 600px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        position: relative;
        box-shadow: var(--shadow-xl);
    }
    
    .upgrade-header {
        background: var(--primary-color);
        color: white;
        padding: 24px;
        border-radius: 16px 16px 0 0;
        text-align: center;
        position: relative;
    }
    
    .upgrade-icon {
        width: 60px;
        height: 60px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 16px;
        font-size: 24px;
    }
    
    .upgrade-header h2 {
        margin: 0;
        font-size: 24px;
        font-weight: 700;
    }
    
    .close-modal {
        position: absolute;
        top: 16px;
        right: 16px;
        background: rgba(255, 255, 255, 0.2);
        border: none;
        border-radius: 8px;
        width: 32px;
        height: 32px;
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s ease;
    }
    
    .close-modal:hover {
        background: rgba(255, 255, 255, 0.3);
    }
    
    .upgrade-body {
        padding: 24px;
    }
    
    .upgrade-message {
        text-align: center;
        margin-bottom: 24px;
        color: var(--text-primary);
    }
    
    .upgrade-message p {
        font-size: 16px;
        font-weight: 500;
        margin: 0;
    }
    
    .upgrade-benefits {
        margin-bottom: 32px;
    }
    
    .upgrade-benefits h3 {
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 16px;
        text-align: center;
    }
    
    .upgrade-benefits ul {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    
    .upgrade-benefits li {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0;
        color: var(--text-primary);
        font-weight: 500;
    }
    
    .upgrade-benefits i.fa-check {
        color: var(--primary-color);
        font-size: 14px;
    }
    
    .pricing-options {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
    }
    
    .pricing-card {
        border: 2px solid var(--border-light);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        position: relative;
        background: var(--bg-secondary);
        transition: all 0.2s ease;
    }
    
    .pricing-card:hover {
        border-color: var(--primary-color);
        transform: translateY(-2px);
    }
    
    .pricing-card.popular {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.2);
    }
    
    .pricing-badge {
        position: absolute;
        top: -8px;
        left: 50%;
        transform: translateX(-50%);
        background: var(--primary-color);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .pricing-card h4 {
        color: var(--text-primary);
        font-size: 18px;
        font-weight: 600;
        margin-bottom: 12px;
    }
    
    .price {
        margin-bottom: 8px;
    }
    
    .amount {
        font-size: 28px;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .period {
        font-size: 14px;
        color: var(--text-secondary);
    }
    
    .savings {
        color: var(--primary-color);
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 16px;
    }
    
    .upgrade-btn {
        width: 100%;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        border: none;
        transition: all 0.2s ease;
    }
    
    .btn-primary {
        background: var(--primary-gradient);
        color: white;
    }
    
    .btn-primary:hover {
        transform: translateY(-1px);
        box-shadow: var(--shadow-md);
    }
    
    .btn-secondary {
        background: var(--bg-primary);
        color: var(--text-primary);
        border: 2px solid var(--border-medium);
    }
    
    .btn-secondary:hover {
        border-color: var(--primary-color);
        background: var(--bg-secondary);
    }
    
    .upgrade-footer {
        text-align: center;
        padding: 16px 24px;
        border-top: 1px solid var(--border-light);
        background: var(--bg-secondary);
        border-radius: 0 0 16px 16px;
    }
    
    .upgrade-footer p {
        margin: 0;
        color: var(--text-secondary);
        font-size: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }
    
    .upgrade-footer i {
        color: var(--primary-color);
    }
    
    @media (max-width: 768px) {
        .pricing-options {
            grid-template-columns: 1fr;
        }
        
        .upgrade-modal-content {
            margin: 10px;
            max-width: none;
        }
    }
    </style>
    `;
    
    document.head.insertAdjacentHTML('beforeend', styles);
}

// Handle API responses that contain upgrade requirements
function handleAPIResponse(response, data) {
    if (!response.ok && data && data.requires_upgrade) {
        showUpgradeModal(
            data.limit_type, 
            data.current_limit, 
            data.message
        );
        return true; // Indicates upgrade modal was shown
    }
    return false; // No upgrade modal shown
}

// Utility function to check subscription status
async function getUserSubscriptionStatus() {
    try {
        const response = await fetch('/api/user/subscription-status');
        if (response.ok) {
            return await response.json();
        }
    } catch (error) {
        console.error('Failed to get subscription status:', error);
    }
    return { tier: 'free', unlimited: false };
}

// Export functions for global use
window.showUpgradeModal = showUpgradeModal;
window.closeUpgradeModal = closeUpgradeModal;
window.upgradeToPremium = upgradeToPremium;
window.redirectToUpgrade = redirectToUpgrade;
window.handleAPIResponse = handleAPIResponse;
window.getUserSubscriptionStatus = getUserSubscriptionStatus;