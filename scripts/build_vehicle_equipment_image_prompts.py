#!/usr/bin/env python3
"""Create source-grounded prompts for the vehicle-equipment image refresh."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "question-bank.json"
OUTPUT = ROOT / "work" / "vehicle-equipment-image-prompts.json"
IMAGE_DIR = ROOT / "public" / "question-images-vehicle-v2"

SPECIAL_NOTES = {
    "V02_07": "Turn-stalk invariant: the stalk is physically pushed UP and only the vehicle's RIGHT green turn-arrow indicator is illuminated. The left arrow must be dark. Never illuminate both arrows.",
    "V02_08": "Turn-stalk invariant: the stalk is physically pulled DOWN and only the vehicle's LEFT green turn-arrow indicator is illuminated. The right arrow must be dark. Never illuminate both arrows.",
    "V02_10": "Head-restraint invariant: show a seated driver in side profile with the head restraint correctly positioned directly behind the back of the head and upper neck. Make the head/head-restraint alignment large and obvious; do not show empty seats.",
    "V02_22": "Pedal-target invariant: show exactly three manual-transmission pedals in the standard left-to-right order—clutch, brake, accelerator. Keep all three visible, but mark only the LEFTMOST clutch pedal with one clean cyan question-circle or subtle cyan outline so the learner knows which pedal is being asked about.",
    "V02_23": "Pedal-target invariant: show exactly three manual-transmission pedals in the standard left-to-right order—clutch, brake, accelerator. Keep all three visible, but mark only the MIDDLE brake pedal with one clean cyan question-circle or subtle cyan outline.",
    "V02_24": "Pedal-target invariant: show exactly three manual-transmission pedals in the standard left-to-right order—clutch, brake, accelerator. Keep all three visible, but mark only the RIGHTMOST narrow accelerator pedal with one clean cyan question-circle or subtle cyan outline.",
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
        help="Replace all vehicle-equipment image references with the generated v2 assets.",
    )
    return parser.parse_args()


def section_prompt(section: str, evidence: str) -> str:
    if section == "V01":
        if "指示灯" in evidence or "仪表板" in evidence:
            return """Asset treatment: a realistic modern instrument-cluster close-up. Recreate the exact ABS warning pictogram from the reference at large readable size, preserving its letters, circle/bracket geometry, color, and illuminated state. Do not add other warning lights."""
        return """Asset treatment: one coherent semi-realistic overhead automotive cutaway showing the ABS hydraulic control path, brake system, and all four wheels on one passenger car. Preserve the source's factual component relationships while making the ABS function easier to understand. No exploded collage and no text labels."""
    if section == "V02":
        if any(token in evidence for token in ["头枕", "安全气囊", "安全带", "驾驶人"]):
            return """Asset treatment: a photorealistic vehicle-cabin safety demonstration. Make the exact tested restraint, head restraint, airbag, or belt fit visually dominant and anatomically correct. Preserve the person's seating position, device placement, and protected body area from the reference."""
        return """Asset treatment: a photorealistic close-up of the exact vehicle control, switch, stalk, pedal, lever, ignition position, window control, or defroster control shown in the reference. Preserve the part's orientation, number of pedals/buttons, icon geometry, and selected position exactly; do not substitute a different control."""
    if section == "V03":
        return """Asset treatment: a clean high-resolution modern dashboard or instrument-cluster close-up. The tested pictogram, gauge, needle, numeral, color, illuminated state, door/hood state, or multi-choice icon panel must match the source exactly. Treat the source as a strict factual template, not loose inspiration. Do not redraw a different symbol and do not add unrelated warning lights."""
    return """Asset treatment: documentary-grade photorealistic Chinese driving scene showing the exact lamp, signal, horn, weather, vehicle relationship, or visibility condition being tested. Headlamp beam type, fog lamps, hazard lights, turn-signal side, front/rear lamps, vehicle direction, following/oncoming relationship, and road geometry must be physically correct."""


