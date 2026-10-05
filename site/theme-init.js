// Runs before first paint so there is no flash of the wrong theme / language.
(function () {
  try {
    var t = localStorage.getItem('sc-theme');
    document.documentElement.className = t === 'light' ? 'light' : 'dark';
    var l = localStorage.getItem('sc-lang');
    if (!l) l = /^en/i.test(navigator.language || '') ? 'en' : 'es';
    document.documentElement.lang = l;
  } catch (e) { document.documentElement.className = 'dark'; }
})();
