"""원작 메뉴 탭 그림에서 캐릭터 아이콘만 잘라 투명 PNG로 만든다 (폰 메뉴용).

tab_mini0N_on.gif (160x49): 왼쪽에 캐릭터 + 단색 탭 배경 -> 배경색을 테두리부터 지워 캐릭터만 남김.
img_mnu0N.gif (63x55): 하늘색 둥근 배경 위 아이콘 -> 같은 방식.
logo_farm.gif: 흰 배경 제거.
"""
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "archive_original" / "jr_naver_images" / "new_pet"
OUT = PROJECT / "assets" / "ui"

# (원본, 자를 영역 or None, 결과 이름)
JOBS = [
    ("tab_mini01_on.gif", (8, 4, 66, 49), "nav_deco"),     # 고양이 - 농장꾸미기
    ("tab_mini02_on.gif", (8, 4, 66, 49), "nav_raise"),    # 판다 - 동물키우기
    ("tab_mini03_on.gif", (8, 4, 66, 49), "nav_item"),     # 사슴 - 아이템박스
    ("tab_mini04_on.gif", (8, 4, 66, 49), "nav_game"),     # 원숭이 - 포인트게임
    ("tab_mini06_on.gif", (8, 4, 66, 49), "nav_work"),     # 찻주전자 - 아르바이트
    ("img_mnu05.gif", None, "nav_book"),                    # 호랑이
    ("img_mnu02.gif", None, "nav_explore"),                 # 돋보기
    ("img_mnu01.gif", None, "nav_travel"),                  # 날개 모자
    ("logo_farm.gif", None, "logo_farm"),
]


def clear_background(rgba, tol=48):
    a = rgba.copy()
    h, w = a.shape[:2]
    rgb = a[..., :3].astype(int)
    seen = np.zeros((h, w), bool)
    q = deque()
    for y in range(h):
        q.extend([(y, 0, rgb[y, 0]), (y, w - 1, rgb[y, w - 1])])
    for x in range(w):
        q.extend([(0, x, rgb[0, x]), (h - 1, x, rgb[h - 1, x])])
    # 테두리 색들과 비슷하고 테두리에서 이어진 픽셀만 지운다
    border = np.array([rgb[y, x] for y, x, _ in q])
    q = deque((y, x) for y, x, _ in q)
    while q:
        y, x = q.popleft()
        if seen[y, x]:
            continue
        if np.abs(border - rgb[y, x]).sum(axis=1).min() > tol:
            continue
        seen[y, x] = True
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx]:
                q.append((ny, nx))
    a[seen, 3] = 0
    ys, xs = np.where(a[..., 3] > 0)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for src, box, name in JOBS:
        im = Image.open(SRC / src).convert("RGBA")
        if box:
            im = im.crop(box)
        out = clear_background(np.array(im))
        Image.fromarray(out, "RGBA").save(OUT / f"{name}.png")
        print(name, out.shape[1], "x", out.shape[0])


if __name__ == "__main__":
    main()
