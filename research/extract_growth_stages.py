"""나무위키 성장표(437x149, 3칸) -> 동물별 기본/1차/2차 투명 스프라이트 추출."""
import json
import shutil
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

SRC_DIR = Path(sys.argv[1])
ORDER_FILE = Path(sys.argv[2])
PROJECT = Path(r"C:\Users\ajou\Desktop\animal-farm-game")
ASSET_DIR = PROJECT / "assets" / "animals"
ARCHIVE_DIR = PROJECT / "archive_original" / "animals"

ANIMALS = [
    ("용", "dragon"), ("토끼", "rabbit"), ("몬스터", "monster"), ("돌고래", "dolphin"),
    ("다람쥐", "squirrel"), ("파랑새", "bluebird"), ("시츄", "shihtzu"), ("펭귄", "penguin"),
    ("양", "sheep"), ("오리", "duck"), ("강아지", "puppy"), ("개구리", "frog"),
    ("거북이", "turtle"), ("늑대", "wolf"), ("호랑이", "tiger"), ("고슴도치", "hedgehog"),
    ("기린", "giraffe"), ("코뿔소", "rhino"), ("크리스마스 고양이", "xmas_cat"), ("고양이", "cat"),
    ("돼지", "pig"), ("코끼리", "elephant"), ("사슴", "deer"), ("족제비", "weasel"),
    ("원숭이", "monkey"), ("팬더", "panda"), ("크리스마스 양", "xmas_sheep"), ("수달", "otter"),
    ("여우", "fox"), ("뱀", "snake"), ("염소", "goat"), ("부엉이", "owl"),
    ("코알라", "koala"), ("캥거루", "kangaroo"), ("북극곰", "polarbear"), ("문어", "octopus"),
    ("독수리", "eagle"), ("크리스마스 다람쥐", "xmas_squirrel"), ("악어", "crocodile"), ("해마", "seahorse"),
    ("열대어", "tropicalfish"), ("바다표범", "seal"), ("아르마딜로", "armadillo"), ("두더지", "mole"),
    ("공작", "peacock"), ("닭", "chicken"), ("유니콘", "unicorn"), ("미국너구리", "raccoon"),
    ("크리스마스 사슴", "xmas_deer"), ("스컹크", "skunk"), ("두루미", "crane"), ("햄스터", "hamster"),
    ("사자", "lion"), ("하마", "hippo"), ("낙타", "camel"), ("타조", "ostrich"),
    ("앵무새", "parrot"), ("상어", "shark"), ("불독", "bulldog"), ("우파루파", "axolotl"),
    ("목도리 도마뱀", "frilledlizard"), ("얼룩말", "zebra"),
]

CELLS = [(7, 145), (148, 289), (292, 430)]
CELL_Y = (4, 126)
ARROWS = [(133, 161), (277, 305)]
ARROW_Y = (58, 90)
STAGES = ["base", "stage1", "stage2"]


