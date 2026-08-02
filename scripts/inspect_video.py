#!/usr/bin/env python3
"""抽帧审视觉：扫 demoData.ts 找 cover/list/article-image/stat 四类场景，各抽 1 帧。

典型用法：
    python scripts/inspect_video.py --project-dir .

    # 自定义输出目录
    python scripts/inspect_video.py --project-dir . --out-dir renders/check

输出：
    renders/check/cover.png
    renders/check/list.png
    renders/check/image.png
    renders/check/stat.png

每个 still 用 --scale=0.25 快速出图，~5-10s/张（共 ~30-40s）。
完整视频渲染留给 `npm run render` / `render:preview`。
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


# 4 个代表版式，按场景类型 → 输出文件名
SCENE_KINDS = [
    ("cover", "cover.png", 0.5),                # cover 出现在 0.5s 左右（title 动画走完）
    ("list", "list.png", None),                 # list 用场景 start + 1.0s
    ("article-image", "image.png", None),       # article-image 用 start + 1.5s（appear 走完）
    ("article-image-stack", "image.png", None), # 找不到单 image 时用 stack 替代
    ("stat", "stat.png", None),                 # stat 用 start + 1.0s
]


def parse_demo_scenes(demodata_path: Path) -> list[dict]:
    """从 demoData.ts 提取所有 scene 的 {kind, start}。不依赖 node/ts 解析器。"""
    if not demodata_path.exists():
        return []
    text = demodata_path.read_text(encoding="utf-8")

    # 匹配 kind: "..." 紧跟着的 start: 数字
    pattern = re.compile(
        r'kind:\s*"([^"]+)"\s*,\s*start:\s*([0-9.]+)',
        re.MULTILINE,
    )
    scenes = []
    for m in pattern.finditer(text):
        scenes.append({"kind": m.group(1), "start": float(m.group(2))})
    return scenes


def pick_frames(scenes: list[dict], fps: int = 30) -> dict[str, int]:
    """从场景列表里挑出 4 个代表帧（frame 编号）。

    规则：
        cover → 第一张 cover
        list → 第一张 list
        image → 优先 article-image，没有就用 article-image-stack
        stat → 第一张 stat
    每个取该场景 start + 1.0s 处的帧。
    """
    chosen: dict[str, int] = {}
    for kind, fname, hardcoded_offset in SCENE_KINDS:
        if fname in chosen:
            continue  # image 已被 image 占用，跳过 stack
        for s in scenes:
            if s["kind"] == kind:
                offset = hardcoded_offset if hardcoded_offset is not None else 1.0
                frame = int((s["start"] + offset) * fps)
                chosen[fname] = max(1, frame)
                break
    return chosen


def remotion_still(project_dir: Path, out_path: Path, frame: int, browser: str | None) -> bool:
    """调一次 `npx remotion still`，按帧输出。"""
    # Windows 下 npx 在 PowerShell/cmd 里是 npx.cmd，subprocess 找不到
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    cmd = [
        npx, "remotion", "still",
        "src/index.ts", "ArticleVideo",
        str(out_path.relative_to(project_dir)),
        f"--frame={frame}",
        "--scale=0.25",
    ]
    if browser:
        cmd.append(f"--browser-executable={browser}")
    print(f"  · frame {frame} → {out_path.name}")
    proc = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True, shell=(sys.platform == "win32"))
    if proc.returncode != 0:
        # 截取 stderr 末尾避免刷屏
        err_tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        print(f"  ! {out_path.name} 失败：{err_tail}", file=sys.stderr)
        return False
    return True


def detect_browser() -> str | None:
    """自动找系统 Chrome / Edge，避免 remotion 下载 113MB。"""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
    ]
    for c in candidates:
        if shutil.which(c) or Path(c).exists():
            return c
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="抽 4 关键帧审 Remotion 视频版式",
    )
    parser.add_argument("--project-dir", default=".", help="Remotion 项目根目录")
    parser.add_argument("--out-dir", default="renders/check", help="输出目录（相对 project-dir）")
    parser.add_argument("--fps", type=int, default=30, help="项目帧率（默认 30）")
    args = parser.parse_args()

    project = Path(args.project_dir).expanduser().resolve()
    demodata = project / "src/demoData.ts"
    out_dir = (project / args.out_dir).resolve() if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scenes = parse_demo_scenes(demodata)
    if not scenes:
        print(f"❌ 没找到 {demodata}，或里面没有 scene", file=sys.stderr)
        sys.exit(1)
    print(f"扫到 {len(scenes)} 个 scene")

    frames = pick_frames(scenes, args.fps)
    if not frames:
        print("❌ 没匹配到 cover/list/image/stat 任何一类", file=sys.stderr)
        sys.exit(2)
    print(f"抽帧计划：{frames}")

    browser = detect_browser()
    if browser:
        print(f"浏览器：{browser}")
    else:
        print("⚠ 没找到系统 Chrome，会触发 Remotion 下载 chrome-headless-shell（113MB）", file=sys.stderr)

    ok = 0
    for fname, frame in frames.items():
        out = out_dir / fname
        if remotion_still(project, out, frame, browser):
            ok += 1
            print(f"  ✓ {out}")

    # 写一个 manifest 方便后续引用
    manifest = {
        "scenes_total": len(scenes),
        "frames": {fname: frame for fname, frame in frames.items()},
        "rendered": ok,
        "browser": browser,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n抽帧 {ok}/{len(frames)} 张 → {out_dir}")
    sys.exit(0 if ok == len(frames) else 3)


if __name__ == "__main__":
    main()
