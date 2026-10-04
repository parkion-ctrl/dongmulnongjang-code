import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "shots2"
OUT.mkdir(parents=True, exist_ok=True)
KEY = "dongmulnongjang.save.v1"

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
handler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

errors = []
results = {}


def set_save(pg, mutate_js):
    pg.evaluate(f"""() => {{
      const s = JSON.parse(localStorage.getItem('{KEY}'));
      {mutate_js}
      localStorage.setItem('{KEY}', JSON.stringify(s));
    }}""")
    pg.reload()
    pg.wait_for_load_state("networkidle")


def get_save(pg):
    return json.loads(pg.evaluate(f"() => localStorage.getItem('{KEY}')"))


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, is_mobile=True, has_touch=True, service_workers="block")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)

    pg.goto(URL)
    pg.wait_for_load_state("networkidle")
    pg.locator(".tile", has_text="용").first.click()
    pg.click("text=분양받기")

    # 짝 맞추기 완료가 노력 점수로 쌓이는지
    set_save(pg, "s.pet.effort = 0;")
    pg.evaluate("() => {}")
    # 엔딩 직전 상태
    set_save(pg, "s.pet.stats = {love: 330, know: 310, charm: 320, power: 305}; s.pet.stage = 2; s.pet.effort = 40;")
    pg.click("text=엔딩 도전하기")
    pg.screenshot(path=str(OUT / "1_ending_confirm.png"))
    pg.click("text=사람이 되기")
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "2_ending_result.png"))
    results["result_title"] = pg.locator(".modal-box h3").inner_text()
    pg.click("text=확인")
    s = get_save(pg)
    results["companions_after_end"] = [(c["slug"], c["score"], c["grade"]) for c in s["companions"]]
    results["party_after_end"] = s["party"]
    results["pet_after_end"] = s["pet"]

    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "3_adopt_locked.png"))
    pg.locator(".tile", has_text="용").first.click()
    results["toast_on_locked"] = pg.locator("#toast").inner_text()
    results["modal_opened_on_locked"] = not pg.locator("#modal").is_hidden()

    # 동료 5명 상태로 파티 제한 확인
    set_save(pg, """
      const mk = (slug, name, g, sc) => ({slug, name, stats: {love: 70, know: 80, charm: 75, power: 85}, effort: 20, score: sc, grade: g, at: 1});
      s.companions.push(mk('wolf','늑대랑','A',390), mk('unicorn','유니','S',460), mk('tiger','호돌이','B',340), mk('penguin','펭펭','C',310));
    """)
    pg.click("[data-tab=dex]")
    pg.click("text=동료")
    pg.screenshot(path=str(OUT / "4_companions.png"), full_page=True)
    results["party_before_add"] = get_save(pg)["party"]
    for name in ["늑대랑", "유니", "호돌이", "펭펭"]:
        pg.locator(".mate", has_text=name).click()
    results["party_after_clicks"] = get_save(pg)["party"]
    results["toast_on_full"] = pg.locator("#toast").inner_text()
    pg.screenshot(path=str(OUT / "5_party_full.png"), full_page=True)

    # 게임 엔딩 이후: 용 다시 분양 가능, 엔딩해도 동료 추가 안 됨
    set_save(pg, "s.gameCleared = true;")
    pg.click("[data-tab=farm]")
    pg.locator(".tile", has_text="용").first.click()
    results["readopt_modal_after_clear"] = not pg.locator("#modal").is_hidden()
    pg.click("text=분양받기")
    set_save(pg, "s.pet.stats = {love: 300, know: 300, charm: 300, power: 300}; s.pet.stage = 2; s.pet.effort = 0;")
    pg.click("text=엔딩 도전하기")
    pg.click("text=사람이 되기")
    pg.click("text=확인")
    s = get_save(pg)
    results["companion_count_after_clear_end"] = len(s["companions"])
    results["dex_dragon"] = s["dex"]["dragon"]
    b.close()

srv.shutdown()
for k, v in results.items():
    print(k, "=", v)
print("ERRORS:", errors or "none")
