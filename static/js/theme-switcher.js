/**
 * Theme Switcher - Modern Dashboard Theme System
 * Gère le changement de thème et la persistance des préférences utilisateur
 */

class ThemeSwitcher {
    constructor() {
        this.themes = ['ocean', 'forest', 'sunset', 'dark'];
        this.currentTheme = this.getStoredTheme() || 'ocean';
        this.init();
    }

    init() {
        this.createThemeSwitcher();
        this.applyTheme(this.currentTheme);
        this.bindEvents();
        this.handleSystemThemeChange();
    }

    createThemeSwitcher() {
        // Créer le conteneur du switcher
        const switcher = document.createElement('div');
        switcher.className = 'theme-switcher';
        switcher.innerHTML = `
            <div class="theme-switcher-toggle" title="Changer de thème">
                <i class="bi bi-palette"></i>
            </div>
            <div class="theme-options">
                ${this.themes.map(theme => `
                    <div class="theme-option ${theme === this.currentTheme ? 'active' : ''}" 
                         data-theme="${theme}" 
                         title="${this.getThemeName(theme)}">
                        <div class="theme-preview"></div>
                    </div>
                `).join('')}
            </div>
        `;

        // Ajouter le switcher au DOM
        document.body.appendChild(switcher);
    }

    getThemeName(theme) {
        const names = {
            'ocean': 'Ocean Glassmorphism',
            'forest': 'Forest Glassmorphism',
            'sunset': 'Sunset Glassmorphism',
            'dark': 'Corporate Dark'
        };
        return names[theme] || theme;
    }

    bindEvents() {
        const switcher = document.querySelector('.theme-switcher');
        const toggle = switcher.querySelector('.theme-switcher-toggle');
        const options = switcher.querySelector('.theme-options');

        // Toggle du menu
        toggle.addEventListener('click', () => {
            options.classList.toggle('show');
            this.addRippleEffect(toggle);
        });

        // Sélection du thème
        options.addEventListener('click', (e) => {
            const themeOption = e.target.closest('.theme-option');
            if (themeOption) {
                const theme = themeOption.dataset.theme;
                this.switchTheme(theme);
                this.addRippleEffect(themeOption);
                options.classList.remove('show');
            }
        });

        // Fermer le menu en cliquant ailleurs
        document.addEventListener('click', (e) => {
            if (!switcher.contains(e.target)) {
                options.classList.remove('show');
            }
        });

        // Raccourci clavier
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'k') {
                e.preventDefault();
                options.classList.toggle('show');
            }
        });
    }

    switchTheme(theme) {
        if (this.themes.includes(theme)) {
            this.currentTheme = theme;
            this.applyTheme(theme);
            this.storeTheme(theme);
            this.updateActiveOption(theme);
            this.notifyThemeChange(theme);
        }
    }

    applyTheme(theme) {
        // Appliquer le thème au document
        document.documentElement.setAttribute('data-theme', theme);
        
        // Ajouter une classe pour les animations
        document.body.classList.add('theme-switching');
        
        // Retirer la classe après l'animation
        setTimeout(() => {
            document.body.classList.remove('theme-switching');
        }, 300);

        // Mettre à jour les métadonnées
        this.updateMetaThemeColor(theme);
    }

    updateMetaThemeColor(theme) {
        const themeColors = {
            'ocean': '#667eea',
            'forest': '#134e5e',
            'sunset': '#ff6b6b',
            'dark': '#2d3748'
        };

        let metaTheme = document.querySelector('meta[name="theme-color"]');
        if (!metaTheme) {
            metaTheme = document.createElement('meta');
            metaTheme.name = 'theme-color';
            document.head.appendChild(metaTheme);
        }
        metaTheme.content = themeColors[theme];
    }

    updateActiveOption(theme) {
        const options = document.querySelectorAll('.theme-option');
        options.forEach(option => {
            option.classList.remove('active');
            if (option.dataset.theme === theme) {
                option.classList.add('active');
            }
        });
    }

    storeTheme(theme) {
        localStorage.setItem('dashboard-theme', theme);
    }

    getStoredTheme() {
        return localStorage.getItem('dashboard-theme');
    }

    notifyThemeChange(theme) {
        // Créer un événement personnalisé
        const event = new CustomEvent('themeChanged', {
            detail: { theme: theme, themeName: this.getThemeName(theme) }
        });
        document.dispatchEvent(event);

        // Notification visuelle
        this.showNotification(`Thème changé vers ${this.getThemeName(theme)}`);
    }

    showNotification(message) {
        // Créer une notification toast
        const notification = document.createElement('div');
        notification.className = 'theme-notification';
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        // Animation d'apparition
        setTimeout(() => notification.classList.add('show'), 100);
        
        // Retirer la notification après 3 secondes
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    addRippleEffect(element) {
        const ripple = document.createElement('div');
        ripple.className = 'ripple-effect';
        
        element.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
    }

    handleSystemThemeChange() {
        // Écouter les changements de thème système
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                if (!this.getStoredTheme()) {
                    // Si aucun thème n'est stocké, utiliser le thème système
                    const systemTheme = e.matches ? 'dark' : 'ocean';
                    this.switchTheme(systemTheme);
                }
            });
        }
    }

    // Méthodes publiques pour l'API
    getCurrentTheme() {
        return this.currentTheme;
    }

    getAvailableThemes() {
        return this.themes.map(theme => ({
            id: theme,
            name: this.getThemeName(theme)
        }));
    }

    setTheme(theme) {
        this.switchTheme(theme);
    }
}

