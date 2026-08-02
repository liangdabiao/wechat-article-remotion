#!/usr/bin/env python3
"""把 TTS 段落（或 ASR SRT）转成 demoData.ts 的 `captions[]` TypeScript 数组。

输入优先级：
    1. --srt（如果传了，优先用 ASR 对齐的 SRT 字幕；segments.json 仅当 source-of-truth 取 time）
    2. --segments work/captions/segments.json（默认；由 generate_tts.py 生成）

输出：
    - 默认：stdout 打印 TS 代码片段（可直接复制粘贴到 demoData.ts 的 `captions: [...]` 块）
    - --out file.ts：写到文件
    - --print-totals：同时打印每段字数 / 累计时长

切分逻辑：
    - 按中文标点切：，。？！；…——
    - 单段超过 14 字再按字切
    - 关键词标 `tone: "accent"`：用 --keywords "关键1,关键2" 传入

用法示例：
    # 1. 默认（用 segments.json 推 captions）
    python3 align_captions.py

    # 2. 有 ASR 对齐的 SRT（更准）
    python3 align_captions.py --srt work/captions/captions.srt

    # 3. 标关键词 + 写到文件
    python3 align_captions.py --keywords "edge-tts,MiniMax,免费" --out work/captions/captions-snippet.ts

依赖：无第三方依赖（仅 Python 标准库）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

# 中文标点（用于切分）
ZH_PUNCT = "。，？！；…——"
# 切分最大字数（避免单 part 太长）
MAX_PART_LEN = 14


def parse_srt(srt_text: str) -> list[dict]:
    """解析 SRT 为 [{index, start, end, text}]，start/end 为秒。"""
    out: list[dict] = []
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        idx_line = lines[0].strip()
        m = re.match(r"(\d+)?\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{3})", lines[1] if idx_line.isdigit() else lines[0])
        if not m:
            continue
        s = _srt_timestamp_to_seconds(m.group(2))
        e = _srt_timestamp_to_seconds(m.group(3))
        text = " ".join(lines[2:] if idx_line.isdigit() else lines[1:]).strip()
        out.append({"start": round(s, 3), "end": round(e, 3), "text": text})
    return out


def _srt_timestamp_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def split_into_parts(text: str) -> list[str]:
    """按中文标点 / 空格切；单段超过 MAX_PART_LEN 再按字切。

    规则：
        1. 首先按中文标点切（保留 part 内的空格，中英混排读得通）
        2. 超过 MAX_PART_LEN 时按最近的空格 / 标点切
        3. 整段没标点没空格就按 MAX_PART_LEN 硬切
    """
    text = text.strip()
    if not text:
        return []
    # 第一步：只按中文标点找切点
    punct_cuts: list[int] = [i for i, ch in enumerate(text) if ch in ZH_PUNCT]
    if punct_cuts:
        parts: list[str] = []
        prev = 0
        for c in punct_cuts:
            seg = text[prev : c + 1]
            if seg:
                parts.append(seg)
            prev = c + 1
        rest = text[prev:]
        if rest:
            parts.append(rest)
    else:
        # 没有任何中文标点，整段作为一个 part
        parts = [text]

    # 第二步：超长 part 兜底切（按最近的标点 / 空格）
    # 用 collections.deque 实现 FIFO，确保最终 parts 顺序与原文一致
    from collections import deque
    final: list[str] = []
    for p in parts:
        queue: deque = deque([p])
        seen: set[str] = set()  # 防死循环
        while queue:
            cur = queue.popleft().rstrip()
            if not cur or cur in seen:
                continue
            seen.add(cur)
            if len(cur) <= MAX_PART_LEN:
                final.append(cur)
                continue
            # 找 part 内最近的标点 / 空格切两半
            inner_cuts = [i for i, ch in enumerate(cur) if ch in ZH_PUNCT or ch == " "]
            if not inner_cuts:
                for i in range(0, len(cur), MAX_PART_LEN):
                    final.append(cur[i : i + MAX_PART_LEN])
                continue
            # 选最接近 len(cur) / 3 的切点（让左半尽量短）
            target = len(cur) // 3
            best = min(inner_cuts, key=lambda i: abs(i - target))
            left = cur[: best + 1].rstrip()
            right = cur[best + 1 :].lstrip()
            # 必须保证两边都更短，否则退化到硬切
            if not left or not right or len(left) >= len(cur) or len(right) >= len(cur):
                for i in range(0, len(cur), MAX_PART_LEN):
                    final.append(cur[i : i + MAX_PART_LEN])
                continue
            # FIFO：先 push left，再 push right
            if left:
                queue.append(left)
            if right:
                queue.append(right)
    return [p for p in final if p]


def find_accent_indices(text: str, keywords: list[str]) -> list[tuple[int, int]]:
    """找 text 中所有 keywords 出现位置（char offset）。

    大小写不敏感：传 "MiniMax" 也能匹配 "minimax" / "MINIMAX"。

    返回 [(start, end), ...] 字符索引，半开区间 [start, end)。
    """
    if not keywords:
        return []
    spans: list[tuple[int, int]] = []
    # 按长度倒序，避免短词先匹配覆盖长词
    for kw in sorted(keywords, key=len, reverse=True):
        if not kw:
            continue
        kw_lower = kw.lower()
        text_lower = text.lower()
        start = 0
        while True:
            i = text_lower.find(kw_lower, start)
            if i < 0:
                break
            spans.append((i, i + len(kw)))
            start = i + len(kw)
    return spans


def build_caption_obj(start: float, end: float, text: str, keywords: list[str]) -> dict:
    """把 (start, end, text, keywords) 转成 {start, end, parts: [...]} 结构。

    输出策略：
        - 默认整段作为 1 个 part（与 demoData.ts 模板对齐）
        - 整段 > MAX_PART_LEN 时按标点 / 空格强制切，每段独立 part
        - 有 keyword accent 命中时，命中区域切为独立 part 标 tone: "accent"
    """
    spans = find_accent_indices(text, keywords)
    text_chunks: list[str]  # 待切的 chunks
    if len(text) <= MAX_PART_LEN:
        text_chunks = [text]
    else:
        # 整段太长，按 split_into_parts 切
        text_chunks = split_into_parts(text)
        if not text_chunks:
            text_chunks = [text]

    obj_parts: list[dict] = []
    for chunk in text_chunks:
        chunk_start_in_text = text.find(chunk)
        if chunk_start_in_text < 0:
            chunk_start_in_text = 0
        chunk_end_in_text = chunk_start_in_text + len(chunk)
        # 这个 chunk 命中的 spans
        hits = [
            (s, e) for (s, e) in spans
            if s >= chunk_start_in_text and e <= chunk_end_in_text
        ]
        if not hits:
            obj_parts.append({"text": chunk})
            continue
        # 按 span 切成 prefix / accent / suffix
        hits.sort()
        cur = chunk_start_in_text
        for hs, he in hits:
            if hs > cur:
                obj_parts.append({"text": text[cur:hs]})
            obj_parts.append({"text": text[hs:he], "tone": "accent"})
            cur = he
        if cur < chunk_end_in_text:
            obj_parts.append({"text": text[cur:chunk_end_in_text]})

    return {"start": start, "end": end, "parts": obj_parts}


def to_typescript(captions: list[dict]) -> str:
    """把 captions[] 序列化成 TS 字面量代码片段。"""
    lines = ["  captions: ["]
    for i, c in enumerate(captions):
        if not c.get("parts"):
            continue
        end_comma = "," if i < len(captions) - 1 else ","
        lines.append("    {")
        lines.append(f"      start: {c['start']:.3f},")
        lines.append(f"      end: {c['end']:.3f},")
        lines.append("      parts: [")
        for j, part in enumerate(c["parts"]):
            inner_end = "," if j < len(c["parts"]) - 1 else ""
            tone = f', tone: "{part["tone"]}"' if part.get("tone") else ""
            # JS 字符串转义
            text = part["text"].replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'        {{text: "{text}"{tone}}}{inner_end}')
        lines.append("      ],")
        lines.append(f"    }}{end_comma}")
    lines.append("  ],")
    return "\n".join(lines)


def load_inputs(
    segments_path: Path | None,
    srt_path: Path | None,
) -> list[dict]:
    """合并 / 优先化输入，返回 [{start, end, text}, ...]。"""
    if srt_path and srt_path.exists():
        text_cues = parse_srt(srt_path.read_text(encoding="utf-8"))
    else:
        text_cues = []

    if segments_path and segments_path.exists():
        data = json.loads(segments_path.read_text(encoding="utf-8"))
        time_cues = [
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": seg.get("text", ""),
            }
            for seg in data.get("segments", [])
        ]
    else:
        time_cues = []

    if text_cues and time_cues:
        # 用 SRT 的 text 替换对应段的 text（按 start 时间最近）
        merged: list[dict] = []
        for tc in time_cues:
            best = min(
                text_cues,
                key=lambda x: abs(x["start"] - tc["start"]),
                default=None,
            )
            if best is not None and abs(best["start"] - tc["start"]) < 1.0:
                merged.append(
                    {
                        "start": tc["start"],
                        "end": tc["end"],
                        "text": best["text"],
                    }
                )
            else:
                merged.append(tc)
        return merged

    if text_cues:
        return text_cues
    if time_cues:
        return time_cues
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SRT/segments.json → demoData.ts 的 captions[] 数组代码",
    )
    parser.add_argument(
        "--segments",
        default="work/captions/segments.json",
        help="TTS 段元数据 JSON（默认 work/captions/segments.json）",
    )
    parser.add_argument(
        "--srt",
        default=None,
        help="ASR 对齐的 SRT 字幕（可选；存在时优先用 SRT 的 text 替换对应段）",
    )
    parser.add_argument(
        "--keywords",
        default="",
        help="标 accent 的关键词，逗号分隔，如：edge-tts,MiniMax,免费",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="输出文件路径（不传则打印到 stdout）",
    )
    parser.add_argument(
        "--print-totals",
        action="store_true",
        help="打印每段字数和累计时长到 stderr",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="项目根目录（决定 --segments/--srt/--out 的相对路径基准）",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    segments_path = out_dir / args.segments if not Path(args.segments).is_absolute() else Path(args.segments)
    srt_path = out_dir / args.srt if args.srt and not Path(args.srt).is_absolute() else (Path(args.srt) if args.srt else None)

    cues = load_inputs(segments_path, srt_path)
    if not cues:
        sys.exit(f"未读到任何字幕。请检查 --segments={segments_path} 或 --srt={srt_path}")

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    captions = [build_caption_obj(c["start"], c["end"], c["text"], keywords) for c in cues]
    captions = [c for c in captions if c["parts"]]  # 去掉空段

    snippet = to_typescript(captions)

    if args.print_totals:
        total = sum(c["end"] - c["start"] for c in captions)
        words = sum(sum(len(p["text"]) for p in c["parts"]) for c in captions)
        print(
            f"  → {len(captions)} 段字幕 / {words} 字 / 累计 {total:.3f}s",
            file=sys.stderr,
        )
        for i, c in enumerate(captions, 1):
            text = "".join(p["text"] for p in c["parts"])
            print(
                f"    [{i:02d}] {c['start']:.3f}-{c['end']:.3f} ({c['end']-c['start']:.3f}s)  {text[:30]}{'...' if len(text) > 30 else ''}",
                file=sys.stderr,
            )

    if args.out:
        out_path = out_dir / args.out if not Path(args.out).is_absolute() else Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(snippet + "\n", encoding="utf-8")
        print(f"  ✓ 写到 {out_path}", file=sys.stderr)
    else:
        print(snippet)


if __name__ == "__main__":
    main()
