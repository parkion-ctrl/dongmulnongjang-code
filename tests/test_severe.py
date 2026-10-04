import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "shots12"
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
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")
    pg.locator(".tile", has_text="여우").first.click()
    pg.click("text=분양받기")
    patch(pg, "s.points=300;s.pet.stats={love:260,charm:250,power:280,know:240};s.pet.stage=2;"
              "s.pet.sick={id:'itch',sev:3,known:true};s.calendar={year:1,month:9,period:3}")
    before = get(pg)
    # 아픈데 푹 쉬기 -> 순이 끝나며 중병(4단계)
    pg.locator(".sched", has_text="푹 쉬기").click()
    pg.click("text=보내기")
    pg.wait_for_timeout(300)
    res["period_news"] = pg.locator(".modal-box .warn").all_inner_texts()
    pg.locator("#modal button.btn", has_text="확인").click()
    pg.wait_for_timeout(300)
    res["forced_title"] = pg.locator(".modal-box h3").inner_text()
    pg.screenshot(path=str(OUT / "1_forced.png"))
    pg.mouse.click(5, 120)  # 바깥 눌러도 안 닫혀야 함
    pg.wait_for_timeout(200)
    res["still_open_after_backdrop"] = not pg.locator("#modal").is_hidden()
    pg.locator("#modal button.btn", has_text="입원시키기").click()
    pg.wait_for_timeout(300)
    res["result_text"] = pg.locator(".modal-box").inner_text()
    pg.screenshot(path=str(OUT / "2_result.png"))
    pg.locator("#modal button.btn", has_text="확인").click()
    pg.wait_for_timeout(400)
    res["festival_after"] = pg.locator(".modal-box h3").inner_text() if not pg.locator("#modal").is_hidden() else None
    after = get(pg)
    res["stats"] = (before["pet"]["stats"], after["pet"]["stats"])
    res["stage"] = (before["pet"]["stage"], after["pet"]["stage"])
    res["points_same"] = before["points"] == after["points"] - (after["points"] - before["points"] if res["festival_after"] else 0)
    res["points"] = (before["points"], after["points"])
    res["sick_after"] = after["pet"].get("sick")
    res["calendar"] = after["calendar"]

    # 중병 상태로 앱을 다시 켜면 바로 강제 입원
    patch(pg, "s.pet.sick={id:'cold',sev:4,known:true}")
    pg.wait_for_timeout(400)
    res["reload_forced"] = pg.locator(".modal-box h3").inner_text() if not pg.locator("#modal").is_hidden() else None
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
