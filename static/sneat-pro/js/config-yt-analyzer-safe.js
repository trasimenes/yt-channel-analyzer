/**
 * Config pour YT Channel Analyzer - Version Safe
 * Configuration personnalisée qui ne cause aucune erreur jQuery
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
  enableMenuLocalStorage: false,
  showDropdownOnHover: true,
  displayCustomizer: false,
  rtl: false,
  style: 'light',
  headerType: 'fixed',
  contentLayout: 'wide',
  layoutCollapsed: false,
  showNavbarDetached: true
};

// Configuration du template customizer (désactivé)
window.templateCustomizer = {
  Lang: {
    'Customizer': 'Customizer',
    'Header Type': 'Header Type',
    'Navbar Type': 'Navbar Type',
    'Menu': 'Menu',
    'Layout': 'Layout',
    'Theme': 'Theme'
  }
};

// Helpers de base (sans jQuery)
if (typeof window.Helpers === 'undefined') {
  window.Helpers = {
    mainLayoutType: 'vertical',
    isRtl: false,
    isStyle: 'light'
  };
}

// Fonction utilitaire pour la configuration avancée (appelée plus tard)
window.YTAnalyzerConfig = {
  init: function() {
    console.log('🔧 Initialisation des configurations avancées...');
    
    // Configuration DataTables si disponible
    if (typeof window.$ !== 'undefined' && window.$.fn && window.$.fn.DataTable) {
      try {
        window.$.extend(true, window.$.fn.dataTable.defaults, {
          language: {
            paginate: {
              pages: {
                previous: 'Précédent',
                next: 'Suivant'
              }
            },
            search: 'Rechercher:',
            lengthMenu: 'Afficher _MENU_ entrées',
            info: 'Affichage de _START_ à _END_ sur _TOTAL_ entrées',
            infoEmpty: 'Aucune entrée à afficher',
            infoFiltered: '(filtré sur un total de _MAX_ entrées)',
            zeroRecords: 'Aucun résultat trouvé',
            emptyTable: 'Aucune donnée disponible'
          }
        });
        console.log('📊 DataTables configuré');
      } catch (e) {
        console.warn('⚠️  Erreur configuration DataTables:', e.message);
      }
    }
    
    // Configuration Bootstrap tooltips si disponible
    if (typeof window.bootstrap !== 'undefined' && window.bootstrap.Tooltip) {
      try {
        // Sera initialisé par main-yt-analyzer.js
        console.log('🎯 Bootstrap tooltips disponibles');
      } catch (e) {
        console.warn('⚠️  Erreur Bootstrap tooltips:', e.message);
      }
    }
    
    console.log('✅ Configuration avancée terminée');
  }
};

console.log('✅ Configuration YT Channel Analyzer chargée (version safe)');