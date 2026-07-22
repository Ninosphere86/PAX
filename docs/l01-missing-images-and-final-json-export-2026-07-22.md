# 科四灯光类缺图补全与最终 JSON 导出

日期：2026-07-22

## 完成内容

- 为科四灯光类-L中原先缺图的 97 道题补齐图片，最终 L 类 127/127 道题均有配图。
- 图片统一为 1280×720 WebP，写实中国道路摄影风格，适合 375px 小程序内容宽度检查。
- 新增“一键导出最终 JSON”按钮，下载文件名固定为 `QuestionBank.json`。
- 最终 JSON 与用户提供的样例保持相同顶层结构：`题库`、`公共解析库`。

## ImageGen 模式

使用 Codex 内置 ImageGen（built-in tool mode），两张用户提供的真实道路照片作为风格参考。每道缺图题单独生成一张图片，没有用一张通用图批量替代。

## 主提示词模板

```text
Use case: photorealistic-natural
Asset type: Chinese driving-theory learning thumbnail, <题目编号>
Primary request: create one memorable realistic road photograph that accurately teaches this question: “<题干>”
Correct answer/action: “<正确选项文本>”
Rule to visualize: <题目详解>
Scene/backdrop: realistic Chinese road environment appropriate to the exact weather, time, intersection, tunnel, bridge, highway, mountain road or emergency named in the question.
Subject: show the exact number and type of people and vehicles named in the question. Make the correct vehicle, direction of travel, road position and lamp state visually unambiguous. If the statement describes an incorrect behavior, depict the proper safe behavior instead.
Style/medium: photorealistic candid road photograph matching the reference images.
Composition/framing: clear 16:9 landscape; decisive vehicle action and lamp state readable at mobile-card size; accurate lane geometry; one coherent scene.
Constraints: lamps on the physically correct side and direction; both amber indicators for hazard lights; low beam must not look like dazzling high beam; correct lanes and stopping positions; no text, labels, arrows, split screen, logos, watermark, malformed markings or impossible placement.
```

## 总览检查与定向重做

生成后以 127 张缩略图总览逐页检查。以下图片因初稿存在方向、画面结构或距离表达问题，使用更严格的场景提示重新生成：

- `L01_018`：改为车辆从白天进入隧道，正面可见近光灯已开启。
- `L01_020`：删除拼贴结构，改为一个连续路口内展示转向灯使用场景。
- `L01_107`：删除交通信号灯，明确为无信号灯控制的夜间交叉路口。
- `L01_124`：删除局部圆形插图，改为一个连续驾驶室画面展示握稳方向、低挡、驻车制动和危险报警灯。
- `L01_126`：拉开警告三角牌与故障车的纵深距离，车辆完整停在应急车道并开启警示灯。

## 最终 JSON 字段映射

- `code` → `题目ID`
- `title` → `题目内容.文本`
- 题图按题目编号输出文件名 → `题目内容.图片`
- `explanation` → `题目内容.简析`
- `type` → `题目类型`（单选、多选、简答）
- `options` 与 `answer` → `题目选项[].文本`、`题目选项[].是否正确`
- `detailedExplanation` → `题目详解`
- 每题 `题目解析库` 及顶层 `公共解析库` 当前输出为空数组