def main() -> None:
    args = parse_args()
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))
    vehicle = [item for item in questions if item.get("category") == "车辆设备类-V"]

    groups: OrderedDict[str, list[dict]] = OrderedDict()
    for item in vehicle:
        source_image = item.get("image", "")
        key = source_image or item["code"]
        groups.setdefault(key, []).append(item)

    payload = []
    for index, (_, items) in enumerate(groups.items(), start=1):
        first = items[0]
        source_image = first.get("image", "")
        evidence = "".join(
            item.get("title", "")
            + answer_text(item)
            + item.get("explanation", "")
            for item in items
        )
        lesson_lines = [
            f'- {item["code"]}｜题目：{item["title"]}｜正确答案含义：{answer_text(item)}｜核对要点：{item.get("explanation", "")}'
            for item in items
        ]
        prompt = f"""Use case: photorealistic-natural
Asset type: 16:9 landscape educational image for a Chinese driving-theory mini program
Input images: Image 1 is the strict factual reference for the tested equipment, icon, control, gauge, vehicle relationship, and light state. Create a new polished image while preserving every test-critical fact.
Primary request: Rebuild this vehicle-equipment learning image at high clarity so a learner can identify the tested device or rule immediately at 375px mini-program width.
Section: {first["section"]}.
Questions sharing this exact source:
{chr(10).join(lesson_lines)}
{section_prompt(first["section"], evidence)}
Accuracy hierarchy: first preserve the exact tested symbol/control/device and its active state; then preserve vehicle/person direction and geometry; only then improve realism, lighting, materials, and composition.
Composition: one coherent 16:9 image, not a collage, unless the source itself is a multi-choice panel. Keep the test-critical subject large, centered, unobstructed, and readable.
Reference fidelity: do not mirror the source, swap left/right, change a switch position, change a pedal count, move a gauge needle, replace an icon, reverse an arrow, change a light color, or invent a person/vehicle.
Teaching interpretation: for true/false questions, preserve the referenced equipment state itself; do not add a caption that reveals the answer. For behavioral scenes, visualize the legally correct evidence without glamorizing unsafe behavior.
Text constraints: no decorative title, explanation, watermark, brand logo, floating arrow, or added number."""
        if first["section"] == "V03" and any(
            token in evidence for token in ["哪个", "以下哪个", "图中哪个"]
        ):
            prompt += """
Multi-choice fidelity: the source is a choice panel. Preserve every displayed choice, its label, order, icon, and color exactly. Do not omit, relabel, merge, or rearrange choices, and do not visually highlight the correct answer.
Multi-choice label fidelity: preserve the source's label system literally. If the source uses “图1/图2/图3/图4”, keep those exact Chinese labels; if it uses A/B/C/D, keep A/B/C/D. Never convert between the two systems."""
        if "左转向灯" in evidence or "向左" in evidence:
            prompt += """
Left/right invariant: the tested left turn signal is on the vehicle's physical LEFT side. Do not mirror it."""
        if "右转向灯" in evidence or "向右" in evidence:
            prompt += """
Left/right invariant: the tested right turn signal is on the vehicle's physical RIGHT side. Do not mirror it."""
        if "前雾灯" in evidence and "后雾灯" not in evidence:
            prompt += """
Fog-lamp invariant: preserve the standard FRONT fog-lamp symbol orientation and green indicator color when illuminated; do not substitute the rear fog-lamp symbol."""
        if "后雾灯" in evidence and "前雾灯" not in evidence:
            prompt += """
Fog-lamp invariant: preserve the standard REAR fog-lamp symbol orientation and amber indicator color when illuminated; do not substitute the front fog-lamp symbol."""
        if "危险报警闪光灯" in evidence:
            prompt += """
Hazard-light invariant: show both left and right amber indicators flashing simultaneously, never a one-sided turn signal."""
        if "150米" in evidence:
            prompt += """
Meeting-light invariant: show opposing vehicles at a long safe approach distance and both using dipped low beams; never show dazzling high beams."""
        if first["code"] in SPECIAL_NOTES:
            prompt += "\n" + SPECIAL_NOTES[first["code"]]

        filename = f"{first['code'].lower().replace('_', '-')}-v2.jpeg"
        payload.append(
            {
                "group": index,
                "codes": [item["code"] for item in items],
                "section": first["section"],
                "sourceImage": source_image,
                "sourcePath": str(ROOT / "public" / source_image.lstrip("/")),
                "outputImage": f"/question-images-vehicle-v2/{filename}",
                "outputPath": str(IMAGE_DIR / filename),
                "prompt": prompt,
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(payload)} grouped prompts for {len(vehicle)} questions to "
        f"{OUTPUT.relative_to(ROOT)}"
    )

    if args.apply:
        replacement_by_code = {
            code: group["outputImage"]
            for group in payload
            for code in group["codes"]
        }
        missing_files = [
            group["outputPath"]
            for group in payload
            if not Path(group["outputPath"]).is_file()
        ]
        if missing_files:
            raise RuntimeError(
                "Generated vehicle-equipment images are missing:\n"
                + "\n".join(missing_files)
            )

        updated = 0
        for item in questions:
            if item.get("category") != "车辆设备类-V":
                continue
            item["image"] = replacement_by_code[item["code"]]
            item["updatedAt"] = "2026-07-23"
            updated += 1

        SOURCE.write_text(
            json.dumps(questions, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(
            f"Applied {updated} vehicle-equipment image references to "
            f"{SOURCE.relative_to(ROOT)}"
        )


if __name__ == "__main__":
    main()
