// Upgrade page functionality with Stripe integration

// Initialize Stripe (replace with your publishable key)
const stripe = Stripe('pk_test_51234567890abcdef'); // This would be replaced with actual key
const elements = stripe.elements();

// Current selected plan
let selectedPlan = 'annual';
let selectedPrice = 59.99;

// DOM elements
let cardElement;
let paymentForm;
let codeForm;

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeStripeElements();
    initializePricingToggle();
    initializePlanSelection();
    initializeFAQ();
    initializeCodeForm();
    
    // Set initial plan selection
    updatePlanSelection('annual');
});

// Initialize Stripe Elements
function initializeStripeElements() {
    // Create card element
    cardElement = elements.create('card', {
        style: {
            base: {
                fontSize: '16px',
                color: 'var(--text-primary)',
                fontFamily: 'Quicksand, sans-serif',
                '::placeholder': {
                    color: '#aab7c4',
                }
            },
            invalid: {
                color: '#fa755a',
                iconColor: '#fa755a'
            }
        }
    });

    // Mount card element
    cardElement.mount('#card-element');

    // Handle real-time validation errors from the card Element
    cardElement.on('change', function(event) {
        const displayError = document.getElementById('payment-messages');
        if (event.error) {
            showMessage(event.error.message, 'error', 'payment-messages');
        } else {
            hideMessage('payment-messages');
        }
    });

    // Handle form submission
    paymentForm = document.getElementById('payment-form');
    paymentForm.addEventListener('submit', handlePaymentSubmit);
}

// Initialize pricing toggle
function initializePricingToggle() {
    const toggleOptions = document.querySelectorAll('.toggle-option');
    
    toggleOptions.forEach(option => {
        option.addEventListener('click', function() {
            const period = this.dataset.period;
            
            // Update toggle UI
            toggleOptions.forEach(opt => opt.classList.remove('active'));
            this.classList.add('active');
            
            // Update pricing display
            updatePricingDisplay(period);
        });
    });
}

// Update pricing display based on selected period
function updatePricingDisplay(period) {
    const annualPlan = document.querySelector('.annual-plan');
    const monthlyPlan = document.querySelector('.monthly-plan');
    
    if (period === 'annual') {
        annualPlan.style.display = 'block';
        monthlyPlan.style.display = 'none';
        annualPlan.classList.add('popular');
        monthlyPlan.classList.remove('popular');
    } else {
        annualPlan.style.display = 'none';
        monthlyPlan.style.display = 'block';
        monthlyPlan.classList.add('popular');
        annualPlan.classList.remove('popular');
    }
}

// Initialize plan selection buttons
function initializePlanSelection() {
    const planButtons = document.querySelectorAll('.select-plan-btn');
    
    planButtons.forEach(button => {
        button.addEventListener('click', function() {
            const plan = this.dataset.plan;
            updatePlanSelection(plan);
            
            // Scroll to payment section
            document.querySelector('.payment-section').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        });
    });
}

