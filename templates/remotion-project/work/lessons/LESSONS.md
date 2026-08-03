# WeChat Article Remotion — 经验沉淀

## 端到端跑通

- 脚手架能正常从 talking-head-remotion 公共库播种字体（Noto Sans SC / Space Grotesk）和 SFX（7 个 mp3）
- `npm install` 一次成功（187 包）
- `npm run typecheck` 零错误（修了 1 个 import 转发的坑）
- `npm run still` cover 场景和 article-image 场景都成功渲染

## 关键修复

### `ArticleVideoProps` import 转发

最初 demoData.ts 和 Root.tsx 从 `./ArticleVideo` import `ArticleVideoProps`，但实际定义在 `./sceneTypes.tsx`。两种修法：
1. 从 ArticleVideo 转发导出 → 选这个，因为外部 import 路径统一
2. 改 import 路径 → 散在多处，外部要分别知道从哪 import

**结论**：组件文件应该 re-export 它用到的公共类型，外部只 import 一次。

## 铁律验证

- ✅ article-image 场景 `object-fit: contain` —— 1200×800 demo 图按比例完整显示，未裁切
- ✅ 图源标签在右下角 + 呼吸动效
- ✅ 主画面元素 ≤ 5（eyebrow + 标题 + 图 + caption + 图源）
- ✅ 顶栏章节进度、底部无底色字幕
- ✅ 无 PIP —— 主舞台完全给图片

## 演示数据

- 默认 demoProject 包含 4 个 scene：cover / article-image / list / outro
- article-image 场景用 `img-01.jpg`（占位 1200×800）
- 用户实际使用时只需替换 demoData.ts 即可

## 后续改进方向

1. **真实文章跑通**：当前只验证了骨架，没有跑通真实公众号 URL（ideaflow API 需要外网）
2. **国际化**：按 user_profile 偏好先不做；如果要做，建议把 `RichText` 抽象成 `<T>` 组件支持多语言 fallback

## 字幕对齐工具（2026-08-03 补完）

✅ `scripts/align_captions.py` 已补完：

- 输入：`work/captions/segments.json`（默认）或 `--srt` 指定的 ASR 对齐 SRT
- 输出：可直接贴入 `demoData.ts` 的 `captions: [...]` 块 TS 代码
- 切分：中文标点优先，超 14 字按标点/空格兜底切
- accent：keyword 大小写不敏感，传 `MiniMax` 也能命中 `minimax` / `MINIMAX`
- 端到端验证：`test-align-tmp/work/captions/segments.json`（3 段 31.56s）跑通

## article-image-stack 场景（2026-08-03 补完）

✅ `templates/remotion-project/src/sceneTypes.tsx` 加了第 7 种场景：

- 三种布局：`row`（左右双联） / `column`（上下双联） / `carousel`（轮播）
- 铁律：每张图 `object-fit: contain`，永不裁切（与 article-image 保持一致）
- 轮播 transition：`crossfade`（淡入淡出） / `push`（推入） / `slide`（水平滑入）
- typecheck 端到端验证：`test-align-tmp/test-sandbox/` 跑通 `npm run typecheck` 0 错误
- demoData.ts 加 row + carousel 两个示例场景（共 6 scene）

**适用场景**：
- `row` —— before/after 对比截图
- `column` —— 步骤前后 / 时间线
- `carousel` —— 同景点多细节图（每张 2.5s 默认）

## ★★★ 图文映射 + 音画对应（2026-08-03 经验沉淀）

### 事故一：图文错位

`广东十大姓氏` 项目中，视频里图片全部和文字错位——陈姓段落显示黄姓的图，依次错位。根因是 `extract_image_captions()` 向图片**后**扫描，而公众号文章图片说明行在图片**前**。

### 事故二：音画不同步

同项目中，画面显示陈姓+珠玑古巷，但音频在念"黄姓位居第二"——因为音频 11 段里没有单独讲陈姓的段落，而 demoData.ts 在该时间段配了陈姓场景。

### 沉淀的通用规则

**图文映射**（已写进 fetch_article.py + SKILL.md + beat-checklist.md）：
- 公众号文章常见结构是「一段介绍 + 一张配图」，图片属于其**前面紧邻**的段落
- `fetch_article.py` 向上扫描，遇到前一张图片行时**跳过**（不 break），保证多图共享同一段落
- 图文**不要求一一对应**：某段没配图就不硬配图，用 list / stat 等非图片场景；某段有多张图就用轮播

**音画对应**（已写进 beat-checklist.md 步骤 5 自检）：
- 场景内容必须与该时间段的口播内容一致——音频在念"黄姓"，画面就得是黄姓，不能配陈姓的图
- 拆稿后逐段核对：音频段落[i] 讲的主题 ↔ 场景[i] 显示的主题 是否匹配
- 如果某张图对应的主题在音频里没有单独口播，要么补一段口播，要么不用那张图

## ★★★ 竖屏画幅（2026-08-03 经验沉淀）

### 默认画幅改为竖屏

公众号图文视频适配抖音/小红书/视频号，默认画幅改为 **1080×1920 竖屏**（不再是 1920×1080 横屏）。

### article-image 竖屏布局

竖屏画布下，article-image 场景采用**标题在上 → 图片居中 → caption 在下**的三段式布局：
- **上方**：eyebrow + title（flexShrink: 0，固定高度）
- **中间**：图片 `flex: 1` 占满剩余空间，`object-fit: contain` 铁律不变
- **下方**：caption（flexShrink: 0，固定高度）
- 竖版图（如 1080×1350）几乎占满全高，效果极佳

### layout 参数适配

竖屏 safe 区域（1080×1920）：
- `safeTop: 160`（横屏 196）
- `safeX: 80`（横屏 120）
- `safeBottom: 140`（横屏 180）
- `captionBottom: 100`（横屏 88，竖屏字幕区稍大）
- `topbarHeight: 60`（横屏 68）

### 注意事项

- 用户说"竖屏"就是**改画布尺寸** 1080×1920，不是在横屏里调整 CSS 布局
- 不要在图片上叠加标题/文字（会互相遮挡，难看）
- 竖屏空间充足，标题在上、图片居中、caption 在下，三段式分开摆放
