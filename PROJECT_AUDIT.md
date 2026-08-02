# Project Audit — WeChat Article Remotion

> 与 [README.md](README.md) 同步维护。每次做大改动后跑一遍这个检查清单并更新本文件。

**Last audit**: 2026-08-03

---

## 1. 文件完整性检查

### Skill 根目录

| 路径 | 类型 | 状态 |
|---|---|---|
| `SKILL.md` | Claude Skill 入口 | ✅ 存在，含 description + 视觉规范 + pipeline + 硬规则 |
| `README.md` | 项目主 README | ✅ 2026-08-03 新建 |
| `PROJECT_AUDIT.md` | 本文件 | ✅ 2026-08-03 新建 |

### references/

| 文件 | 字节数 | 状态 |
|---|---|---|
| `visual-guide.md` | ~3 KB | ✅ 完整，含铁律、图片布局规则、抽帧清单 |
| `scene-types.md` | ~6 KB | ✅ 完整，含 6 场景 TS 数据模型 + 进场节奏 |
| `beat-checklist.md` | ~6 KB | ✅ 完整，含步骤 0~5 自检 + 3000 字技术评测示例 |

### scripts/

| 文件 | 行数 | 状态 |
|---|---|---|
| `scaffold_wechat_article_project.py` | 156 | ✅ 完整，参数 `--project-dir` / `--title` / `--article-url` / `--audio` / `--duration` / `--force` |
| `fetch_article.py` | 196 | ✅ 完整，4 阶段：抓 md → 提 URL + caption → 下载 + 转 jpg → 写 images.json |
| `generate_tts.py` | ~100 | ✅ **2026-08-03 新增** —— 统一入口，`--engine {auto,minimax,edge-tts}`，自动探测 .env 凭据 |
| `generate_tts_minimax.py` | ~230 | ✅ **2026-08-03 新增** —— 从 `demo-wx-article/scripts/gen_tts_minimax.py` 抽离并改进，参数化更彻底 |
| `generate_tts_edge_tts.py` | ~235 | ✅ **2026-08-03 新增** —— edge-tts 免费方案，无需 API key；带 `--list-voices` |
| `README.md` | ~190 | ✅ **2026-08-03 新增** —— 三个脚本的速查 + 详细用法 |
| `requirements.txt` | 16 | ✅ **2026-08-03 新增** —— requests + Pillow + edge-tts（注释掉，按需启用） |

### templates/remotion-project/

| 文件 | 状态 |
|---|---|
| `package.json` | ✅ 9 依赖全锁定，无浮动版本 |
| `tsconfig.json` | ✅ ES2022 + ESNext + strict |
| `.gitignore` | ✅ 排除 node_modules / renders / *.mp4 等 |
| `README.md` | ✅ 模板级 README |
| `PROJECT_BRIEF.md` | ✅ 含 8 步流程 |
| `public/assets/{article-images,audio,fonts,music}/.gitkeep` | ✅ 占位 |
| `renders/.gitkeep` | ✅ 占位 |
| `work/{source,audio,captions,lessons}/` | ✅ 占位 + `lessons/LESSONS.md` |
| `src/index.ts` | ✅ registerRoot(RemotionRoot) |
| `src/Root.tsx` | ✅ Composition + Folder 注册 |
| `src/ArticleVideo.tsx` | ✅ 主组合，背景 + 音频 + scenes + topbar + captions + brand |
| `src/background.tsx` | ✅ PremiumGridBackground（SVG 透视格子） |
| `src/sceneTypes.tsx` | ✅ 6 场景 View + TopBar + CaptionLayer，约 905 行 |
| `src/demoData.ts` | ✅ 占位 4 scene demo |
| `src/shared.ts` | ✅ progress / frameFromSeconds / clamp / ease |
| `src/theme.ts` | ✅ colors / fonts / layout |

---

## 2. 依赖完整性检查

### Node（package.json）

```
dependencies:
  @remotion/media     4.0.484
  react               19.1.0
  react-dom           19.1.0
  remotion            4.0.484

devDependencies:
  @remotion/cli       4.0.484
  @types/node         24.0.10
  @types/react        19.1.8
  @types/react-dom    19.1.6
  typescript          5.8.3
```

