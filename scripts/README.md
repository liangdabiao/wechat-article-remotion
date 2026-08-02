# scripts/ — 工具脚本

> 三个 Python 脚本覆盖端到端 pipeline 的所有非渲染步骤。脚手架、Remotion 渲染相关命令见上级 `templates/remotion-project/package.json`。

## 速查

| 脚本 | 用途 | 调用时机 |
|---|---|---|
| [`scaffold_wechat_article_project.py`](#scaffold_wechat_article_projectpy) | 从模板生成新 Remotion 项目 + 播种字体/SFX | 每次新建项目 |
| [`fetch_article.py`](#fetch_articlepy) | 抓公众号文章 → markdown + 下载原文图 + PIL 读宽高 | 拿到 URL 后 |
| [`generate_tts.py`](#generate_ttspy) | **统一 TTS 入口**（自动选 minimax / edge-tts） | LLM 拆稿完、跑渲染前 |
| [`generate_tts_minimax.py`](#generate_tts_minimaxpy) | MiniMax T2A v2 实现（需 API key） | 通常不需要直接调 |
| [`generate_tts_edge_tts.py`](#generate_tts_edge_ttspy) | edge-tts 免费实现（无需 key） | 通常不需要直接调 |

---

## `scaffold_wechat_article_project.py`

从 `templates/remotion-project/` 复制一份新工程到 `--project-dir`，并从 `talking-head-remotion/assets/library/` 播种字体 + SFX。

```bash
python3 scaffold_wechat_article_project.py \
  --project-dir ./my-wx-video \
  --title "示例公众号文章" \
  --article-url "https://mp.weixin.qq.com/s/xxxxx"
```

可选参数：
- `--audio <path>`：把已生成好的 `voice.m4a` 直接拷进新项目
- `--duration <float>`：目标时长（默认 18.0；有 `--audio` 时自动 ffprobe 覆盖）
- `--force`：目标目录非空时强制覆盖模板文件

---

## `fetch_article.py`

抓公众号文章 → markdown，下载所有原文图到 `public/assets/article-images/`，PIL 读宽高写到 `work/source/images.json`。

```bash
python3 fetch_article.py \
  --url "https://mp.weixin.qq.com/s/xxxxx" \
  --out-dir ./my-wx-video
```

底层走 [ideaflow-article-to-markdown](https://huggingface.co/spaces/ideaflow/article-to-markdown) 公开 API。**注意：第三方服务无 SLA**，失败时手动复制粘贴文章也行 —— 之后只跑"下载图片 + PIL 读宽高"那部分即可。

依赖：`requests` + `Pillow`（在仓库根 `requirements.txt` 已声明）。

---

## `generate_tts.py`（**统一入口** ⭐）

TTS 一站式入口，**自动按 minimax 凭据探测决定引擎**。

### 选引擎逻辑

| `--engine` | 行为 |
|---|---|
| `auto`（默认） | 探测 `../.env` 里的 `minimaxi=` + `minimaxi-group-id=`，都有 → minimax；否则 edge-tts |
| `minimax` | 强制用 MiniMax T2A v2（需 key） |
| `edge-tts` | 强制用 edge-tts（无需 key） |

### 用法

```bash
# 1. 默认（auto）
python3 generate_tts.py \
  --script work/source/tts-script.md \
  --out-dir ./my-wx-video

# 2. 强制 edge-tts，并换女声 + 减速
python3 generate_tts.py \
  --engine edge-tts \
  --voice zh-CN-XiaoxiaoNeural \
  --rate "-10%" \
  --script work/source/tts-script.md \
  --out-dir ./my-wx-video

# 3. 强制 minimax，指定 voice_id
python3 generate_tts.py \
  --engine minimax \
  --voice-id female-shaonv \
  --speed 1.2 \
  --script work/source/tts-script.md \
  --out-dir ./my-wx-video

# 4. 列出 edge-tts 可用 voice
python3 generate_tts.py --engine edge-tts --list-voices
```

### 凭据

- minimax：从 `--api-key` / `--group-id` 读；或从以下 .env 路径自动找：
  - `<out-dir>/../.env`（项目根的 .env，**最常见**）
  - `<out-dir>/.env`
  - `./.env`
  - `~/.env`
- edge-tts：**无需任何凭据**。只要能联网调 Microsoft Edge 的在线 TTS 服务。

### 依赖

- 公共：`requests`
- minimax 专属：仅 `requests`
- edge-tts 专属：`edge-tts`
- 系统：`ffmpeg` / `ffprobe`（用于验证 mp3 时长 + 拼接 + 转 m4a）

`requirements.txt` 已包含（edge-tts 行默认注释，按需取消）。

### 输出（两个引擎**完全一致**）

```
public/assets/audio/voice.mp3        拼接后的整段 mp3
public/assets/audio/voice.m4a        AAC 版（Remotion 用）
work/captions/segments.json          每段 start/duration/end + engine 元信息
work/audio/tts-segments/seg-NN.mp3   临时分段（可手动删）
```

`segments.json` 结构：

```json
{
  "engine": "edge-tts",
  "voice": "zh-CN-YunxiNeural",
  "rate": "+0%",
  "volume": "+0%",
  "pitch": "+0Hz",
  "total": 87.234,
  "voice_mp3": "assets/audio/voice.mp3",
  "voice_m4a": "assets/audio/voice.m4a",
  "segments": [
    {"index": 1, "text": "...", "mp3": "work/audio/tts-segments/seg-01.mp3",
     "start": 0.0, "duration": 8.234, "end": 8.234},
    ...
  ]
}
```

---

## `generate_tts_minimax.py`

`generate_tts.py --engine minimax` 的实现。**一般不直接调**，统一入口已经覆盖。

直接调用的场景：你想用 `--api-key` / `--group-id` 临时覆盖 .env，或者写 CI 强制锁定 minimax。

```bash
python3 generate_tts_minimax.py \
  --script work/source/tts-script.md \
  --out-dir ./my-wx-video \
  --voice-id female-shaonv \
  --speed 1.0
```

凭据逻辑与统一入口一致。

---

## `generate_tts_edge_tts.py`

`generate_tts.py --engine edge-tts` 的实现。**一般不直接调**。

直接调用的场景：想 `--list-voices`、或绕过统一入口的凭据探测。

### 推荐中文 voice

| Voice | 性别 | 风格 |
|---|---|---|
| `zh-CN-YunxiNeural` | 男 | 青年 / 通用（默认） |
| `zh-CN-XiaoxiaoNeural` | 女 | 温柔 / 旁白 |
| `zh-CN-YunyangNeural` | 男 | 阳光 / 新闻 |
| `zh-CN-XiaoyiNeural` | 女 | 甜美 |
| `zh-CN-liaoning-XiaobeiNeural` | 女 | 东北口音 |
| `zh-CN-shaanxi-XiaoniNeural` | 女 | 陕西方言 |
| `zh-HK-WanLungNeural` | 男 | 粤语 |
| `zh-TW-HsiaoChenNeural` | 女 | 台湾国语 |

### 语速 / 音量 / 音调

edge-tts 用百分比 / Hz 控制：
- `--rate "+20%"` 加速 20%；`"-10%"` 减速 10%
- `--volume "+10%"` 加大；`"-20%"` 减小
- `--pitch "+5Hz"` 升调；`"-5Hz"` 降调

### ⚠️ 合规提示

edge-tts 借的是 Microsoft Edge 浏览器内置的"Read Aloud"在线 TTS 服务，**没有正式 SLA**。
- 个人 / Demo / 内部用：完全 OK
- 商用 / 持续服务：建议改用 minimax 或 Google TTS / Azure Speech 等正式 API
