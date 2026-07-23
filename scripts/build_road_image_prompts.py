#!/usr/bin/env python3
"""Create grouped, question-grounded prompts for the road-traffic image refresh."""

from __future__ import annotations

import argparse
import json
import re
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "question-bank.json"
OUTPUT = ROOT / "work" / "road-image-prompts.json"

SECTION_SCENES = {
    "R01": "expressway lane-specific minimum and maximum speeds",
    "R02": "ordinary-road speed limits and low-speed hazard locations",
    "R04": "new-driver probation rules, accompanying drivers, and probation signs",
    "R06": "safe overtaking, yielding to overtaking traffic, and prohibited overtaking locations",
    "R09": "roads without center lines or separated lanes",
    "R10": "congested roads, zipper merging, queues, and lane reductions",
    "R11": "priority, courtesy, pedestrian protection, and yielding to emergency vehicles",
    "R12": "safe lane changes, turn signals, blind spots, and maintaining distance",
}


def answer_text(question: dict) -> str:
    keys = [key for key in question.get("answer", "") if key in "ABCD"]
    labels = [question.get("options", {}).get(key, "") for key in keys]
    return "；".join(label for label in labels if label)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Replace every road-traffic-category image reference with the generated v2 asset.",
    )
    return parser.parse_args()


def group_key(item: dict) -> str:
    # Keep one asset per question. Some legacy rows reuse the same source image
    # despite testing incompatible lane counts or maneuvers, so grouping by the
    # old image would preserve the very ambiguity this refresh is meant to fix.
    return item["code"]


