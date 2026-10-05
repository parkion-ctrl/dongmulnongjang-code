"""Wayback에 보관된 원작 페이지를 받아 글자/이미지 목록을 뽑는다 (원작 시스템 조사용).

사용: python fetch_pages.py <timestamp>/<url> ...
결과: archive_original/pages/<경로>.html, .txt (본문 글자 + 참조 이미지)
"""
import html
import re
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "archive_original" / "pages"


def fetch(spec):
    ts, url = spec.strip().split("/", 1)
    raw_url = f"https://web.archive.org/web/{ts}id_/{url}"
    req = urllib.request.Request(raw_url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=40).read()
    for enc in ("euc-kr", "cp949", "utf-8"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = data.decode("utf-8", "replace")
    name = re.sub(r"^https?://[^/]+/", "", url).replace("/", "__").replace("?", "_") or "index"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.html").write_text(text, encoding="utf-8")
    imgs = sorted(set(re.findall(r"[\w./:-]+\.(?:gif|jpg|png|swf)", text, re.I)))
    body = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    body = html.unescape(re.sub(r"<[^>]+>", " ", body))
    body = re.sub(r"\s+", " ", body).strip()
    (OUT / f"{name}.txt").write_text(body + "\n\nIMAGES:\n" + "\n".join(imgs), encoding="utf-8")
    return name, body, imgs


def main():
    for spec in sys.argv[1:]:
        try:
            name, body, imgs = fetch(spec)
            print(f"=== {name} ({len(body)} chars, {len(imgs)} imgs)")
            print(body[:1500])
            print("IMG:", " ".join(i.split("/")[-1] for i in imgs if "new_pet" in i or i.endswith(".swf"))[:1200])
        except Exception as e:
            print(f"=== {spec} FAILED {e}")
        time.sleep(4)


if __name__ == "__main__":
    main()
