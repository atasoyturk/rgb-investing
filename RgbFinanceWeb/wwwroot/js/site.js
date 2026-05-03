
(function () {


    var THEME_KEY = 'rgb-finance-theme';

    function getStoredTheme() {
        return localStorage.getItem(THEME_KEY) || 'light';
    }

    function applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        var btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.textContent = theme === 'dark' ? 'Light Theme' : 'Dark Theme';
        }
        localStorage.setItem(THEME_KEY, theme);
    }

    function toggleTheme() {
        var current = document.body.getAttribute('data-theme') || 'light';
        applyTheme(current === 'dark' ? 'light' : 'dark');
    }

    /* --- Sayfa yüklenince temayı uygula --- */
    document.addEventListener('DOMContentLoaded', function () {
        applyTheme(getStoredTheme());

        var btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.addEventListener('click', toggleTheme);
        }
    });

    /* --- Güven çubuklarını canlandır --- */
    document.addEventListener('DOMContentLoaded', function () {
        var fills = document.querySelectorAll('.conf-fill[data-width]');
        fills.forEach(function (el) {
            var width = el.getAttribute('data-width');
            setTimeout(function () {
                el.style.width = width + '%';
            }, 100);
        });
    });
    
})();