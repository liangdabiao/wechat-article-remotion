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
    """对每个图 URL，提取其在 markdown 里紧接着的第一个非空行作为 caption。

    公众号文章里图片后通常有一行 "xxx・图来自@yyy"，是判断图归属/丢留的关键信号。
    返回 {url: caption}；caption 为空字符串表示无可用 caption。
    """
    lines = md.split("\n")
    url_to_caption: dict[str, str] = {}
    for i, line in enumerate(lines):
        m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", line)
        if not m:
            continue
        url = m.group(1).strip()
        # 找紧随的非空、非图片、非纯空白行
        cap = ""
        for j in range(i + 1, min(i + 6, len(lines))):
            cand = lines[j].strip()
            if not cand:
                continue
            if cand.startswith("!["):
                break  # 下一张图，放弃
            # 跳过纯标点/分隔符
            if len(cand) >= 2 and not re.fullmatch(r"[\s\-·、|]+", cand):
                cap = cand
                break
        url_to_caption[url] = cap
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
        images.append(
            {
                "index": idx,
                "filename": jpg_path.name,
                "staticFile": f"assets/article-images/{jpg_path.name}",
                "width": w,
                "height": h,
                "imageAspect": aspect,
                "caption": url_to_caption.get(url, ""),
                "sourceUrl": url,
            }
        )
        cap_preview = url_to_caption.get(url, "")[:40]
        print(f"  ✓ {jpg_path.name}  {w}x{h}  aspect={aspect}  cap={cap_preview!r}")

    print("[4/4] 写 images.json")
    (source_dir / "images.json").write_text(
        json.dumps(images, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  → {len(images)} 张图片清单已写入 {source_dir / 'images.json'}")
    print("完成。下一步：用 LLM 按 references/beat-checklist.md 拆稿。")


if __name__ == "__main__":
    main()
