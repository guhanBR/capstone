// Theme Switching Manager
(function () {
    const THEME_KEY = 'sparepro_theme_preference';

    function getSavedTheme() {
        const saved = localStorage.getItem(THEME_KEY);
        if (saved) return saved;
        return 'dark'; // Default industrial dark theme
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);

        const icon = document.getElementById('theme-icon');
        const text = document.getElementById('theme-text');
        if (icon) {
            icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
        if (text) {
            text.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
        }
    }

    window.toggleTheme = function () {
        const current = document.documentElement.getAttribute('data-theme') || 'dark';
        const nextTheme = current === 'dark' ? 'light' : 'dark';
        applyTheme(nextTheme);

        // Optionally sync with backend if authenticated
        fetch('/api/user/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ theme: nextTheme })
        }).catch(err => console.log('Theme sync omitted or guest user'));
    };

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Apply on immediate script execute to prevent FOUC (flash of unstyled content)
    applyTheme(getSavedTheme());
})();
