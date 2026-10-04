import sys, os, pathlib
HERE=os.path.dirname(os.path.abspath(__file__)); URL=pathlib.Path(HERE,'index.html').as_uri()
from playwright.sync_api import sync_playwright
times=[float(x) for x in sys.argv[1:]] or [2.0,5.5,9.0,13.0,16.5,20.5,24.0,27.5,31.0,33.5,37.0]
os.makedirs(os.path.join(HERE,"stills"),exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium",args=["--allow-file-access-from-files","--font-render-hinting=none"])
    pg=b.new_page(viewport={"width":1080,"height":1920})
    logs=[]
    pg.on("console",lambda m:logs.append(m.text)); pg.on("pageerror",lambda e:logs.append("ERR "+str(e)))
    pg.goto(URL); pg.evaluate("window.promoReady")
    for t in times:
        pg.evaluate("t=>window.render(t)",t); pg.screenshot(path=os.path.join(HERE,"stills",f"t_{t:05.2f}.png"))
    b.close(); print("\n".join(logs[:10]) or "no console errors")
