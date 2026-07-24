#!/usr/bin/env python3
"""Create grouped, question-grounded prompts for the special-topic image refresh."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "question-bank.json"
OUTPUT = ROOT / "work" / "special-topic-image-prompts.json"
IMAGE_DIR = ROOT / "public" / "question-images-topic-v2"
CATEGORY = "专项题型类-T"

SECTION_NOTES = {
    "T01": (
        "Distance-and-parking treatment: use a realistic Chinese road scene with the tested "
        "distance physically understandable. Keep road type, parking position, vehicle direction, "
        "warning-triangle placement, intersection, hydrant, bus stop, fuel station, bridge, tunnel, "
        "bend, or narrow-road geometry exact. When a number is indispensable, show it once as a "
        "large clean distance marker and render the digits exactly."
    ),
    "T02": (
        "Eligibility-and-review treatment: use a respectful realistic scene at a Chinese traffic "
        "service office, driving review, examination, or enforcement context. Make the tested time "
        "period and consequence memorable without inventing an official seal or dense legal text."
    ),
    "T03": (
        "Driver-assistance acronym treatment: use a clean modern dashboard or educational panel. "
        "Preserve every acronym and choice label from the reference literally; LDW and ACC must "
        "never be misspelled, expanded incorrectly, swapped, or decorated."
    ),
    "T04": (
        "Mixed-rule treatment: first follow the exact factual subject in the source—road sign, "
        "vehicle relationship, road marking, speed/distance rule, licence consequence, or safe "
        "behavior—then improve realism and thumbnail readability. Never replace a tested sign or "
        "maneuver with a generic driving scene."
    ),
    "T05": (
        "Licence-and-application treatment: use a realistic Chinese traffic-service, examination, "
        "licence, calendar, or enforcement scene. Make the tested duration and consequence visually "
        "clear while avoiding fake seals, fabricated statutes, or unrelated English text."
    ),
}

SPECIAL_NOTES = {
    "T01_01": "Show a car travelling above 100 km/h on an expressway while keeping more than 100 metres behind the same-lane lead car.",
    "T01_02": "Correct-rule invariant: in snowy expressway visibility below 200 metres, show at least 100 metres following distance. Do not show 50 metres.",
    "T01_03": "Show car A illegally parked within 50 metres of an intersection. The intersection and prohibited proximity must be unmistakable.",
    "T01_04": "False-statement correction: show the no-parking zone within 30 metres of a fire hydrant or fire-station entrance, never 50 metres.",
    "T01_05": "Show the 50-metre no-parking zone before an intersection.",
    "T01_06": "Show a vehicle kept outside the 50-metre no-parking zone near a bridge, steep slope, or tunnel.",
    "T01_07": "Show car A legally stopped more than 30 metres beyond a bus stop; keep the bus-stop position and separation clear.",
    "T01_08": "Show a road narrower than 4 metres with no parking within 50 metres; preserve realistic road width.",
    "T01_09": "Show one blue car illegally parked less than 30 metres from a fuel station; the fuel station and car must be in one coherent scene.",
    "T01_10": "Show one representative special road location with a clear 50-metre no-parking zone; do not create a collage of many locations.",
    "T01_11": "Expressway-breakdown invariant: one disabled car is fully in the emergency lane with hazards on, and one warning triangle is placed more than 150 metres behind it in the direction of approaching traffic.",
    "T01_12": "Show a sharp bend with a clear 50-metre no-parking zone; do not place a car inside that zone.",
    "T01_14": "Show an expressway car travelling below 100 km/h while keeping at least 50 metres behind the same-lane lead car.",
    "T01_16": "Ordinary-road breakdown rule: place the warning triangle 50–100 metres behind the disabled vehicle, not within 50 metres.",
}


def answer_text(question: dict) -> str:
    keys = [key for key in question.get("answer", "") if key in "ABCD"]
    return "；".join(
        question.get("options", {}).get(key, "")
        for key in keys
        if question.get("options", {}).get(key, "")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Replace all special-topic image references with generated v2 assets.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))
    topic = [item for item in questions if item.get("category") == CATEGORY]

    payload = []
    for index, first in enumerate(topic, start=1):
        source_image = first.get("image", "")
        prompt = f"""Use case: photorealistic-natural
Asset type: 16:9 educational cover image for a Chinese driving-theory mini program
Input images: Image 1 is visual reference only. Legacy images and legacy explanations can be stale or wrong; never copy a detail that conflicts with the question and correct answer below.
Primary request: Rebuild this special-topic learning image so its one tested rule is immediately understandable at a 375px mini-program width.
Section: {first["section"]}.
Question code: {first["code"]}
Authoritative question: {first["title"]}
Authoritative correct-answer meaning: {answer_text(first)}
{SECTION_NOTES[first["section"]]}
Accuracy hierarchy: the authoritative question and correct answer above have highest priority. Then preserve the tested vehicle/person direction, road geometry, sign or symbol, distance, number, and active state before improving realism.
Composition: one coherent 16:9 image, not a collage unless the source itself is a choice panel. Keep the lesson subject large, uncluttered, and readable.
Teaching rule: visualize the legally correct fact from the authoritative question and correct answer. Do not use the legacy explanation as a source of truth. Do not present an unsafe or false statement as recommended behavior.
Reference fidelity: do not mirror left/right, swap vehicles, alter a road marking, change a sign, change a distance, invent an extra person or vehicle, or substitute a generic scene.
Text constraints: no decorative title, paragraph, watermark, brand logo, or invented licence plate. Render only test-critical digits, Chinese characters, Latin letters, or acronyms that are required by the source."""

        if any(
            token in first.get("title", "")
            for token in ["以下", "哪个", "图中", "如图"]
        ):
            prompt += """
Choice/reference fidelity: if the source is a multi-choice panel or uses A/B/C/D, 图1/图2/图3/图4, or vehicle letters, preserve every label, order, icon, color, and vehicle identity exactly. Never convert one label system to another."""
        if first["code"] in SPECIAL_NOTES:
            prompt += "\n" + SPECIAL_NOTES[first["code"]]

        filename = f"{first['code'].lower().replace('_', '-')}-v2.jpeg"
        payload.append(
            {
                "group": index,
                "codes": [first["code"]],
                "section": first["section"],
                "sourceImage": source_image,
                "sourcePath": str(ROOT / "public" / source_image.lstrip("/")),
                "outputImage": f"/question-images-topic-v2/{filename}",
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
        f"Wrote {len(payload)} per-question prompts for {len(topic)} questions to "
        f"{OUTPUT.relative_to(ROOT)}"
    )

    if args.apply:
        replacements = {
            code: group["outputImage"]
            for group in payload
            for code in group["codes"]
        }
        missing = [
            group["outputPath"]
            for group in payload
            if not Path(group["outputPath"]).is_file()
        ]
        if missing:
            raise RuntimeError(
                "Generated special-topic images are missing:\n" + "\n".join(missing)
            )

        updated = 0
        for item in questions:
            if item.get("category") != CATEGORY:
                continue
            item["image"] = replacements[item["code"]]
            item["updatedAt"] = "2026-07-24"
            updated += 1

        SOURCE.write_text(
            json.dumps(questions, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(f"Applied {updated} special-topic image references.")


if __name__ == "__main__":
    main()
