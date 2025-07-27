/**
 * Config pour YT Channel Analyzer
 * Configuration personnalisée pour éviter les erreurs JS
 */

'use strict';

// Configuration globale pour YT Channel Analyzer
window.config = {
  colors: {
    primary: '#696cff',
    secondary: '#8592a3',
    success: '#71dd37',
    info: '#03c3ec',
    warning: '#ffab00',
    danger: '#ff3e1d',
    dark: '#233446',
    black: '#000',
    white: '#fff',
    cardColor: '#fff',
    bodyBg: '#f5f5f9',
    bodyColor: '#697a8d',
    headingColor: '#566a7f',
    textMuted: '#a1acb8',
    borderColor: '#eceef1'
  },
  colors_label: {
    primary: '#666ee81a',
    secondary: '#8592a31a',
    success: '#71dd371a',
    info: '#03c3ec1a',
    warning: '#ffab001a',
    danger: '#ff3e1d1a',
    dark: '#2334461a'
  },
  colors_dark: {
    cardColor: '#2b2c40',
    bodyBg: '#25293c',
    bodyColor: '#b4bdc6',
    headingColor: '#cbcbe2',
    textMuted: '#7983bb',
    borderColor: '#444564'
  },
  enableMenuLocalStorage: false, // Désactiver le localStorage pour éviter les erreurs
  showDropdownOnHover: true,
  displayCustomizer: false, // Désactiver le customizer
  rtl: false,
  style: 'light',
  headerType: 'fixed',
  contentLayout: 'wide',
  layoutCollapsed: false,
  showNavbarDetached: true
};

// Configuration du template customizer (vide pour éviter les erreurs)
window.templateCustomizer = {
  Lang: {
    'Customizer': 'Customizer',
    'Header Type': 'Header Type',
    'Navbar Type': 'Navbar Type',
    'Menu': 'Menu',
    'Collapsed': 'Collapsed',
    'Layout': 'Layout',
    'Bordered': 'Bordered',
    'Semi Dark': 'Semi Dark',
    'Fixed': 'Fixed',
    'Static': 'Static',
    'Detached': 'Detached',
    'Menu Hidden': 'Menu Hidden',
    'Layout Fluid': 'Layout Fluid',
    'Layout Boxed': 'Layout Boxed',
    'Theme': 'Theme',
    'Light': 'Light',
    'Dark': 'Dark',
    'System': 'System'
  }
};

// Configuration pour éviter les erreurs de pagination
if (typeof window.Helpers === 'undefined') {
  window.Helpers = {
    _slideUp: function() {},
    _slideDown: function() {},
    _slideToggle: function() {},
    initCustomOptionCheck: function() {},
    initAOS: function() {},
    navbarToggleClass: function() {},
    handleNavbarToggleClass: function() {},
    scrollToActive: function() {},
    mainLayoutType: 'vertical',
    isRtl: false,
    isStyle: 'light'
  };
}

// Configuration DataTables reportée après l'initialisation de jQuery
window.configureDataTables = function() {
  if (typeof $ !== 'undefined' && typeof $.fn !== 'undefined' && typeof $.fn.DataTable !== 'undefined') {
    $.extend(true, $.fn.dataTable.defaults, {
      language: {
        paginate: {
          pages: {
            previous: 'Précédent',
            next: 'Suivant'
          }
        }
      }
    });
    console.log('📊 DataTables configuré pour YT Channel Analyzer');
  }
};

// Appeler la configuration DataTables quand jQuery est prêt
if (typeof $ !== 'undefined') {
  $(document).ready(function() {
    window.configureDataTables();
  });
} else {
  // Si jQuery n'est pas encore chargé, on attend
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(window.configureDataTables, 100);
  });
}

console.log('✅ Configuration YT Channel Analyzer chargée');