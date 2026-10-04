"""동물 이미지 전체를 data URI로 묶은 assets/sprites_bundle.js 를 만든다.

파일 수 제한이 있는 곳(미리보기 페이지)에 올릴 때와, 첫 로딩 요청 수를 줄이기 위해 쓴다.
게임은 window.SPRITE_DATA 에 경로가 있으면 그걸, 없으면 개별 파일을 쓴다.
"""
import base64
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
MIME = {".gif": "image/gif", ".webp": "image/webp", ".png": "image/png"}


def main():
    data = {}
    files = sorted((PROJECT / "assets" / "animals").rglob("*")) + sorted((PROJECT / "assets" / "deco").glob("*")) \
        + sorted((PROJECT / "assets" / "food").glob("*")) \
        + sorted((PROJECT / "assets" / "medicine").glob("*"))
    for f in files:
        # 원작 GIF가 있는 단계의 추출본 webp는 게임에서 안 쓰므로 뺀다
        if f.suffix.lower() == ".webp" and f.with_suffix(".gif").exists():
            continue
        if f.suffix.lower() in MIME:
            rel = f.relative_to(PROJECT).as_posix()
            data[rel] = f"data:{MIME[f.suffix.lower()]};base64," + base64.b64encode(f.read_bytes()).decode()
    out = PROJECT / "assets" / "sprites_bundle.js"
    out.write_text("window.SPRITE_DATA=" + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(len(data), "images,", round(out.stat().st_size / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
