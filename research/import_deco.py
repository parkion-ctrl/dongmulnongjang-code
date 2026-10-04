"""원작 꾸미기 아이템(new_pet/item/)을 게임 에셋으로 복사한다.

원작 규칙: <이름>.gif = 상점 아이콘(100px), <이름>d.gif = 농장에 배치되는 그림, <이름>s.gif = 작은 아이콘.
결과: assets/deco/<이름>.gif, assets/deco/<이름>d.gif + assets/deco.json (이름/가격)
"""
import json
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SRC = PROJECT / "archive_original" / "jr_naver_images" / "new_pet" / "item"
OUT = PROJECT / "assets" / "deco"

# (원작 파일명, 한글 이름, 가격) - 이름/가격은 임시
DECO = [
    ("Fence_Farm", "나무 울타리", 15), ("Fence_Green", "초록 울타리", 15), ("Fence_Star", "별 울타리", 20),
    ("Love_Fence", "하트 울타리", 20), ("Flowergarden", "꽃밭", 25), ("Yellow_flower", "노란 꽃", 10),
    ("Pink_flower", "분홍 꽃", 10), ("Sunflower", "해바라기", 15), ("Tree_BigLeaf", "둥근 나무", 30),
    ("Tree_Cherry", "체리 나무", 35), ("Coconut", "야자나무", 35), ("baobab", "바오밥나무", 60),
    ("Scarecrow", "허수아비", 25), ("Carrot", "당근", 10), ("Flower_Cart", "꽃수레", 30),
    ("Weathervane", "바람개비", 20), ("Postbox", "우체통", 25), ("StreetLight", "가로등", 25),
    ("Lamplight", "등불", 20), ("123signal", "신호등", 30), ("7redflag", "빨간 깃발", 15),
    ("Slide", "미끄럼틀", 50), ("Rockingchair", "흔들의자", 35), ("Couch", "하트 소파", 40),
    ("Table", "식탁", 35), ("Fountain", "숲 분수", 60), ("PongPong_Fountain", "퐁퐁 분수", 55),
    ("Sea_fountain", "조개 분수", 50), ("Mermaid", "인어 분수", 80), ("WoodenHouse", "통나무집", 80),
    ("Woodenapartment", "나무 아파트", 100), ("House_on_Tree", "나무 위 집", 90),
    ("House_Coconut", "야자잎 집", 80), ("House_Heater", "그루터기 집", 70),
    ("House_on_Cloud", "구름 위 집", 120), ("Castle", "모래성", 60), ("Shrine", "신전", 90),
    ("Totem", "토템", 40), ("Balloon", "열기구", 70), ("Cloud_Big", "큰 구름", 20),
    ("Cloud_Small", "작은 구름", 15), ("Sun", "해님", 30), ("Moon", "달님", 30), ("Big_star", "큰 별", 20),
    ("Present_box", "선물상자", 20), ("Love", "LOVE 전구", 50), ("Jellyfish", "해파리 아치", 60),
    ("Leaf", "나뭇잎 방석", 25),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = []
    for name, ko, price in DECO:
        icon, deco = SRC / f"{name}.gif", SRC / f"{name}d.gif"
        if not (icon.exists() and deco.exists()):
            print("missing", name)
            continue
        shutil.copy2(icon, OUT / icon.name)
        shutil.copy2(deco, OUT / deco.name)
        catalog.append({"id": name, "name": ko, "price": price})
    (PROJECT / "assets" / "deco.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    print(len(catalog), "deco items")


if __name__ == "__main__":
    main()
