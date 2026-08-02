# WeChat Article Remotion

> 把任意一篇微信公众号文章（`https://mp.weixin.qq.com/s/...`）转成 Studio 风格的 Remotion 视频 —— 暖白画布 + 上下镜像透视格子 + 顶部章节进度 + 公众号原文图完整保留（`object-fit: contain` 永不裁切）。

这是一个 Claude Skill，定位在 `.claude/skills/` 下，被 Claude Code / Trae IDE / Codex / workbuddy 等支持 Skill 的工具加载并执行端到端 pipeline。

---

## 怎样配置使用

在 codex,claude code, workbuddy 等 Agent 命令AI：

❯ 安装skill: https://github.com/liangdabiao/wechat-article-remotion
 ，然后需要安装好 remotion。

配置好，就可以开始使用了。

在codex,claude code, workbuddy:

❯ paper-cutout-remotion skill 制作： 制作一个纸片风分层动画视频：  苏东坡 赤壁怀古



## 目录

- [项目状态](#项目状态)
- [核心能力](#核心能力)
- [项目结构](#项目结构)
- [依赖清单](#依赖清单)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [端到端 Pipeline](#端到端-pipeline)
- [6 个场景类型](#6-个场景类型)
- [硬规则（不可妥协）](#硬规则不可妥协)
- [与 talking-head-remotion 的关系](#与-talking-head-remotion-的关系)
- [渲染命令参考](#渲染命令参考)
- [已知问题与改进方向](#已知问题与改进方向)
- [贡献指南](#贡献指南)

---

## 项目状态

| 维度 | 状态 | 说明 |
|---|---|---|
| Skill 入口 | ✅ 完整 | `SKILL.md` 含 description、视觉规范、pipeline、硬规则 |
| 规范文档 | ✅ 3 份 | `references/` 下 `visual-guide.md` / `scene-types.md` / `beat-checklist.md` |
| 脚手架脚本 | ✅ 2 份 | `scripts/scaffold_wechat_article_project.py` / `scripts/fetch_article.py` |
| Remotion 模板 | ✅ 8 源文件 | `templates/remotion-project/src/{index,Root,ArticleVideo,background,sceneTypes,demoData,shared,theme}.{ts,tsx}` |
| 公共素材库 | ✅ 跨 skill 共享 | 从 `talking-head-remotion/assets/library/` 播种（9 字体 + 7 SFX） |
| 端到端验证 | ✅ 2 个 demo | `demo-wx-article`（4 张图，88s 视频）、`demo-wx-llm`（27 张图，12 scene） |
| TTS 工具脚本 | ✅ 完整（2026-08-03 抽离） | `scripts/generate_tts.py`（统一入口）/ `generate_tts_minimax.py`（MiniMax 实现）/ `generate_tts_edge_tts.py`（edge-tts 免费实现） |
| 字幕对齐工具 | ⚠️ 文档建议未实现 | `scripts/align_captions.py` 在 LESSONS.md 中建议补；当前手动写 `captions[]` |

> 详细检查结果见 [PROJECT_AUDIT.md](PROJECT_AUDIT.md) 章节末段（与本 README 一同维护）。

---

## 核心能力

### 视觉

- **暖白画布** `#f7f8f3` + 上下镜像透视格子背景（SVG 实时绘制）
- **顶部黑色章节进度条**（白色填充、章节名字高亮）
- **底部无底色黑字字幕**（关键词蓝色 `#2f6fff` 强调）
- **默认画幅 1920×1080 @ 30fps 横屏**
- **完全无 PIP** —— 主舞台让给公众号原文图（与 talking-head-remotion 的最大差异）

### 场景

6 个场景类型（5 基础 + 1 核心新增）：

| kind | 用途 | 关键字段 |
|---|---|---|
| `cover` | 开头标题 | `eyebrow, titleLines, subtitle` |
| `list` | 步骤、要点、清单 | `eyebrow, heading, items[]` |
| `stat` | 数据、金句 | `eyebrow, number, unit, title, metrics[]` |
| `compare` | 对比、选 A/B | `eyebrow, heading, choices[]` |
| `outro` | 结尾 CTA | `eyebrow, title, subtitle` |
| **`article-image`** | **公众号原文图完整展示** | `eyebrow, imageSrc, imageAspect, title, caption?, source?` |

详见 [references/scene-types.md](references/scene-types.md)。

### 动效词汇（4 类）

- **进场**：图片 `scale 0.96→1` + opacity（0.6s）；eyebrow / 标题 / caption 各错开 0.18s
- **持续**：背景 wash / 格子呼吸；图源标签 6s 呼吸一次
- **强调**：关键词 `1.0x→1.04x→1.0x` spring，0.25s
- **示意**：多图轮播（`article-image-stack` 待沉淀）

---

## 项目结构

```text
.claude/skills/wechat-article-remotion/
├── SKILL.md                          # 入口：description / 视觉规范 / pipeline / 硬规则
├── README.md                         # 本文件
├── PROJECT_AUDIT.md                  # 项目全面检查报告（与本 README 同步维护）
│
├── references/                       # 规范文档
│   ├── visual-guide.md               # 视觉规范、铁律、抽帧清单
│   ├── scene-types.md                # 6 场景的 TS 数据模型 + 动效配方
│   └── beat-checklist.md             # 文章 → 视频 beat 拆稿模板
│
├── scripts/                          # 脚手架 + 抓文 + TTS 工具
│   ├── scaffold_wechat_article_project.py
│   ├── fetch_article.py
│   ├── generate_tts.py               # ⭐ 统一入口（auto / minimax / edge-tts）
│   ├── generate_tts_minimax.py       # MiniMax T2A v2 实现（需 key）
│   ├── generate_tts_edge_tts.py      # edge-tts 免费实现（无需 key）
│   └── README.md                     # 脚本使用手册
│
└── templates/                        # Remotion 模板（被脚手架复制到目标项目）
    └── remotion-project/
        ├── package.json              # 依赖 + npm scripts
        ├── tsconfig.json             # ES2022 / ESNext / strict
        ├── .gitignore                # 排除 node_modules / renders / *.mp4 等
        ├── README.md                 # 模板级 README（用法）
        ├── PROJECT_BRIEF.md          # 模板级项目说明
        ├── public/assets/
        │   ├── article-images/       # 抓回的公众号原文图（.gitkeep 占位）
        │   ├── audio/                # 配音 + SFX（.gitkeep 占位）
        │   ├── fonts/                # 字体（脚手架从跨 skill 库播种）
        │   └── music/                # BGM（按需）
        ├── renders/                  # 渲染输出（.gitkeep 占位）
        ├── work/                     # 制作中产物
        │   ├── source/               # article.md / images.json / notes.md
        │   ├── audio/                # TTS 临时分段
        │   ├── captions/             # segments.json / SRT
        │   └── lessons/LESSONS.md    # 经验沉淀
        └── src/
            ├── index.ts              # registerRoot(RemotionRoot)
            ├── Root.tsx              # Composition 注册
            ├── ArticleVideo.tsx      # 主组合：背景 + 音频 + scenes + topbar + captions + brand
            ├── background.tsx        # PremiumGridBackground（SVG 透视格子）
            ├── sceneTypes.tsx        # 6 场景 View + TopBar + CaptionLayer
            ├── demoData.ts           # 数据（唯一真相；运行时被 LLM 拆稿填入）
            ├── shared.ts             # progress / frameFromSeconds / clamp / ease
            └── theme.ts              # colors / fonts / layout
```

---

## 依赖清单

### Node（package.json 全部锁定）

| 包 | 版本 | 用途 |
|---|---|---|
| `remotion` | `4.0.484` | Remotion 运行时（核心） |
| `@remotion/cli` | `4.0.484` | `studio` / `render` / `still` 命令 |
| `@remotion/media` | `4.0.484` | 媒体相关 hook |
| `react` | `19.1.0` | UI 框架 |
| `react-dom` | `19.1.0` | UI 框架 |
| `@types/node` | `24.0.10` | Node 类型 |
| `@types/react` | `19.1.8` | React 类型 |
| `@types/react-dom` | `19.1.6` | React DOM 类型 |
| `typescript` | `5.8.3` | 编译器 |

无浮动版本（全部 `=` 锁定），`npm install` 行为可预测。

### Python

| 包 | 用途 | 引入位置 |
|---|---|---|
| `requests` | 调 ideaflow API / 下载原文图 / MiniMax T2A | `fetch_article.py` + `generate_tts_minimax.py` |
| `Pillow` | 读图宽高 + RGBA → RGB 转换 | `fetch_article.py` |
| `edge-tts` | **免费 TTS 引擎**（无 API key） | `generate_tts_edge_tts.py` |
| `ffmpeg` / `ffprobe`（系统二进制） | 量时长 / 拼接 mp3 / 转 m4a | 两个 TTS 脚本 |

**已提供 [`requirements.txt`](requirements.txt)** —— 公共依赖必装，edge-tts 行注释掉，按需取消注释启用免费方案。

### 跨 Skill 共享素材

| 来源 | 数量 | 说明 |
|---|---|---|
| `talking-head-remotion/assets/library/fonts/` | 9 个 ttf | Noto Sans SC (5 字重) + Space Grotesk (4 字重) + SOURCES.md |
| `talking-head-remotion/assets/library/sfx/` | 7 个 mp3 | 详见 `sfx/SOURCES.md`（Mixkit License） |

脚手架 `seed_from_library()` 自动复制到新项目 `public/assets/{fonts,audio}/`。

### 第三方 API（运行期）

| 服务 | 用途 | 配置位置 |
|---|---|---|
| ideaflow Article-to-Markdown | 公众号 → markdown | 硬编码在 `fetch_article.py` |
| MiniMax T2A v2 (`speech-02-hd`) | 配音 | 根目录 `.env` 的 `minimaxi` + `minimaxi-group-id` |

> 注意：TTS 调用脚本 `scripts/generate_tts.py` 当前不存在于 skill，文档与实现脱节（详见 [PROJECT_AUDIT.md 缺失项](#项目状态)）。

---

## 环境要求

| 依赖 | 推荐版本 | 检查命令 |
|---|---|---|
| Node.js | 20.x 或 22.x | `node --version` |
| npm | 10.x+ | `npm --version` |
| Python | 3.10+ | `python --version` |
| ffmpeg | 6.x+ | `ffmpeg -version` |
| Chrome / Chromium | 由 Remotion 自动管理 | （无） |
| 操作系统 | Windows 10/11、macOS、Linux | — |

`package.json` 未声明 OS 限制；`@types/node@24` 建议 Node 22+。

---

## 快速开始

### 0. 准备 .env（仅 TTS 步骤需要）

仓库根目录（不是 skill 目录）建一个 `.env`：

```ini
minimaxi=sk-api-你的key
minimaxi-group-id=你的group_id
```

### 1. 脚手架生成新项目

```bash
# 从 skill 目录出发
python3 .claude/skills/wechat-article-remotion/scripts/scaffold_wechat_article_project.py \
  --project-dir ./my-wx-video \
  --title "示例公众号文章" \
  --article-url "https://mp.weixin.qq.com/s/xxxxx"
```

脚手架会：

1. 复制 `templates/remotion-project/` → `./my-wx-video/`
2. 从 `talking-head-remotion/assets/library/{fonts,sfx}/` 复制全部素材
3. 替换占位符：`__PROJECT_TITLE__` / `__DURATION_SECONDS__` / `__ARTICLE_URL__` / `__AUDIO_PATH__`
4. 写 `manifest.json`

### 2. 抓公众号文章 + 下载原文图

```bash
cd my-wx-video
python3 ../.claude/skills/wechat-article-remotion/scripts/fetch_article.py \
  --url "https://mp.weixin.qq.com/s/xxxxx" \
  --out-dir .
```

产物：

- `work/source/article.md` —— 抓回的 markdown
- `work/source/images.json` —— 图片清单（含 width/height/imageAspect）
- `public/assets/article-images/img-NN.jpg` —— 原文图（统一转 jpg）

### 3. 拆稿 → 填 `src/demoData.ts`

按 [references/beat-checklist.md](references/beat-checklist.md) 在 Claude 会话里用 LLM 拆稿，把结果写进 `src/demoData.ts` 的 `demoProject.scenes[]` / `captions[]` / `chapters[]`。

### 4. TTS 配音

**统一入口** `scripts/generate_tts.py`，**自动按 minimax 凭据探测选择引擎**：

```bash
# 1. 默认（自动选）
python3 ../.claude/skills/wechat-article-remotion/scripts/generate_tts.py \
  --script work/source/tts-script.md \
  --out-dir .

# 2. 强制 edge-tts（无需 key）
python3 .../generate_tts.py --engine edge-tts --voice zh-CN-XiaoxiaoNeural ...

# 3. 强制 minimax
python3 .../generate_tts.py --engine minimax --voice-id female-shaonv ...
```

> 三个脚本的详细参数 + 用法见 [scripts/README.md](scripts/README.md)。
>
> 已知遗留：`SKILL.md` 第 65 行历史引用 `scripts/generate_tts.py`（✅ 2026-08-03 已补完）。

### 5. 回写字幕 time

把 `work/captions/segments.json` 里每段的 `start` / `end` 拷进 `src/demoData.ts` 的 `captions[]`。

> **未来改进**：可写一个 `scripts/align_captions.py` 自动转 SRT → `captions[]`（已在 [work/lessons/LESSONS.md](templates/remotion-project/work/lessons/LESSONS.md) 建议）。

### 6. 渲染

```bash
npm install
npm run typecheck         # tsc --noEmit
npm run still             # 渲 1 帧静态图（校对场景布局）
npm run render:preview    # 低清 proof（先出这个，不要一上来跑 1080p）
npm run render            # 正式 1080p（仅在用户确认 preview 后再跑）
```

---

## 端到端 Pipeline

```text
用户：https://mp.weixin.qq.com/s/xxx
   │
   ▼
[1] scripts/fetch_article.py
    · ideaflow API → markdown
    · 提取 ![](url) + 下载原文图到 public/assets/article-images/img-NN.jpg
    · PIL 读每张图 WxH → imageAspect
    · 写 work/source/article.md 和 work/source/images.json
   │
   ▼
[2] 运行时 LLM 拆稿（在本会话里执行）
    · 按 references/beat-checklist.md 拆 6-12 个 scene
    · 输出 scenes[]、captions[]、chapters[] 到 src/demoData.ts
   │
   ▼
[3] TTS 配音（统一入口 `scripts/generate_tts.py`）
    · 默认自动按 minimax 凭据探测选择引擎：
        - 有 minimax 凭据（`../.env` 里有 `minimaxi=` + `minimaxi-group-id=`）→ 用 MiniMax T2A v2
        - 无 minimax 凭据 → 自动降级到 edge-tts（**免费 / 无需 key**）
    · 显式：`--engine minimax` 或 `--engine edge-tts`
    · 必须 ffprobe 验证每段 mp3 能解码 + 量时长，否则杂音
    · 产物归档路径（两个引擎输出格式完全一致）：
        - public/assets/audio/voice.m4a     # 最终 AAC，Remotion 用
        - public/assets/audio/voice.mp3     # 备用
        - work/captions/segments.json       # 每段时长 + 累计起点 + engine 元信息
        - work/audio/tts-segments/seg-NN.mp3 # 临时分段
        - work/source/narration.md          # TTS 专用稿（每段一段）
   │
   ▼
[4] 用真实音频时长回写 demoData.ts 的 captions time
   │
   ▼
[5] npm run typecheck / still / render:preview
   │
   ▼
[6] Subagent 独立视觉审核
    · 每场景抽"开始 0.3s"和"中段"两帧
    · 重点：图片 contain 不裁切、关键词不先于字幕、每场景元素数 ≤ 5
   │
   ▼
[7] 询问用户是否需要最终 1080p 渲染（可选）
    · 展示 preview 结果：时长、质量、内容覆盖情况
    · 只有用户明确确认后才跑 `npm run render`
    · 如果用户满意 preview，无需跑最终版
```

---

## 6 个场景类型

详见 [references/scene-types.md](references/scene-types.md)。要点速查：

| 场景 | 数据模型 | 进场节奏（推荐） | 何时用 |
|---|---|---|---|
| `cover` | `{eyebrow, titleLines, subtitle}` | eyebrow 0.14s → 标题 0.25s → 副标题 0.52s | 视频开场第一帧 |
| `list` | `{eyebrow, heading, items[]}` | 标题栏 0.16~0.24s，每行 0.28+0.1n s | "三大要点""四个步骤"等结构化内容 |
| `stat` | `{eyebrow, number, unit, title, metrics[]}` | 巨数字 0.16s → 解释 0.28s → mini 数据 0.52+0.08n s | "95.7%""增长 3 倍" |
| `compare` | `{eyebrow, heading, choices[]}` | 小标 0.16s → 标题 0.24s → 选项 0.38+0.12n s | "A vs B""开源 vs 闭源" |
| `outro` | `{eyebrow, title, subtitle}` | 小标 0.16s → 标题 0.24s → 副标 0.48s | 视频最后一帧 |
| `article-image` | `{eyebrow, imageSrc, imageAspect, title, caption?, source?, appearAt?, titleAppearAt?, captionAppearAt?}` | eyebrow 0.08s → 图 0.16s → 标题 0.24s → caption 0.5s | 截图、表格、流程图、信息图等带文字的图 |

---

## 硬规则（不可妥协）

1. **公众号图片永远 `object-fit: contain`，永不裁切** —— Code Review 看到 `object-fit: cover` 用在 article image 上即 fail。
2. **每屏 ≤ 5 个文字元素 + 至少一个非文字视觉主体**（沿用 talking-head-remotion 硬规则）。`article-image` 场景的非文字主体就是那张图。
3. **逐元素进场**：`article-image` 场景里图片 / 标题 / 解读 / 图源各有 `appearAt`，错开 0.18s 进场。
4. **数据驱动**：`demoData.ts` 是唯一真相，component 内不写死画面。
5. **音画强同步**：用「前 1s / 后 0.5s 双帧」抽帧审计，关键词不能先于字幕。
6. **图片不随意丢**（防丢图铁律）：
   - 写 `demoData.ts` 前必须先 `ls public/assets/article-images/` 看实际下载了多少张
   - 必须读 `work/source/article.md` 把每张图映射到所属章节（图后第一行通常是 caption，如"陈白沙祠・图来自@xxx"）
   - **尽可能保留正文有用的图片**——内容图、景观图、细节图都该用上；判定为无用（二维码 / 分割线装饰 / 重复 / 模糊缩略图）才能丢，且必须向用户说明丢了几张、为什么
   - 同景点多图必须用 `imageSources[]` 轮播，不要只挑 1 张代表
   - 单图场景停留 ≤ 6s；多图轮播间隔 1.5-3s（更短观感眼花）
7. **共用 talking-head-remotion 公共素材库** —— 字体/SFX 用 `seed_from_library()` 复制，新动效回流到 `talking-head-remotion/assets/library/animations/`。
8. **国际化（i18n）先不处理**，按 user_profile 偏好默认中文。

---

## 与 talking-head-remotion 的关系

| 维度 | talking-head-remotion | wechat-article-remotion |
|---|---|---|
| 场景 | 5（cover/list/stat/compare/outro） | 6（+ article-image） |
| PIP | 右下圆形 206px | **无** |
| 字幕安全区 | 避开 PIP | 主舞台让给图片 |
| 顶栏 | 章节进度 | 章节进度（一致） |
| 视觉调性 | Studio 暖白 | Studio 暖白（一致） |
| 公共素材库 | 字体/SFX 宿主 | **完全共用**（只读） |

**两者是兄弟 skill**：talking-head-remotion 是 `assets/library/` 的所有者，wechat-article-remotion 通过 `seed_from_library()` 借用。新动效组件从 wechat-article-remotion 沉淀时，约定回流到 `talking-head-remotion/assets/library/animations/`。

---

## 渲染命令参考

```bash
npm run studio          # 打开 Remotion Studio 实时预览
npm run typecheck       # tsc --noEmit
npm run still           # 渲 1 帧静态图（校对场景布局）
npm run render:preview  # 低清 proof（先出这个，--scale=0.5 --crf=28 --concurrency=2）
npm run render          # 正式 1080p（仅在用户确认 preview 后再跑）
```

### 渲染调试节奏

- 默认先出低清 proof（`npm run render:preview`），不要一上来跑 1920×1080 全片。
- preview 完成后，**必须先向用户展示结果，询问是否需要最终版**，得到确认后才跑 `npm run render`。禁止自动推进到最终渲染。
- 长渲染把输出重定向到 `work/render.log`，只 tail 日志尾部。
- 用户打断后先检查后台进程：`pgrep -fl "remotion|chrome-headless|Google Chrome for Testing|Chromium"`。
- 不要用模糊的 CLI 探测命令（如 `remotion render --help`），优先看 `package.json` 里已有脚本或官方文档。

---

## 已知问题与改进方向

### 文档 / 实现不一致（✅ 2026-08-03 已修复）

- ~~❌ `scripts/generate_tts.py` ~~ —— 文档引用了不存在的脚本
   - ✅ **已修复**：抽离为 `scripts/generate_tts_minimax.py` + `scripts/generate_tts_edge_tts.py`（免费方案）+ `scripts/generate_tts.py`（统一入口，自动按 minimax 凭据降级）
- ❌ `scripts/align_captions.py` —— LESSONS.md 中建议补的"SRT → `captions[]` 转换"工具未实现。
- ❌ 模板 `public/assets/audio/.gitkeep` 占位存在，但模板 `package.json` 也没声明 `ffmpeg-static` 等系统依赖。

### 模板小问题

- `.gitkeep` 全空（这是占位文件，正常）
- 模板 `tsconfig.json` 写死 `"types": ["node"]`，未声明 `@remotion/*` 的类型（Remotion 自己 inject，可忽略）

### 建议沉淀到库的新增项

1. **`article-image-stack` 场景**：当前只有单图版本；多图（左/右双联、上下双联）参考 [scene-types.md 第 6 节](references/scene-types.md) 提到的"未来版本"
2. **真实文章跑通模板**：当前两个 demo 跑通真实公众号 URL，但模板自身只有占位 `img-01.jpg`
3. **`align_captions.py`**：把 SRT / `segments.json` 自动转成 `captions[]` 数组
4. **国际化**：按 user_profile 偏好先不做；如果要做，把 `RichText` 抽象成 `<T>` 组件支持多语言 fallback

---

## 贡献指南

### 改动模板后必跑

```bash
# 1. 复制一份到 demo
python3 scripts/scaffold_wechat_article_project.py --project-dir ./test-tpl --force
cd test-tpl
npm install
npm run typecheck
npm run still
```

### 改公共素材库（fonts / sfx）

先改 `talking-head-remotion/assets/library/`，再跑脚手架验证播种。SFX 必须在 `SOURCES.md` 补授权说明。

### 改 SKILL.md / references/

跟 `talking-head-remotion` 保持同一行文风格：先讲"是什么 / 为什么"，再讲"怎么做"；硬规则用"❌ 禁止 / ✅ 必须"格式。

---

## License

项目内字体（SIL Open Font License）和 SFX（Mixkit License）保留原作者声明。代码部分未声明开源协议，默认仅供内部使用。
