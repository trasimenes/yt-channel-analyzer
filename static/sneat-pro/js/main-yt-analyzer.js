/**
 * Main JS pour YT Channel Analyzer
 * Version simplifiée sans les fonctionnalités qui causent des erreurs
 */

'use strict';

$(function () {
  console.log('🚀 YT Channel Analyzer - JavaScript initialisé');

  // Initialiser la configuration avancée maintenant que jQuery est prêt
  if (typeof window.YTAnalyzerConfig !== 'undefined' && window.YTAnalyzerConfig.init) {
    window.YTAnalyzerConfig.init();
  }

  // Configuration de base
  let isRtl = $('html').attr('dir') === 'rtl';
  let isStyle = $('html').hasClass('dark-style') ? 'dark' : 'light';

  // Initialisation du menu avec support du hover
  const menuEl = document.getElementById('layout-menu');
  if (menuEl && typeof Menu !== 'undefined') {
    const menu = new Menu(menuEl, {
      orientation: 'vertical', 
      closeChildren: false,
      showDropdownOnHover: window.config.showDropdownOnHover || true,
      animate: true,
      accordion: false
    });
    window.Helpers.mainMenu = menu;
    console.log('✅ Menu initialisé avec support du hover');
  }

  // Perfect Scrollbar pour le menu
  if (typeof PerfectScrollbar !== 'undefined') {
    const menuInner = document.querySelector('#layout-menu .menu-inner');
    if (menuInner) {
      new PerfectScrollbar(menuInner, {
        suppressScrollX: true,
        wheelPropagation: false
      });
    }
  }

  // Gestion du toggle du menu
  const menuToggle = document.querySelector('.layout-menu-toggle');
  if (menuToggle) {
    menuToggle.addEventListener('click', function(e) {
      e.preventDefault();
      window.Helpers.toggleCollapsed();
    });
  }

  // Gestion de la recherche avec toggle
  const searchToggler = document.querySelector('.search-toggler');
  const searchInputWrapper = document.querySelector('.navbar-search-wrapper.search-input-wrapper');
  
  if (searchToggler && searchInputWrapper) {
    searchToggler.addEventListener('click', function(e) {
      e.preventDefault();
      searchInputWrapper.classList.toggle('d-none');
      if (!searchInputWrapper.classList.contains('d-none')) {
        const searchInput = searchInputWrapper.querySelector('.search-input');
        if (searchInput) {
          searchInput.focus();
        }
      }
    });

    // Fermer la recherche avec Escape ou en cliquant sur X
    const searchCloseBtn = searchInputWrapper.querySelector('.search-toggler');
    if (searchCloseBtn) {
      searchCloseBtn.addEventListener('click', function(e) {
        e.preventDefault();
        searchInputWrapper.classList.add('d-none');
      });
    }

    // Fermer avec Escape
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && !searchInputWrapper.classList.contains('d-none')) {
        searchInputWrapper.classList.add('d-none');
      }
    });
  }

  // Helpers pour les fonctions communes
  window.Helpers = $.extend(window.Helpers || {}, {
    LAYOUT_BREAKPOINT: 1200,
    ROOT_EL: document.documentElement,
    
    toggleCollapsed: function() {
      const layout = document.querySelector('.layout-wrapper');
      if (layout) {
        layout.classList.toggle('layout-menu-collapsed');
        // Stocker l'état dans localStorage si activé
        if (window.config.enableMenuLocalStorage) {
          localStorage.setItem('templateCustomizer-' + 'layout-menu-collapsed', 
            layout.classList.contains('layout-menu-collapsed'));
        }
      }
    },

    // Hover behavior pour menu collapsed
    initMenuHover: function() {
      const layoutMenu = document.getElementById('layout-menu');
      const layoutWrapper = document.querySelector('.layout-wrapper');
      
      if (layoutMenu && layoutWrapper) {
        let hoverTimeout;

        // Hover sur le menu quand il est collapsed
        layoutMenu.addEventListener('mouseenter', function() {
          clearTimeout(hoverTimeout);
          if (layoutWrapper.classList.contains('layout-menu-collapsed')) {
            layoutWrapper.classList.add('layout-menu-hover');
          }
        });

        layoutMenu.addEventListener('mouseleave', function() {
          hoverTimeout = setTimeout(function() {
            layoutWrapper.classList.remove('layout-menu-hover');
          }, 300); // Délai de 300ms avant de cacher
        });

        // Éviter que le hover se ferme si on survole le contenu
        const layoutPage = document.querySelector('.layout-page');
        if (layoutPage) {
          layoutPage.addEventListener('mouseenter', function() {
            layoutWrapper.classList.remove('layout-menu-hover');
          });
        }
      }
    },

    initCustomOptionCheck: function() {
      // Initialisation des options personnalisées
      $('.form-check-input[type="checkbox"]').each(function() {
        if (this.checked) {
          $(this).closest('.form-check').addClass('checked');
        }
      });
    },

    // Animation simple pour les éléments
    _slideUp: function(element, duration = 300) {
      $(element).slideUp(duration);
    },

    _slideDown: function(element, duration = 300) {
      $(element).slideDown(duration);
    },

    _slideToggle: function(element, duration = 300) {
      $(element).slideToggle(duration);
    }
  });

  // Initialisation des tooltips Bootstrap
  if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
    $('[data-bs-toggle="tooltip"]').each(function() {
      new bootstrap.Tooltip(this);
    });
  }

  // Initialisation des popovers Bootstrap
  if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
    $('[data-bs-toggle="popover"]').each(function() {
      new bootstrap.Popover(this);
    });
  }

  // Gestion des dropdowns avec hover
  $('.dropdown').hover(
    function() {
      $(this).addClass('show');
      $(this).find('.dropdown-menu').addClass('show');
    },
    function() {
      $(this).removeClass('show');
      $(this).find('.dropdown-menu').removeClass('show');
    }
  );

  // Auto-close alerts
  $('.alert').each(function() {
    const alert = this;
    if ($(alert).find('.btn-close').length) {
      setTimeout(function() {
        $(alert).fadeOut();
      }, 5000);
    }
  });

  // Gestion des formulaires avec validation basique
  $('form').on('submit', function(e) {
    const form = this;
    let isValid = true;

    // Validation des champs requis
    $(form).find('[required]').each(function() {
      if (!this.value.trim()) {
        $(this).addClass('is-invalid');
        isValid = false;
      } else {
        $(this).removeClass('is-invalid');
      }
    });

    if (!isValid) {
      e.preventDefault();
      return false;
    }
  });

  // Smooth scrolling pour les ancres
  $('a[href^="#"]').on('click', function(e) {
    const target = $(this.getAttribute('href'));
    if (target.length) {
      e.preventDefault();
      $('html, body').stop().animate({
        scrollTop: target.offset().top - 100
      }, 1000);
    }
  });

  console.log('✅ YT Channel Analyzer - Interface initialisée avec succès');
});

