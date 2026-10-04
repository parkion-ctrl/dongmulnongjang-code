"""코드·문서만 공개 저장소(parkion-ctrl/dongmulnongjang-code)에 올린다.

원작 그림(assets/)과 원작 텍스트 데이터는 네이버 저작물이라 공개 저장소에 넣지 않는다.
사용: python research/sync_public.py ["커밋 메시지"]
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
REPO = "parkion-ctrl/dongmulnongjang-code"
INCLUDE = ["index.html", "sw.js", "manifest.json", "README.md", ".gitignore", "research", "tests"]
EXCLUDE = shutil.ignore_patterns("*.log", "*.jsonl", "recipes_original.json", "__pycache__", "shots")
NOTICE = """> **공개 저장소 안내:** 원작 「동물농장」 그림(`assets/`)과 원작 텍스트 데이터는 네이버(NHN) 저작물이라
> 이 저장소에는 넣지 않았다. 코드·문서·스크립트만 있으며, 그대로 실행하면 그림이 비어 보인다.

"""


def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)


def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else "코드·문서 동기화"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        run(["gh", "repo", "clone", REPO, str(work)], tmp)
        for item in work.iterdir():
            if item.name != ".git":
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        for name in INCLUDE:
            src = PROJECT / name
            if src.is_dir():
                shutil.copytree(src, work / name, ignore=EXCLUDE)
            elif src.exists():
                shutil.copy2(src, work / name)
        readme = work / "README.md"
        readme.write_text(NOTICE + readme.read_text(encoding="utf-8"), encoding="utf-8")
        run(["git", "add", "-A"], work)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=work).returncode == 0:
            print("변경 없음")
            return
        run(["git", "commit", "-q", "-m", msg + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"], work)
        run(["git", "push", "-q"], work)
        print("pushed:", f"https://github.com/{REPO}")


if __name__ == "__main__":
    main()
