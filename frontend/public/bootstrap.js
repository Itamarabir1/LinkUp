(function () {
  try {
    var lang = localStorage.getItem('linkup-lang');
    if (lang === 'en') {
      document.documentElement.setAttribute('lang', 'en');
      document.documentElement.setAttribute('dir', 'ltr');
    }
  } catch (e) {}
})();

(function () {
  try {
    var k = 'linkup-theme';
    var t = localStorage.getItem(k);
    if (t === 'light' || t === 'dark') {
      document.documentElement.setAttribute('data-theme', t);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  } catch (e) {}
})();