def label_mask(arr):
    """좌상단 금색 이름 라벨 모양(글자 포함)만 정확히 잡는다 - 직사각형으로 지우면 캐릭터 머리까지 잘림."""
    r, g, b = (arr[..., i].astype(int) for i in range(3))
    gold = (r > 190) & (g > 130) & (b < 140) & (r - b > 80)
    h, w = gold.shape
    seeds = [(y, x) for y in range(8, 20) for x in range(2, 12) if gold[y, x]]
    comp = np.zeros((h, w), bool)
    q = deque(seeds)
    for y, x in seeds:
        comp[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < 50 and 0 <= nx < 220 and gold[ny, nx] and not comp[ny, nx]:
                comp[ny, nx] = True
                q.append((ny, nx))
    if not comp.any():
        return comp
    ys, xs = np.where(comp)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    box = comp[y0:y1, x0:x1]
    outside = flood_from_border(~box)
    filled = comp.copy()
    filled[y0:y1, x0:x1] |= ~outside
    return max_filter(filled, 1)


def clean_sheet(arr):
    a = arr.copy()
    a[label_mask(a)] = 255
    f = a.astype(int)
    mx, mn = f.max(axis=2), f.min(axis=2)
    gray = (mx - mn) < 18
    for x0, x1 in ARROWS:
        zone = np.zeros(gray.shape, bool)
        zone[ARROW_Y[0]:ARROW_Y[1], x0:x1] = True
        a[zone & gray] = 255
    return a


BG_DIST = 30
GAP_RADIUS = 2
EDGE_DIST = 120


def min_filter(mask, r):
    p = np.pad(mask, r, constant_values=True)
    out = np.ones_like(mask)
    for dy in range(2 * r + 1):
        for dx in range(2 * r + 1):
            out &= p[dy:dy + mask.shape[0], dx:dx + mask.shape[1]]
    return out


def max_filter(mask, r):
    return ~min_filter(~mask, r)


def flood_from_border(passable):
    h, w = passable.shape
    seen = np.zeros((h, w), bool)
    q = deque((y, x) for y in range(h) for x in (0, w - 1) if passable[y, x])
    q.extend((y, x) for x in range(w) for y in (0, h - 1) if passable[y, x])
    for y, x in q:
        seen[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and passable[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return seen


def alpha_from_bg(crop):
    dist = np.abs(crop.astype(int) - 255).sum(axis=2)
    passable = dist < BG_DIST
    # 배경을 깎은 상태로 채워서 외곽선의 좁은 틈으로 흰 털 안쪽까지 번지지 않게 함
    core = flood_from_border(min_filter(passable, GAP_RADIUS))
    bg = max_filter(core, GAP_RADIUS) & passable
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    edge = max_filter(bg, 1) & ~bg & (dist < EDGE_DIST)
    alpha[edge] = np.clip(dist[edge] * 255 // EDGE_DIST, 60, 255).astype(np.uint8)
    return drop_specks(alpha)


def defringe(rgba, band_px=2, full_at=200):
    """배경과 맞닿은 테두리 몇 픽셀에서 흰 배경이 섞인 만큼 투명도를 주고 색을 되돌린다(흰 테두리 제거)."""
    rgb = rgba[..., :3].astype(float)
    alpha = rgba[..., 3].astype(float) / 255
    bg = alpha == 0
    band = max_filter(bg, band_px) & ~bg
    dist = np.abs(rgb - 255).sum(axis=2)
    a = np.clip(dist / full_at, 0, 1)
    a = np.where(band, np.minimum(a, alpha), alpha)
    safe = np.maximum(a, 1e-3)[..., None]
    unmixed = 255 - (255 - rgb) / safe
    rgb = np.where(band[..., None], np.clip(unmixed, 0, 255), rgb)
    return np.dstack([rgb, a * 255]).round().astype(np.uint8)


def drop_specks(alpha, min_size=25):
    h, w = alpha.shape
    seen = np.zeros((h, w), bool)
    out = alpha.copy()
    for sy in range(h):
        for sx in range(w):
            if alpha[sy, sx] == 0 or seen[sy, sx]:
                continue
            comp = []
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            while q:
                y, x = q.popleft()
                comp.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and alpha[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            ys = [p[0] for p in comp]
            xs = [p[1] for p in comp]
            thin = (max(ys) - min(ys)) <= 3 or (max(xs) - min(xs)) <= 3
            if len(comp) < min_size or thin:
                for y, x in comp:
                    out[y, x] = 0
    return out


def trim(rgba, pad=2):
    ys, xs = np.where(rgba[..., 3] > 0)
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, rgba.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, rgba.shape[1])
    return rgba[y0:y1, x0:x1]


def main():
    order = json.loads(ORDER_FILE.read_text(encoding="utf-8"))
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for src_name, (ko, slug) in zip(order, ANIMALS):
        shutil.copy2(SRC_DIR / src_name, ARCHIVE_DIR / src_name)
        arr = clean_sheet(np.array(Image.open(SRC_DIR / src_name).convert("RGB")))
        out_dir = ASSET_DIR / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for (x0, x1), stage in zip(CELLS, STAGES):
            crop = arr[CELL_Y[0]:CELL_Y[1], x0:x1]
            rgba = trim(defringe(np.dstack([crop, alpha_from_bg(crop)])))
            fname = f"{slug}_{stage}.webp"
            Image.fromarray(rgba, "RGBA").save(out_dir / fname, "WEBP", lossless=True)
            files.append(f"assets/animals/{slug}/{fname}")
        catalog[slug] = {"name": ko, "source": src_name, "stages": files}
        print(slug, ko)
    (PROJECT / "assets" / "animals.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(len(catalog), "animals")


if __name__ == "__main__":
    main()
