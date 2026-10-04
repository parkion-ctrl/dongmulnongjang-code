"""여행지 그림 생성: 원작 세피아 사진 -> 컬러 아이콘(1장씩), 컬러판 -> 계절별 풍경(4장씩).

사용: python gen_travel.py color [1 2 ...]   /   python gen_travel.py season [1 2 ...] [--seasons spring,summer]
결과: assets/travel/spot{N}_color.png (원본), spot{N}_{season}.jpg / research/gen_travel_log.jsonl
"""
import argparse
import base64
import io
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "assets" / "ui" / "travel"
OUT = PROJECT / "assets" / "travel"
LOG = PROJECT / "research" / "gen_travel_log.jsonl"
MODEL = "gpt-image-2"

SPOTS = {
    1: ("구름위성 몽마랜드", "a dreamy amusement land built on floating rocky islands in the clouds, a round plaza with a ring of tiny houses, fluffy clouds and sparkles"),
    2: ("진흙거품 온천", "a cozy hot spring resort: big round hot spring pools with bubbling mud, wooden decks and thatched roofs, steam rising"),
    3: ("눈의 나라", "a snowy kingdom with snow-capped mountains, snow-covered bushes, falling snowflakes and a little snowman"),
    4: ("강아지 발바닥 정글", "a sunny jungle plateau with a big mesa cliff, tropical trees, round ponds shaped like dog paw prints and little animal statues"),
    5: ("박쥐 숲의 굴 탐험", "a mysterious forest with pointed rocky mountains and cave entrances, bats flying, twisted dry trees and glittering dust"),
    6: ("하늘섬", "floating sky islands above a sea of swirling clouds, small pyramid-like rocks, sparkles and a rainbow-tinted sky"),
}
SEASONS = {
    "spring": "spring: cherry blossoms and pink petals, fresh green grass, wildflowers, soft warm sunlight",
    "summer": "summer: lush deep green foliage, bright blue sky with big white clouds, strong sunshine, cicada-summer vibe",
    "autumn": "autumn: red and orange maple leaves, golden trees, falling leaves, warm sunset light",
    "winter": "winter: everything covered in thick white snow, icicles, gentle snowfall, cold blue light, cozy warm windows",
}
STYLE = ("cute early-2000s Korean children's web game illustration (Junior Naver 'Animal Farm'), clean outlines, "
         "soft cel shading, bright saturated pastel colors, no text, no letters, no people, no frame")


def load_key():
    for line in (PROJECT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("OPENAI_API_KEY not found")


def png_bytes(path, size=512):
    im = Image.open(path).convert("RGB")
    im = im.resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def call(key, prompt, ref_bytes, size, quality):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for k, v in {"model": MODEL, "prompt": prompt, "size": size, "quality": quality, "n": "1", "output_format": "png"}.items():
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="ref.png"\r\nContent-Type: image/png\r\n\r\n'.encode())
    body.write(ref_bytes)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=body.getvalue(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} {e.read().decode(errors='replace')[:600]}")
    return base64.b64decode(res["data"][0]["b64_json"]), res.get("usage"), round(time.time() - t0, 1)


def log(entry):
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["color", "season"])
    ap.add_argument("spots", nargs="*", type=int)
    ap.add_argument("--seasons", default="spring,summer,autumn,winter")
    ap.add_argument("--quality", default="medium")
    a = ap.parse_args()
    key = load_key()
    OUT.mkdir(parents=True, exist_ok=True)
    for n in a.spots or list(SPOTS):
        name, desc = SPOTS[n]
        if a.mode == "color":
            prompt = (f"The reference is a faded sepia thumbnail of a travel destination called '{name}': {desc}. "
                      f"Redraw it as a full-color picture with exactly the same composition and elements. Style: {STYLE}.")
            data, usage, sec = call(key, prompt, png_bytes(SRC / f"sum_travel_sub01_0{n}.gif"), "1024x1024", a.quality)
            (OUT / f"spot{n}_color.png").write_bytes(data)
            log({"spot": n, "mode": "color", "usage": usage, "sec": sec})
            print(n, "color", sec, usage, flush=True)
        else:
            ref = png_bytes(OUT / f"spot{n}_color.png", 768)
            for season in a.seasons.split(","):
                prompt = (f"Wide landscape scene of the travel destination '{name}' shown in the reference: {desc}. "
                          f"Keep the same place and landmarks, seen as a wide establishing shot. Season is {SEASONS[season]}. "
                          f"Style: {STYLE}.")
                data, usage, sec = call(key, prompt, ref, "1536x1024", a.quality)
                im = Image.open(io.BytesIO(data)).convert("RGB")
                im.thumbnail((900, 600), Image.LANCZOS)
                im.save(OUT / f"spot{n}_{season}.jpg", "JPEG", quality=85)
                log({"spot": n, "mode": season, "usage": usage, "sec": sec})
                print(n, season, sec, usage, flush=True)


if __name__ == "__main__":
    main()
