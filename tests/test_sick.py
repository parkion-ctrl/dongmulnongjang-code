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
OUT = Path(__file__).parent / "shots" / "shots11"
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
    pg.locator(".tile", has_text="토끼").first.click()
    pg.click("text=분양받기")

    # 1) 먹을 수 없는 요리: 먹이기 목록에 없음, 아이템박스엔 남고 버튼 비활성
    patch(pg, "s.foodBag={badsoup:1}")
    pg.click("text=음식주기")
    pg.wait_for_timeout(200)
    res["feed_modal_opened_with_only_bad"] = not pg.locator("#modal").is_hidden()
    res["care_after_basic_feed"] = get(pg)["careLeft"]
    pg.click("[data-tab=shop]")
    card = pg.locator(".box-panel .food-card")
    res["bad_in_box"] = card.count() == 1 and card.first.locator("button").is_disabled()
    res["bad_btn_text"] = card.first.locator("button").inner_text()

    # 2) 피로 높을 때 병 걸림 (강제: Math.random=0)
    pg.click("[data-tab=farm]")
    patch(pg, "s.pet.fatigue=95;s.points=500")
    pg.evaluate("()=>{Math.random=()=>0}")
    pg.locator(".sched", has_text="공원 놀이").click()
    pg.click("text=보내기")
    pg.wait_for_timeout(300)
    res["news"] = pg.locator(".modal-box .warn").all_inner_texts()
    pg.screenshot(path=str(OUT / "1_sick_news.png"))
    pg.locator("#modal button.btn", has_text="확인").click()
    s = get(pg)
    res["sick"] = s["pet"].get("sick")
    pg.screenshot(path=str(OUT / "2_sick_farm.png"), full_page=True)
    # 아픈 동안 학교 막힘
    pg.locator(".sched", has_text="동물학교").click()
    res["school_blocked"] = pg.locator("#modal").is_hidden()

    # 3) 진료 -> 처방 -> 약 구매 -> 먹이기
    pg.click("text=동물병원 가기")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "3_clinic.png"))
    pg.click("text=진료 받을래요")
    res["diagnosis"] = pg.locator(".modal-box .rx").inner_text()
    pg.screenshot(path=str(OUT / "4_diag.png"))
    pg.click(".modal-box >> text=약국 가기")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "5_pharmacy.png"))
    s = get(pg)
    fam = pg.evaluate("()=>{const s=JSON.parse(localStorage.getItem('dongmulnongjang.save.v1'));return {cold:'cough_mask',itch:'mitten',forget:'lumicap',blue:'butter_cookie',achy:'zelkova',night:'lightning_bug'}[s.pet.sick.id]}")
    wrong = 'mitten01' if fam != 'mitten' else 'cough_mask01'
    right = f"{fam}01"
    patch(pg, f"s.medBag={{'{wrong}':1,'{right}':1}}")
    pg.click("[data-tab=shop]")
    pg.locator(".box-tabs button").nth(3).click()
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "6_box_med.png"))
    res["med_cards"] = pg.locator(".box-panel .food-card").count()
    NAMES = {"cough_mask01": "기침 마스크", "mitten01": "근질근질 장갑", "lumicap01": "깜빡깜빡 모자",
             "butter_cookie01": "버터쿠키", "zelkova01": "느티나무 버섯", "lightning_bug01": "반딧불"}
    wname, rname = NAMES[wrong], NAMES[right]
    pg.locator(".box-panel .food-card", has_text=wname).locator("button").click()
    res["wrong_msg"] = pg.locator(".modal-box p").inner_text()
    pg.screenshot(path=str(OUT / "7_wrong_med.png"))
    pg.locator("#modal button.btn", has_text="확인").click()
    pg.locator(".box-panel .food-card", has_text=rname).locator("button").click()
    res["right_msg"] = pg.locator(".modal-box p").inner_text()
    pg.locator("#modal button.btn", has_text="확인").click()
    res["sick_after"] = get(pg)["pet"].get("sick")

    # 4) 입원
    patch(pg, "s.pet.sick={id:'cold',sev:3,known:true};s.pet.fatigue=80")
    pg.click("[data-tab=town]")
    pg.locator(".town-row", has_text="동물병원").click()
    pg.locator(".seg button", has_text="입원실").click()
    pg.click("text=입원시키기")
    pg.click(".modal-box >> text=내고 입원")
    pg.wait_for_timeout(300)
    res["discharge_title"] = pg.locator(".modal-box h3").inner_text()
    pg.locator("#modal button.btn", has_text="확인").click()
    s = get(pg)
    res["after_stay"] = (s["pet"].get("sick"), s["pet"]["fatigue"], s["points"])
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
