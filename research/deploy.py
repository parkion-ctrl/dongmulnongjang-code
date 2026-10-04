"""dist/ 를 새로 만들고 Cloudflare Pages(dongmulnongjang.pages.dev)에 올린다.

필요: 게임 폴더 .env 의 CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID
사용: python research/deploy.py
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
PAGES_PROJECT = "dongmulnongjang"


def load_env():
    env = dict(os.environ)
    for line in (PROJECT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and line.startswith("CLOUDFLARE_"):
            k, v = line.split("=", 1)
            env[k] = v.strip()
    return env


def main():
    subprocess.run([sys.executable, str(PROJECT / "research" / "build_dist.py")], check=True)
    cmd = ["npx", "--yes", "wrangler@4", "pages", "deploy", "dist", "--project-name", PAGES_PROJECT,
           "--branch", "main", "--commit-dirty=true"]
    subprocess.run(cmd, cwd=PROJECT, env=load_env(), check=True, shell=(os.name == "nt"))
    print(f"https://{PAGES_PROJECT}.pages.dev")


if __name__ == "__main__":
    main()
