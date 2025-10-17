// Theme management functionality
(function() {
    'use strict';
    
    let userThemePreference = 'light'; // system, light, dark
    
    // Get effective theme based on user preference
    function getEffectiveTheme(preference = userThemePreference) {
        if (preference === 'system') {
            // Check system preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                return 'dark';
            }
            return 'light';
        }
        return preference; // 'light' or 'dark'
    }
    
    // Load theme preference from localStorage first, then backend
    async function loadThemePreference() {
        // First check localStorage for immediate access
        const savedTheme = localStorage.getItem('theme-preference');
        if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'system')) {
            userThemePreference = savedTheme;
        }
        
        // Then sync with backend preferences
        try {
            const response = await fetch('/api/user/preferences');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.preferences.theme_preference) {
                    const serverTheme = data.preferences.theme_preference;
                    if (serverTheme !== userThemePreference) {
                        userThemePreference = serverTheme;
                        localStorage.setItem('theme-preference', serverTheme);
                    }
                }
            }
        } catch (error) {
            console.log('Could not load theme preference from server, using local storage');
        }
        
        return getEffectiveTheme();
    }
    
    // Apply theme to document
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }
    
    // Apply theme from preference setting
    function applyThemeFromPreference(preference) {
        userThemePreference = preference;
        // Save to localStorage for immediate access on next page load
        localStorage.setItem('theme-preference', preference);
        const effectiveTheme = getEffectiveTheme(preference);
        applyTheme(effectiveTheme);
    }
    
    // Expose function globally for settings page
    window.applyThemeFromPreference = applyThemeFromPreference;
    
    // Initialize theme on page load
    async function initTheme() {
        // Load theme preference from backend and apply
        const effectiveTheme = await loadThemePreference();
        applyTheme(effectiveTheme);
        
        // Add smooth transition for theme switches
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }
    
    // Initialize when DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
    
})();