✅ 全部用 `=` 锁定，无 `^` `~` `*` 浮动版本。
✅ `@remotion/*` 全部对齐到同一个 minor.patch（4.0.484）。
✅ React 19 + TS 5.8 是 Remotion 4.x 推荐的版本组合。
⚠️ `@types/node@24` 实际要求 Node 22+，未在 `engines` 字段声明（建议补）。

### Python

| 包 | 引入位置 | 文档化？ |
|---|---|---|
| `requests` | `fetch_article.py` + demo TTS 脚本 | ⚠️ 仅在脚本 docstring，未提供 `requirements.txt` |
| `Pillow` | `fetch_article.py` | ⚠️ 同上 |
| `ffmpeg` / `ffprobe`（系统二进制） | demo TTS 脚本 | ⚠️ 同上 |

**建议**：在 skill 根目录补一份 `requirements.txt`：

```text
requests>=2.31
Pillow>=10.0
```

### 跨 Skill 共享库（`talking-head-remotion/assets/library/`）

| 子目录 | 文件 | 状态 |
|---|---|---|
| `fonts/` | `NotoSansSC-{300,400,500,700,900}.ttf` | ✅ 5 字重 |
| `fonts/` | `SpaceGrotesk-{400,500,600,700}.ttf` | ✅ 4 字重 |
| `fonts/` | `SOURCES.md` | ✅ Google Fonts 来源说明 |
| `sfx/` | `sfx-deep-impact.mp3` | ✅ Mixkit item 1143 |
| `sfx/` | `sfx-movie-trailer-epic-impact.mp3` | ✅ Mixkit item 2908 |
| `sfx/` | `sfx-hard-pop-click.mp3` | ✅ Mixkit item 2364 |
| `sfx/` | `sfx-small-sweep-transition.mp3` | ✅ Mixkit item 166 |
| `sfx/` | `sfx-long-pop.mp3` | ✅ Mixkit item 2358 |
| `sfx/` | `sfx-positive-interface-beep.mp3` | ✅ Mixkit item 2870 |
| `sfx/` | `sfx-whoosh-fast-transition.mp3` | ✅ Mixkit item 1492 |
| `sfx/` | `SOURCES.md` | ✅ 全部授权说明 |

✅ 跨 skill 引用稳定（`talking-head-remotion` 是 sibling skill，不会被删除）。

### 第三方 API

| 服务 | 用途 | 配置 | 状态 |
|---|---|---|---|
| ideaflow Article-to-Markdown | 公众号 → markdown | 硬编码在 `fetch_article.py` | ⚠️ 第三方免费服务，无 SLA；失败无降级方案 |
| MiniMax T2A v2 | 配音 | 根 `.env` 的 `minimaxi` + `minimaxi-group-id` | ✅ 已在 `demo-wx-article/scripts/gen_tts_minimax.py` 跑通 |

---

## 3. 端到端验证

### demo-wx-article

- 路径：`d:/video-spec-builder-main/demo-wx-article/`
- 抓了 4 张图（`work/source/images.json` 显示 4 个 imageAspect：1.03/1.84/1.82/1.93）
- TTS 10 段（`work/audio/tts-segments/seg-{01..10}.mp3`）
- 字幕对齐 10 段（`work/captions/segments.json`）
- 抽帧 22 张（`work/audit-frames/f-*.png`）
- 渲染产物：`renders/{frame-030.png, preview-low.mp4, demo.mp4}`
- 经验沉淀：`work/lessons/LESSONS.md` 端到端跑通

### demo-wx-llm

- 路径：`d:/video-spec-builder-main/demo-wx-llm/`
- 抓了 27 张图（覆盖真实 WorkBuddy 培训文章）
- 12 scene 计划（`work/source/notes.md` 列出 12 beat）
- 渲染产物：`renders/{check-*.png, frame-030.png, preview-low.mp4, demo.mp4}`

✅ 真实文章 + 真实 TTS + 真实 Remotion 渲染均跑通。

---

## 4. 文档一致性检查

### 文档引用 vs 实际文件

