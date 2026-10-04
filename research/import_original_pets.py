"""Wayback에서 받은 원작 동물 GIF(new_pet/pet/)를 게임 에셋으로 복사한다.

원작 파일 규칙: <이름>[_1|_2][_face1].gif (135px, 투명 배경)
  _1/_2 = 1차/2차 성장, _face1 = 다른 자세. 이름은 영어 또는 한글 자판 영타(ghfkddl=호랑이 등).
결과: assets/animals/<slug>/<slug>_<stage>.gif, <slug>_<stage>_pose.gif
"""
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "archive_original" / "jr_naver_images" / "new_pet" / "pet"

ORIGINAL_NAME = {
    "dragon": "dragon", "rabbit": "rabbit", "monster": "monster", "dolphin": "dolphin",
    "squirrel": "chipmunk", "bluebird": "bluebird", "shihtzu": "sichu", "penguin": "penguin",
    "sheep": "sheep", "duck": "swan", "puppy": "dog", "frog": "frog", "turtle": "turtle",
    "wolf": "wolf", "tiger": "ghfkddl", "hedgehog": "hedgehog", "giraffe": "rlflsp",
    "rhino": "dicerorhininae", "xmas_cat": "c_rhdiddl", "cat": "cat", "pig": "pig",
    "elephant": "elephant", "deer": "deer", "weasel": "weasel", "monkey": "monkey",
    "panda": "panda", "xmas_sheep": "c_did", "otter": "otter", "fox": "fox", "snake": "snake",
    "goat": "goat", "owl": "owl", "koala": "koala", "kangaroo": "kangaroo",
    "polarbear": "polarbear", "xmas_squirrel": "c_ekfkawnl", "ostrich": "ostrich",
    "lion": "lion", "hippo": "hippo", "camel": "camel", "xmas_deer": "c_tktma",
    "parrot": "parrot", "hamster": "goatmxj",
}
STAGES = [("base", ""), ("stage1", "_1"), ("stage2", "_2")]


def main():
    report = {}
    for slug, name in ORIGINAL_NAME.items():
        out = PROJECT / "assets" / "animals" / slug
        out.mkdir(parents=True, exist_ok=True)
        stages, poses = [], []
        for stage, suffix in STAGES:
            src = SRC / f"{name}{suffix}.gif"
            if src.exists():
                shutil.copy2(src, out / f"{slug}_{stage}.gif")
                stages.append(stage)
            pose = SRC / f"{name}{suffix}_face1.gif"
            if pose.exists():
                shutil.copy2(pose, out / f"{slug}_{stage}_pose.gif")
                poses.append(stage)
        report[slug] = {"original": name, "stages": stages, "poses": poses}
    (PROJECT / "assets" / "animals_original.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    full = [s for s, r in report.items() if len(r["stages"]) == 3]
    print(len(full), "animals with all 3 original stages")
    print("pose counts:", {s: len(r["poses"]) for s, r in report.items() if len(r["poses"]) < 3})


if __name__ == "__main__":
    main()
