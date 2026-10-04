"""배포용 dist/ 폴더를 만든다 (게임 실행에 필요한 파일만, archive_original 등은 제외).

사용: python build_dist.py  ->  dist/ 를 Cloudflare Pages 에 업로드
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DIST = PROJECT / "dist"

FILES = ["manifest.json"]
# 동물/꾸미기/음식 그림은 묶음 파일에도 들어 있지만, 묶음에 없을 때를 대비해 개별 파일도 올린다
DIRS = ["assets/backgrounds", "assets/icons", "assets/ui", "assets/animals", "assets/deco", "assets/food", "assets/medicine", "assets/school", "assets/travel"]
VERSIONED = ["assets/sprites_bundle.js", "assets/food_data.js"]

# Cloudflare Pages 캐시 설정: 화면/서비스워커는 매번 확인, 나머지는 하루 캐시
HEADERS = """/index.html
  Cache-Control: no-cache
/sw.js
  Cache-Control: no-cache
/
  Cache-Control: no-cache
/assets/*
  Cache-Control: public, max-age=86400
/assets/*.js
  Cache-Control: no-cache
"""


def main():
    subprocess.run([sys.executable, str(PROJECT / "research" / "build_sprite_bundle.py")], check=True)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for f in FILES:
        shutil.copy2(PROJECT / f, DIST / f)
    for d in DIRS:
        # 원본 생성 이미지(*_color.png)는 참고용이라 올리지 않는다
        shutil.copytree(PROJECT / d, DIST / d, ignore=shutil.ignore_patterns("*_color.png"))
    (DIST / "assets").mkdir(exist_ok=True)
    shutil.copy2(PROJECT / "assets" / "sprites_bundle.js", DIST / "assets" / "sprites_bundle.js")
    shutil.copy2(PROJECT / "assets" / "food_data.js", DIST / "assets" / "food_data.js")
    build = time.strftime("%Y%m%d%H%M%S")
    html = (PROJECT / "index.html").read_text(encoding="utf-8")
    for v in VERSIONED:
        assert f'src="{v}"' in html, v
        html = html.replace(f'src="{v}"', f'src="{v}?v={build}"')
    (DIST / "index.html").write_text(html, encoding="utf-8")
    sw = (PROJECT / "sw.js").read_text(encoding="utf-8").replace("__BUILD__", build)
    (DIST / "sw.js").write_text(sw, encoding="utf-8")
    (DIST / "_headers").write_text(HEADERS, encoding="utf-8")
    files = [p for p in DIST.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(f"dist ready: {len(files)} files, {size / 1e6:.1f} MB, build {build}")


if __name__ == "__main__":
    main()
