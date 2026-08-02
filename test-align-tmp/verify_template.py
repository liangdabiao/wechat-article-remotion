"""快速 sandbox: 复制 templates/remotion-project 到 test-sandbox，替换占位符，跑 typecheck。"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILL_ROOT = ROOT.parent
TPL = SKILL_ROOT / "templates" / "remotion-project"
DST = ROOT / "test-sandbox"


def main() -> int:
    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(
        TPL,
        DST,
        ignore=shutil.ignore_patterns("node_modules", "renders", "work", "public/assets"),
    )
    # 替换占位符
    demo = DST / "src" / "demoData.ts"
    text = demo.read_text(encoding="utf-8")
    text = text.replace("__PROJECT_TITLE__", "Demo").replace("__DURATION_SECONDS__", "37")
    demo.write_text(text, encoding="utf-8")
    print("[1/3] sandbox ready:", DST)

    # npm install (offline cache 可能 hit；不带 lockfile 走最新)
    print("[2/3] npm install ...")
    r = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund", "--prefer-offline"],
        cwd=DST, capture_output=True, text=True, shell=True,
    )
    print("  exit:", r.returncode)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print("STDERR:", r.stderr[-2000:])
        return r.returncode

    # typecheck
    print("[3/3] npm run typecheck ...")
    r = subprocess.run(
        ["npm", "run", "typecheck"],
        cwd=DST, capture_output=True, text=True, shell=True,
    )
    print("  exit:", r.returncode)
    print(r.stdout[-2000:])
    if r.returncode != 0:
        print("STDERR:", r.stderr[-2000:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
