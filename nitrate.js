// nitrate.js — shared site JavaScript for nitrateonline.com

(function () {
  'use strict';

  // Mobile nav toggle
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.querySelector('.primary-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
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
