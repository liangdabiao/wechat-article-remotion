#!/usr/bin/env python3
"""抓取微信公众号文章 → markdown + 下载原文图 + PIL 读宽高。

依赖：
    pip install requests Pillow

用法：
    python3 fetch_article.py --url "https://mp.weixin.qq.com/s/xxx" --out-dir .

输出：
    work/source/article.md              # 抓回的 markdown
    work/source/images.json             # 图片清单（含宽高比）
    public/assets/article-images/img-NN.<ext>   # 原文图（统一转 jpg）
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image

IDEAFLOW_URL = "https://ideaflow-article-to-markdown.hf.space/resolve/mark"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_markdown(article_url: str) -> str:
    """调 ideaflow API 把公众号文章转 markdown。"""
    resp = requests.post(
        IDEAFLOW_URL,
        headers={
            "Referer": "https://ideaflow-article-to-markdown.hf.space/",
            "User-Agent": UA,
            "Content-Type": "application/json",
        },
        json={"blogUrl": article_url},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    md = data.get("data", {}).get("markdown", "")
    if not md:
        raise RuntimeError(f"ideaflow 返回无 markdown：{data}")
    return md


def extract_image_urls(md: str) -> list[str]:
    """提取 markdown 里所有 ![alt](url) 形式的图片 URL。"""
    urls = re.findall(r"!\[.*?\]\((.+?)\)", md)
    # 去重但保序
    seen: set[str] = set()
    uniq: list[str] = []
    for u in urls:
        u = u.strip()
        if u and u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def extract_image_captions(md: str) -> dict[str, str]:
    """对每个图 URL，提取其所属段落作为 caption。

    ★★★ 核心规则：公众号文章的图文结构是「一段介绍 + 一张配图」，
    图片说明行（如 "👇🏼韶关南雄珠玑古巷"）出现在图片正前方，
    图片后的非空行是下一话题的段落，不是当前图的 caption。
    因此必须向上（图片前）扫描，而非向下。

    优先级：
      1. 图片紧上方的「图片说明行」（如 "👇🏼xxx"、"📷xxx"、emoji 开头的短行）
      2. 图片说明行再往上的「正文段落」（该图真正归属的内容段）
    返回 {url: caption}；caption 为空字符串表示无可用 caption。
    """
    lines = md.split("\n")
    url_to_caption: dict[str, str] = {}

    def is_image_label(line_text: str) -> bool:
        """判断是否是图片说明行（如 👇🏼韶关南雄珠玑古巷 / 📷xxx / 图x：xxx）。"""
        stripped = line_text.strip()
        if not stripped:
            return False
        # 以常见 emoji/符号开头的短行（≤40字）通常是图片说明
        # 用实际 emoji 字符匹配，不用 \u{} 转义（Python re 不支持）
        if len(stripped) <= 40 and re.match(
            r"^[" + "\U0001F300-\U0001F9FF\U00002600-\U000027BF" + "👇🏼📷▶▶️✅❌⭐💡📌📊🎬🔥📢✨👍👇▲]",
            stripped,
        ):
            return True
        # "图X" / "图片" 开头的短标注
        if len(stripped) <= 40 and re.match(r"^(图\s*\d|图片|fig\.|Figure)", stripped, re.IGNORECASE):
            return True
        return False

    def is_content_line(line_text: str) -> bool:
        """判断是否是有意义的正文行（排除纯标点、空行、图片行）。"""
        stripped = line_text.strip()
        if not stripped:
            return False
        if stripped.startswith("!["):
            return False
        # 纯标点/分隔符不算有意义内容
        if len(stripped) <= 3:
            return False
        if re.fullmatch(r"[\s\-·、|!！?？…—\-]+$", stripped):
            return False
        return True

    for i, line in enumerate(lines):
        m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", line)
        if not m:
            continue
        url = m.group(1).strip()

        # === 向上扫描（图片前的行）===
        # 先找紧上方的图片说明行（👇🏼xxx），再找说明行前的正文段落
        # ★ 关键：遇到前一张图片行（![）时不要 break，而是跳过它继续向上——
        #   多张连续图属于同一段落，跳过中间的图片行才能找到共同所属段落
        image_label = ""
        parent_paragraph = ""
        for j in range(i - 1, max(i - 15, -1), -1):
            cand = lines[j].strip()
            if not cand:
                continue
            if cand.startswith("!["):
                continue  # 上一张图，跳过（不 break，继续向上找共同段落）
            if is_image_label(cand) and not image_label and not parent_paragraph:
                image_label = cand
                continue
            if is_content_line(cand):
                parent_paragraph = cand
                break  # 找到正文段落即停

        # 组合 caption：优先 "说明行"（如 👇🏼韶关南雄珠玑古巷），
        # 次选正文段落，两者都有时用说明行（更精炼）
        cap = image_label if image_label else parent_paragraph
        url_to_caption[url] = cap

        # 同时记录所属段落到额外的 context 字段（供 LLM 参考）
        if parent_paragraph and parent_paragraph != cap:
            url_to_caption[f"{url}__context"] = parent_paragraph

    return url_to_caption


def download_image(url: str, dest: Path, referer: str) -> Path:
    """下载单张图。公众号图片通常需要带 Referer。"""
    resp = requests.get(
        url,
        headers={"Referer": referer, "User-Agent": UA},
        timeout=60,
        stream=True,
    )
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def normalize_to_jpg(src: Path, dest: Path) -> Path:
    """把所有图片统一转 jpg（白底填充透明通道），方便后续 pipeline 走通。"""
    im = Image.open(src).convert("RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
    bg.save(dest, "JPEG", quality=92)
    src.unlink(missing_ok=True)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="抓公众号文章 + 下载原文图 + PIL 读宽高",
    )
    parser.add_argument("--url", required=True, help="mp.weixin.qq.com/s/xxx")
    parser.add_argument(
        "--out-dir",
        default=".",
        help="项目根目录（默认当前目录）",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    source_dir = out_dir / "work/source"
    img_dir = out_dir / "public/assets/article-images"
    source_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] 抓 markdown：{args.url}")
    md = fetch_markdown(args.url)
    md_path = source_dir / "article.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  → 写入 {md_path}（{len(md)} 字符）")

    print("[2/4] 提取图片 URL + caption")
    urls = extract_image_urls(md)
    url_to_caption = extract_image_captions(md)
    print(f"  → {len(urls)} 张图")

    print("[3/4] 下载 + 格式统一为 jpg")
    referer = "https://mp.weixin.qq.com/"
    images: list[dict] = []
    for idx, url in enumerate(urls, 1):
        ext = Path(urlparse(url).path).suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        raw_path = img_dir / f"img-{idx:02d}.raw{ext}"
        try:
            download_image(url, raw_path, referer=referer)
        except Exception as e:
            print(f"  ✗ 第 {idx} 张下载失败：{url}  ({e})")
            continue

        jpg_path = img_dir / f"img-{idx:02d}.jpg"
        try:
            normalize_to_jpg(raw_path, jpg_path)
        except Exception as e:
            print(f"  ✗ 第 {idx} 张格式转换失败：{e}")
            continue

        with Image.open(jpg_path) as im:
            w, h = im.size
        aspect = round(w / h, 4) if h else 0
        caption_text = url_to_caption.get(url, "")
        context_text = url_to_caption.get(f"{url}__context", "")
        images.append(
            {
                "index": idx,
                "filename": jpg_path.name,
                "staticFile": f"assets/article-images/{jpg_path.name}",
                "width": w,
                "height": h,
                "imageAspect": aspect,
                "caption": caption_text,
                "context": context_text,
                "sourceUrl": url,
            }
        )
        cap_preview = caption_text[:40]
        ctx_preview = context_text[:40] if context_text else "-"
        print(f"  ✓ {jpg_path.name}  {w}x{h}  aspect={aspect}  cap={cap_preview!r}  ctx={ctx_preview!r}")

    print("[4/4] 写 images.json")
    (source_dir / "images.json").write_text(
        json.dumps(images, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  → {len(images)} 张图片清单已写入 {source_dir / 'images.json'}")
    print("完成。下一步：用 LLM 按 references/beat-checklist.md 拆稿。")


if __name__ == "__main__":
    main()
