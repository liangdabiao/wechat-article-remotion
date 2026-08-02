#!/usr/bin/env python3
"""用 Microsoft edge-tts 给每段口播生成 mp3，ffprobe 量时长，ffmpeg 拼接。

适用场景：免费、无需 API key、追求"够用"的中文配音质量。
底层走的是 Microsoft Edge 浏览器内置的 Read Aloud 神经语音（zh-CN-* 系列），
由社区包 `edge-tts` 封装，pip 装上即用。

⚠️ 合规提示：edge-tts 借的是 Edge 的在线 TTS，没有正式 SLA；
商用或对稳定性要求高请改用 `generate_tts_minimax.py`（付费 / 走 MiniMax API）。

依赖：
    pip install edge-tts requests
    # ffmpeg / ffprobe 需在 PATH（用于验证和拼接）

常用中文 voice：
    zh-CN-YunxiNeural        青年男（新闻 / 通用）  ← 默认
    zh-CN-XiaoxiaoNeural     温柔女
    zh-CN-YunyangNeural      阳光男
    zh-CN-XiaoyiNeural       甜美女
    zh-CN-liaoning-XiaobeiNeural  东北女
    zh-CN-shaanxi-XiaoniNeural    陕西女
    zh-HK-WanLungNeural      粤语男
    zh-TW-HsiaoChenNeural    台湾女

用法：
    python3 generate_tts_edge_tts.py \
        --script work/source/tts-script.md \
        --out-dir .

    # 换女声
    python3 generate_tts_edge_tts.py --voice zh-CN-XiaoxiaoNeural ...

    # 调语速（+20% 加速 / -20% 减速）
    python3 generate_tts_edge_tts.py --rate "+0%" ...

输出（与 minimax 版格式完全一致，方便回写 demoData.ts）：
    public/assets/audio/voice.mp3
    public/assets/audio/voice.m4a
    work/captions/segments.json
    work/audio/tts-segments/seg-NN.mp3
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "zh-CN-YunxiNeural"
DEFAULT_RATE = "+0%"   # -50% ~ +100%，默认 0
DEFAULT_VOLUME = "+0%" # -50% ~ +50%
DEFAULT_PITCH = "+0Hz" # -50Hz ~ +50Hz


def split_paragraphs(text: str) -> list[str]:
    """把 TTS 稿拆成段（按空行），去掉 markdown 标题前缀和首行'TTS 脚本'标记。"""
    paragraphs: list[str] = []
    for raw in re.split(r"\n\s*\n", text):
        s = re.sub(r"^#+\s*", "", raw.strip())
        s = re.sub(r"\s+", " ", s)
        if s and not s.startswith("TTS 脚本"):
            paragraphs.append(s)
    return paragraphs


async def _synthesize_one(
    text: str,
    out_path: Path,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
    max_retries: int = 3,
) -> None:
    """调一次 edge-tts，失败重试。"""
    last_error: str = ""
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(
                text=text, voice=voice, rate=rate, volume=volume, pitch=pitch,
            )
            await communicate.save(str(out_path))
            return
        except Exception as e:
            last_error = str(e)
            print(f"  ! {last_error}（第 {attempt + 1} 次重试）")
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"edge-tts 调用失败：{text[:30]}...  最后错误：{last_error}")


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


async def run(args: argparse.Namespace) -> None:
    project = Path(args.out_dir).expanduser().resolve()
    audio_dir = project / "public/assets/audio"
    captions_dir = project / "work/captions"
    tmp_dir = project / "work/audio/tts-segments"
    for d in (audio_dir, captions_dir, tmp_dir):
        d.mkdir(parents=True, exist_ok=True)

    script_text = Path(args.script).read_text(encoding="utf-8")
    paragraphs = split_paragraphs(script_text)
    if not paragraphs:
        sys.exit(f"{args.script} 没拆出任何段落")
    print(
        f"[1/3] 拆出 {len(paragraphs)} 段口播"
        f"（voice={args.voice}, rate={args.rate}, volume={args.volume}, pitch={args.pitch}）"
    )

    # 逐段合成（不并发，避免触发 edge-tts 反爬限速）
    segments_meta: list[dict] = []
    accumulated = 0.0
    for idx, para in enumerate(paragraphs, 1):
        mp3_path = tmp_dir / f"seg-{idx:02d}.mp3"
        print(f"[2/3] 第 {idx}/{len(paragraphs)} 段：{para[:30]}...")
        await _synthesize_one(
            para, mp3_path,
            voice=args.voice, rate=args.rate,
            volume=args.volume, pitch=args.pitch,
        )
        dur = ffprobe_duration(mp3_path)
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
                "engine": "edge-tts",
                "voice": args.voice,
                "rate": args.rate,
                "volume": args.volume,
                "pitch": args.pitch,
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="edge-tts 免费批量 TTS + 拼接（无需 API key）",
    )
    parser.add_argument("--script", required=True, help="TTS 稿 markdown 路径")
    parser.add_argument("--out-dir", default=".", help="项目根目录")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"edge-tts voice（默认 {DEFAULT_VOICE}）")
    parser.add_argument("--rate", default=DEFAULT_RATE, help="语速，如 +20%% / -10%%（默认 0%%）")
    parser.add_argument("--volume", default=DEFAULT_VOLUME, help="音量，-50%% ~ +50%%（默认 0%%）")
    parser.add_argument("--pitch", default=DEFAULT_PITCH, help="音调，-50Hz ~ +50Hz（默认 0Hz）")
    parser.add_argument("--list-voices", action="store_true", help="只列出可用 voice 后退出（zh 优先）")
    args = parser.parse_args()

    if args.list_voices:
        # 列出所有 voice 并按 zh 优先排序
        try:
            voices = asyncio.run(edge_tts.list_voices())
        except Exception as e:
            sys.exit(f"list_voices 失败：{e}")
        zh = [v for v in voices if v["Locale"].startswith("zh")]
        others = [v for v in voices if not v["Locale"].startswith("zh")]
        for v in zh + others:
            print(f"  {v['ShortName']:40s}  {v['Locale']:8s}  {v['Gender']:6s}  {v.get('FriendlyName','')}")
        return

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
