# ASCII Vision — promo video

`ascii-vision-promo.mp4` is a 1080x1920 (9:16), 40 s, 30 fps vertical ad that walks through the
application's features. Everything is generated from code, so it can be edited and re-rendered:

* the ASCII art is produced by the **real ASCII Vision engine** (`gen_data.py`) from procedurally
  generated images (no third-party photos),
* the animation is an HTML page driven by a deterministic timeline (`index.html`, `scenes.js`),
* the soundtrack is synthesised (`audio.py`) — original, royalty-free.

## Re-render

```bash
pip install -e ".[dev]" playwright scipy          # from the repository root
cd promo
python gen_data.py                                # engine output + source images -> assets/
python audio.py                                   # -> promo_audio.wav
python render.py                                  # frames -> frames/ (needs Chromium; set the path in render.py)
ffmpeg -framerate 30 -i frames/f_%05d.jpg -i promo_audio.wav -c:v libx264 -crf 17 -pix_fmt yuv420p \
       -c:a aac -b:a 192k -af "loudnorm=I=-15:TP=-2:LRA=11,alimiter=limit=0.84:level=disabled" \
       -movflags +faststart -shortest ascii-vision-promo.mp4
```

`python stills.py 5.6 13.9` saves single frames to `stills/` to check a scene without rendering everything.
Scene timings live in `scenes.js` (`SCENES`); headline copy is in the `data-t` attributes of `index.html`.
The last scene is the "Desarrollado por Symmetrical Code" end card.

Fonts: Syne, Space Mono and Inter (SIL OFL, via Google Fonts) plus the fonts bundled with the app.
