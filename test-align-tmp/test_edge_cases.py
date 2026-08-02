"""align_captions.py 边界用例测试。"""
import sys
from pathlib import Path
# skill 根目录的 scripts/ 下
SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import align_captions as ac  # noqa: E402

KW = ["edge-tts", "MiniMax", "Python", "Rust", "OpenAI", "Claude"]

CASES = [
    ("短句", "大家好，欢迎收听本期的 AI 早班车。"),
    ("中文长段无标点",
     "今天我们要聊一聊 Claude 3.5 Sonnet 模型的最新能力提升以及 OpenAI o1 系列推理模型的差异化定位这两个完全不同的技术路线之间的本质差异和适用场景"),
    ("多 keyword",
     "Python 是世界上最流行的 AI 编程语言，但 Rust 正在崛起成为新的系统级 AI 基础设施首选"),
    ("全英文",
     "Edge TTS is a free Python wrapper for Microsoft Edge browser built-in speech synthesis engine."),
    ("空", ""),
    ("混排带数字",
     "据 2024 年最新统计，edge-tts 每天被调用 100 万次，minimax 也在快速增长。"),
    ("仅 ASCII keyword",
     "DeepSeek V3 is now the leading open-source model."),
    ("单字 keyword",
     "我们做 AI 的人，要时刻记住 A 在这里代表的是 Augmented，不是 Artificial。"),
]


def main() -> None:
    for name, text in CASES:
        if not text:
            print(f"[{name}] (空) 跳过\n")
            continue
        obj = ac.build_caption_obj(0.0, 1.0, text, KW)
        parts = obj["parts"]
        print(f"[{name}] {len(text)} chars → {len(parts)} parts")
        for p in parts:
            tone = " [ACCENT]" if p.get("tone") == "accent" else ""
            print(f'  - "{p["text"]}"{tone}')
        # 校验：拼接回来应等于原文（去除 accent 标记后）
        rejoined = "".join(p["text"] for p in parts)
        ok = rejoined == text
        print(f"  拼接回原文: {'✓' if ok else f'✗ 差 {set(text) - set(rejoined)}'}\n")


if __name__ == "__main__":
    main()
