// nitrate.js — shared site JavaScript for nitrateonline.com

(function () {
  'use strict';

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.primary-nav');

  function closeNav() {
    if (nav && nav.classList.contains('open')) {
      nav.classList.remove('open');
      if (toggle) toggle.setAttribute('aria-expanded', 'false');
    }
  }

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
      if (open) {
        // Focus first link when nav opens
        var firstLink = nav.querySelector('a');
        if (firstLink) firstLink.focus();
      }
    });

    // Close nav on Escape key
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        closeNav();
        toggle.focus();
      }
    });

    // Close nav when clicking outside
    document.addEventListener('click', function (e) {
      if (!nav.contains(e.target) && !toggle.contains(e.target)) {
        closeNav();
      }
    });

    // Close nav when a link is clicked (mobile)
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        closeNav();
      }
    });
  }

  // Bing site-scoped search
  document.querySelectorAll('.search-form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var q = form.querySelector('input[type="search"], input[type="text"]');
      if (q && q.value.trim()) {
        window.open(
          'https://www.bing.com/search?q=site%3Anitrateonline.com+' +
            encodeURIComponent(q.value.trim()),
          '_blank',
          'noopener,noreferrer'
        );
      }
    });
  });
})();