// Update selected plan
function updatePlanSelection(plan) {
    selectedPlan = plan;
    selectedPrice = plan === 'annual' ? 59.99 : 7.99;
    
    // Update payment button text
    const paymentBtnText = document.getElementById('payment-btn-text');
    const planName = plan === 'annual' ? 'Annual' : 'Monthly';
    const price = plan === 'annual' ? '$59.99/year' : '$7.99/month';
    
    paymentBtnText.textContent = `Pay ${price} - ${planName} Plan`;
    
    // Update visual selection
    document.querySelectorAll('.pricing-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    const selectedCard = document.querySelector(`.${plan}-plan`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
}

// Handle payment form submission
async function handlePaymentSubmit(event) {
    event.preventDefault();
    
    const submitButton = document.getElementById('submit-payment');
    const buttonText = document.getElementById('payment-btn-text');
    const originalText = buttonText.textContent;
    
    // Disable submit button and show loading
    submitButton.disabled = true;
    buttonText.textContent = 'Processing...';
    
    try {
        // Get form data
        const formData = new FormData(paymentForm);
        const email = formData.get('email');
        const name = formData.get('name');
        
        // Validate required fields
        if (!email || !name) {
            throw new Error('Please fill in all required fields');
        }
        
        // Create payment method
        const {error, paymentMethod} = await stripe.createPaymentMethod({
            type: 'card',
            card: cardElement,
            billing_details: {
                name: name,
                email: email,
            },
        });
        
        if (error) {
            throw new Error(error.message);
        }
        
        // For now, just simulate successful payment
        // In production, this would call your backend to create the subscription
        await simulatePaymentProcessing();
        
        // Show success message
        showMessage('Payment successful! Redirecting to your account...', 'success', 'payment-messages');
        
        // Redirect after a delay
        setTimeout(() => {
            window.location.href = '/settings?upgraded=true';
        }, 2000);
        
    } catch (error) {
        // Show error message
        showMessage(error.message, 'error', 'payment-messages');
        
        // Re-enable submit button
        submitButton.disabled = false;
        buttonText.textContent = originalText;
    }
}

// Simulate payment processing (for demo purposes)
function simulatePaymentProcessing() {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve();
        }, 2000);
    });
}

// Initialize promotional code form
function initializeCodeForm() {
    codeForm = document.getElementById('code-form');
    codeForm.addEventListener('submit', handleCodeSubmit);
}

// Handle promotional code submission
async function handleCodeSubmit(event) {
    event.preventDefault();
    
    const codeInput = document.getElementById('promo-code');
    const redeemBtn = document.querySelector('.redeem-btn');
    const code = codeInput.value.trim();
    
    if (!code) {
        showMessage('Please enter a promotional code', 'error', 'code-messages');
        return;
    }
    
    // Disable button and show loading
    redeemBtn.disabled = true;
    redeemBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Checking...';
    
    try {
        // First validate the code
        const validationResponse = await validatePromoCode(code);
        
        if (validationResponse.valid) {
            // Show validation success message with preview
            const previewMessage = validationResponse.preview_message || 'Code is valid!';
            showMessage(`${previewMessage} Redeeming...`, 'success', 'code-messages');
            
            // Wait a moment for user to see the preview
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Now redeem the code
            const redemptionResponse = await redeemPromoCode(code);
            
            if (redemptionResponse.redeemed) {
                showMessage(redemptionResponse.message, 'success', 'code-messages');
                
                // Redirect based on code type
                const redirectUrl = redemptionResponse.redirect_to || '/settings';
                const queryParam = redemptionResponse.code_type === 'upgrade' ? 'upgraded=true&method=code' : 'promo_redeemed=true';
                
                setTimeout(() => {
                    window.location.href = `${redirectUrl}?${queryParam}`;
                }, 2000);
            } else {
                throw new Error(redemptionResponse.message || 'Failed to redeem code');
            }
        } else {
            throw new Error(validationResponse.message || 'Invalid promotional code');
        }
        
    } catch (error) {
        // Handle specific error types
        let errorMessage = 'An error occurred while processing your code';
        
        if (error.message) {
            errorMessage = error.message;
        } else if (error.error) {
            // Handle API error response format
            switch (error.error) {
                case 'code_expired':
                    errorMessage = 'This promotional code has expired';
                    break;
                case 'code_exhausted':
                    errorMessage = 'This promotional code has been fully redeemed';
                    break;
                case 'user_limit_reached':
                    errorMessage = 'You have already used this promotional code';
                    break;
                case 'rate_limited':
                    errorMessage = 'Too many attempts. Please try again later';
                    break;
                case 'not_eligible':
                    errorMessage = 'You are not eligible for this promotional code';
                    break;
                case 'authentication_required':
                    errorMessage = 'Please log in to redeem promotional codes';
                    break;
                default:
                    errorMessage = error.message || 'Invalid promotional code';
            }
        }
        
        showMessage(errorMessage, 'error', 'code-messages');
        
        // Re-enable button
        redeemBtn.disabled = false;
        redeemBtn.innerHTML = '<i class="fas fa-gift"></i> Redeem';
    }
}

