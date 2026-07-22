#!/usr/bin/env python3
"""Create grouped, question-grounded prompts for the emergency image refresh."""

from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "question-bank.json"
OUTPUT = ROOT / "work" / "emergency-image-prompts.json"

SECTION_SCENES = {
    "E01": "Chinese expressway breakdown and emergency-lane safety",
    "E02": "Chinese urban or intercity road traffic-accident handling",
    "E03": "Chinese road collision geometry and accident responsibility",
    "E04": "roadside rescue, injured-person assistance, and safe waiting positions",
    "E05": "adverse weather and intersection hazard management",
    "E06": "special road sections, water crossings, slopes, bridges, tunnels, parking, and prohibited maneuvers",
    "E07": "Chinese railway crossings, warning signals, and safe crossing behavior",
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
        help="Replace every emergency-category image reference with the generated v2 asset.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))
    emergency = [item for item in questions if item.get("category") == "应急处理类-E"]
    groups: OrderedDict[str, list[dict]] = OrderedDict()
    for item in emergency:
        groups.setdefault(item["image"], []).append(item)

    payload = []
    for index, (source_image, items) in enumerate(groups.items(), start=1):
        first = items[0]
        lesson_lines = []
        for item in items:
            lesson_lines.append(
                f'- {item["code"]}｜题目：{item["title"]}｜正确答案含义：{answer_text(item)}｜核对要点：{item.get("explanation", "")}'
            )
        labels_needed = any(
            token in "".join(
                [
                    item.get("title", ""),
                    answer_text(item),
                    item.get("explanation", ""),
                ]
            )
            for item in items
            for token in ["A车", "B车", "A 车", "B 车"]
        )
        signal_needed = any(word in "".join(item["title"] for item in items) for word in ["标志", "信号灯", "红灯", "铁路道口"])
        prompt = f"""Use case: photorealistic-natural
Asset type: 16:9 landscape educational cover image for a Chinese driving-theory mini program
Input images: Image 1 is a content and road-geometry reference only; create a new independent image rather than retouching or copying it.
Primary request: Rebuild the referenced driving scene as a new, highly realistic educational photograph that makes the correct safety or liability point visually understandable.
Scene family: {SECTION_SCENES[first['section']]}.
Questions sharing this scene:
{chr(10).join(lesson_lines)}
Style/medium: documentary-grade photorealistic road photography, modern Chinese road environment, real people and vehicles, realistic materials and natural proportions.
Composition/framing: one coherent 16:9 scene, not a collage; preserve the reference image's test-critical vehicle count, people, maneuver, lane geometry, signal state, warning equipment, relative positions, and camera direction; keep all essential evidence readable at 375px mini-program width.
Safety interpretation: visualize the legally correct situation or the exact hazardous situation being judged. Do not accidentally depict a prohibited action as safe. When the question says a statement is false, show the visual evidence that makes it false.
Constraints: accurate right-hand traffic, accurate lane width and markings, no brand logos, no watermark, no decorative caption, no invented vehicles or people, no gore, no dramatic movie effects."""
        if labels_needed:
            prompt += "\nVehicle labels: add only simple, large, unambiguous A and B markers above the correct vehicles; no other text."
        else:
            prompt += "\nText: no Chinese or English captions, no arrows, no UI graphics."
        if signal_needed:
            prompt += "\nTraffic-control accuracy: reproduce the referenced Chinese road sign, railway signal, barrier, or warning light exactly; do not invent symbols or change the active light state."

        payload.append({
            "group": index,
            "codes": [item["code"] for item in items],
            "section": first["section"],
            "sourceImage": source_image,
            "sourcePath": str(ROOT / "public" / source_image.lstrip("/")),
            "outputImage": f"/question-images-emergency-v2/{first['code'].lower().replace('_', '-')}-v2.jpeg",
            "outputPath": str(ROOT / "public" / "question-images-emergency-v2" / f"{first['code'].lower().replace('_', '-')}-v2.jpeg"),
            "prompt": prompt,
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(payload)} grouped prompts for {len(emergency)} questions to {OUTPUT.relative_to(ROOT)}")

    if args.apply:
        replacement_by_code = {
            code: group["outputImage"]
            for group in payload
            for code in group["codes"]
        }
        missing = [item["code"] for item in emergency if item["code"] not in replacement_by_code]
        if missing:
            raise RuntimeError(f"Missing generated-image mapping for: {', '.join(missing)}")

        missing_files = [
            group["outputPath"]
            for group in payload
            if not Path(group["outputPath"]).is_file()
        ]
        if missing_files:
            raise RuntimeError(
                "Generated images are missing:\n" + "\n".join(missing_files)
            )

        updated = 0
        for item in questions:
            if item.get("category") != "应急处理类-E":
                continue
            item["image"] = replacement_by_code[item["code"]]
            item["updatedAt"] = "2026-07-22"
            updated += 1

        SOURCE.write_text(
            json.dumps(questions, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Applied {updated} emergency image references to {SOURCE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
