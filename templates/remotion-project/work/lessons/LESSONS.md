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
