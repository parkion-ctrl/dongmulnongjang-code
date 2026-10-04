"""원작 요리 조합표(recipes_original.json) -> 게임 데이터(assets/food_data.js) + 음식 그림(assets/food/).

- 음식 id = 원작 그림 파일 이름(확장자 제외). 같은 결과가 여러 조합으로 나와도 하나의 음식.
- 단계(tier): 어떤 조합의 결과로도 안 나오는 음식 = 1(기본 재료, 가게에서 삼). 결과는 재료 단계 중 큰 값 + 1 (최대 4).
- 효과는 원작 수치가 없어 단계별 임시값: 합계 1단계 10 / 2단계 25 / 3단계 45 / 4단계 70, 지수는 id 해시로 1~2개.
"""
import hashlib
import json
import time
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SRC_JSON = PROJECT / "research" / "recipes_original.json"
ARCHIVE = PROJECT / "archive_original" / "jr_naver_images"
OUT_IMG = PROJECT / "assets" / "food"
OUT_JS = PROJECT / "assets" / "food_data.js"

STATS = ["love", "charm", "power", "know"]
TIER_TOTAL = {1: 10, 2: 25, 3: 45, 4: 70}
BASE_PRICE = 15
BAD = {"id": "badsoup", "name": "먹을 수 없는 요리", "img": "http://image.jr.naver.com/new_pet/material/badsoup.gif"}


def local_path(url):
    rel = url.split("image.jr.naver.com", 1)[-1].lstrip(":80").lstrip("/")
    return ARCHIVE / rel


def ensure_image(url, dest):
    if dest.exists():
        return True
    lp = local_path(url)
    if lp.exists():
        dest.write_bytes(lp.read_bytes())
        return True
    for attempt in range(3):
        try:
            req = urllib.request.Request(f"https://web.archive.org/web/2005id_/{url}", headers={"User-Agent": "Mozilla/5.0"})
            dest.write_bytes(urllib.request.urlopen(req, timeout=40).read())
            time.sleep(3)
            return True
        except Exception as e:
            print("img retry", url, e)
            time.sleep(20 * (attempt + 1))
    return False


def gains_for(fid, tier):
    h = hashlib.md5(fid.encode()).digest()
    total = TIER_TOTAL[tier]
    s1 = STATS[h[0] % 4]
    if tier == 1 or h[1] % 3 == 0:
        return {s1: total}
    s2 = STATS[(h[0] + 1 + h[2] % 3) % 4]
    big = round(total * 0.6)
    return {s1: big, s2: total - big}


def main():
    raw = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    recipes, seen = [], set()
    for r in raw:
        key = (tuple(sorted([Path(r["a"]["img"]).stem, Path(r["b"]["img"]).stem])), Path(r["result"]["img"]).stem)
        if key not in seen:
            seen.add(key)
            recipes.append(r)
    foods = {}
    for r in recipes:
        for part in ("a", "b", "result"):
            item = r[part]
            fid = Path(item["img"].split("?")[0]).stem
            item["id"] = fid
            foods.setdefault(fid, {"id": fid, "name": item["name"], "img": item["img"]})
    results = {r["result"]["id"] for r in recipes}
    tier = {fid: 1 for fid in foods if fid not in results}
    for _ in range(10):
        for r in recipes:
            a, b, c = r["a"]["id"], r["b"]["id"], r["result"]["id"]
            if a in tier and b in tier:
                t = min(4, max(tier[a], tier[b]) + 1)
                if tier.get(c, 0) < t and c not in [x for x in foods if foods[x].get("base")]:
                    tier[c] = max(tier.get(c, 0), t)
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    out_foods = []
    for fid, f in sorted(foods.items(), key=lambda kv: (tier.get(kv[0], 4), kv[1]["name"])):
        t = tier.get(fid, 4)
        ok = ensure_image(f["img"], OUT_IMG / f"{fid}.gif")
        out_foods.append({"id": fid, "name": f["name"], "tier": t, "gain": gains_for(fid, t),
                          "price": BASE_PRICE if t == 1 else None, "img": ok})
    ensure_image(BAD["img"], OUT_IMG / "badsoup.gif")
    data = {
        "foods": out_foods,
        "bad": {"id": "badsoup", "name": BAD["name"], "gain": {}, "fatigue": 10},
        "recipes": [{"id": r["id"], "a": r["a"]["id"], "b": r["b"]["id"], "result": r["result"]["id"]} for r in recipes],
    }
    OUT_JS.write_text("window.FOOD_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    from collections import Counter
    print(len(out_foods), "foods, tiers:", Counter(f["tier"] for f in out_foods), "| recipes:", len(recipes),
          "| missing images:", [f["id"] for f in out_foods if not f["img"]])


if __name__ == "__main__":
    main()
