# ASCII Vision — landing page

A static, dependency-free page (`index.html` + `assets/`) that promotes the app and links to the Windows installer.

* **Download button**: at load time it asks the GitHub API for the latest release and points to the asset whose
  name matches `*Setup*.exe` (the file produced by the *Windows installer* workflow). Until a release exists, the
  buttons simply open the Releases page.
* **Preview locally**: `python -m http.server -d site 8000` and open <http://localhost:8000>.
* **Publish**: the `Landing page` workflow deploys `site/` to GitHub Pages on every push to `main` that touches it.
  Enable it once under *Settings -> Pages -> Source: GitHub Actions*. The site will live at
  `https://<user>.github.io/ascii-vision/`; if you use another URL, update the `canonical` and `og:image`
  tags in `index.html`.
* **Assets**: `app-screenshot.png` is a real capture of the GUI, `promo.mp4`/`promo-poster.jpg` come from the
  promo video (see `../promo`), `symmetrical-code.png` and `favicon.svg` are the Symmetrical Code brand files.
  Fonts (Syne, Space Mono, Inter) are SIL OFL and self-hosted.
