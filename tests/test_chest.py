"""보물상자 자물쇠 퍼즐 테스트: 3종(길 잇기·보석 밝히기·연동 원판)을 화면을 눌러서 풀고 상자가 열리는지."""
import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = str(Path(__file__).resolve().parent.parent)
OUT = Path(__file__).parent / "shots" / "chest"
OUT.mkdir(parents=True, exist_ok=True)
KEY = "dongmulnongjang.save.v1"

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
handler.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"

errors = []
results = {}
MATES = """[{slug:'dragon', name:'용용', stats:{love:420, know:380, charm:400, power:450}, effort:20, score:1700, grade:'A', at:1}]"""

# 풀이 계획: 누를 칸 번호 목록(퍼즐 상태를 보고 계산)
PLAN = """(puz) => {
  const taps = [];
  if (puz.type === 'pipe') { puz.path.forEach(c => { for (let k = puz.rot[c]; k % 4; k++) taps.push(c); }); return taps; }
  if (puz.type === 'lights') {
    const n = puz.n;
    const tog = (on, c) => { const x = c % n, y = Math.floor(c / n); [[0,0],[1,0],[-1,0],[0,1],[0,-1]].forEach(([dx,dy]) => { const nx=x+dx, ny=y+dy; if (nx>=0&&ny>=0&&nx<n&&ny<n) on[ny*n+nx]^=1; }); };
    for (let top = 0; top < (1 << n); top++) {
      const on = puz.on.slice(), t = [];
      for (let x = 0; x < n; x++) if (top >> x & 1) { tog(on, x); t.push(x); }
      for (let y = 0; y < n - 1; y++) for (let x = 0; x < n; x++) if (!on[y*n+x]) { tog(on, (y+1)*n+x); t.push((y+1)*n+x); }
      if (on.every(Boolean)) return t;
    }
  }
  const n = puz.n;
  for (let m = 0; m < 6 ** n; m++) {
    const pos = puz.pos.slice(); let x = m; const t = [];
    for (let i = 0; i < n; i++) { const k = x % 6; x = Math.floor(x / 6); for (let j = 0; j < k; j++) { [i, ...[].concat(puz.link[i])].forEach(q => { pos[q] = (pos[q]+1)%6; }); t.push(i); } }
    if (pos.every(v => v === 0)) return t;
  }
  return taps;
}"""


def get_save(pg):
    return json.loads(pg.evaluate(f"() => localStorage.getItem('{KEY}')"))


def setup(pg, floor):
    pg.evaluate(f"""() => {{ const mates = {MATES};
      localStorage.setItem('{KEY}', JSON.stringify({{ points: 100, companions: mates, party: ['dragon'],
        tower: {{ best: 20, saved: 1, cleared: false, seen: {{}}, story: {{}}, doorOpen: false,
          run: {{ floor: {floor}, members: {{ dragon: {{ hp: 450, mp: 380 }} }}, loot: {{ points: 0, items: {{}} }},
                 room: 'chest', scene: 'chest', turn: 0, log: [] }} }} }})); }}""")
    pg.reload()
    pg.wait_for_load_state("networkidle")
    pg.click("[data-tab=explore]")


def tap_cell(pg, puz, i):
    box = pg.locator("#puzzle-canvas").bounding_box()
    W = 600
    # 원판 배치는 index.html 의 dialLayout 과 같게
    H = (330 if puz["n"] <= 3 else 620) if puz["type"] == "dials" else 600
    if puz["type"] == "dials":
        x, y = ((i + 0.5) * W / puz["n"], 118) if puz["n"] <= 3 else (
            [(150, 118), (450, 118), (150, 420), (450, 420)] if puz["n"] == 4 else [(100, 118), (300, 118), (500, 118), (200, 420), (400, 420)])[i]
    else:
        pad = 30 if puz["type"] == "pipe" else 24
        cs = (W - pad * 2) / puz["n"]
        x = pad + (i % puz["n"] + 0.5) * cs
        y = pad + (i // puz["n"] + 0.5) * cs
    pg.mouse.click(box["x"] + x / W * box["width"], box["y"] + y / H * box["height"])


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, is_mobile=True, has_touch=True, service_workers="block")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    pg.goto(URL)
    pg.wait_for_load_state("networkidle")

    setup(pg, 5)
    pg.screenshot(path=str(OUT / "0_chest.png"), full_page=True)
    done = {}
    for attempt in range(120):
        floor = [5, 12, 22][attempt % 3]
        setup(pg, floor)
        pg.evaluate("() => { Math._r = Math._r || Math.random; let first = true; Math.random = () => { if (first) { first = false; return 0.9; } return Math._r(); }; }")
        pg.click("text=자물쇠 풀기")
        pg.evaluate("() => { Math.random = Math._r; }")
        puz = get_save(pg)["tower"]["run"]["puzzle"]
        key = f"{puz['type']}{puz['n']}"
        if key in done:
            continue
        pg.screenshot(path=str(OUT / f"1_{key}_start.png"), full_page=True)
        taps = pg.evaluate(PLAN, puz)
        for i, c in enumerate(taps):
            tap_cell(pg, puz, c)
            if i == len(taps) // 2:
                pg.screenshot(path=str(OUT / f"2_{key}_mid.png"), full_page=True)
        pg.wait_for_timeout(600)
        run = get_save(pg)["tower"]["run"]
        done[key] = {"taps": len(taps), "room": run["room"], "title": run.get("title"), "points": run["loot"]["points"]}
        pg.screenshot(path=str(OUT / f"3_{key}_open.png"), full_page=True)
        if len(done) >= 9:
            break
    results["solved"] = done

    # 함정 상자(20%): 퍼즐 없이 체력만 깎임
    setup(pg, 5)
    pg.evaluate("() => { Math._r = Math._r || Math.random; Math.random = () => 0.05; }")
    pg.click("text=자물쇠 풀기")
    pg.evaluate("() => { Math.random = Math._r; }")
    run = get_save(pg)["tower"]["run"]
    results["trap"] = (run["room"], run.get("title"), run["members"]["dragon"]["hp"], run.get("puzzle"), run["loot"]["points"])
    pg.screenshot(path=str(OUT / "4_trap.png"), full_page=True)

    # 포기
    setup(pg, 5)
    pg.evaluate("() => { Math._r = Math._r || Math.random; let first = true; Math.random = () => { if (first) { first = false; return 0.9; } return Math._r(); }; }")
    pg.click("text=자물쇠 풀기")
    pg.evaluate("() => { Math.random = Math._r; }")
    pg.click("text=포기하고 지나가기")
    run = get_save(pg)["tower"]["run"]
    results["give_up"] = (run["room"], run["loot"]["points"], run.get("puzzle"))

    # 퍼즐 중 새로고침해도 이어서
    setup(pg, 5)
    pg.evaluate("() => { Math._r = Math._r || Math.random; let first = true; Math.random = () => { if (first) { first = false; return 0.9; } return Math._r(); }; }")
    pg.click("text=자물쇠 풀기")
    pg.evaluate("() => { Math.random = Math._r; }")
    before = get_save(pg)["tower"]["run"]["puzzle"]
    pg.reload()
    pg.wait_for_load_state("networkidle")
    pg.click("[data-tab=explore]")
    results["resume_same_puzzle"] = get_save(pg)["tower"]["run"]["puzzle"] == before and pg.locator("#puzzle-canvas").count() == 1
    b.close()

srv.shutdown()
for k, v in results.items():
    print(k, "=", v)
print("ERRORS:", errors or "none")