def main() -> None:
    args = parse_args()
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))
    road = [item for item in questions if item.get("category") == "道路通行类-R"]
    groups: OrderedDict[str, list[dict]] = OrderedDict()
    for item in road:
        groups.setdefault(group_key(item), []).append(item)

    payload = []
    for index, (key, items) in enumerate(groups.items(), start=1):
        first = items[0]
        source_image = first.get("image", "")
        lesson_lines = []
        for item in items:
            lesson_lines.append(
                f'- {item["code"]}｜题目：{item["title"]}｜正确答案含义：{answer_text(item)}｜核对要点：{item.get("explanation", "")}'
            )

        evidence_text = "".join(
            item.get("title", "") + answer_text(item) + item.get("explanation", "")
            for item in items
        )
        labels_needed = any(token in evidence_text for token in ["红车", "白车", "蓝车", "A车", "B车", "甲车", "乙车"])
        traffic_control_needed = any(
            token in evidence_text
            for token in ["标志", "标线", "信号灯", "人行横道", "停止线", "铁路道口", "限速", "速度", "车速", "公里", "时速"]
        )
        answer_evidence = "".join(answer_text(item) for item in items)
        required_numbers = list(dict.fromkeys(re.findall(r"\d+", answer_evidence)))
        if not required_numbers:
            required_numbers = list(
                dict.fromkeys(
                    re.findall(
                        r"\d+(?!\s*(?:道|车道|条))",
                        "".join(item.get("title", "") for item in items),
                    )
                )
            )

        input_line = (
            "Input images: Image 1 is a road-geometry and factual-content reference only; create a new independent image rather than retouching or copying it."
            if source_image
            else "Input images: none; construct the scene solely from the verified question and answer details below."
        )
        prompt = f"""Use case: photorealistic-natural
Asset type: 16:9 landscape educational cover image for a Chinese driving-theory mini program
{input_line}
Primary request: Create one new realistic road-safety learning image that makes the correct driving rule or the exact judged hazard immediately understandable.
Scene family: {SECTION_SCENES[first['section']]}.
Questions sharing this scene:
{chr(10).join(lesson_lines)}
Style/medium: documentary-grade photorealistic traffic photography in a modern Chinese road environment, realistic vehicles and people, natural proportions and materials.
Composition/framing: one coherent 16:9 scene, not a collage; preserve the test-critical vehicle count, vehicle direction, maneuver, lane geometry, right-of-way relationship, road markings, people, traffic-control state, and camera direction. Keep the essential evidence large and readable at 375px mini-program width.
Teaching interpretation: visualize the legally correct situation or the exact hazardous situation being judged. For false statements, show the evidence that makes the statement false without visually endorsing the prohibited behavior.
Road accuracy: Chinese right-hand traffic; realistic full-width lanes; correct solid and dashed markings; vehicles remain inside their intended lanes unless the question specifically judges a lane-crossing maneuver.
Constraints: no brand logos, no watermark, no decorative title, no UI graphics, no invented vehicles or people, no gore, no cinematic crash effects, no contradictory actions."""
        if labels_needed:
            prompt += "\nVehicle identity: keep the referenced vehicle colors exact and visually unambiguous; add A/B markers only when the question itself requires A/B identification, with no other text."
        else:
            prompt += "\nText: no captions, arrows, labels, floating numbers, or explanatory overlays."
        if traffic_control_needed:
            prompt += "\nTraffic-control accuracy: reproduce only the test-critical Chinese sign, signal, crossing, speed marking, or lane marking; keep its symbol, color, direction, and active state accurate and legible."
        if required_numbers and any(token in evidence_text for token in ["限速", "速度", "车速", "公里", "时速"]):
            prompt += (
                "\nSpeed-sign accuracy: show the exact test-critical numerals "
                + ", ".join(required_numbers)
                + ". Use a standard red-ring sign for a maximum speed and a standard blue circular sign for a minimum speed. Position lane-specific signs directly above or beside the correct lane; do not add any conflicting numbers."
            )
        if "同方向两条机动车道" in evidence_text or "两车道" in evidence_text:
            prompt += "\nLane-count invariant: show exactly TWO travel lanes in this direction, separated by exactly ONE dashed white divider; the right shoulder is not a travel lane. Do not show a third travel lane."
        if "同方向三条机动车道" in evidence_text:
            prompt += "\nLane-count invariant: show exactly THREE travel lanes in this direction, separated by exactly TWO dashed white dividers; the right shoulder is not a travel lane."
        if first["section"] == "R01" and len(required_numbers) == 2:
            prompt += "\nLane-range sign placement: show exactly TWO speed signs total—the blue minimum-speed sign and red-ring maximum-speed sign—as one close paired set directly above the single lane tested in the question. Do not show any speed sign or number above another lane."
        if first["section"] == "R01" and len(required_numbers) == 1:
            sign_kind = "blue circular minimum-speed"
            if "蓝底" in evidence_text or "最低" in evidence_text or "不能低于" in evidence_text:
                sign_kind = "blue circular minimum-speed"
            elif "红圈" in evidence_text or "最高" in evidence_text or "不能超过" in evidence_text:
                sign_kind = "red-ring maximum-speed"
            prompt += (
                "\nSingle-sign invariant: show exactly ONE speed sign total, a "
                + sign_kind
                + " sign with the exact number "
                + required_numbers[0]
                + ", positioned over the lane or road tested. Do not show any other speed sign, arrow, or number."
            )
        if first["section"] == "R01" and ("左侧车道" in evidence_text or "左道" in evidence_text or "最左侧" in evidence_text):
            prompt += "\nTarget-lane invariant: the tested vehicle and any lane-specific speed sign must be clearly aligned with the far-left travel lane in the driving direction."
        if first["section"] == "R01" and ("中间车道" in evidence_text or "中道" in evidence_text):
            prompt += "\nTarget-lane invariant: the tested vehicle and any lane-specific speed sign must be clearly aligned with the middle travel lane."
        if first["section"] == "R01" and ("右侧车道" in evidence_text or "右道" in evidence_text):
            prompt += "\nTarget-lane invariant: the tested vehicle and any lane-specific speed sign must be clearly aligned with the far-right travel lane; do not count the shoulder as a lane."
        if "仅凭感觉确认车速" in evidence_text:
            prompt += "\nInstrument-check invariant: use an interior driver viewpoint with the real dashboard speedometer clearly visible and the driver deliberately checking it. Do not use roadside speed signs or overhead gantries; the teaching point is that actual speed must be read from the instrument, not guessed by feeling."

        filename = f"{first['code'].lower().replace('_', '-')}-v2.jpeg"
        payload.append(
            {
                "group": index,
                "codes": [item["code"] for item in items],
                "section": first["section"],
                "sourceImage": source_image,
                "sourcePath": str(ROOT / "public" / source_image.lstrip("/")) if source_image else None,
                "outputImage": f"/question-images-road-v2/{filename}",
                "outputPath": str(ROOT / "public" / "question-images-road-v2" / filename),
                "prompt": prompt,
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload)} grouped prompts for {len(road)} questions to {OUTPUT.relative_to(ROOT)}")

    if args.apply:
        replacement_by_code = {
            code: group["outputImage"]
            for group in payload
            for code in group["codes"]
        }
        missing = [item["code"] for item in road if item["code"] not in replacement_by_code]
        if missing:
            raise RuntimeError(f"Missing generated-image mapping for: {', '.join(missing)}")

        missing_files = [
            group["outputPath"]
            for group in payload
            if not Path(group["outputPath"]).is_file()
        ]
        if missing_files:
            raise RuntimeError("Generated images are missing:\n" + "\n".join(missing_files))

        updated = 0
        for item in questions:
            if item.get("category") != "道路通行类-R":
                continue
            item["image"] = replacement_by_code[item["code"]]
            item["updatedAt"] = "2026-07-23"
            updated += 1

        SOURCE.write_text(
            json.dumps(questions, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Applied {updated} road-traffic image references to {SOURCE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
