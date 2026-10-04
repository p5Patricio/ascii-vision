(() => {
const W = 1080, H = 1920;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, a, b) => clamp((t - a) / (b - a));
const eo = x => 1 - Math.pow(1 - x, 3);
const eio = x => (x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const ebk = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const lerp = (a, b, x) => a + (b - a) * x;
const $ = id => document.getElementById(id);
const hash = (a, b = 0, c = 0) => { let h = (a * 374761393 + b * 668265263 + c * 2147483647) | 0; h = (h ^ (h >>> 13)) * 1274126177 | 0; return ((h ^ (h >>> 16)) >>> 0) / 4294967295; };

const SCENES = [['s0', 0, 3.4], ['s1', 3.4, 7.4], ['s2', 7.4, 11.4], ['s3', 11.4, 15.0], ['s4', 15.0, 18.6], ['s5', 18.6, 22.4],
  ['s6', 22.4, 26.4], ['s7', 26.4, 29.0], ['s8', 29.0, 32.8], ['s9', 32.8, 35.8], ['s10', 35.8, 40.0]];
const DUR = 40.0;
const GLOW = { s0: [[25, 224, 255], [31, 92, 255]], s1: [[31, 92, 255], [25, 224, 255]], s2: [[53, 224, 122], [31, 92, 255]], s3: [[25, 224, 255], [150, 80, 255]],
  s4: [[255, 90, 160], [25, 224, 255]], s5: [[31, 92, 255], [53, 224, 122]], s6: [[150, 80, 255], [25, 224, 255]], s7: [[53, 224, 122], [25, 224, 255]],
  s8: [[25, 224, 255], [53, 224, 122]], s9: [[31, 92, 255], [25, 224, 255]], s10: [[31, 92, 255], [25, 224, 255]] };

// ---------------------------------------------------------------- headlines
function buildHeadline(h) {
  let html = ''; const parts = h.dataset.t.split('<br>');
  parts.forEach((ln, li) => {
    let accent = false;
    ln.split(/(\{|\})/).forEach(tk => {
      if (tk === '{') accent = true; else if (tk === '}') accent = false;
      else tk.split(/\s+/).filter(Boolean).forEach(w => { html += `<span class="w">${accent ? `<em>${w}</em>` : w}</span> `; });
    });
    if (li < parts.length - 1) html += '<br>';
  });
  h.innerHTML = html;
}
function animHead(sec, L) {
  sec.querySelectorAll('h1.hl .w').forEach((w, i) => {
    const p = eo(prog(L, 0.08 + i * 0.09, 0.08 + i * 0.09 + 0.55));
    w.style.transform = `translateY(${(1 - p) * 46}px)`; w.style.opacity = p; w.style.filter = `blur(${(1 - p) * 12}px)`;
  });
}
const pop = (el, p, from = .86) => { el.style.opacity = clamp(p * 1.4); el.style.transform = `translateY(${(1 - p) * 30}px) scale(${lerp(from, 1, p)})`; };

// ---------------------------------------------------------------- ascii drawing
const REFW = 12, REFH = 26.4, GL = 'abcdefghijklmnopqrstuvwxyz0123456789#@%&*+=<>/\\|{}░▒▓█▀▄';
function prep(d) {
  if (d._cs) return d;
  d._chars = d.rows.map(r => Array.from(r));
  d._cs = [];
  if (d.colors) { const bin = atob(d.colors); const b = d._dark ? (v => Math.round(v * .55)) : (v => Math.min(255, Math.round(v * 1.45 + 14))); for (let i = 0; i < d.n * d.cols; i++) d._cs.push(`rgb(${b(bin.charCodeAt(i * 3))},${b(bin.charCodeAt(i * 3 + 1))},${b(bin.charCodeAt(i * 3 + 2))})`); }
  return d;
}
// p: reveal progress 0..1 (sweeping left->right with noise); glitch glyphs while settling.
function drawAscii(ctx, d, x, y, w, h, o = {}) {
  prep(d);
  const rows = d.n, cols = d.cols, cw = w / cols, ch = h / rows, p = o.p === undefined ? 1 : o.p, fr = o.frame || 0;
  ctx.save(); ctx.translate(x, y); ctx.scale(cw / REFW, ch / REFH);
  ctx.font = `20px JB, DJV, monospace`; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
  for (let r = 0; r < rows; r++) {
    const row = d._chars[r];
    for (let c = 0; c < cols; c++) {
      const ch0 = row[c]; if (ch0 === ' ') continue;
      let t0 = (o.sweep === false ? hash(r, c) : (c / cols) * .72 + hash(r, c) * .28) * .75;
      let glyph = ch0, fill = d._cs.length ? d._cs[r * cols + c] : (o.mono || '#cfe3ff');
      if (p < 1) {
        if (p <= t0) continue;
        if (p < t0 + .25) { glyph = GL[Math.floor(hash(r, c, fr) * GL.length)]; fill = '#8ff3ff'; }
      }
      ctx.fillStyle = fill; ctx.fillText(glyph, c * REFW, (r + .5) * REFH);
    }
  }
  ctx.restore();
}
function offscreen(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
const IMG = {}; const OFF = {};
function loadImg(src) { return new Promise(res => { const i = new Image(); i.onload = () => res(i); i.src = src; }); }

// ---------------------------------------------------------------- persistent layers
const glowCv = $('glow'), glowCtx = glowCv.getContext('2d'); glowCv.style.width = W + 'px'; glowCv.style.height = H + 'px';
function drawGlow(t) {
  let i = SCENES.findIndex(s => t >= s[1] && t < s[2]); if (i < 0) i = SCENES.length - 1;
  const cur = GLOW[SCENES[i][0]], nxt = GLOW[SCENES[Math.min(i + 1, SCENES.length - 1)][0]];
  const k = eio(prog(t, SCENES[i][2] - .6, SCENES[i][2]));
  const mix = (a, b) => a.map((v, j) => Math.round(lerp(v, b[j], k)));
  const A = mix(cur[0], nxt[0]), B = mix(cur[1], nxt[1]);
  glowCtx.clearRect(0, 0, 270, 480);
  let g = glowCtx.createRadialGradient(135, 90 + Math.sin(t) * 6, 0, 135, 90, 190); g.addColorStop(0, `rgba(${A},.26)`); g.addColorStop(1, `rgba(${A},0)`);
  glowCtx.fillStyle = g; glowCtx.fillRect(0, 0, 270, 480);
  g = glowCtx.createRadialGradient(135, 400 + Math.cos(t) * 6, 0, 135, 400, 200); g.addColorStop(0, `rgba(${B},.22)`); g.addColorStop(1, `rgba(${B},0)`);
  glowCtx.fillStyle = g; glowCtx.fillRect(0, 0, 270, 480);
}
const rainCv = $('rain'), rainCtx = rainCv.getContext('2d'); const RAIN = '.:-=+*#%@01<>/\\|{}░▒▓';
function drawRain(t, amp) {
  rainCtx.clearRect(0, 0, W, H); rainCtx.font = '22px JB, DJV, monospace'; rainCtx.textBaseline = 'top';
  for (let k = 0; k < 39; k++) {
    const x = k * 28 + 10, sp = 60 + hash(k) * 140, off = hash(k, 1) * 2600, y = ((t * sp + off) % 2600) - 300;
    for (let j = 0; j < 14; j++) {
      const yy = y - j * 26; if (yy < -24 || yy > H + 24) continue;
      const ch = RAIN[Math.floor(hash(k, j, Math.floor(t * 5 + j * .3)) * RAIN.length)];
      rainCtx.fillStyle = `rgba(25,224,255,${(1 - j / 14) * (j === 0 ? .55 : .22) * amp})`; rainCtx.fillText(ch, x, yy);
    }
  }
}
const prog$ = $('prog'); SCENES.forEach(() => { prog$.insertAdjacentHTML('beforeend', '<i><b></b></i>'); });

// ---------------------------------------------------------------- scene state
const el = {}; SCENES.forEach(s => el[s[0]] = $(s[0]));
let ctx0, ctx1, ctx3, ctx4, ctx6, ctxw, ctx7, ctx8;

function setup() {
  document.querySelectorAll('h1.hl').forEach(buildHeadline);
  SCENES.forEach(([id]) => { if (id === 's10') return; const sec = el[id], wrap = document.createElement('div'); wrap.className = 'body'; wrap.style.cssText = 'position:absolute;inset:0;transform:translateY(' + (id === 's1' ? 110 : id === 's9' ? 170 : 120) + 'px)';
    Array.from(sec.children).forEach(c => { if (!c.matches('h1.hl')) wrap.appendChild(c); }); sec.appendChild(wrap); });
  ctx0 = $('s0cv').getContext('2d'); ctx1 = $('s1cv').getContext('2d'); ctx3 = $('s3cv').getContext('2d'); ctx4 = $('s4cv').getContext('2d');
  ctx6 = $('s6cv').getContext('2d'); ctxw = $('s6wave').getContext('2d'); ctx7 = $('s7cv').getContext('2d');
  // S2 tiles
  const T = [['FAST', 'Brightness · Shades', 'preset_fast'], ['BALANCED', 'MSE · ASCII', 'preset_balanced'], ['HIGH', 'SSIM · ASCII', 'preset_high'], ['MAX', 'SSIM · Braille', 'preset_max']];
  let html = ''; T.forEach((t, i) => {
    const x = 60 + (i % 2) * 498, y = 520 + Math.floor(i / 2) * 500;
    html += `<div class="card" id="s2t${i}" style="left:${x}px;top:${y}px;width:462px;height:470px;background:#070d1d"><canvas id="s2c${i}" width="430" height="323" style="margin:16px"></canvas>
      <div style="position:absolute;left:24px;top:358px;font:800 38px 'Syne'">${t[0]}</div><div style="position:absolute;left:24px;top:410px;font:700 19px 'Space Mono';color:#8aa0cc">${t[1]}</div>
      <div id="s2b${i}" style="position:absolute;right:20px;top:372px;width:20px;height:20px;border-radius:50%;background:var(--gr);box-shadow:0 0 18px var(--gr);opacity:0"></div></div>`;
  });
  $('s2tiles').innerHTML = html;
  // S3 chips
  const C = [['ASCII', '@%#*+=-:.', 60, 1290, 460], ['SHADES', '░▒▓█', 560, 1290, 460], ['BLOCKS', '▄▖▗▘▙▚▛▜', 60, 1380, 460], ['BRAILLE', '⣿⣷⣯⣟⡿⢿⣻⣽', 560, 1380, 460], ['TUS SÍMBOLOS', '.o(O#', 60, 1470, 960]];
  html = ''; C.forEach((c, i) => { html += `<div class="chip" id="s3c${i}" style="left:${c[2]}px;top:${c[3]}px;width:${c[4]}px;font-size:22px"><b style="font:700 20px 'Space Mono';margin-right:16px">${c[0]}</b><span style="font-family:JB,DJV;font-size:26px">${c[1]}</span></div>`; });
  $('s3chips').innerHTML = html;
  // S4 chips
  html = ''; [['Black', 60], ['White', 300], ['Transparent', 540]].forEach((c, i) => { html += `<div class="chip" id="s4c${i}" style="left:${c[1]}px;top:1290px;width:${i == 2 ? 480 : 220}px;text-align:center">${c[0]}</div>`; });
  html += `<div class="chip" id="s4c3" style="left:60px;top:1390px;width:960px;text-align:center">Color por carácter · ANSI · HTML · SVG · PNG</div>`;
  $('s4chips').innerHTML = html;
  // S5 list
  const E = [['TXT', 'ascii_art.txt', 'Texto con color ANSI 24 bits'], ['HTML', 'ascii_art.html', 'Autónomo y comprimido por tramos'], ['SVG', 'ascii_art.svg', 'Vectorial: escala sin perder nitidez'],
    ['PNG', 'ascii_art.png', 'Con fondo negro, blanco o transparente'], ['COPIAR', 'Portapapeles', 'Pega tu arte donde quieras']];
  html = ''; E.forEach((e, i) => {
    html += `<div class="card" id="s5c${i}" style="left:60px;top:${520 + i * 176}px;width:960px;height:152px;background:#0a1226">
      <canvas id="s5t${i}" width="168" height="126" style="position:absolute;left:14px;top:13px;border-radius:12px;background:#05070f"></canvas>
      <div style="position:absolute;left:210px;top:24px;font:800 44px 'Syne'">${e[0]}</div>
      <div style="position:absolute;left:210px;top:84px;font:700 20px 'Space Mono';color:#9fb4e8">${e[1]}</div>
      <div style="position:absolute;left:210px;top:114px;font:500 19px 'Inter';color:#7d8db3">${e[2]}</div>
      <div id="s5k${i}" class="chip on" style="right:24px;top:52px;padding:12px 22px;font-size:20px;background:rgba(53,224,122,.18);border-color:var(--gr);color:#d8ffe8;opacity:0">✔ ${i == 4 ? 'Copiado' : 'Guardado'}</div></div>`;
  });
  $('s5list').innerHTML = html;
  E.forEach((e, i) => { const c = $('s5t' + i).getContext('2d'); drawAscii(c, DATA.hero_color, 0, 0, 168, 126); });
  // S6 chips, S9 chips
  html = ''; ['FPS ORIGINAL', 'AUDIO CONSERVADO', 'H.264'].forEach((c, i) => { html += `<div class="chip" id="s6c${i}" style="left:${[90, 392, 746][i]}px;top:1500px">${c}</div>`; });
  $('s6chips').innerHTML = html;
  html = '<div style="display:flex;gap:16px">'; ['Windows 10 / 11', 'Sin instalar Python'].forEach((c, i) => { html += `<div class="chip on" id="s9c${i}" style="position:static">${c}</div>`; });
  html += '</div><div class="chip on" id="s9c2" style="position:static">Sin permisos de administrador</div>';
  $('s9chips').innerHTML = html;
  // pre-rendered offscreens
  ['ascii', 'shades', 'blocks', 'braille'].forEach(n => { const o = offscreen(960, 720); const c = o.getContext('2d'); c.fillStyle = '#05070f'; c.fillRect(0, 0, 960, 720); drawAscii(c, DATA['cs_' + n], 30, 30, 900, 675); OFF['cs_' + n] = o; });
  const mk = (bg, d) => { const o = offscreen(960, 720); const c = o.getContext('2d');
    if (bg === 'black') { c.fillStyle = '#05060c'; c.fillRect(0, 0, 960, 720); }
    else if (bg === 'white') { c.fillStyle = '#fff'; c.fillRect(0, 0, 960, 720); }
    else { for (let y = 0; y < 720; y += 24) for (let x = 0; x < 960; x += 24) { c.fillStyle = ((x + y) / 24) % 2 ? '#2a3041' : '#1d2230'; c.fillRect(x, y, 24, 24); } }
    drawAscii(c, d, 30, 30, 900, 675); return o; };
  DATA.hero_color_white._dark = true; OFF.black = mk('black', DATA.hero_color); OFF.white = mk('white', DATA.hero_color_white); OFF.trans = mk('trans', DATA.hero_color);
  // terminal
  term.init();
}

// ---------------------------------------------------------------- terminal typewriter
const term = { lines: [
  ['$ ascii-vision --input foto.jpg --output arte.png --color', 'cmd'], ['✔ Saved arte.png', 'ok'],
  ['$ ascii-vision --input-glob "fotos/*.jpg" --output out/', 'cmd'], ['✔ 48 files converted', 'ok'],
  ['$ ascii-vision --input clip.mp4 --output ascii.mp4', 'cmd'], ['✔ Saved ascii.mp4', 'ok']], sched: [],
  init() { let t = 0.55; this.lines.forEach(l => { const n = l[0].length; if (l[1] === 'cmd') { this.sched.push([t, t + n / 120]); t += n / 120 + .2; } else { this.sched.push([t, t]); t += .14; } }); this.end = t; },
  color(s) {
    const esc = x => x.replace(/&/g, '&amp;').replace(/</g, '&lt;');
    return s.replace(/(^\$ )|(--[a-z-]+)|("[^"]*")|(✔)|([^\s]+|\s+)/g, (m, p, f, q, ok, o) =>
      p ? '<span style="color:#35e07a">$ </span>' : f ? `<span style="color:#19e0ff">${f}</span>` : q ? `<span style="color:#ffd27a">${esc(q)}</span>` : ok ? '<span style="color:#35e07a">✔</span>' : esc(m));
  },
  render(L) {
    let out = ''; const cur = Math.floor(L * 2) % 2 === 0 ? '█' : ' ';
    for (let i = 0; i < this.lines.length; i++) {
      const [a, b] = this.sched[i]; if (L < a) break; const [txt, kind] = this.lines[i];
      const n = kind === 'cmd' ? Math.min(txt.length, Math.floor((L - a) * 120)) : txt.length;
      out += this.color(txt.slice(0, n)) + (kind === 'cmd' && n < txt.length ? `<span style="color:#fff">${cur}</span>` : '') + '\n';
    }
    if (L >= this.end) out += this.color('$ ') + `<span style="color:#fff">${cur}</span>`;
    $('s8pre').innerHTML = out;
  } };

// ---------------------------------------------------------------- per-scene updaters
function u0(L) {
  const p = eio(prog(L, 0.55, 2.9)); ctx0.clearRect(0, 0, 900, 675); ctx0.fillStyle = '#05070f'; ctx0.fillRect(0, 0, 900, 675);
  ctx0.globalAlpha = 1 - .93 * p; ctx0.drawImage(IMG.sunset, 0, 0, 900, 675); ctx0.globalAlpha = 1;
  drawAscii(ctx0, DATA.hero_color, 0, 0, 900, 675, { p: p * 1.02, frame: Math.floor(L * 24) });
  if (p > 0 && p < 1) { const sx = (p * 1.0) * 900 * .72 + 40; const g = ctx0.createLinearGradient(sx - 60, 0, sx + 6, 0); g.addColorStop(0, 'rgba(25,224,255,0)'); g.addColorStop(1, 'rgba(25,224,255,.55)'); ctx0.fillStyle = g; ctx0.fillRect(sx - 60, 0, 66, 675); ctx0.fillStyle = '#c6faff'; ctx0.fillRect(sx + 4, 0, 3, 675); }
  const c = $('s0card'), k = eo(prog(L, 0.15, 0.9)); c.style.opacity = k; c.style.transform = `translateY(${(1 - k) * 60}px) scale(${lerp(.94, 1, k)})`;
  ['s0c1', 's0c2', 's0c3'].forEach((id, i) => pop($(id), ebk(prog(L, 1.5 + i * .2, 2.1 + i * .2))));
}
function u1(L) {
  const win = $('s1win'), k = eo(prog(L, 0.1, 0.8)); win.style.opacity = k; win.style.transform = `translateY(${(1 - k) * 70}px)`;
  // flying file
  const f = $('s1file'), q = eio(prog(L, 0.5, 1.4)), x = lerp(740, 400, q), y = lerp(330, 620, q) - Math.sin(q * Math.PI) * 120;
  f.style.transform = `translate(${x - 700}px,${y - 300}px) scale(${lerp(1.1, .8, q)}) rotate(${(1 - q) * 8}deg)`; f.style.opacity = L < .5 ? eo(prog(L, 0.3, 0.5)) : (L < 1.45 ? 1 : 0);
  const flash = prog(L, 1.4, 1.9), dz = $('s1drop'); dz.style.borderColor = flash > 0 && flash < 1 ? '#007acc' : '#3c3c3c'; dz.style.background = flash > 0 && flash < 1 ? '#252526' : '#1e1e1e';
  dz.style.color = L > 1.45 ? '#cfd8e8' : '#858585'; dz.innerHTML = L > 1.45 ? 'paisaje.jpg  ✔' : 'Drag &amp; Drop Image Here<br>or Click to Browse';
  const pv = $('s1prev'), r = eo(prog(L, 1.5, 2.1)); pv.style.clipPath = `inset(0 0 ${(1 - r) * 100}% 0)`;
  const ratio = L < 1.9 ? 0.5 : 0.5 + 0.38 * Math.sin((L - 1.9) * 2.5);
  ctx1.fillStyle = '#151515'; ctx1.fillRect(0, 0, 900, 675); ctx1.drawImage(IMG.sunset, 0, 0, 900, 675);
  const sx = ratio * 900; ctx1.save(); ctx1.beginPath(); ctx1.rect(sx, 0, 900 - sx, 675); ctx1.clip(); ctx1.fillStyle = '#0b0b0b'; ctx1.fillRect(0, 0, 900, 675); drawAscii(ctx1, DATA.hero_color, 0, 0, 900, 675); ctx1.restore();
  $('s1h').style.left = sx - 1 + 'px';
  Array.from($('s1tb').children).forEach((b, i) => pop(b, ebk(prog(L, 2.2 + i * .12, 2.7 + i * .12)), .8));
}
function u2(L) {
  const sel = Math.floor(Math.max(0, L - 2.2) / .45) % 4;
  ['preset_fast', 'preset_balanced', 'preset_high', 'preset_max'].forEach((key, i) => {
    const st = .25 + i * .3, card = $('s2t' + i), k = eo(prog(L, st, st + .5));
    card.style.opacity = k; card.style.transform = `translateY(${(1 - k) * 70}px) scale(${lerp(.94, 1, k)})`;
    const c = $('s2c' + i).getContext('2d'); c.fillStyle = '#05070f'; c.fillRect(0, 0, 430, 323);
    drawAscii(c, DATA[key], 0, 0, 430, 323, { p: prog(L, st + .2, st + 1.5) * 1.02, frame: Math.floor(L * 24) });
    const on = L > 2.2 && sel === i; card.style.borderColor = on ? '#19e0ff' : 'rgba(140,180,255,.16)'; card.style.boxShadow = on ? '0 0 60px rgba(25,224,255,.35),0 40px 120px rgba(0,0,0,.55)' : '';
    $('s2b' + i).style.opacity = L > st + 1.5 ? 1 : 0;
  });
}
function sweepMix(ctx, A, B, p, w, h) {
  ctx.drawImage(A, 0, 0); if (p <= 0) return; const sx = p * (w + 80) - 40;
  ctx.save(); ctx.beginPath(); ctx.rect(0, 0, Math.max(0, sx), h); ctx.clip(); ctx.drawImage(B, 0, 0); ctx.restore();
  if (p < 1) { const g = ctx.createLinearGradient(sx - 50, 0, sx + 4, 0); g.addColorStop(0, 'rgba(25,224,255,0)'); g.addColorStop(1, 'rgba(25,224,255,.5)'); ctx.fillStyle = g; ctx.fillRect(sx - 50, 0, 54, h); ctx.fillStyle = '#d9fbff'; ctx.fillRect(sx, 0, 3, h); }
}
function u3(L) {
  const names = ['ascii', 'shades', 'blocks', 'braille'], T = [0.35, 1.2, 1.95, 2.7]; let idx = 0; T.forEach((t, i) => { if (L >= t) idx = i; });
  const prev = idx === 0 ? null : OFF['cs_' + names[idx - 1]], cur = OFF['cs_' + names[idx]], p = prog(L, T[idx], T[idx] + .5);
  ctx3.fillStyle = '#05070f'; ctx3.fillRect(0, 0, 960, 720);
  if (L < T[0]) { /* empty */ } else if (!prev) { ctx3.drawImage(cur, 0, 0); ctx3.fillStyle = `rgba(5,7,15,${1 - eo(p)})`; ctx3.fillRect(0, 0, 960, 720); } else sweepMix(ctx3, prev, cur, eio(p), 960, 720);
  for (let i = 0; i < 5; i++) { const on = i === idx || (i === 4 && L > 3.2); const c = $('s3c' + i); c.classList.toggle('on', on); pop(c, ebk(prog(L, 0.2 + i * .12, 0.7 + i * .12)), .85); }
}
function u4(L) {
  const T = [0.3, 1.45, 2.55], keys = ['black', 'white', 'trans']; let idx = 0; T.forEach((t, i) => { if (L >= t) idx = i; });
  const p = eio(prog(L, T[idx], T[idx] + .55)); ctx4.fillStyle = '#05060c'; ctx4.fillRect(0, 0, 960, 720);
  if (L < T[0]) { ctx4.globalAlpha = eo(prog(L, 0, .3)); ctx4.drawImage(OFF.black, 0, 0); ctx4.globalAlpha = 1; }
  else if (idx === 0) ctx4.drawImage(OFF.black, 0, 0);
  else { ctx4.drawImage(OFF[keys[idx - 1]], 0, 0); ctx4.save(); ctx4.beginPath(); ctx4.arc(480, 360, p * 820, 0, 7); ctx4.clip(); ctx4.drawImage(OFF[keys[idx]], 0, 0); ctx4.restore(); }
  for (let i = 0; i < 3; i++) $('s4c' + i).classList.toggle('on', L >= T[0] && i === idx);
  ['s4c0', 's4c1', 's4c2', 's4c3'].forEach((id, i) => pop($(id), ebk(prog(L, 0.2 + i * .12, 0.7 + i * .12)), .85));
}
function u5(L) {
  const cvs = document.querySelectorAll('#s5list .card');
  cvs.forEach((c, i) => {
    const st = .15 + i * .26, k = ebk(prog(L, st, st + .6)), dir = i % 2 ? 1 : -1;
    c.style.opacity = clamp(k * 1.5); c.style.transform = `translateX(${(1 - k) * 700 * dir}px)`;
    const kk = $('s5k' + i), q = ebk(prog(L, st + .75, st + 1.05)); kk.style.opacity = clamp(q * 1.5); kk.style.transform = `scale(${lerp(.7, 1, q)})`;
  });
}
function wave(ctx, L) {
  ctx.clearRect(0, 0, 900, 150); const n = 84, pp = prog(L, .2, 3.9);
  for (let i = 0; i < n; i++) {
    const a = hash(i, 3), env = .35 + .65 * Math.abs(Math.sin(i * .21 + L * 3.1)) * (.5 + a), h = 14 + env * 96, x = 24 + i * 10.2;
    ctx.fillStyle = i / n < pp ? '#19e0ff' : 'rgba(140,170,255,.28)'; ctx.fillRect(x, 75 - h / 2, 6, h);
  }
  $('s6time').textContent = `00:${String(Math.floor(L * 7.5)).padStart(2, '0')} / 00:30`;
}
function u6(L) {
  const f = Math.floor(L * 30) % 90; ctx6.fillStyle = '#02050f'; ctx6.fillRect(0, 0, 900, 760);
  const k = eo(prog(L, 0.2, .8)); ctx6.globalAlpha = k; drawAscii(ctx6, DATA.donut[f], 40, -10, 820, 780); ctx6.globalAlpha = 1;
  $('s6pip').style.backgroundPosition = `${-(Math.floor(f / 9) % 10) * 210}px 0`; wave(ctxw, L);
  ['s6c0', 's6c1', 's6c2'].forEach((id, i) => pop($(id), ebk(prog(L, 1.0 + i * .2, 1.5 + i * .2))));
}
function u7(L) {
  const f = Math.floor(L * 30) % 60; ctx7.fillStyle = '#02050f'; ctx7.fillRect(0, 0, 900, 675); drawAscii(ctx7, DATA.blob[f], 70, 60, 760, 570);
  $('s7rec').style.opacity = Math.floor(L * 2) % 2 ? .25 : 1;
  const dip = prog(L, .7, 1.0) * (1 - prog(L, 1.5, 1.8)), fps = Math.round(lerp(30, 21, dip)), cols = Math.round(lerp(56, 40, dip));
  $('s7fps').textContent = `${fps} FPS`; $('s7fps').style.color = dip > .5 ? '#ffd27a' : '#35e07a';
  $('s7cols').textContent = `${cols} cols · ${dip > .5 ? 'Brightness' : 'MSE'}`; $('s7bar').style.width = `${lerp(100, 66, dip)}%`;
}
function u8(L) {
  const c = $('s8term'), k = eo(prog(L, .1, .7)); c.style.opacity = k; c.style.transform = `translateY(${(1 - k) * 70}px)`; term.render(L);
  const cv = $('s8cv').getContext('2d'), p = prog(L, .9, 2.4); cv.fillStyle = '#05070f'; cv.fillRect(0, 0, 693, 520);
  cv.globalAlpha = .9 * (1 - p); cv.drawImage(IMG.sunset, 0, 0, 693, 520); cv.globalAlpha = 1;
  drawAscii(cv, DATA.hero_color, 0, 0, 693, 520, { p: eio(p) * 1.02, frame: Math.floor(L * 24) });
  const on = L > .8; $('s8cv').style.opacity = on ? 1 : 0; $('s8lab').style.opacity = on ? 1 : 0;
}
function u9(L) {
  const d = $('s9dlg'), k = eo(prog(L, .1, .7)); d.style.opacity = k; d.style.transform = `translateY(${(1 - k) * 70}px) scale(${lerp(.95, 1, k)})`;
  const p = eio(prog(L, .6, 1.9)); $('s9bar').style.width = p * 100 + '%'; $('s9p').textContent = Math.round(p * 100) + ' %';
  $('s9s').textContent = p < .35 ? 'Copiando archivos…' : p < .75 ? 'Creando accesos directos…' : p < 1 ? 'Finalizando…' : 'Todo listo para convertir tus imágenes.';
  $('s9t').textContent = p < 1 ? 'Instalando…' : '¡Listo!'; $('s9btn').style.opacity = p < 1 ? .35 : 1;
  pop($('s9ico'), ebk(prog(L, 2.0, 2.5)), .5);
  ['s9c0', 's9c1', 's9c2'].forEach((id, i) => pop($(id), ebk(prog(L, 1.9 + i * .15, 2.4 + i * .15))));
}
function u10(L) {
  const lg = $('endlogo'), k = ebk(prog(L, .15, 1.0)); lg.style.opacity = clamp(k * 1.6); lg.style.transform = `scale(${lerp(.6, 1, k)}) rotate(${(1 - k) * -18}deg)`;
  lg.style.filter = `drop-shadow(0 0 ${30 + 14 * Math.sin(L * 2.2)}px rgba(31,92,255,.7))`;
  const g = $('endglow'); g.style.opacity = eo(prog(L, 0, 1)); g.style.transform = `scale(${1 + .05 * Math.sin(L * 1.6)})`;
  pop($('endby'), eo(prog(L, 1.0, 1.5)), .98); pop($('endname'), eo(prog(L, 1.25, 1.85)), .96); pop($('endtag'), eo(prog(L, 1.75, 2.3)), .98);
}
const UP = { s0: u0, s1: u1, s2: u2, s3: u3, s4: u4, s5: u5, s6: u6, s7: u7, s8: u8, s9: u9, s10: u10 };
const RAINAMP = { s0: 1, s10: .8 };

// ---------------------------------------------------------------- render(t)
window.render = t => {
  drawGlow(t);
  let cur = SCENES.findIndex(s => t >= s[1] && t < s[2]); if (cur < 0) cur = SCENES.length - 1;
  drawRain(t, RAINAMP[SCENES[cur][0]] || .45);
  SCENES.forEach(([id, a, b], i) => {
    const L = t - a, dur = b - a, sec = el[id], vis = L >= -.0001 && L < dur;
    sec.style.display = vis ? 'block' : 'none'; if (!vis) { prog$.children[i].firstChild.style.width = t >= b ? '100%' : '0'; return; }
    const inn = eo(prog(L, 0, .3)), out = prog(L, dur - .3, dur);
    sec.style.opacity = id === 's10' ? 1 : inn * (1 - out); sec.style.transform = `translateY(${(1 - inn) * 30 - out * 24}px)`;
    animHead(sec, L); UP[id](L); prog$.children[i].firstChild.style.width = (L / dur * 100) + '%';
  });
  const endK = prog(t, 35.8, 36.3); $('top').style.opacity = 1 - endK; prog$.style.opacity = 1 - endK;
};
window.DURATION = DUR;
window.promoReady = (async () => {
  await Promise.all([document.fonts.load("20px JB"), document.fonts.load("20px DJV"), document.fonts.load("800 80px Syne"), document.fonts.load("700 20px 'Space Mono'"), document.fonts.load("500 20px Inter"), document.fonts.load("600 20px Inter")]);
  IMG.sunset = await loadImg('assets/sunset.jpg'); setup(); await document.fonts.ready; window.render(0); return true;
})();
})();
