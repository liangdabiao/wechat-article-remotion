#!/usr/bin/env python3
"""用 MiniMax T2A v2 给每段口播生成 mp3，ffprobe 量时长，ffmpeg 拼接。

适用场景：已经有 MiniMax API key 的项目，追求稳定的中文 TTS 质量。
没有 MiniMax key？请用 `scripts/generate_tts_edge_tts.py`（免费）或直接
`scripts/generate_tts.py`（自动选引擎）。

依赖：
    pip install requests
    # ffmpeg / ffprobe 需在 PATH（用于验证和拼接）

凭据读取顺序（先 --api-key 后 .env）：
    1. --api-key 参数
    2. ../.env (项目根 .env) 的 minimaxi= / minimaxi-group-id= 行
    3. ~/.env 同上

用法：
    python3 generate_tts_minimax.py \
        --script work/source/tts-script.md \
        --out-dir .

输出：
    public/assets/audio/voice.mp3          # 拼接后的整段（mp3 备）
    public/assets/audio/voice.m4a          # AAC 版（Remotion 用）
    work/captions/segments.json            # 每段实际时长 + 累计起点
    work/audio/tts-segments/seg-NN.mp3     # 临时分段（可手动清）
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

API_BASE = "https://api.minimaxi.com/v1/t2a_v2"
DEFAULT_VOICE = "female-shaonv"  # 少女声；可改为 male-qn-qingse / moss_audio_xxx 等
MODEL = "speech-02-hd"


def split_paragraphs(text: str) -> list[str]:
    """把 TTS 稿拆成段（按空行），去掉 markdown 标题前缀和首行'TTS 脚本'标记。"""
    paragraphs: list[str] = []
    for raw in re.split(r"\n\s*\n", text):
        s = re.sub(r"^#+\s*", "", raw.strip())
        s = re.sub(r"\s+", " ", s)
        if s and not s.startswith("TTS 脚本"):
            paragraphs.append(s)
    return paragraphs


def call_t2a(
    api_key: str,
    group_id: str,
    text: str,
    voice_id: str,
    out_path: Path,
    *,
    speed: float = 1.0,
    max_retries: int = 3,
) -> dict:
    """调 MiniMax T2A v2，hex 解码 audio 写文件。返回 audio_length / sample_rate / bitrate。"""
    payload = {
        "model": MODEL,
        "text": text,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": 1.0,
            "pitch": 0,
        },
        "audio_setting": {
            "sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 1,
        },
    }
    last_error: str = ""
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                API_BASE,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                print(f"  ! {last_error}")
                time.sleep(1.5 * (attempt + 1))
                continue
            data = resp.json()
            if data.get("base_resp", {}).get("status_code") != 0:
                last_error = f"API 错误：{data.get('base_resp')}"
                print(f"  ! {last_error}")
                time.sleep(1.5 * (attempt + 1))
                continue
            hex_audio = data["data"]["audio"]
            out_path.write_bytes(bytes.fromhex(hex_audio))
            extra = data.get("extra_info", {})
            return {
                "audio_length": round(float(extra.get("audio_length", 0)) / 1000.0, 3),
                "sample_rate": extra.get("sample_rate"),
                "bitrate": extra.get("bitrate"),
            }
        except Exception as e:
            last_error = f"异常：{e}"
            print(f"  ! {last_error}")
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"T2A 调用失败：{text[:30]}...  最后错误：{last_error}")


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-hide_banner", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1",
            str(path),
        ],
        text=True,
    ).strip()
    return round(float(out), 3)


def concat_mp3(segments: list[Path], out_path: Path) -> None:
    list_file = out_path.parent / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{p.as_posix()}'" for p in segments) + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_path),
        ],
        check=True,
    )
    list_file.unlink(missing_ok=True)


def mp3_to_m4a(mp3: Path, m4a: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(mp3),
            "-c:a", "aac", "-b:a", "128k",
            str(m4a),
        ],
        check=True,
    )


def load_credentials(
    explicit_key: str | None,
    explicit_group: str | None,
    out_dir: Path,
) -> tuple[str, str]:
    """从 --api-key / --group-id / 上下级 .env 读凭据。"""
    api_key = explicit_key
    group_id = explicit_group

    # 候选 .env 路径：项目根（out_dir 上一级）、仓库根（再上一级）、当前 cwd
    candidates = [
        out_dir.parent / ".env",  # 仓库根（out_dir 通常是脚手架生成的项目）
        out_dir / ".env",
        Path.cwd() / ".env",
        Path.home() / ".env",
    ]
    if not api_key or not group_id:
        for env_path in candidates:
            if not env_path.exists():
                continue
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not api_key and line.startswith("minimaxi="):
                    api_key = line.split("=", 1)[1].strip()
                elif not group_id and line.startswith("minimaxi-group-id="):
                    group_id = line.split("=", 1)[1].strip()
            if api_key and group_id:
                break

    if not api_key:
        sys.exit(
            "未找到 minimaxi api key（用 --api-key 或在 .env 写 minimaxi=...）"
        )
    if not group_id:
        sys.exit(
            "未找到 minimaxi-group-id（用 --group-id 或在 .env 写 minimaxi-group-id=...）"
        )
    return api_key, group_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MiniMax T2A v2 批量 TTS + 拼接",
    )
    parser.add_argument("--script", required=True, help="TTS 稿 markdown 路径")
    parser.add_argument("--out-dir", default=".", help="项目根目录")
    parser.add_argument("--api-key", default=None, help="MiniMax api key")
    parser.add_argument("--group-id", default=None, help="MiniMax group_id")
    parser.add_argument("--voice-id", default=DEFAULT_VOICE, help=f"MiniMax voice_id（默认 {DEFAULT_VOICE}）")
    parser.add_argument("--speed", type=float, default=1.0, help="语速 0.5~2.0（默认 1.0）")
    args = parser.parse_args()

    project = Path(args.out_dir).expanduser().resolve()
    audio_dir = project / "public/assets/audio"
    captions_dir = project / "work/captions"
    tmp_dir = project / "work/audio/tts-segments"
    for d in (audio_dir, captions_dir, tmp_dir):
        d.mkdir(parents=True, exist_ok=True)

    api_key, group_id = load_credentials(args.api_key, args.group_id, project)

    script_text = Path(args.script).read_text(encoding="utf-8")
    paragraphs = split_paragraphs(script_text)
    if not paragraphs:
        sys.exit(f"{args.script} 没拆出任何段落")
    print(f"[1/3] 拆出 {len(paragraphs)} 段口播（voice={args.voice_id}, speed={args.speed}）")

    segments_meta: list[dict] = []
    accumulated = 0.0
    for idx, para in enumerate(paragraphs, 1):
        mp3_path = tmp_dir / f"seg-{idx:02d}.mp3"
        print(f"[2/3] 第 {idx}/{len(paragraphs)} 段：{para[:30]}...")
        info = call_t2a(api_key, group_id, para, args.voice_id, mp3_path, speed=args.speed)
        probed = ffprobe_duration(mp3_path)
        dur = info["audio_length"] or probed
        segments_meta.append({
            "index": idx,
            "text": para,
            "mp3": str(mp3_path.relative_to(project)),
            "start": round(accumulated, 3),
            "duration": dur,
            "end": round(accumulated + dur, 3),
        })
        accumulated += dur
        print(f"  ✓ dur={dur:.3f}s 累计={accumulated:.3f}s")

    total = round(accumulated, 3)
    print(f"[3/3] 总时长 {total}s，拼接 voice.mp3 / voice.m4a")
    concat_mp3([project / m["mp3"] for m in segments_meta], audio_dir / "voice.mp3")
    mp3_to_m4a(audio_dir / "voice.mp3", audio_dir / "voice.m4a")

    (captions_dir / "segments.json").write_text(
        json.dumps(
            {
                "engine": "minimax",
                "voice_id": args.voice_id,
                "speed": args.speed,
                "total": total,
                "voice_mp3": "assets/audio/voice.mp3",
                "voice_m4a": "assets/audio/voice.m4a",
                "segments": segments_meta,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"  ✓ voice.mp3 + voice.m4a  segments.json  total={total}s")


if __name__ == "__main__":
    main()