// Validate promotional code via API
async function validatePromoCode(code) {
    const response = await fetch('/api/promo-codes/validate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: code }),
        credentials: 'same-origin' // Include session cookies
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        // Throw the error data to be handled by the calling function
        const error = new Error(data.message || 'Validation failed');
        error.error = data.error;
        error.status = response.status;
        throw error;
    }
    
    return data;
}

// Redeem promotional code via API  
async function redeemPromoCode(code) {
    const response = await fetch('/api/promo-codes/redeem', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code: code }),
        credentials: 'same-origin' // Include session cookies
    });
    
    const data = await response.json();
    
    if (!response.ok) {
        // Throw the error data to be handled by the calling function
        const error = new Error(data.message || 'Redemption failed');
        error.error = data.error;
        error.status = response.status;
        throw error;
    }
    
    return data;
}

// Initialize FAQ functionality
function initializeFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        question.addEventListener('click', function() {
            const isActive = item.classList.contains('active');
            
            // Close all other FAQ items
            faqItems.forEach(otherItem => {
                otherItem.classList.remove('active');
            });
            
            // Toggle current item
            if (!isActive) {
                item.classList.add('active');
            }
        });
    });
}

// Utility function to show messages
function showMessage(message, type, containerId) {
    const container = document.getElementById(containerId);
    container.textContent = message;
    container.className = `message ${type} show`;
    
    // Auto-hide error messages after 5 seconds
    if (type === 'error') {
        setTimeout(() => {
            hideMessage(containerId);
        }, 5000);
    }
}

// Utility function to hide messages
function hideMessage(containerId) {
    const container = document.getElementById(containerId);
    container.classList.remove('show');
}

// Add smooth scrolling for internal links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add animation on scroll
function addScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in');
            }
        });
    }, observerOptions);
    
    // Observe all sections
    document.querySelectorAll('section').forEach(section => {
        observer.observe(section);
    });
}

// Initialize scroll animations
addScrollAnimations();

// Handle pricing card hover effects
document.querySelectorAll('.pricing-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = this.classList.contains('popular') ? 'scale(1.05) translateY(-8px)' : 'translateY(-8px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = this.classList.contains('popular') ? 'scale(1.05)' : '';
    });
});

// Feature card interactions
document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('click', function() {
        // Add a subtle bounce effect when clicked
        this.style.transform = 'scale(0.98)';
        setTimeout(() => {
            this.style.transform = '';
        }, 150);
    });
});

// Add loading states for better UX
function addLoadingState(element, originalText) {
    element.disabled = true;
    element.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${originalText}`;
}

function removeLoadingState(element, originalText) {
    element.disabled = false;
    element.innerHTML = originalText;
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // ESC to close any open modals or reset forms
    if (e.key === 'Escape') {
        hideMessage('payment-messages');
        hideMessage('code-messages');
    }
    
    // Enter on pricing cards to select plan
    if (e.key === 'Enter' && e.target.closest('.pricing-card')) {
        const planBtn = e.target.closest('.pricing-card').querySelector('.select-plan-btn');
        if (planBtn) {
            planBtn.click();
        }
    }
});

// Add accessibility improvements
function improveAccessibility() {
    // Add ARIA labels to interactive elements
    document.querySelectorAll('.pricing-card').forEach((card, index) => {
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.setAttribute('aria-label', `Select ${card.querySelector('.plan-name').textContent} plan`);
    });
    
    // Add ARIA labels to FAQ items
    document.querySelectorAll('.faq-question').forEach((question, index) => {
        question.setAttribute('aria-expanded', 'false');
        question.setAttribute('aria-controls', `faq-answer-${index}`);
        
        const answer = question.nextElementSibling;
        if (answer) {
            answer.setAttribute('id', `faq-answer-${index}`);
        }
    });
}

// Initialize accessibility improvements
improveAccessibility();

// Export functions for testing (if needed)
window.upgradePageUtils = {
    updatePlanSelection,
    showMessage,
    hideMessage,
    simulatePaymentProcessing,
    validatePromoCode,
    redeemPromoCode
};