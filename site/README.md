# ASCII Vision — landing page

A static, dependency-free page (`index.html`, `style.css`, `app.js`, `assets/`) that promotes the app and links to
the Windows installer. It follows the **Symmetrical Code design system** (`DESIGN.md`), with the tool's own touch.

## Design

* **Tokens, theme and type** — the dark/light tokens, `html.dark`/`html.light` switch (persisted in
  `localStorage['sc-theme']`), Syne 800 for H1/H2 only, Geist for text and Geist Mono for eyebrows/meta. Fonts are
  self-hosted (`assets/fonts`), so the strict Content-Security-Policy in `index.html` holds.
* **Shape language** — `Button` and `CutCard` cut the top-left and bottom-right corners at 45° (no `border-radius`),
  with a 1 px ring that follows the diagonal edges (even-odd `clip-path`). One primary button per view.
* **Layout** — hairline section separators instead of boxes, fixed 64 px navbar with a mobile sheet (scroll lock,
  focus trap, Escape to close), CSS-only grid + glow backdrop, no continuous animation, `prefers-reduced-motion` honoured.
* **Voice** — Spanish (MX, "tú") with a full English mirror (toggle in the navbar, persisted in `localStorage['sc-lang']`).
* **The tool's touch** — a single terminal-green accent (`--svc-accent`, the same override mechanism the Symmetrical Code
  service pages use) and a before/after comparer built from the app's own output. `assets/compare-original.webp` is a procedurally
  ray-traced scene and `assets/compare-ascii.webp` is its conversion with
  `ascii-vision --preset "High Quality" --columns 190 --color`; regenerate both with `python promo/gen_compare.py`
  (no third-party photos).
* Contrast: text uses `--muted` rather than `--subtle` (3.6:1 dark / 2.9:1 light) and code flags use the brand blue on the
  light theme (the light cyan is 3.7:1), so every text colour clears the 4.5:1 floor the design system asks for.

## Behaviour

* **Download button**: at load time it asks the GitHub API for the latest release and points to the asset whose
  name matches `*Setup*.exe` (produced by the *Windows installer* workflow). Until a release exists, the buttons open
  the Releases page.
* **Preview locally**: `python -m http.server -d site 8000` and open <http://localhost:8000> (the CSP needs http, not `file://`).
* **Publish**: the `Landing page` workflow deploys `site/` to GitHub Pages when you run it by hand (Actions tab ->
  Run workflow). Enable Pages once under *Settings -> Pages -> Source: GitHub Actions*. The site is served from
  <https://ascii.symmetricalcode.com/> (custom domain set in Pages settings; DNS is a `CNAME ascii -> p5patricio.github.io`
  record in the symmetricalcode.com zone). If you serve it from another URL, update `canonical` and `og:image` in `index.html`.
* **Assets**: `app-screenshot.png` is a real capture of the GUI, `promo.mp4`/`promo-poster.jpg` come from the promo
  video (see `../promo`), `favicon.svg` is the Symmetrical Code mark. Syne, Geist and Geist Mono are SIL OFL.
