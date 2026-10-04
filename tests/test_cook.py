import functools
import http.server
import json
import subprocess
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
subprocess.run([sys.executable, str(Path(ROOT) / "research" / "build_sprite_bundle.py")], check=True)
OUT = Path(__file__).parent / "shots" / "shots9"
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
    pg.locator(".tile", has_text="고양이").nth(1).click()
    pg.click("text=분양받기")
    patch(pg, "s.points=500")
    pg.click("[data-tab=town]")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "1_town.png"))
    pg.locator(".town-row", has_text="쿠킹샵").click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(OUT / "2_cook.png"))
    s = get(pg)
    known = s["recipeKnown"]
    res["known_start"] = len(known)
    rec = pg.evaluate(f"()=>{{const D=window.FOOD_DATA,M=Object.fromEntries(D.foods.map(f=>[f.id,f]));const r=D.recipes.find(x=>x.id==='{known[0]}');return [r.a,r.b,r.result,M[r.a].name,M[r.b].name,M[r.result].name]}}")
    res["recipe"] = rec[3:]
    # 재료 구매(조합 재료 + 아무 재료 하나)
    patch(pg, f"s.foodBag={{'{rec[0]}':1,'{rec[1]}':1}}")
    pg.click("[data-tab=town]")
    pg.locator(".town-row", has_text="쿠킹샵").click()
    pg.locator(".pick-btn").nth(0).click()
    pg.locator(".modal-box .food-card", has_text=rec[3]).click()
    pg.locator(".pick-btn").nth(1).click()
    pg.locator(".modal-box .food-card", has_text=rec[4]).click()
    pg.screenshot(path=str(OUT / "3_slots.png"))
    pg.click(".cook-btn")
    pg.wait_for_timeout(300)
    res["success_title"] = pg.locator(".modal-box h3").inner_text()
    pg.screenshot(path=str(OUT / "4_success.png"))
    pg.click(".modal-box >> text=확인")
    res["bag_after_success"] = get(pg)["foodBag"]
    # 실패: 기본 재료 2개 사서 엉뚱한 조합
    base = pg.evaluate("()=>window.FOOD_DATA.foods.filter(f=>f.tier===1).slice(0,2).map(f=>f.name)")
    for name in base:
        pg.locator(".food-card", has_text=name).locator("button").click()
    pg.locator(".pick-btn").nth(0).click()
    pg.locator(".modal-box .food-card", has_text=base[0]).click()
    pg.locator(".pick-btn").nth(1).click()
    pg.locator(".modal-box .food-card", has_text=base[1]).click()
    pg.click(".cook-btn")
    pg.wait_for_timeout(300)
    res["second_title"] = pg.locator(".modal-box h3").inner_text()
    pg.click(".modal-box >> text=확인")
    pg.screenshot(path=str(OUT / "5_after_fail_banner.png"))
    pg.click(".book-btn")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "6_book.png"))
    pg.click(".modal-box >> text=닫기")
    pg.click("[data-tab=shop]")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "6b_box_food.png"))
    res["box_food_cards"] = pg.locator(".box-panel .food-card").count()
    # 먹이기
    pg.click("[data-tab=farm]")
    before = get(pg)["pet"]["stats"]
    pg.click("text=음식주기")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "7_feed_pick.png"))
    pg.locator(".modal-box .food-card", has_text=rec[5]).click()
    pg.wait_for_timeout(300)
    after = get(pg)["pet"]["stats"]
    res["fed_gain"] = {k: after[k] - before[k] for k in after}
    res["food_gain_expected"] = pg.evaluate(f"()=>window.FOOD_DATA.foods.find(f=>f.id==='{rec[2]}').gain")
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
