# 题库管理页与 E02_30 更新记录（2026-07-23）

## 页面设计审查

1. **导航与页头 — 良好**
   - 沿用现有墨绿色视觉体系，没有改变信息架构。
   - 侧栏主导航统一为 44px 高，分类项统一为 34px 高。
   - 页面标题、说明、身份信息的字号和行高重新分级，减少小字与基线不齐。

2. **生产文件与筛选工具 — 良好**
   - JSON、图片 ZIP、CSV、新增题目等操作统一使用 Lucide 图标，不再混用字符图标。
   - 主要按钮与筛选控件统一为 40px 高；图标统一为 17px，文字统一为 12–13px。
   - 搜索、视图切换、重置按钮使用一致的对齐和间距规则。

3. **题目审查卡片 — 良好**
   - 题号、题干、选项、解析的字号层级重新整理。
   - 编辑按钮扩大可点击区域并校正图标位置。
   - 保留小程序 375px 内容宽度，方便按实际显示尺寸审查图片和题目。

4. **可访问性 — 改善**
   - 为键盘焦点增加清晰的 `:focus-visible` 样式。
   - 提高主要控件高度和正文可读性。
   - 本次完成视觉与交互冒烟检查；不等同于完整的键盘、读屏器或 WCAG 合规认证。

## E02_30 图片校验

- 场景：夜间中国高速公路。
- 车道：左侧三条正常行车道，最右侧设置接近正常车道宽度的完整应急车道。
- 分隔：行车道与应急车道之间使用连续白色实线。
- 事故车：完全停在右侧应急车道内，开启危险报警闪光灯。
- 警示牌：位于事故车后方、来车方向一侧，通过强透视明确表现约 150 米距离；不得紧贴车辆或占用正常车道。
- 人员：转移至右侧护栏外，不在道路上停留。

生成工具：OpenAI 内置 ImageGen。

最终文件：`public/question-images-emergency-v2/e02-30-v3.jpeg`（1280×720，JPEG）。

## E02_30 生成提示词

```text
Use case: precise-object-edit
Asset type: Chinese driving-theory learning question cover image, 16:9 landscape
Input images: Image 1 is the current edit target and general photorealistic night-highway style reference.
Primary request: Rebuild the entire scene so it accurately teaches the correct response to a nighttime traffic accident on a Chinese expressway.
Scene/backdrop: A modern divided Chinese expressway at night, photographed from the approaching-traffic direction. Show three normal traffic lanes on the left, separated by dashed white lane markings, and a full-width hard shoulder/emergency lane on the extreme right. The emergency lane must be realistically wide, nearly the width of a normal lane, separated from the rightmost traffic lane by one continuous solid white edge line, with a metal guardrail on its right edge.
Subject and spatial logic: One disabled dark sedan is stopped completely inside the right emergency lane far ahead. Its red hazard lights flash clearly. A red reflective warning triangle stands in the same emergency lane approximately 150 meters behind the disabled car, toward approaching traffic. Make the separation unmistakably long through strong road perspective: the triangle is prominent in the near foreground and the disabled car is small and far ahead. The warning triangle must not be next to the vehicle and must not block a normal traffic lane. Two occupants have already moved beyond the right-side guardrail near the distant car, safely off the roadway.
Style/medium: highly photorealistic documentary road-safety photograph, natural camera exposure, realistic asphalt, reflectors and highway lighting.
Composition/framing: wide 16:9, eye-level approaching-driver viewpoint, clear depth from foreground warning triangle to distant disabled car. All lane boundaries and the full emergency-lane width remain visible.
Lighting/mood: nighttime expressway lighting, controlled headlight and hazard-light reflections, serious but non-graphic.
Constraints: preserve strict Chinese right-hand traffic road geometry; continuous solid edge line between traffic lane and emergency lane; only one disabled car; triangle approximately 150 meters behind car; people only beyond the right guardrail; no collision victims; no gore; no road blockage.
Avoid: narrow emergency shoulder, car straddling the solid line, triangle beside the car, triangle in a live travel lane, people standing on roadway, reversed traffic direction, extra crashed vehicles, police scene, floating objects, illegible road markings, text, numbers, labels, arrows, logos, watermarks.
```

## 验证结果

- TypeScript 类型检查通过。
- 生产构建通过。
- 图片导出清单重建成功：1922 张图片，压缩包预计约 116.6 MB。
- 在 1275×956 视口和 375px 小程序内容宽度下完成页面对比检查。
