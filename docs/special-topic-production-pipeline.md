# 专项题图片持续生产流程

## 目标

专项题图片采用“小批次、可恢复、先审核后接入”的生产方式。任务中断或 Codex 会话重启时，以持久清单为唯一进度依据，不依赖聊天历史或临时提示词文件。

## 数据分层

| 层级 | 路径 | 保存内容 | 保留策略 |
| --- | --- | --- | --- |
| 正式图片 | `public/question-images-topic-v2/` | 每题独立的 1280×720 JPEG | 永久保留并进入 Git |
| 生产清单 | `ops/special-topic-image-pipeline.json` | 题号、状态、题目指纹、来源和输出路径 | 永久保留并进入 Git |
| 当前批次 | `work/special-topic-current-batch.json` | 当前最多 8 题的完整提示词 | 下批覆盖，不进入 Git |
| 核对图 | `work/topic-refresh-2026-07-24/*-contact-sheet*.jpg` | 每分段当前核对拼图 | 每分段只保留最新版本，不进入 Git |

## 状态定义

- `pending`：尚未生成。
- `generated`：图片已落盘并通过文件、格式和尺寸检查，等待视觉审核。
- `approved`：逐题核对内容后通过。
- `redo`：视觉审核未通过，进入下一次重做队列。
- `review_required`：题干、答案或详细解析发生变化，需要重新核对。

## 固定批次

- 默认每批 8 题。
- 一次只生成一个批次，不把全部 236 条长提示词载入任务上下文。
- 所有图片统一遵循 [`docs/image-review-standards.md`](image-review-standards.md)：主题必须是画面最显著内容，并通过约 360px 宽的手机预览测试。
- 每批顺序：
  1. 从清单提取 `pending` 或 `redo`。
  2. 逐题生成并保存到固定路径。
  3. 校验 JPEG 格式及 1280×720 尺寸。
  4. 标记为 `generated`。
  5. 制作滚动核对图并逐题对照题干、答案、原图。
  6. 通过的标记为 `approved`，问题图标记为 `redo`。
  7. 提交该批正式图片与清单。

## 恢复与操作命令

使用工作区自带的 Python（包含 Pillow）：

```bash
PYTHON_BIN=/Users/ninosphere666/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3

$PYTHON_BIN scripts/manage_special_topic_pipeline.py sync
$PYTHON_BIN scripts/manage_special_topic_pipeline.py summary
$PYTHON_BIN scripts/manage_special_topic_pipeline.py next --section T04 --limit 8
$PYTHON_BIN scripts/manage_special_topic_pipeline.py validate T04_17 T04_18
$PYTHON_BIN scripts/manage_special_topic_pipeline.py mark generated T04_17 T04_18
$PYTHON_BIN scripts/manage_special_topic_pipeline.py mark approved T04_17 T04_18
$PYTHON_BIN scripts/manage_special_topic_pipeline.py mark redo T04_18 --note "标志方向错误"
```

恢复任务时先运行 `summary`，再运行 `next`。不读取旧聊天记录、不重新生成已标记为 `approved` 的题目。

## 数据安全

- 正式题库 `app/question-bank.json` 只在 T04、T05 全部分段通过后统一切换图片路径。
- 生成完成但未审核的文件不会自动成为正式题库引用。
- 每道题使用独立文件名，防止不同题目因旧图复用而串题。
- 题目指纹变化会把已通过项目自动改为 `review_required`。
- 临时提示词和核对图不进入 Git，避免仓库历史膨胀。

## 被替换旧图归档

正式题库完成路径切换后运行：

```bash
$PYTHON_BIN scripts/archive_replaced_topic_images.py
$PYTHON_BIN scripts/archive_replaced_topic_images.py --apply
```

默认归档到工作区本地 `题库图片/旧图/专项题型类-T/`，并生成 `archive-index.json`，记录旧图、新图、题号和 SHA-256。该目录位于站点项目外，不进入 Git、网站构建产物或线上服务器。

- 已无题目引用的旧图会移动到归档目录。
- 仍被其他分类引用的共享旧图只复制归档，不移动源文件，避免破坏其他题目。
- 可通过 `--destination` 指向用户指定的其他题库图片文件夹。
