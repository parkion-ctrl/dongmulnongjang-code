"""2차성장 동물 그림을 참고 이미지로 넣어 '사람이 된 모습'을 생성한다.

사용: python gen_humans.py <slug> [<slug> ...] [--quality low|medium|high] [--tries N]
결과: assets/humans/drafts/<slug>_<n>.png, 사용량은 research/gen_humans_log.jsonl
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
OUT_DIR = PROJECT / "assets" / "humans" / "drafts"
LOG = PROJECT / "research" / "gen_humans_log.jsonl"
MODEL = "gpt-image-2"

ANIMAL_KO = {
    "dragon": "용", "unicorn": "유니콘", "tiger": "호랑이",
}

# 동물별로 의상/소품에 녹일 특징 (2차성장 그림 기준)
FEATURES = {
    "dragon": "magenta-pink and purple palette with rainbow (yellow, teal, orange) accents; small dragon horns and a rainbow spiky crest worn like a hair ornament; little orange-gold dragon wings on the back; a pink scaled tail",
    "unicorn": "white and pale lavender palette with a long flowing purple-blue mane as hair; a single black spiral horn on the forehead; dark purple swirl tattoo patterns as clothing embroidery",
    "tiger": "white tiger palette (white with grey-brown stripes); round tiger ears; striped tail; calm, dignified expression with green eyes",
}

# 1부(15세 견습) -> 2부(5년 뒤 20세) 타임스킵 방식. 성인은 같은 성별의 15세 그림을 두 번째 참고로 받는다.
VARIANTS = {
    "young_m": {"who": "a boy around 15 years old, anime proportions about 6 heads tall, youthful face",
                "hair": "short to medium hair, slightly messy",
                "outfit": "apprentice adventurer: simple tunic with a short hooded capelet, leather belt with pouches, "
                          "boots, one small shoulder guard, a short sword",
                "pose": "dynamic action pose dashing forward with the short sword raised, capelet and tail swinging, "
                        "energetic grin, slightly low camera angle"},
    "young_f": {"who": "a girl around 15 years old, anime proportions about 6 heads tall, youthful face",
                "hair": "shoulder-length hair",
                "outfit": "apprentice adventurer: simple tunic dress over leggings with a short hooded capelet, "
                          "leather belt with pouches, boots, one small shoulder guard, a short wand",
                "pose": "casting a small sparkling spell with the wand held up, other hand open, light hop on one foot, "
                        "seen from a slightly low angle looking up at her"},
    "adult_m": {"who": "a young man around 20 years old, anime proportions about 7 heads tall", "base": "young_m",
                "hair": "grown long and tied back in a low ponytail, side-swept bangs - clearly different from the short spiky hair in image 2",
                "pose": "heroic front-facing stance, both hands resting on the pommel of a longsword planted in front of him, "
                        "long cloak billowing to one side, calm confident gaze at the viewer"},
    "adult_f": {"who": "a young woman around 20 years old, anime proportions about 7 heads tall", "base": "young_f",
                "hair": "long hair, styled differently from image 2",
                "pose": "turning to look back over her shoulder, holding a tall staff, mantle and hair flowing in the wind, "
                        "graceful calm expression, viewed slightly from behind and to the side"},
}

ART = (
    "Art style: cute but polished Korean children's web game art based on the reference animal (Junior Naver 'Animal Farm'), "
    "clean dark-brown outlines, soft cel shading with gentle highlights, bright saturated colors. "
    "Keep the animal's identity clearly readable through hair, colors, and costume details: {features}. "
    "Modest medieval fantasy clothing, no revealing outfit, no cleavage, no modern clothing. "
    "Whole body visible including feet. "
    "Single character only, centered, on a plain pure white background, no text, no frame, no ground shadow."
)

YOUNG = (
    "Image 1 is an animal character. Draw the HUMAN form of this {animal}: in the story, the animal raised by the player "
    "transforms into a person who joins the party to climb a fantasy tower. "
    "The person is {who}. Hairstyle: {hair}. Outfit in the animal's colors: {outfit}. Pose and composition: {pose}. "
)

ADULT = (
    "Image 1 is the original {animal} character. Image 2 is the human form of that {animal} at age 15. "
    "Draw the SAME person five years later, like a story time-skip redesign (as in Fire Emblem: Three Houses part 1 to part 2). "
    "The person is now {who}. Hairstyle: {hair}. Pose and composition: {pose}. "
    "Must stay clearly recognizable as the same person: same face shape, eye color, color palette and signature motifs. "
    "Must change visibly: a more mature face and build, a NEW hairstyle (different length and styling from image 2), "
    "and an evolved, upgraded outfit that keeps image 2's motifs but now looks like an experienced veteran adventurer "
    "rather than an apprentice (fuller armor or finer robes, a longer cloak or mantle, a better weapon). "
)


def load_key():
    for line in (PROJECT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("OPENAI_API_KEY not found in .env")


def reference_png(slug):
    im = Image.open(PROJECT / "assets" / "animals" / slug / f"{slug}_stage2.webp").convert("RGBA")
    scale = max(1, 512 // max(im.size))
    im = im.resize((im.width * scale, im.height * scale), Image.LANCZOS)
    canvas = Image.new("RGBA", (max(im.size) + 64,) * 2, (255, 255, 255, 255))
    canvas.paste(im, ((canvas.width - im.width) // 2, (canvas.height - im.height) // 2), im)
    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for k, v in fields.items():
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (fname, data, ctype) in files:
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\n'
                   f"Content-Type: {ctype}\r\n\r\n".encode())
        body.write(data)
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    return body.getvalue(), f"multipart/form-data; boundary={boundary}"


def png_bytes(path):
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def latest(slug, variant):
    files = sorted(OUT_DIR.glob(f"{slug}_{variant}_*.png"), key=lambda f: f.stat().st_mtime)
    return files[-1] if files else None


def generate(key, slug, quality, n_index, variant):
    v = VARIANTS[variant]
    animal = ANIMAL_KO.get(slug, slug)
    images = [("image[]", (f"{slug}_ref.png", reference_png(slug), "image/png"))]
    if "base" in v:
        young = latest(slug, v["base"])
        if not young:
            raise SystemExit(f"{slug}: generate {v['base']} first")
        images.append(("image[]", (young.name, png_bytes(young), "image/png")))
        prompt = ADULT.format(animal=animal, who=v["who"], hair=v["hair"], pose=v["pose"])
    else:
        prompt = YOUNG.format(animal=animal, who=v["who"], hair=v["hair"], outfit=v["outfit"], pose=v["pose"])
    prompt += ART.format(features=FEATURES[slug])
    fields = {"model": MODEL, "prompt": prompt, "size": "1024x1536", "quality": quality,
              "output_format": "png", "n": "1"}
    data, ctype = multipart(fields, images)
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=data, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": ctype})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            res = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{slug}: HTTP {e.code} {e.read().decode(errors='replace')[:800]}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{slug}_{variant}_{n_index}.png"
    out.write_bytes(base64.b64decode(res["data"][0]["b64_json"]))
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"slug": slug, "file": out.name, "quality": quality, "model": MODEL,
                            "usage": res.get("usage"), "sec": round(time.time() - t0, 1)}, ensure_ascii=False) + "\n")
    print(f"{slug} -> {out.name} ({time.time() - t0:.0f}s) usage={res.get('usage')}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--quality", default="medium")
    ap.add_argument("--tries", type=int, default=1)
    ap.add_argument("--variants", default="young_m,young_f,adult_m,adult_f")
    args = ap.parse_args()
    key = load_key()
    for slug in args.slugs:
        for variant in args.variants.split(","):
            start = len(list(OUT_DIR.glob(f"{slug}_{variant}_*.png"))) if OUT_DIR.exists() else 0
            for i in range(args.tries):
                generate(key, slug, args.quality, start + i + 1, variant)


if __name__ == "__main__":
    main()