// Fonctions utilitaires globales
window.YTAnalyzer = {
  showToast: function(message, type = 'info') {
    // Fonction pour afficher des notifications toast
    const toastHtml = `
      <div class="bs-toast toast toast-placement-ex m-2 fade bg-${type} top-0 end-0 show" role="alert">
        <div class="toast-header">
          <i class="bx bx-${type === 'success' ? 'check' : type === 'warning' ? 'error' : type === 'danger' ? 'x' : 'info'}-circle me-2"></i>
          <div class="me-auto fw-semibold">${type === 'success' ? 'Succès' : type === 'warning' ? 'Attention' : type === 'danger' ? 'Erreur' : 'Info'}</div>
          <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
      </div>
    `;
    
    const toastContainer = document.createElement('div');
    toastContainer.innerHTML = toastHtml;
    document.body.appendChild(toastContainer);
    
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
      const toast = new bootstrap.Toast(toastContainer.querySelector('.toast'));
      toast.show();
    }
    
    setTimeout(() => {
      if (toastContainer.parentNode) {
        toastContainer.remove();
      }
    }, 5000);
  },

  loading: {
    show: function(element) {
      $(element).prop('disabled', true).append(' <i class="bx bx-loader-alt bx-spin"></i>');
    },
    hide: function(element) {
      $(element).prop('disabled', false).find('.bx-spin').remove();
    }
  }
};

console.log('📦 YT Channel Analyzer - Utilitaires chargés');