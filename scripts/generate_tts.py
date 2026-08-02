#!/usr/bin/env python3
"""TTS 统一入口：按需选 minimax / edge-tts / 显式指定。

默认行为（不传 --engine 时）：
    1. 探测 minimax 凭据（--api-key 或 ../.env 的 minimaxi= / minimaxi-group-id=）
    2. 有 minimax 凭据 → 用 MiniMax T2A v2
    3. 没有 → 自动降级到 edge-tts（免费、无 key）

依赖（两个引擎二选一即可，全装也行）：
    pip install requests                # minimax 引擎 + ffprobe 之外的公共依赖
    pip install edge-tts                # edge-tts 引擎

用法：
    # 自动选（推荐）
    python3 generate_tts.py --script work/source/tts-script.md --out-dir .

    # 强制 edge-tts
    python3 generate_tts.py --engine edge-tts --voice zh-CN-XiaoxiaoNeural ...

    # 强制 minimax
    python3 generate_tts.py --engine minimax --voice-id female-shaonv ...

    # 列出 edge-tts 可用 voice
    python3 generate_tts.py --engine edge-tts --list-voices
"""
import argparse
import sys
from pathlib import Path

# 探测 minimax 凭据（不强制 import 失败）
def _probe_minimax_credentials(out_dir: Path) -> bool:
    """检查 .env 里是否同时有 minimaxi= 和 minimaxi-group-id=。"""
    candidates = [
        out_dir.parent / ".env",
        out_dir / ".env",
        Path.cwd() / ".env",
        Path.home() / ".env",
    ]
    has_key = False
    has_group = False
    for env_path in candidates:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("minimaxi=") and line.split("=", 1)[1].strip():
                has_key = True
            elif line.startswith("minimaxi-group-id=") and line.split("=", 1)[1].strip():
                has_group = True
        if has_key and has_group:
            return True
    return has_key and has_group


def _filter_args(raw: list[str], engine: str) -> list[str]:
    """把当前脚本的 --engine 去掉（连同它的值），再按引擎过滤掉不兼容的参数。"""
    cleaned = []
    skip_next = False
    minimax_only = {"--api-key", "--group-id", "--voice-id", "--speed"}
    edge_only = {"--voice", "--rate", "--volume", "--pitch", "--list-voices"}
    for i, arg in enumerate(raw):
        if skip_next:
            skip_next = False
            continue
        # 吞掉 --engine 及其值
        if arg == "--engine":
            # 下一个是值（除非它本身是 --xxx 形式）
            if i + 1 < len(raw) and not raw[i + 1].startswith("-"):
                skip_next = True
            continue
        if arg.startswith("--engine="):
            continue
        # 引擎专属参数
        if engine == "edge-tts" and arg in minimax_only:
            print(f"  · edge-tts 引擎忽略参数 {arg}")
            continue
        if engine == "minimax" and arg in edge_only:
            print(f"  · minimax 引擎忽略参数 {arg}")
            continue
        # 参数值（要带值一起透传）
        if arg in minimax_only or arg in edge_only:
            cleaned.append(arg)
            if i + 1 < len(raw) and not raw[i + 1].startswith("-"):
                cleaned.append(raw[i + 1])
                skip_next = True
            continue
        cleaned.append(arg)
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TTS 统一入口（minimax / edge-tts）",
        add_help=True,
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "minimax", "edge-tts"],
        default="auto",
        help="TTS 引擎（默认 auto：有 minimax 凭据走 minimax，否则 edge-tts）",
    )
    parser.add_argument("--script", required=True, help="TTS 稿 markdown 路径")
    parser.add_argument("--out-dir", default=".", help="项目根目录")
    args, _unknown = parser.parse_known_args()

    project = Path(args.out_dir).expanduser().resolve()

    # 选定引擎
    if args.engine == "auto":
        if _probe_minimax_credentials(project):
            engine = "minimax"
        else:
            engine = "edge-tts"
        print(f"[auto] 未指定 --engine，探测到 minimax 凭据={'是' if engine=='minimax' else '否'} → 选 {engine}")
    else:
        engine = args.engine
        print(f"[手动] --engine={engine}")

    # 透传剩余参数
    raw_argv = sys.argv[1:]
    forward_argv = ["--script", args.script, "--out-dir", args.out_dir] + _filter_args(raw_argv, engine)
    sys.argv = [sys.argv[0]] + forward_argv

    if engine == "minimax":
        from generate_tts_minimax import main as _run
    else:
        from generate_tts_edge_tts import main as _run
    _run()


if __name__ == "__main__":
    main()
