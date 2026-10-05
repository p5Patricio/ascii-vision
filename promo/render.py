import os, math, time, pathlib
HERE=os.path.dirname(os.path.abspath(__file__)); URL=pathlib.Path(HERE,'index.html').as_uri()
from multiprocessing import Pool
from playwright.sync_api import sync_playwright
FPS=30; DUR=40.0; TOTAL=int(DUR*FPS); WORKERS=4
FORCE=os.environ.get('FORCE')=='1'; START=int(os.environ.get('START','0')); END=int(os.environ.get('END',TOTAL))
OUT=os.path.join(HERE,"frames"); os.makedirs(OUT,exist_ok=True)
def work(rng):
    a,b=rng
    with sync_playwright() as p:
        br=p.chromium.launch(executable_path="/opt/pw-browsers/chromium",args=["--allow-file-access-from-files","--font-render-hinting=none","--disable-gpu-vsync"])
        pg=br.new_page(viewport={"width":1080,"height":1920}); pg.goto(URL); pg.evaluate("window.promoReady")
        for i in range(a,b):
            f=f"{OUT}/f_{i:05d}.jpg"
            if not FORCE and os.path.exists(f): continue
            pg.evaluate("t=>window.render(t)",i/FPS); pg.screenshot(path=f,type="jpeg",quality=94)
        br.close()
    return b-a
if __name__=="__main__":
    t0=time.time(); step=max(1,math.ceil((END-START)/(WORKERS*3)))
    chunks=[(i,min(END,i+step)) for i in range(START,END,step)]
    with Pool(WORKERS) as pool:
        done=0
        for n in pool.imap_unordered(work,chunks):
            done+=n; print(f"{done}/{TOTAL} {time.time()-t0:.0f}s",flush=True)
