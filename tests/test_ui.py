import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "shots6"
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
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")
    pg.locator(".tile", has_text="팬더").first.click()
    pg.click("text=분양받기")
    pg.wait_for_timeout(500)
    pg.screenshot(path=str(OUT / "1_room_top.png"))
    pg.screenshot(path=str(OUT / "2_room_full.png"), full_page=True)

    pg.locator(".wish-btn.want").click()
    pg.wait_for_timeout(300)
    res["bubble_after_wish"] = pg.locator(".bubble").inner_text()
    s = get(pg)
    res["fatigue_after_play"] = s["pet"]["fatigue"]
    res["wish_rerolled"] = s["pet"]["wish"]

    patch(pg, "s.pet.fatigue=100")
    pg.locator(".sched", has_text="동물학교").click()
    pg.wait_for_timeout(200)
    res["study_blocked"] = pg.locator("#modal").is_hidden()
    pg.locator(".sched", has_text="푹 쉬기").click()
    pg.click("text=보내기")
    pg.click("text=확인")
    res["fatigue_after_rest"] = get(pg)["pet"]["fatigue"]

    pg.fill(".chat input", "사랑해")
    pg.click(".chat .btn")
    pg.wait_for_timeout(200)
    res["chat_reply"] = pg.locator(".bubble").inner_text()

    patch(pg, "s.points=500")
    pg.click("[data-tab=town]")
    pg.locator(".town-row", has_text="아이템 가게").click()
    for name in ["통나무집", "해바라기", "나무 울타리", "미끄럼틀"]:
        pg.locator(".deco-card", has_text=name).locator("button").click()
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "3_deco_shop.png"))
    res["decoBag"] = get(pg)["decoBag"]
    pg.click("[data-tab=shop]")
    pg.locator(".box-tabs button").nth(1).click()
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "3b_box_deco.png"))
    res["box_deco_cards"] = pg.locator(".box-panel .food-card").count()
    pg.locator(".box-panel .food-card").first.locator("button").click()
    pg.wait_for_timeout(300)
    res["went_to_yard_edit"] = pg.locator(".stage.yard.editing").count() == 1
    pg.click("text=다 꾸몄어요")

    pg.click("[data-tab=yard]")
    pg.wait_for_timeout(500)
    pg.screenshot(path=str(OUT / "4_yard.png"))
    pg.click("text=농장 꾸미기")
    pg.wait_for_timeout(300)
    for name in ["통나무집", "해바라기", "나무 울타리", "미끄럼틀"]:
        pg.locator(".tray-item", has_text=name).click()
        pg.wait_for_timeout(250)
    stage = pg.locator(".stage.yard").bounding_box()
    targets = [(0.25, 0.55), (0.75, 0.85), (0.5, 0.97), (0.8, 0.6)]
    for i, (tx, ty) in enumerate(targets):
        bb = pg.locator(".deco").nth(i).bounding_box()
        sx, sy = bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] * 0.8
        pg.mouse.move(sx, sy)
        pg.mouse.down()
        pg.mouse.move(stage["x"] + stage["width"] * tx, stage["y"] + stage["height"] * ty, steps=8)
        pg.mouse.up()
        pg.wait_for_timeout(250)
    pg.screenshot(path=str(OUT / "5_yard_edit.png"), full_page=True)
    res["items"] = [(i["id"], round(i["x"]), round(i["y"])) for i in get(pg)["yard"]["items"]]
    pg.locator(".skins button").nth(4).click()
    pg.wait_for_timeout(200)
    pg.click("text=다 꾸몄어요")
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(OUT / "6_yard_done.png"))
    pg.click("[data-tab=dex]")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "7_nav_dex.png"))
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
