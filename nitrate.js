// nitrate.js — shared site JavaScript for nitrateonline.com

(function () {
  'use strict';

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
