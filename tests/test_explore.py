"""탐험(북쪽 탑) 브라우저 테스트: 허브·상인·장비·전투·퀴즈·저장·봉인된 문·전멸."""
import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "explore"
OUT.mkdir(parents=True, exist_ok=True)
KEY = "dongmulnongjang.save.v1"

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
handler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

errors = []
results = {}

MATES = """[
  {slug:'dragon', name:'용용', stats:{love:420, know:380, charm:400, power:450}, effort:20, score:1700, grade:'A', at:1},
  {slug:'rabbit', name:'토순', stats:{love:350, know:500, charm:330, power:360}, effort:20, score:1600, grade:'A', at:1},
  {slug:'wolf', name:'늑대랑', stats:{love:500, know:310, charm:380, power:420}, effort:20, score:1650, grade:'A', at:1},
  {slug:'penguin', name:'펭펭', stats:{love:320, know:340, charm:450, power:520}, effort:20, score:1660, grade:'A', at:1}
]"""


def put_save(pg, obj_js):
    pg.evaluate(f"() => localStorage.setItem('{KEY}', JSON.stringify({obj_js}))")
    pg.reload()
    pg.wait_for_load_state("networkidle")


def fight(pg, sel):
    """전투 명령을 누르고 효과 연출이 끝날 때까지 기다린다."""
    pg.click(sel)
    pg.wait_for_function("() => !document.querySelector('.ex-cmds.busy')")


def get_save(pg):
    return json.loads(pg.evaluate(f"() => localStorage.getItem('{KEY}')"))


def mutate(pg, js):
    pg.evaluate(f"""() => {{ const s = JSON.parse(localStorage.getItem('{KEY}')); {js}
      localStorage.setItem('{KEY}', JSON.stringify(s)); }}""")
    pg.reload()
    pg.wait_for_load_state("networkidle")
    pg.click("[data-tab=explore]")


SEEN_ROOMS = set()


