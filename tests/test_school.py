import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "shots13"
OUT.mkdir(parents=True, exist_ok=True)
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
h.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
KEY = "dongmulnongjang.save.v1"
errs, res = [], {}
import re
_src = Path(ROOT, "index.html").read_text(encoding="utf-8")
ANSWERS = dict(re.findall(r"\['([^']+\?)', '([^']+)'", _src))


def get(pg):
    return json.loads(pg.evaluate(f"()=>localStorage.getItem('{KEY}')"))


def patch(pg, js):
    pg.evaluate(f"()=>{{const s=JSON.parse(localStorage.getItem('{KEY}'));{js};localStorage.setItem('{KEY}',JSON.stringify(s));}}")
    pg.reload()
    pg.wait_for_load_state("networkidle")


def ok(pg):
    pg.locator("#modal button.btn", has_text="확인").click()
    pg.wait_for_timeout(200)


def to_school(pg):
    pg.click("[data-tab=farm]")
    pg.locator(".sched", has_text="동물학교").click()
    pg.wait_for_timeout(300)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, is_mobile=True,
                       has_touch=True, service_workers="block").new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("requestfailed", lambda r: errs.append("failed " + r.url))
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")
    pg.locator(".tile", has_text="코끼리").first.click()
    pg.click("text=분양받기")
    patch(pg, "s.points=500")
    to_school(pg)
    res["hub_buttons"] = pg.locator(".school-btn").count()
    pg.screenshot(path=str(OUT / "1_hub.png"), full_page=True)

    # 수업: 정답을 골라서 3문제
    know0 = get(pg)["pet"]["stats"]["know"]
    pg.locator(".school-btn").nth(0).click()
    for i in range(3):
        ans = ANSWERS[pg.locator(".quiz-q").inner_text()]
        pg.locator(".quiz-opt").filter(has_text=re.compile("^" + re.escape(ans) + "$")).click()
        if i == 0:
            pg.screenshot(path=str(OUT / "2_quiz.png"), full_page=True)
        pg.locator(".cook-btn").click()
    res["class_extra"] = pg.locator(".modal-box p").all_inner_texts()[1]
    ok(pg)
    res["know_gain"] = get(pg)["pet"]["stats"]["know"] - know0

    # 색칠
    to_school(pg)
    pg.locator(".school-btn").nth(1).click()
    pg.locator(".sheet-pick button").first.click()
    pg.wait_for_timeout(500)
    cv = pg.locator(".paint-canvas").bounding_box()
    filled = 0
    for i, (fx, fy) in enumerate([(0.05, 0.3), (0.95, 0.6), (0.1, 0.95), (0.5, 0.02), (0.9, 0.98)]):
        pg.locator(".palette button").nth(i * 2).click()
        pg.locator(".paint-canvas").click(position={"x": cv["width"] * fx, "y": cv["height"] * fy})
        pg.wait_for_timeout(150)
    pg.screenshot(path=str(OUT / "3_paint.png"), full_page=True)
    pg.locator(".cook-btn", has_text="다 칠했어요").click()
    pg.wait_for_timeout(300)
    res["paint_title"] = pg.locator(".modal-box h3").inner_text()
    pg.screenshot(path=str(OUT / "4_paint_done.png"))
    ok(pg)
    res["drawings_saved"] = len(get(pg)["drawings"])

    # 책방
    to_school(pg)
    pg.locator(".school-btn").nth(2).click()
    pg.locator(".book-row").first.click()
    pg.screenshot(path=str(OUT / "5_book.png"))
    pg.click("text=다 읽었어요")
    pg.wait_for_timeout(200)
    res["book_title"] = pg.locator(".modal-box h3").inner_text()
    ok(pg)

    # 말 가르치기 -> 대화
    to_school(pg)
    pg.locator(".school-btn").nth(3).click()
    pg.fill(".teach-form input >> nth=0", "잘 자")
    pg.fill(".teach-form input >> nth=1", "좋은 꿈 꿔요 주인님!")
    pg.locator(".teach-form .cook-btn").click()
    pg.wait_for_timeout(200)
    ok(pg)
    pg.fill(".chat input", "오늘도 잘 자")
    pg.click(".chat .btn")
    pg.wait_for_timeout(200)
    res["chat_reply"] = pg.locator(".bubble").inner_text()
    s = get(pg)
    res["calendar"] = s["calendar"]
    res["points"] = s["points"]
    to_school(pg)
    pg.screenshot(path=str(OUT / "6_hub_gallery.png"), full_page=True)
    b.close()
srv.shutdown()
for k, v in res.items():
    print(k, "=", v)
print("ERR:", errs or "none")