// Initialiser le switcher de thème au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    window.themeSwitcher = new ThemeSwitcher();
});

// Ajouter les styles CSS pour le switcher
const switcherStyles = `
<style>
.theme-switcher {
    position: fixed;
    top: 50%;
    right: 20px;
    transform: translateY(-50%);
    z-index: 1060;
    font-family: inherit;
}

.theme-switcher-toggle {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: var(--surface-primary);
    backdrop-filter: blur(var(--blur-intensity));
    -webkit-backdrop-filter: blur(var(--blur-intensity));
    border: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: var(--theme-transition);
    box-shadow: var(--shadow-md);
    position: relative;
    overflow: hidden;
}

.theme-switcher-toggle:hover {
    transform: scale(1.05);
    box-shadow: var(--shadow-lg);
    border-color: var(--border-color-strong);
}

.theme-switcher-toggle i {
    font-size: 1.5rem;
    color: var(--text-primary);
    transition: var(--theme-transition);
}

.theme-options {
    position: absolute;
    right: 70px;
    top: 50%;
    transform: translateY(-50%);
    background: var(--surface-overlay);
    backdrop-filter: blur(calc(var(--blur-intensity) * 1.5));
    -webkit-backdrop-filter: blur(calc(var(--blur-intensity) * 1.5));
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-xl);
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    box-shadow: var(--shadow-lg);
    opacity: 0;
    visibility: hidden;
    transform: translateY(-50%) translateX(10px);
    transition: var(--theme-transition);
}

.theme-options.show {
    opacity: 1;
    visibility: visible;
    transform: translateY(-50%) translateX(0);
}

.theme-option {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 2px solid var(--border-color);
    cursor: pointer;
    transition: var(--theme-transition);
    position: relative;
    overflow: hidden;
}

.theme-option:hover {
    transform: scale(1.1);
    box-shadow: var(--shadow-md);
}

.theme-option.active {
    border-color: var(--accent-primary);
    border-width: 3px;
}

.theme-option.active::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: white;
    box-shadow: 0 0 0 2px var(--accent-primary);
}

.theme-option[data-theme="ocean"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
}

.theme-option[data-theme="forest"] {
    background: linear-gradient(135deg, #134e5e 0%, #71b280 50%, #a8e6cf 100%);
}

.theme-option[data-theme="sunset"] {
    background: linear-gradient(135deg, #ff6b6b 0%, #feca57 50%, #ff9ff3 100%);
}

.theme-option[data-theme="dark"] {
    background: linear-gradient(135deg, #2d3748 0%, #4a5568 50%, #1a202c 100%);
}

.theme-notification {
    position: fixed;
    top: 20px;
    right: 20px;
    background: var(--surface-overlay);
    backdrop-filter: blur(var(--blur-intensity));
    -webkit-backdrop-filter: blur(var(--blur-intensity));
    border: 1px solid var(--border-color);
    border-radius: var(--border-radius-md);
    padding: 1rem 1.5rem;
    color: var(--text-primary);
    font-weight: 500;
    box-shadow: var(--shadow-lg);
    z-index: 1070;
    transform: translateX(100%);
    transition: var(--theme-transition);
}

.theme-notification.show {
    transform: translateX(0);
}

.ripple-effect {
    position: absolute;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.6);
    transform: scale(0);
    animation: ripple 0.6s linear;
    pointer-events: none;
}

@keyframes ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

.theme-switching {
    transition: var(--theme-transition);
}

/* Responsive */
@media (max-width: 768px) {
    .theme-switcher {
        bottom: 20px;
        right: 20px;
        top: auto;
        transform: none;
    }
    
    .theme-options {
        right: 0;
        bottom: 70px;
        top: auto;
        transform: translateY(10px);
        flex-direction: row;
    }
    
    .theme-options.show {
        transform: translateY(0);
    }
    
    .theme-notification {
        right: 10px;
        left: 10px;
        top: 10px;
    }
}
</style>
`;

// Injecter les styles
document.head.insertAdjacentHTML('beforeend', switcherStyles); 