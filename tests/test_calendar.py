import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "shots7"
OUT.mkdir(parents=True, exist_ok=True)
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
h.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
KEY = "dongmulnongjang.save.v1"
errs, res = [], {}


def get(pg):
    return json.loads(pg.evaluate(f"()=>localStorage.getItem('{KEY}')"))


def patch(pg, js):
    pg.evaluate(f"()=>{{const s=JSON.parse(localStorage.getItem('{KEY}'));{js};localStorage.setItem('{KEY}',JSON.stringify(s));}}")
    pg.reload()
    pg.wait_for_load_state("networkidle")


def run_schedule(pg, name):
    pg.locator(".sched", has_text=name).click()
    pg.click("text=보내기")
    pg.wait_for_timeout(250)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, is_mobile=True,
                       has_touch=True, service_workers="block").new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")
    pg.locator(".tile", has_text="여우").first.click()
    pg.click("text=분양받기")
    pg.wait_for_timeout(400)
    res["start_date"] = pg.locator(".date-bar strong").inner_text()
    pg.screenshot(path=str(OUT / "1_top.png"))
    for _ in range(3):
        pg.click("text=음식주기")
        pg.wait_for_timeout(150)
    res["care_left_after_3"] = get(pg)["careLeft"]
    res["care_buttons_disabled"] = pg.locator(".act").first.is_disabled()
    pg.screenshot(path=str(OUT / "2_full.png"), full_page=True)

    run_schedule(pg, "푹 쉬기")
    pg.screenshot(path=str(OUT / "3_school_result.png"))
    pg.click("text=확인")
    s = get(pg)
    res["after_school"] = (s["calendar"], s["careLeft"], s["pet"]["effort"], s["pet"]["stats"]["know"])


    patch(pg, "s.calendar={year:1,month:9,period:3};s.pet.stats.charm=420")
    run_schedule(pg, "공원 놀이")
    pg.click("text=확인")
    pg.wait_for_timeout(400)
    res["festival_title"] = pg.locator(".modal-box h3").inner_text() if not pg.locator("#modal").is_hidden() else None
    res["festival_text"] = pg.locator(".modal-box p").first.inner_text() if res["festival_title"] else None
    pg.screenshot(path=str(OUT / "5_festival.png"))
    pg.click("text=좋아!")
    res["date_after_festival"] = get(pg)["calendar"]

    patch(pg, "s.calendar={year:1,month:2,period:3}")
    run_schedule(pg, "푹 쉬기")
    pg.click("text=확인")
    res["date_after_feb"] = get(pg)["calendar"]
    pg.screenshot(path=str(OUT / "6_spring_year2.png"))
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
