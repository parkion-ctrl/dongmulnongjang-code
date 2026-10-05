"""원작 탐험(북쪽 탑) 그림을 게임 폴더(assets/explore/)로 옮긴다.

- ex_01~07.gif: 원작 몬스터 도감 그림(투명 배경) → 그대로 복사
- 탐험 머리 그림: top_0924_img01+02 (보라색 성 안 '탐험' 제목) 이어 붙이기
- 북쪽탑의 전설 그림 img_0924_01.gif
- 마법 상인 길데스텐: 사용법 그림에서 잘라 흰 배경을 투명하게
- 탐험 아이템(원작 item/game_*.gif: 검·방패·물약, gold_bar=황금덩어리, magicsoul=마법의 정령, northtowercoin)
사용: python research/import_explore.py
"""
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "archive_original" / "jr_naver_images" / "new_pet" / "explore"
OUT = ROOT / "assets" / "explore"
ITEM_SRC = SRC.parent / "item"
ITEMS = ["game_woodsword", "game_knightsword", "game_lightningsword", "game_xsword",
         "game_woodshield", "game_ironshield", "game_crystalshield", "game_rainbowshield",
         "game_shealingpotion", "game_healingpotion", "game_magicpotion",
         "gold_bar", "magicsoul", "northtowercoin", "god_fabric", "solidwood"]


def clear_white(im, tol=28):
    """가장자리에서 이어진 흰 배경만 투명하게(그림 안쪽의 흰색은 보존)."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()
    white = lambda p: p[0] > 255 - tol and p[1] > 255 - tol and p[2] > 255 - tol
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    seen = set()
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        seen.add((x, y))
        if not white(px[x, y]):
            continue
        px[x, y] = (255, 255, 255, 0)
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return im.crop(im.getbbox())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(1, 8):
        shutil.copy2(SRC / f"ex_{i:02d}.gif", OUT / f"ex_{i:02d}.gif")
    shutil.copy2(SRC / "img_0924_01.gif", OUT / "legend.gif")
    a = Image.open(SRC / "top_0924_img01.gif").convert("RGB")
    b = Image.open(SRC / "top_0924_img02.gif").convert("RGB")
    head = Image.new("RGB", (a.width + b.width, a.height))
    head.paste(a, (0, 0))
    head.paste(b, (a.width, 0))
    head.save(OUT / "head.png")
    merchant = Image.open(SRC / "img_0924_05.gif").convert("RGB").crop((30, 40, 222, 192))
    clear_white(merchant).save(OUT / "merchant.png")
    for name in ITEMS:
        # 일부(코인·정령)는 흰 배경이라 투명 처리해서 png로
        clear_white(Image.open(ITEM_SRC / f"{name}.gif")).save(OUT / f"{name}.png")
    print("ok", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
