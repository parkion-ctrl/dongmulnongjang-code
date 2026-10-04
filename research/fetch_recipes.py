"""원작 쿠킹샵 요리법 팝업(foodshop/pop/foods_*.html, 139개)에서 조합표를 뽑는다.

팝업 구조: 재료A(그림+이름) + 재료B(그림+이름) = 결과(그림+이름)
결과: research/recipes_original.json, 원본 HTML은 archive_original/pages/recipes/
"""
import json
import re
import time
import urllib.request
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
LIST = Path(r"C:\Users\ajou\AppData\Local\Temp\food_pops.json")
RAW = PROJECT / "archive_original" / "pages" / "recipes"
OUT = PROJECT / "research" / "recipes_original.json"


def decode(data):
    for enc in ("euc-kr", "cp949", "utf-8"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", "replace")


def parse(text):
    body = text[text.lower().find("<body"):]
    seq = []
    for m in re.finditer(r"<img[^>]*>|>([^<>]{1,})<", body, re.I):
        s = m.group(0)
        if s.lower().startswith("<img"):
            src = re.search(r"src=[\"']?([^\"' >]+)", s, re.I)
            if src:
                seq.append(("img", src.group(1)))
        elif m.group(1) and m.group(1).strip() and m.group(1).strip() != "&nbsp;":
            seq.append(("txt", m.group(1).strip()))
    items = []
    for i, (kind, val) in enumerate(seq):
        if kind == "txt" and i > 0 and seq[i - 1][0] == "img":
            items.append({"name": val, "img": re.sub(r"^https?://web\.archive\.org/web/\d+(im_|id_)?/", "", seq[i - 1][1])})
    return items


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    pops = json.loads(LIST.read_text())
    recipes = []
    for url, ts in pops:
        name = url.rsplit("/", 1)[-1]
        cache = RAW / name
        if cache.exists():
            text = cache.read_text(encoding="utf-8")
        else:
            for attempt in range(4):
                try:
                    req = urllib.request.Request(f"https://web.archive.org/web/{ts}id_/{url}", headers={"User-Agent": "Mozilla/5.0"})
                    text = decode(urllib.request.urlopen(req, timeout=40).read())
                    cache.write_text(text, encoding="utf-8")
                    break
                except Exception as e:
                    print("retry", name, e, flush=True)
                    time.sleep(30 * (attempt + 1))
            else:
                print("FAIL", name, flush=True)
                continue
            time.sleep(4)
        items = parse(text)
        if len(items) >= 3:
            recipes.append({"id": name.replace(".html", ""), "a": items[0], "b": items[1], "result": items[2]})
            print(name, items[0]["name"], "+", items[1]["name"], "=", items[2]["name"], flush=True)
        else:
            print("?", name, items, flush=True)
    OUT.write_text(json.dumps(recipes, ensure_ascii=False, indent=1), encoding="utf-8")
    print("DONE", len(recipes), "recipes", flush=True)


if __name__ == "__main__":
    main()
