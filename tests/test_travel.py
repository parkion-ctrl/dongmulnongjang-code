import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "shots10"
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


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, is_mobile=True,
                       has_touch=True, service_workers="block").new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("requestfailed", lambda r: errs.append("failed " + r.url))
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")
    pg.locator(".tile", has_text="펭귄").first.click()
    pg.click("text=분양받기")
    patch(pg, "s.points=400;s.calendar={year:1,month:12,period:0};s.pet.fatigue=50")
    # 키우기의 여행사 일정 -> 여행사 화면으로 이동
    pg.locator(".sched", has_text="여행사").click()
    pg.wait_for_timeout(400)
    res["opened_travel_from_schedule"] = pg.locator(".spot-card").count() == 6
    pg.screenshot(path=str(OUT / "1_list.png"))
    pg.locator(".spot-card").nth(2).click()  # 눈의 나라
    pg.locator(".opt-card").nth(3).click()   # 비행기
    pg.locator(".opt-card").nth(6).click()   # 호텔
    pg.wait_for_timeout(200)
    res["preview"] = pg.locator(".travel-preview").inner_text()
    pg.screenshot(path=str(OUT / "2_plan.png"), full_page=True)
    res["selected_is_color"] = "spot3_icon" in pg.locator(".spot-card.on .spot-photo").get_attribute("src")
    before = get(pg)
    pg.click("text=여행 보내기")
    pg.click(".modal-box .btn >> nth=1")
    pg.wait_for_timeout(400)
    res["result_title"] = pg.locator(".modal-box h3").inner_text()
    res["result_img"] = pg.locator(".modal-box .travel-img").get_attribute("src")
    pg.screenshot(path=str(OUT / "3_result.png"))
    pg.click(".modal-box >> text=확인")
    after = get(pg)
    res["points"] = (before["points"], after["points"])
    res["fatigue"] = (before["pet"]["fatigue"], after["pet"]["fatigue"])
    res["know_gain"] = after["pet"]["stats"]["know"] - before["pet"]["stats"]["know"]
    res["date"] = after["calendar"]
    res["souvenirs"] = {k: v for k, v in after["foodBag"].items() if v}
    res["back_on_farm"] = not pg.locator("#screen-farm").is_hidden()
    pg.click("[data-tab=town]")
    pg.screenshot(path=str(OUT / "4_town.png"))
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
