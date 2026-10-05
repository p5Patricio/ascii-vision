(function () {
  'use strict';
  var REPO = 'p5Patricio/ascii-vision';
  var root = document.documentElement;
  var $ = function (s, c) { return (c || document).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
  };

  /* ---------- Copy (ES is the source, EN mirrors it) ---------- */
  var T = {
    es: {
      skip: 'Saltar al contenido', 'nav.label': 'Principal', 'nav.features': 'Funciones', 'nav.how': 'Cómo funciona', 'nav.terminal': 'Terminal', 'nav.faq': 'Preguntas',
      'nav.cta': 'Descargar', 'nav.menu': 'Abrir menú', 'nav.menuClose': 'Cerrar menú', 'nav.lang': 'Cambiar idioma', 'nav.theme': 'Cambiar tema', 'nav.sheet': 'Menú',
      'hero.eyebrow': 'Aplicación de escritorio · Windows', 'hero.title': 'Convierte imágenes y video en arte ASCII.',
      'hero.lead': 'Arrastra una imagen, elige la calidad y exporta a TXT, HTML, SVG o PNG. También convierte video con audio y muestra tu webcam en vivo.',
      'hero.cta1': 'Descargar para Windows', 'hero.cta2': 'Ver cómo funciona', 'hero.meta': 'Windows 10 y 11 · No necesitas instalar Python · Licencia MIT',
      'hero.metaRel': 'Versión {tag} · {mb} MB · Windows 10 y 11 · Licencia MIT',
      'cmp.alt1': 'Paisaje al atardecer con montañas y un lago: imagen original', 'cmp.alt2': 'El mismo paisaje convertido en arte ASCII a color', 'cmp.l': 'Original',
      'cmp.range': 'Desliza para comparar el original con el arte ASCII', 'cmp.cap': 'Hecho con ASCII Vision · calidad High Quality · 150 columnas',
      'feat.eyebrow': 'Funciones', 'feat.title': 'Todo lo que necesitas, en una sola app.', 'feat.desc': 'Pensada para que el resultado se vea bien a la primera y para afinarlo cuando quieras.',
      'f1.t': 'Arrastra y compara', 'f1.d': 'Suelta una imagen y desliza el divisor para comparar el original con el arte ASCII.',
      'f2.t': 'Cuatro niveles de calidad', 'f2.d': 'Fast, Balanced, High y Maximum. Cada uno ajusta la métrica (Brightness, MSE, SSIM) y el juego de caracteres.',
      'f3.t': 'Tu juego de caracteres', 'f3.d': 'ASCII, Shades, Blocks y Braille, o define el tuyo con hasta 256 símbolos.',
      'f4.t': 'Color por carácter', 'f4.d': 'Conserva el color de la imagen y elige fondo negro, blanco o transparente.',
      'f5.t': 'Exporta a lo que quieras', 'f5.d': 'TXT (con color ANSI), HTML autónomo, SVG vectorial, PNG o directo al portapapeles.',
      'f6.t': 'Video con audio', 'f6.d': 'Convierte un video a MP4 H.264 con arte ASCII, conservando el FPS original y el audio. Desde la línea de comandos.',
      'f7.t': 'Webcam en vivo', 'f7.d': 'Vista previa en tiempo real con calidad adaptativa para sostener los FPS que elijas.',
      'f8.t': 'Línea de comandos', 'f8.d': 'Procesa carpetas completas, guarda perfiles y úsalo en tus scripts.',
      'how.eyebrow': 'Cómo funciona', 'how.title': 'De imagen a arte ASCII en tres pasos.', 'how.desc': 'Un recorrido de 40 segundos por las funciones principales.',
      's1.t': 'Arrastra', 's1.d': 'Suelta cualquier PNG, JPG, BMP, WEBP, TIFF o GIF.',
      's2.t': 'Elige', 's2.d': 'Calidad, caracteres, color y fondo; después pulsa «Generate ASCII».',
      's3.t': 'Exporta', 's3.d': 'Guarda en TXT, HTML, SVG o PNG, o cópialo al portapapeles.',
      'video.label': 'Video de presentación de ASCII Vision', 'video.fallback': 'Descargar el video',
      'dl.eyebrow': 'Descarga', 'dl.title': 'Instálalo en un clic.', 'dl.p1': 'Instalador para Windows 10 y 11', 'dl.p2': 'No necesitas instalar Python ni dependencias',
      'dl.p3': 'Se instala solo para tu usuario, sin permisos de administrador', 'dl.p4': 'Gratis y de código abierto (MIT)', 'dl.btn': 'Descargar el instalador',
      'dl.note': 'Si Windows muestra «Windows protegió tu PC», pulsa <strong>Más información → Ejecutar de todas formas</strong>. Aparece porque el instalador aún no cuenta con firma de código.',
      'py.title': '¿Prefieres Python?', 'py.label': 'Instalar con Python', 'py.or': 'o clona el repositorio',
      'cli.eyebrow': 'Terminal', 'cli.title': 'También en tu terminal.', 'cli.desc': 'La misma conversión de la ventana, lista para scripts: lotes, perfiles guardados y video.',
      'faq.eyebrow': 'Preguntas frecuentes', 'faq.title': 'Lo que suelen preguntar.',
      'q1.q': '¿Es gratis?', 'q1.a': 'Sí. ASCII Vision es de código abierto bajo licencia MIT: puedes usarlo, modificarlo y compartirlo.',
      'q2.q': '¿Funciona en Mac o Linux?', 'q2.a': 'El instalador es para Windows. En Mac y Linux puedes usarlo con Python 3.13 o superior, instalándolo desde el repositorio de GitHub (las instrucciones están en la sección de descarga).',
      'q3.q': '¿Qué formatos de imagen acepta?', 'q3.a': 'PNG, JPG, BMP, WEBP, TIFF y GIF. Para video (MP4, AVI, MOV, MKV, WEBM) usa la línea de comandos.',
      'q4.q': '¿Se conserva el audio al convertir un video?', 'q4.a': 'Sí. El resultado mantiene el FPS original y el audio, en MP4 H.264.',
      'q5.q': '¿Mis imágenes se suben a algún servidor?', 'q5.a': 'No. Todo se procesa en tu equipo; la aplicación no envía tus archivos a ningún sitio.',
      'foot.by': 'Desarrollado por', 'foot.tag': 'Convertimos ideas claras en productos digitales listos para crecer.', 'foot.nav': 'Enlaces',
      'foot.code': 'Código en GitHub', 'foot.rel': 'Versiones', 'foot.issue': 'Reportar un problema', 'foot.lic': 'Licencia MIT',
      'meta.title': 'ASCII Vision — Convierte imágenes y video en arte ASCII',
      'meta.desc': 'ASCII Vision convierte imágenes, video y webcam en arte ASCII, Braille y bloques. Exporta a TXT, HTML, SVG o PNG. Descarga gratis el instalador para Windows.'
    },
    en: {
      skip: 'Skip to content', 'nav.label': 'Main', 'nav.features': 'Features', 'nav.how': 'How it works', 'nav.terminal': 'Terminal', 'nav.faq': 'FAQ',
      'nav.cta': 'Download', 'nav.menu': 'Open menu', 'nav.menuClose': 'Close menu', 'nav.lang': 'Change language', 'nav.theme': 'Toggle theme', 'nav.sheet': 'Menu',
      'hero.eyebrow': 'Desktop app · Windows', 'hero.title': 'Turn images and video into ASCII art.',
      'hero.lead': 'Drag in an image, pick the quality and export to TXT, HTML, SVG or PNG. It also converts video with audio and shows your webcam live.',
      'hero.cta1': 'Download for Windows', 'hero.cta2': 'See how it works', 'hero.meta': 'Windows 10 and 11 · No need to install Python · MIT license',
      'hero.metaRel': 'Version {tag} · {mb} MB · Windows 10 and 11 · MIT license',
      'cmp.alt1': 'Sunset landscape with mountains and a lake: original image', 'cmp.alt2': 'The same landscape converted to colour ASCII art', 'cmp.l': 'Original',
      'cmp.range': 'Slide to compare the original with the ASCII art', 'cmp.cap': 'Made with ASCII Vision · High Quality preset · 150 columns',
      'feat.eyebrow': 'Features', 'feat.title': 'Everything you need, in one app.', 'feat.desc': 'Built so the result looks good on the first try, and so you can fine-tune it whenever you want.',
      'f1.t': 'Drag and compare', 'f1.d': 'Drop an image and slide the divider to compare the original with the ASCII art.',
      'f2.t': 'Four quality levels', 'f2.d': 'Fast, Balanced, High and Maximum. Each one sets the metric (Brightness, MSE, SSIM) and the character set.',
      'f3.t': 'Your own character set', 'f3.d': 'ASCII, Shades, Blocks and Braille, or define your own with up to 256 symbols.',
      'f4.t': 'Colour per character', 'f4.d': 'Keep the image’s colour and choose a black, white or transparent background.',
      'f5.t': 'Export to anything', 'f5.d': 'TXT (with ANSI colour), standalone HTML, vector SVG, PNG or straight to the clipboard.',
      'f6.t': 'Video with audio', 'f6.d': 'Turn a video into an ASCII-art H.264 MP4 that keeps the original frame rate and audio. From the command line.',
      'f7.t': 'Live webcam', 'f7.d': 'Real-time preview with adaptive quality to hold the FPS you choose.',
      'f8.t': 'Command line', 'f8.d': 'Process whole folders, save profiles and use it in your scripts.',
      'how.eyebrow': 'How it works', 'how.title': 'From image to ASCII art in three steps.', 'how.desc': 'A 40-second tour of the main features.',
      's1.t': 'Drag', 's1.d': 'Drop any PNG, JPG, BMP, WEBP, TIFF or GIF.',
      's2.t': 'Choose', 's2.d': 'Quality, characters, colour and background; then press “Generate ASCII”.',
      's3.t': 'Export', 's3.d': 'Save as TXT, HTML, SVG or PNG, or copy it to the clipboard.',
      'video.label': 'ASCII Vision presentation video', 'video.fallback': 'Download the video',
      'dl.eyebrow': 'Download', 'dl.title': 'Install it in one click.', 'dl.p1': 'Installer for Windows 10 and 11', 'dl.p2': 'No need to install Python or dependencies',
      'dl.p3': 'Installs for your user only, no administrator rights', 'dl.p4': 'Free and open source (MIT)', 'dl.btn': 'Download the installer',
      'dl.note': 'If Windows shows “Windows protected your PC”, choose <strong>More info → Run anyway</strong>. It appears because the installer is not code-signed yet.',
      'py.title': 'Prefer Python?', 'py.label': 'Install with Python', 'py.or': 'or clone the repository',
      'cli.eyebrow': 'Terminal', 'cli.title': 'Also in your terminal.', 'cli.desc': 'The same conversion as the window, ready for scripts: batches, saved profiles and video.',
      'faq.eyebrow': 'FAQ', 'faq.title': 'What people ask.',
      'q1.q': 'Is it free?', 'q1.a': 'Yes. ASCII Vision is open source under the MIT license: you can use, modify and share it.',
      'q2.q': 'Does it work on Mac or Linux?', 'q2.a': 'The installer is for Windows. On Mac and Linux you can run it with Python 3.13 or newer, installing from the GitHub repository (the steps are in the download section).',
      'q3.q': 'Which image formats does it accept?', 'q3.a': 'PNG, JPG, BMP, WEBP, TIFF and GIF. For video (MP4, AVI, MOV, MKV, WEBM) use the command line.',
      'q4.q': 'Is the audio kept when converting a video?', 'q4.a': 'Yes. The result keeps the original frame rate and the audio, as H.264 MP4.',
      'q5.q': 'Are my images uploaded to a server?', 'q5.a': 'No. Everything is processed on your computer; the app never sends your files anywhere.',
      'foot.by': 'Built by', 'foot.tag': 'We turn clear ideas into digital products ready to grow.', 'foot.nav': 'Links',
      'foot.code': 'Code on GitHub', 'foot.rel': 'Releases', 'foot.issue': 'Report an issue', 'foot.lic': 'MIT license',
      'meta.title': 'ASCII Vision — Turn images and video into ASCII art',
      'meta.desc': 'ASCII Vision turns images, video and webcam into ASCII, Braille and block art. Export to TXT, HTML, SVG or PNG. Download the Windows installer for free.'
    }
  };
  var lang = root.lang === 'en' ? 'en' : 'es';
  var release = null;
  var t = function (k) { return (T[lang] && T[lang][k]) || T.es[k] || k; };

  function applyLang() {
    root.lang = lang;
    $$('[data-i18n]').forEach(function (el) { el.textContent = t(el.getAttribute('data-i18n')); });
    $$('[data-i18n-html]').forEach(function (el) { el.innerHTML = t(el.getAttribute('data-i18n-html')); });
    $$('[data-i18n-attr]').forEach(function (el) {
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var p = pair.split(':'); if (p.length === 2) el.setAttribute(p[0].trim(), t(p[1].trim()));
      });
    });
    document.title = t('meta.title');
    var d = $('meta[name="description"]'); if (d) d.setAttribute('content', t('meta.desc'));
    var og = $('meta[property="og:title"]'); if (og) og.setAttribute('content', t('meta.title'));
    $('#lang-label').textContent = lang === 'es' ? 'EN' : 'ES';
    setMenuLabel(menuOpen);
    renderMeta();
  }
  $('#lang').addEventListener('click', function () { lang = lang === 'es' ? 'en' : 'es'; store.set('sc-lang', lang); applyLang(); });

  /* ---------- Theme ---------- */
  $('#theme').addEventListener('click', function () {
    var next = root.classList.contains('light') ? 'dark' : 'light';
    root.className = next; store.set('sc-theme', next);
    var m = $('meta[name="theme-color"]'); if (m) m.setAttribute('content', next === 'light' ? '#f5f7fa' : '#05070b');
  });

  /* ---------- Navbar: border after 8px of scroll ---------- */
  var nav = $('#nav');
  function onScroll() { nav.classList.toggle('is-scrolled', window.scrollY > 8); }
  window.addEventListener('scroll', onScroll, { passive: true }); onScroll();

  /* ---------- Mobile sheet: scroll lock, Escape, focus trap + return ---------- */
  var sheet = $('#sheet'), menuBtn = $('#menu'), menuOpen = false, lastFocus = null;
  var main = $('#main'), footer = $('.footer');
  function setMenuLabel(open) { var l = t(open ? 'nav.menuClose' : 'nav.menu'); menuBtn.setAttribute('aria-label', l); menuBtn.setAttribute('title', l); }
  function focusables() { return $$('a[href], button:not([disabled])', sheet).concat([menuBtn]); }
  function toggleSheet(open) {
    menuOpen = open; sheet.hidden = !open; menuBtn.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('is-locked', open);
    [main, footer].forEach(function (n) { if (open) n.setAttribute('inert', ''); else n.removeAttribute('inert'); });
    setMenuLabel(open);
    if (open) { lastFocus = document.activeElement; var f = $('a', sheet); if (f) f.focus(); }
    else if (lastFocus) { menuBtn.focus(); lastFocus = null; }
  }
  menuBtn.addEventListener('click', function () { toggleSheet(!menuOpen); });
  $$('a', sheet).forEach(function (a) { a.addEventListener('click', function () { toggleSheet(false); }); });
  document.addEventListener('keydown', function (e) {
    if (!menuOpen) return;
    if (e.key === 'Escape') { e.preventDefault(); toggleSheet(false); return; }
    if (e.key === 'Tab') {
      var f = focusables(), first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  window.matchMedia('(min-width: 1024px)').addEventListener('change', function (m) { if (m.matches && menuOpen) toggleSheet(false); });

  /* ---------- Active section -> aria-current ---------- */
  var links = $$('.nav__links a[href^="#"]');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) {
          if (a.getAttribute('href') === '#' + en.target.id) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    $$('main section[id]').forEach(function (s) { io.observe(s); });
  }

  /* ---------- Before / after comparer ---------- */
  var cmp = $('#cmp'), range = $('#cmp-range');
  function setPos(v) { cmp.style.setProperty('--pos', v + '%'); }
  range.addEventListener('input', function () { setPos(range.value); });
  setPos(range.value);

  /* ---------- Download: point the buttons at the newest installer ---------- */
  var dlLinks = [$('#dl-hero'), $('#dl-main')], meta = $('#dlmeta');
  function renderMeta() {
    if (!release) { meta.textContent = t('hero.meta'); return; }
    meta.textContent = t('hero.metaRel').replace('{tag}', release.tag).replace('{mb}', release.mb);
  }
  try {
    fetch('https://api.github.com/repos/' + REPO + '/releases/latest', { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (rel) {
        var a = (rel.assets || []).filter(function (x) { return /setup.*\.exe$/i.test(x.name); })[0];
        if (!a) return;
        dlLinks.forEach(function (l) { if (l) l.href = a.browser_download_url; });
        release = { tag: rel.tag_name, mb: Math.round(a.size / 1048576) }; renderMeta();
      })
      .catch(function () { /* no release yet: buttons keep opening the releases page */ });
  } catch (e) { /* ignore */ }

  applyLang();
})();
