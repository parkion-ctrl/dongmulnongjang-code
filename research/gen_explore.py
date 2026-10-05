"""탐험(북쪽 탑) 그림 생성: 원작에 없는 방 장면·마도사 모습을 원작 그림을 참고로 AI(gpt-image-2)로 만든다.

사용: python research/gen_explore.py [이름 ...]   (이름 없으면 아직 없는 것 전부)
결과: assets/explore/room_<이름>.jpg (장면), <이름>.png (투명 배경: mage, ghost, spirit_aura) / research/gen_explore_log.jsonl
"""
import base64
import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image

from import_explore import clear_white

PROJECT = Path(__file__).resolve().parent.parent
EX = PROJECT / "assets" / "explore"
LOG = PROJECT / "research" / "gen_explore_log.jsonl"
MODEL = "gpt-image-2"

STYLE = ("cute early-2000s Korean children's web game illustration (Junior Naver 'Animal Farm' explore mode), "
         "clean dark outlines, soft cel shading, slightly spooky but friendly Halloween-castle mood, "
         "purple and indigo palette with warm torch light. Match the art style of the reference images. "
         "No text, no letters, no people, no UI, no frame.")
SCENE = "Wide landscape background scene for a mobile game, the center and lower-middle kept fairly empty and uncluttered. "

# 이름: (프롬프트, 참고 그림들, 크기, 투명 여부)
JOBS = {
    "hall": (SCENE + "Inside an old stone tower: a long purple stone hall with gothic arched windows, wall torches with orange flames, "
             "cobwebs, a worn red carpet leading forward, moonlight through the windows. This is the backdrop behind a monster battle.",
             ["head.png", "legend.gif"], "1536x1024", False),
    "fork": (SCENE + "Inside an old stone tower: a landing where the corridor splits into two big wooden arched doors side by side, "
             "one door slightly glowing purple and one slightly glowing gold, torches between them, stone stairs behind.",
             ["head.png", "legend.gif"], "1536x1024", False),
    "chest": (SCENE + "A small stone chamber in a tower with one big old wooden treasure chest with gold trim and a heart-shaped lock in the center, "
              "sparkles leaking from the gap of the lid, a few scattered gold coins, torches on the walls.",
              ["head.png", "gold_bar.png"], "1536x1024", False),
    "spring": (SCENE + "A hidden room inside a stone tower with a round healing spring: clear glowing turquoise water in a mossy stone basin, "
               "small fairy lights floating, little glowing mushrooms and ferns, soft calm light.",
               ["head.png", "magicsoul.png"], "1536x1024", False),
    "trap": (SCENE + "A narrow stone tower corridor full of traps: floor tiles with strange glowing rune patterns, small arrow holes in the walls, "
             "a pit with spikes far below on one side, dim torch light, a bit scary but cute.",
             ["head.png", "legend.gif"], "1536x1024", False),
    "lost": (SCENE + "A quiet corner of a stone tower corridor with a small cozy alcove, a lit candle, a blanket and a tiny bag on the floor "
             "as if a little lost child animal had been resting there, gentle warm light, safe feeling.",
             ["head.png", "legend.gif"], "1536x1024", False),
    "stairs": (SCENE + "A spiral stone staircase going up inside an old tower, light shining down from above, torches along the wall, "
               "a feeling of having cleared the floor and climbing higher.",
               ["head.png", "legend.gif"], "1536x1024", False),
    "spirit_aura": ("Single game item icon: 'Essence of Spirit' (정령의 기운) - a small swirling wisp of glowing mint-green and white spirit energy "
                    "with tiny sparkles, floating inside a little round glass orb with a golden cap, cute Korean kids' game item icon style like the references, "
                    "clean outlines. Plain pure white background, single object, centered, no text.",
                    ["magicsoul.png", "god_fabric.png", "gold_bar.png"], "1024x1024", True),
    "ghost": ("Full-body character sprite of a mischievous little ghost who had disguised itself as a lost animal child: a round white sheet ghost "
              "with a cheeky grin and tongue out, tiny arms raised, a torn animal-ear hood (the disguise) slipping off its head, translucent pale blue edges, "
              "cute Korean children's game style matching the references, clean outlines, cel shading. "
              "Plain pure white background, single character only, no shadow, no text.",
              ["ex_02.gif", "ex_04.gif"], "1024x1024", True),
    "mage": ("Full-body character sprite of 'the Dark Mage' (암흑의 마도사), the final boss of the north tower in a cute Korean children's game. "
             "A small but menacing old sorcerer in a tall pointed hood and long dark purple robe with a tattered hem, glowing yellow eyes, "
             "long white beard, holding a crooked staff topped with swirling dark smoke and a purple flame. "
             "Same pose and silhouette as the grey '?' silhouette reference (staff raised on the right with smoke). "
             "Same art style as the reaper and dracula references: clean outlines, cel shading. "
             "Plain pure white background, single character only, no shadow on the ground, no text.",
             ["ex_07.gif", "ex_05.gif", "ex_04.gif"], "1024x1024", True),
}


def load_key():
    for line in (PROJECT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENAI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("OPENAI_API_KEY not found")


def png_bytes(path):
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    im.thumbnail((768, 768))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def call(key, prompt, refs, size, transparent):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    fields = {"model": MODEL, "prompt": prompt, "size": size, "quality": "medium", "n": "1", "output_format": "png"}
    for k, v in fields.items():
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for i, ref in enumerate(refs):
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; filename="ref{i}.png"\r\nContent-Type: image/png\r\n\r\n'.encode())
        body.write(ref)
        body.write(b"\r\n")
    body.write(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/images/edits", data=body.getvalue(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} {e.read().decode(errors='replace')[:600]}")
    return base64.b64decode(res["data"][0]["b64_json"]), res.get("usage"), round(time.time() - t0, 1)


def out_path(name):
    return EX / (f"{name}.png" if JOBS[name][3] else f"room_{name}.jpg")


def main():
    names = sys.argv[1:] or [n for n in JOBS if not out_path(n).exists()]
    key = load_key()
    for name in names:
        prompt, refs, size, transparent = JOBS[name]
        data, usage, secs = call(key, STYLE + " " + prompt, [png_bytes(EX / r) for r in refs], size, transparent)
        im = Image.open(io.BytesIO(data))
        if transparent:
            # 모델이 투명 배경을 지원하지 않아 흰 배경으로 받은 뒤 가장자리 흰색을 투명하게
            im = clear_white(im.convert("RGB"), tol=18)
            im.thumbnail((420, 420))
            im.save(out_path(name))
        else:
            im = im.convert("RGB")
            im.thumbnail((960, 960))
            im.save(out_path(name), quality=86)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"name": name, "size": size, "secs": secs, "usage": usage, "at": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False) + "\n")
        print(name, secs, "s", usage)


if __name__ == "__main__":
    main()
