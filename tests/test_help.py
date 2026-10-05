"""탐험 '도움 요청' 방 테스트: 물자(물약)·미로(성공/시간 초과)·몬스터 2마리, 보상과 유령 손해."""
import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "help"
OUT.mkdir(parents=True, exist_ok=True)
KEY = "dongmulnongjang.save.v1"

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
handler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html?test=1"

errors = []
results = {}

MATES = """[
  {slug:'dragon', name:'용용', stats:{love:420, know:380, charm:400, power:450}, effort:20, score:1700, grade:'A', at:1, gear:{weapon:'game_woodsword'}},
  {slug:'rabbit', name:'토순', stats:{love:350, know:500, charm:330, power:360}, effort:20, score:1600, grade:'A', at:1},
  {slug:'wolf', name:'늑대랑', stats:{love:500, know:310, charm:380, power:420}, effort:20, score:1650, grade:'A', at:1},
  {slug:'penguin', name:'펭펭', stats:{love:320, know:340, charm:450, power:520}, effort:20, score:1660, grade:'A', at:1}
]"""

# 미로 BFS 로 길을 찾아 방향 목록을 돌려준다(벽 비트 1=위 2=오른쪽 4=아래 8=왼쪽)
SOLVE = """() => {
  const m = window.__dnMaze(); const n = m.n, W = m.walls;
  const prev = {0: null}; const q = [0];
  const D = [[0,-1,1],[1,0,2],[0,1,4],[-1,0,8]];
  while (q.length) { const c = q.shift(); const x = c % n, y = Math.floor(c / n);
    for (const [dx,dy,b] of D) { if (W[c] & b) continue; const nx=x+dx, ny=y+dy, ni=ny*n+nx;
      if (nx<0||ny<0||nx>=n||ny>=n||ni in prev) continue; prev[ni]=[c,dx,dy]; q.push(ni); } }
  const path = []; let c = n*n-1; while (prev[c]) { path.unshift([prev[c][1], prev[c][2]]); c = prev[c][0]; }
  return path;
}"""


def fight(pg, sel):
    """전투 명령을 누르고 효과 연출이 끝날 때까지 기다린다."""
    pg.click(sel)
    pg.wait_for_function("() => !document.querySelector('.ex-cmds.busy')")


def get_save(pg):
    return json.loads(pg.evaluate(f"() => localStorage.getItem('{KEY}')"))


