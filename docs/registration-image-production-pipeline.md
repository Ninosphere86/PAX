# 登记管理类图片生产流程

登记管理类-M 共 54 道题，按 M01、M02、M03 三个分段持续生产。流程使用持久清单记录每题状态，避免图片生成历史无序膨胀。

## 核心文件

- 生产脚本：`scripts/manage_registration_pipeline.py`
- 持久清单：`ops/registration-image-pipeline.json`
- 当前批次：`work/registration-current-batch.json`
- 批次总览：`work/registration-review-<首题号>-<末题号>.jpg`
- 新图目录：`public/question-images-registration-v2/`
- 旧图归档：工作区本地 `题库图片/旧图/登记管理类-M/`（位于站点项目外）

## 状态

- `pending`：等待生产
- `generated`：图片已生成，等待核对
- `approved`：已核对，可更新题库
- `redo`：审图发现问题，需要重做
- `review_required`：题目内容发生变化，需要重新核对

## 常用命令

```bash
python scripts/manage_registration_pipeline.py sync
python scripts/manage_registration_pipeline.py summary
python scripts/manage_registration_pipeline.py next --section M01 --limit 6
python scripts/manage_registration_pipeline.py validate M01_01 M01_02
python scripts/manage_registration_pipeline.py mark generated M01_01 M01_02
python scripts/manage_registration_pipeline.py mark approved M01_01 M01_02
python scripts/manage_registration_pipeline.py mark redo M01_02 --note "警告标志距离不准确"
python scripts/manage_registration_pipeline.py apply
python scripts/manage_registration_pipeline.py archive
python scripts/manage_registration_pipeline.py archive --apply
```

## 审图协作

每批图片完成后，`finalize_registration_batch.py` 会自动生成三列总览图。总览图直接在 Codex 对话中提供，不在题库页面增加审图功能。

审图统一遵循 [`docs/image-review-standards.md`](image-review-standards.md)。重点先检查主题是否是画面最显著内容，再检查约 360px 宽的手机预览；任何必须放大才能看清的答题或判断依据都不能通过。

反馈时只需按总览图中的题号说明，例如：

```text
M01_02：警告标志距离看起来不足 150 米
M01_05：车辆被盗抢的场景还不够明确
```

需要修改的题目在生产清单中标记为 `redo`，重做后重新生成该批次总览图。

旧图只保存在工作区本地 `题库图片/旧图/`，不进入 Git、网站构建产物或线上服务器。