| 文档路径 | 引用 | 实际 | 一致？ |
|---|---|---|---|
| `SKILL.md:35` | `scripts/scaffold_wechat_article_project.py` | 存在 | ✅ |
| `SKILL.md:53` | `scripts/fetch_article.py` | 存在 | ✅ |
| `SKILL.md:65` | `scripts/generate_tts.py` | 存在（2026-08-03 新增） | ✅ |
| `templates/.../README.md:39` | `scaffold_wechat_article_project.py` | 存在 | ✅ |
| `templates/.../README.md:47` | `../skills/wechat-article-remotion/scripts/fetch_article.py` | 存在 | ✅ |
| `templates/.../README.md:57` | `generate_tts.py` | 存在（2026-08-03 新增） | ✅ |
| `templates/.../PROJECT_BRIEF.md:14` | `scripts/generate_tts.py` | 存在 | ✅ |
| `templates/.../src/demoData.ts:7` | `scripts/generate_tts.py` | 存在 | ✅ |
| `templates/.../work/lessons/LESSONS.md:38` | 建议补 `align_captions.py` | 不存在 | ⚠️ 建议项 |
| `references/scene-types.md:134` | `scripts/fetch_article.py` | 存在 | ✅ |

**结论**：2026-08-03 修复了所有 4 处文档/脚本不一致（`scripts/generate_tts.py` 引用）。

### 模板 README vs SKILL.md

| 字段 | SKILL.md | template README.md |
|---|---|---|
| 视觉规范 | ✅ 完整 | ✅ 完整 |
| 场景类型 | ✅ 完整 | ✅ 完整 |
| 公共素材库 | ✅ 完整 | ✅ 完整 |
| 端到端 workflow | ✅ 完整 | ✅ 完整 |
| 硬规则 | ✅ 完整 | ✅ 完整 |
| 目录结构 | ❌ 未列 | ✅ 完整 |

差异无害（SKILL.md 是 Claude 加载的入口，template README.md 是脚手架生成后给用户看的）。

---

## 5. 改进项（按优先级）

### 高优先级（影响使用）

~~1. **补 `scripts/generate_tts_minimax.py`**（或 `generate_tts.py`）~~
   - ✅ **2026-08-03 已完成**：抽离并改进为 skill 级别官方实现
   - 修了哪 3 处文档：模板 README.md:55 / PROJECT_BRIEF.md:14 / demoData.ts:7（全部已修）
   - 同时补了 `scripts/generate_tts_edge_tts.py`（免费方案）+ `scripts/generate_tts.py`（统一入口）+ `requirements.txt` + `scripts/README.md`（脚本使用手册）

2. ~~**补 `scripts/align_captions.py`**~~
   - ✅ **2026-08-03 已完成**：`scripts/align_captions.py` 已补完
   - 功能：把 `work/captions/segments.json`（或 `--srt` 指定的 SRT）自动转成 `demoData.ts` 的 `captions[]` 数组 TS 代码片段
   - 特性：keyword accent 大小写不敏感；按中文标点 + 空格切分长段（每段 ≤ 14 字）；可选 `--out` 写文件 + `--print-totals` 统计
   - 端到端验证：`test-align-tmp/work/captions/segments.json`（3 段 31.56s / 176 字）跑通，输出 `captions-snippet.ts` 可直接贴入 `demoData.ts`

3. ~~**补 `requirements.txt`**~~ ✅ **2026-08-03 已完成**
   - `requests>=2.31,<3.0` / `Pillow>=10.0,<12.0` / `edge-tts>=6.1,<8.0`（注释行，按需取消）

### 中优先级（可观测性）

4. ~~**package.json 加 `engines` 字段**~~ ✅ **2026-08-03 已完成**
   ```json
   "engines": {
     "node": ">=20.0.0",
     "npm": ">=10.0.0"
   }
   ```
5. **`SKILL.md` 补"目录结构"小节**（参考 `template README.md`）

### 低优先级（未来增强）

6. ~~**`article-image-stack` 场景**：多图轮播 / 双联~~ ✅ **2026-08-03 已完成**
   - `sceneTypes.tsx` 加 `ArticleImageStackScene` 类型 + View 组件 + 样式 + SceneRouter 注册
   - 三种布局：`row`（左右双联） / `column`（上下双联） / `carousel`（轮播）
   - 轮播 transition：`crossfade` / `push` / `slide`
   - 铁律：每张图 `object-fit: contain` 永不裁切；`imageAspect` 决定 max-width 还是 max-height
   - 端到端验证：`test-align-tmp/test-sandbox/` 跑 `npm run typecheck` 0 错误
   - demoData.ts 加 row + carousel 两个示例场景（共 6 scene）