def setup(pg, ask, slug="cat", extra=""):
    """5층 '도움 요청' 방에 들어간 상태를 만든다."""
    pg.evaluate(f"""() => {{
      const mates = {MATES};
      const members = {{}}; mates.forEach(c => members[c.slug] = {{ hp: c.stats.power, mp: c.stats.know }});
      const s = {{ points: 1000, companions: mates, party: mates.map(c => c.slug),
        goodsBag: {{ game_shealingpotion: 1, game_woodshield: 1 }},
        tower: {{ best: 9, saved: 1, cleared: false, seen: {{}}, story: {{}}, doorOpen: false,
          run: {{ floor: 5, members, loot: {{ points: 0, items: {{}} }}, room: 'lost', scene: 'lost',
                 guest: {{ slug: '{slug}', ask: '{ask}' }}, turn: 0, log: [] }} }} }};
      {extra}
      localStorage.setItem('{KEY}', JSON.stringify(s));
    }}""")
    pg.reload()
    pg.wait_for_load_state("networkidle")
    pg.click("[data-tab=explore]")
    if errors:
        print("PAGE ERRORS:", errors)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, is_mobile=True, has_touch=True, service_workers="block")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")

    # 1) 물자: 물약 1개 주기 (유령 확률 0 으로 고정해 보상 확인)
    setup(pg, "supply")
    pg.screenshot(path=str(OUT / "1_supply_ask.png"), full_page=True)
    pg.evaluate("() => { Math._r = Math.random; Math.random = () => 0.5; }")
    pg.click("text=물약 1개 주기")
    pg.evaluate("() => { Math.random = Math._r; }")
    pg.screenshot(path=str(OUT / "2_supply_done.png"), full_page=True)
    s = get_save(pg)
    results["supply_potion_left"] = s["goodsBag"].get("game_shealingpotion")
    results["supply_title"] = s["tower"]["run"]["title"]
    results["supply_loot"] = s["tower"]["run"]["loot"]

    # 2) 물약이 없으면 버튼 막힘
    setup(pg, "supply", extra="s.goodsBag = {};")
    results["supply_disabled_without_potion"] = pg.locator(".ex-cmds .ex-btn").first.is_disabled()

    # 3) 미로: 길 찾아 성공
    setup(pg, "maze", slug="hamster")
    pg.click("text=길 찾아 주기")
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "3_maze.png"), full_page=True)
    path = pg.evaluate(SOLVE)
    results["maze_path_len"] = len(path)
    names = {(0, -1): "up", (1, 0): "right", (0, 1): "down", (-1, 0): "left"}
    # 첫 칸은 화살표 버튼, 나머지는 키보드로
    pg.click(f".ex-pad-{names[tuple(path[0])]}")
    keys = {"up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight"}
    for dx, dy in path[1:]:
        pg.keyboard.press(keys[names[(dx, dy)]])
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / "4_maze_done.png"), full_page=True)
    s = get_save(pg)
    results["maze_room_after"] = s["tower"]["run"]["room"]
    results["maze_title"] = s["tower"]["run"]["title"]

    # 4) 미로: 시간 초과(제한 시간을 짧게 조작)
    setup(pg, "maze", slug="hamster")
    pg.click("text=길 찾아 주기")
    pg.evaluate("() => { window.__dnMaze().end = Date.now() + 300; }")
    pg.wait_for_timeout(900)
    s = get_save(pg)
    results["maze_timeout_title"] = s["tower"]["run"]["title"]

    # 5) 몬스터 2마리
    setup(pg, "hunt", slug="koala")
    pg.click("text=몬스터 물리쳐 주기")
    pg.screenshot(path=str(OUT / "5_hunt.png"), full_page=True)
    results["hunt_foes"] = len(get_save(pg)["tower"]["run"]["foes"])
    pg.locator(".ex-foe-card").nth(1).click()
    results["target_after_tap"] = get_save(pg)["tower"]["run"]["target"]
    for _ in range(30):
        run = get_save(pg)["tower"]["run"]
        if not run or run["room"] != "battle":
            break
        fight(pg, ".ex-cmd-attack")
    pg.screenshot(path=str(OUT / "6_hunt_done.png"), full_page=True)
    run = get_save(pg)["tower"]["run"]
    results["hunt_after"] = (run["room"], run["title"]) if run else "wiped"

    # 6) 유령: 손해 5종이 모두 나오는지 반복
    seen = {}
    for i in range(40):
        setup(pg, "supply", extra="s.goodsBag.game_shealingpotion = 5; s.goodsBag.game_magicpotion = 3;")
        pg.evaluate("() => { Math._r = Math.random; let first = true; Math.random = () => { if (first) { first = false; return 0.01; } return Math._r(); }; }")
        pg.click("text=물약 1개 주기")
        pg.evaluate("() => { Math.random = Math._r; }")
        s = get_save(pg)
        run = s["tower"]["run"]
        log = " ".join(run["log"])
        kind = ("points" if "주머니" in log else "potions" if "훔쳐" in log else "curse" if "저주" in log
                else "retreat" if "떨어졌어요" in log else "seal" if "봉인" in log else "?")
        if kind not in seen:
            seen[kind] = {"floor": run["floor"], "points": s["points"], "debuff": run.get("debuff"), "sealed": run.get("sealed")}
            pg.screenshot(path=str(OUT / f"7_ghost_{kind}.png"), full_page=True)
        if len(seen) == 5:
            break
    results["ghost_kinds"] = seen

    # 저주 상태에서 다음 층 → 상태 표시와 능력치 감소
    setup(pg, "supply", extra="s.tower.run.room = 'cleared'; s.tower.run.debuff = { from: 5, until: 8, ratio: 0.8 }; s.tower.run.sealed = [{ slug: 'dragon', kind: 'weapon' }];")
    pg.click("text=6층으로 올라가기")
    pg.screenshot(path=str(OUT / "8_cursed_status.png"), full_page=True)
    results["status_text"] = pg.locator(".ex-status").inner_text() if pg.locator(".ex-status").count() else None
    b.close()

srv.shutdown()
for k, v in results.items():
    print(k, "=", v)
print("ERRORS:", errors or "none")