def step(pg):
    """지금 방에 맞는 버튼 하나를 누른다. 저장 지점이면 저장."""
    s = get_save(pg)
    run = s["tower"]["run"]
    if not run:
        return None
    if run["room"] == "battle":
        live_mp = any(m["mp"] >= 30 for m in run["members"].values() if m["hp"] > 0)
        fight(pg, ".ex-cmd-magic" if any(f.get("boss") for f in run["foes"]) and live_mp else ".ex-cmd-attack")
    elif run["room"] == "quiz":
        pg.locator(".quiz-opt").first.click()
    elif run["room"] == "fork":
        pg.locator(".ex-door").nth(len(SEEN_ROOMS) % 2).click()
    elif run["room"] == "chest":
        pg.click("text=그냥 지나가기")
    elif run["room"] == "trap":
        pg.locator(".ex-cmds .ex-btn").first.click()
    elif run["room"] == "merchant":
        pg.click("text=인사하고 지나가기")
    elif run["room"] == "lost":
        pg.click("text=미안하지만 지나가기")
    elif run["room"] == "door":
        return "door"
    elif run["room"] == "cleared":
        if pg.locator("#modal").is_visible():
            pg.locator("#modal-box button").last.click()
        if pg.locator("text=저장하기").count():
            pg.click("text=저장하기")
            pg.wait_for_timeout(50)
            if not get_save(pg)["tower"]["run"]["room"] == "cleared":
                return "?"
        pg.locator("button", has_text="층으로 올라가기").click()
    return run["floor"]


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, is_mobile=True, has_touch=True, service_workers="block")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")

    # 동료 없음
    pg.click("[data-tab=explore]")
    pg.screenshot(path=str(OUT / "0_no_mates.png"), full_page=True)
    results["start_disabled_without_mates"] = pg.locator(".ex-go button").first.is_disabled()

    put_save(pg, f"{{ points: 1000, companions: {MATES}, party: ['dragon','rabbit','wolf','penguin'] }}")
    pg.click("[data-tab=explore]")
    pg.screenshot(path=str(OUT / "1_hub.png"), full_page=True)

    # 상인: 나무 검 2개, 물약 1개
    pg.click("text=마법 상인 길데스텐")
    pg.screenshot(path=str(OUT / "2_merchant.png"), full_page=True)
    card = pg.locator(".food-card", has_text="나무 검")
    card.locator("button").click()
    card.locator("button").click()
    pg.locator(".food-card", has_text="체력 회복 약(소)").locator("button").click()
    s = get_save(pg)
    results["points_after_buy"] = s["points"]
    results["bag_after_buy"] = s["goodsBag"]
    pg.click("text=탐험으로")

    # 장비: 용용에게 나무 검
    pg.locator(".ex-mate", has_text="용용").click()
    pg.locator(".ex-gear-pick button", has_text="나무 검").click()
    pg.screenshot(path=str(OUT / "3_gear.png"))
    pg.click("#modal-box >> text=닫기")
    s = get_save(pg)
    results["dragon_gear"] = s["companions"][0].get("gear")
    results["bag_after_equip"] = s["goodsBag"]

    # 1층 전투
    pg.click("text=1층부터 오르기")
    pg.screenshot(path=str(OUT / "4_battle.png"), full_page=True)
    # 아이템 버튼
    pg.click(".ex-cmd-item")
    pg.screenshot(path=str(OUT / "6_potions.png"))
    pg.click("#modal-box >> text=닫기")
    fight(pg, ".ex-cmd-attack")
    pg.screenshot(path=str(OUT / "5_after_attack.png"), full_page=True)
    results["log_after_attack"] = pg.locator(".ex-log").inner_text()[:200]

    # 10층까지 올라가서 저장
    floors = []
    for _ in range(300):
        s = get_save(pg)
        run = s["tower"]["run"]
        if run and run["room"] not in SEEN_ROOMS and run["room"] != "cleared":
            SEEN_ROOMS.add(run["room"])
            pg.screenshot(path=str(OUT / f"room_{run['room']}.png"), full_page=True)
        if run and run["floor"] == 10 and run["room"] == "cleared":
            if pg.locator("#modal").is_visible():
                pg.screenshot(path=str(OUT / "8_story10.png"))
                pg.locator("#modal-box button").last.click()
            pg.screenshot(path=str(OUT / "9_floor10_cleared.png"), full_page=True)
            pg.click("text=저장하기")
            break
        if not run:
            break
        floors.append(step(pg))
    s = get_save(pg)
    results["rooms_seen"] = sorted(SEEN_ROOMS)
    results["after_floor10"] = {k: s["tower"][k] for k in ("best", "saved", "story")}
    results["run_alive"] = bool(s["tower"]["run"])
    results["points_after_save"] = s["points"]
    results["bag_after_save"] = s["goodsBag"]
    pg.screenshot(path=str(OUT / "10_saved.png"), full_page=True)

    # 나가기 → 허브에 11층 시작 버튼
    pg.click("text=탑에서 나가기")
    pg.click("#modal-box >> text=나가기")
    results["start_buttons"] = pg.locator(".ex-go button").all_inner_texts()

    # 30층 봉인된 문 → 주문 → 마도사. 약한 파티로 전멸 확인
    mutate(pg, """s.tower.saved = 21; s.tower.best = 29;
      s.tower.run = { floor: 30, members: {}, loot: { points: 77, items: { gold_bar: 1 } }, room: null, foes: null, turn: 0, log: [] };
      s.companions.forEach(c => s.tower.run.members[c.slug] = { hp: 200, mp: 0 });""")
    pg.click("text=탑에서 나가기")
    pg.click("#modal-box >> text=계속 탐험")
    # run.room 이 null 이면 화면이 빈 방 → enterFloor 를 거치도록 31층 대신 29층 클리어 상태로 만든다
    mutate(pg, "s.tower.run.floor = 29; s.tower.run.room = 'cleared'; s.tower.run.result = '';")
    pg.click("text=30층으로 올라가기")
    pg.screenshot(path=str(OUT / "11_door.png"), full_page=True)
    results["door_room"] = get_save(pg)["tower"]["run"]["room"]
    pg.fill(".ex-cmds input", "아브라카다브라")
    pg.click("text=주문 외우기")
    results["door_wrong_toast"] = pg.locator("#toast").inner_text()
    pg.fill(".ex-cmds input", "익스 피니트 릭투")
    pg.click("text=주문 외우기")
    pg.screenshot(path=str(OUT / "12_mage.png"), full_page=True)
    results["mage_room"] = get_save(pg)["tower"]["run"]["room"]
    for _ in range(40):
        if not get_save(pg)["tower"]["run"]:
            break
        fight(pg, ".ex-cmd-guard" if _ % 2 else ".ex-cmd-attack")
    pg.screenshot(path=str(OUT / "13_wipe.png"))
    results["wipe_title"] = pg.locator("#modal-box h3").inner_text() if pg.locator("#modal").is_visible() else None
    s = get_save(pg)
    results["after_wipe_points"] = s["points"]
    results["after_wipe_gold"] = s["goodsBag"].get("gold_bar")

    # 아이템박스 용품 탭
    pg.click("#modal-box >> text=확인")
    pg.click("[data-tab=shop]")
    pg.click(".box-tabs button >> nth=2")
    pg.screenshot(path=str(OUT / "14_goods_tab.png"), full_page=True)
    results["goods_cards"] = pg.locator(".food-card strong").all_inner_texts()

    # 몬스터 도감
    pg.click("[data-tab=explore]")
    pg.click("text=몬스터 도감")
    pg.screenshot(path=str(OUT / "15_book.png"), full_page=True)
    results["book_seen"] = pg.locator(".ex-book-row:not(.unseen)").count()
    b.close()

srv.shutdown()
for k, v in results.items():
    print(k, "=", v)
print("ERRORS:", errors or "none")