7. **国际化**：把 `RichText` 抽象成 `<T>` 组件
8. **Subagent 视觉审核脚本自动化**：当前是手动 prompt 抽帧
9. **ideaflow 降级方案**：备一个 wechat-article API（ideaflow 无 SLA）

---

## 6. 变更日志

### 2026-08-03

- 新建 `README.md`（项目主 README）
- 新建 `PROJECT_AUDIT.md`（本文档）
- 识别出 3 处文档/脚本不一致（`scripts/generate_tts.py` 引用）
- 验证 2 个 demo 端到端跑通
- 确认 9 个 Node 依赖 + 9 个字体 + 7 个 SFX 全部就位

### 2026-08-03（v2：抽离 TTS 工具链）

- 新建 `scripts/generate_tts.py` —— **统一入口**，`--engine {auto,minimax,edge-tts}`，自动探测 .env minimax 凭据
- 新建 `scripts/generate_tts_minimax.py` —— 从 `demo-wx-article/scripts/gen_tts_minimax.py` 抽离并改进
- 新建 `scripts/generate_tts_edge_tts.py` —— **edge-tts 免费方案**（无需 API key），带 `--list-voices`
- 新建 `requirements.txt` —— requests + Pillow + edge-tts（注释行，按需启用）
- 新建 `scripts/README.md` —— 三个脚本速查 + 详细用法
- 修复 4 处文档/脚本不一致：SKILL.md:65、模板 README.md:55、PROJECT_BRIEF.md:14、demoData.ts:7
- 端到端验证：在 `test-tts-tmp/` 跑通 3 段 TTS，生成 31.56s 配音 + segments.json

### 2026-08-03（v3：补完小尾巴）

- 新建 `scripts/align_captions.py` —— SRT / `segments.json` → `captions[]` TS 代码片段
   - keyword 大小写不敏感匹配（`MiniMax` ↔ `minimax`）
   - 中文标点优先切分；超 14 字按标点/空格兜底切；FIFO 顺序保证
   - 端到端验证：`test-align-tmp/` 3 段 31.56s / 176 字，输出顺序正确
- 修 `templates/remotion-project/package.json` —— 补 `engines.node>=20 / npm>=10`
- 修 `SKILL.md` —— 硬规则编号 6 重复 bug 修复（原 6 子项 + 6 共用 → 6/7/8）
- 同步文档过期项：
   - README.md: 56 行"字幕对齐工具"标 ✅；193 行"generate_tts.py 不存在"删除；280-298 行补 align_captions 用法
   - PROJECT_AUDIT.md（本文档）：第 2 项 align_captions 标 ✅，第 4 项 engines 标 ✅
   - LESSONS.md: 移除"建议补 align_captions"项，改记为已完成
- 验证 `tsconfig.json` 的 `types: ["node"]` —— Remotion 4.x 自动 inject @remotion/* 类型，**无需手动声明**（保留现状）

### 2026-08-03（v4：article-image-stack 场景）

- `templates/remotion-project/src/sceneTypes.tsx` 加第 7 种场景 `article-image-stack`：
   - `ImageStackSlot` 子类型 + `ArticleImageStackScene` 类型
   - `ImageStackSlotView` 子组件（行/列布局复用）+ `ArticleImageStackSceneView` 主组件
   - 三种布局：`row`（左右双联） / `column`（上下双联） / `carousel`（轮播）
   - 轮播 transition：`crossfade` / `push` / `slide`
   - 9 套新样式常量（`articleImageStackLayoutStyle` / `articleImageStackRowStyle` / `articleImageStackCarouselCaptionStyle` 等）
- `templates/remotion-project/src/demoData.ts` 加 row（before/after）+ carousel（3 张同点多图）两个示例场景，共 6 scene
- `references/scene-types.md` 加第 7 节 `article-image-stack`（数据模型 + 视觉 + 铁律 + 进场节奏 + 适用场景）
- `SKILL.md` 第 6 节「6 个场景类型」→「7 个场景类型」表格
- `README.md`：项目状态 + 场景表 + 动效词汇 + 6 场景表 + 已知问题都同步
- `templates/remotion-project/work/lessons/LESSONS.md` 移除"建议补 article-image-stack"项，改记为已完成
- 端到端验证：`test-align-tmp/test-sandbox/` 跑 `npm install` + `npm run typecheck` **0 错误**
