import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "shots8"
OUT.mkdir(parents=True, exist_ok=True)
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
h.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
errs, res = [], {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_context(viewport={"width": 400, "height": 760}, device_scale_factor=2, is_mobile=True,
                       has_touch=True, service_workers="block").new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")
    pg.locator(".tile", has_text="여우").first.click()
    pg.click("text=분양받기")
    pg.wait_for_timeout(400)
    res["page_scrolls"] = pg.evaluate("()=>document.scrollingElement.scrollHeight > innerHeight + 1")
    res["main_scrollable"] = pg.evaluate("()=>{const m=document.querySelector('.app>main');return m.scrollHeight>m.clientHeight}")
    nav = pg.locator(".nav").bounding_box()
    res["nav_at_bottom"] = abs(nav["y"] + nav["height"] - 760) < 2
    pg.evaluate("()=>{const m=document.querySelector('.app>main');m.scrollTop=m.scrollHeight}")
    pg.wait_for_timeout(200)
    chat = pg.locator(".chat").bounding_box()
    res["chat_visible_above_nav"] = chat["y"] + chat["height"] <= nav["y"]
    pg.screenshot(path=str(OUT / "bottom.png"))
    pg.click("[data-tab=shop]")
    res["shop_scroll_reset"] = pg.evaluate("()=>document.querySelector('.app>main').scrollTop") == 0
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
