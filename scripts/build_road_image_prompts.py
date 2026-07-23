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

NUMBER_OVERRIDES = {
    "R02_21": ["120", "60"],
    "R02_24": ["30"],
    "R02_25": ["30"],
    "R02_30": [],
}

SPECIAL_NOTES = {
    "R02_10": "Instrument-check invariant: use an interior driver viewpoint in a deceleration lane with the dashboard speedometer large and clearly visible. The driver checks the speedometer rather than guessing speed. Show no roadside speed sign or overhead speed number.",
    "R02_21": "False-statement correction: do not show 90 as the universal expressway minimum. Show exactly a red-ring 120 maximum-speed sign and a blue circular 60 minimum-speed sign, with no 90 sign anywhere.",
    "R02_24": "False-statement correction: the snowy or icy road maximum is 30 km/h, not 50. Show exactly one red-ring 30 sign and no 50 sign.",
    "R02_25": "False-statement correction: for U-turns, turns, or steep descents the maximum is 30 km/h, not 40. Show exactly one red-ring 30 sign and no 40 sign.",
    "R02_26": "Door-opening safety invariant: show a parked car at the road edge; the driver first checks the mirror and turns to inspect rear traffic, waits until the adjacent lane is clear, then opens the door only slightly. No vehicle may be passing close beside the open door.",
    "R02_28": "Expressway-breakdown invariant: one disabled car is fully inside the right emergency lane with hazard lights on, while every occupant has moved beyond the right guardrail. Nobody waits inside or stands beside the vehicle.",
    "R02_29": "No-private-towing invariant: show a disabled car being recovered by one professional flatbed tow truck in the emergency lane. Do not show an ordinary passenger car towing it by rope or bar.",
    "R02_30": "Safe-ramp invariant: show a car remaining in the acceleration lane with its left turn signal on, checking a safe gap and yielding to mainline traffic before a gradual merge. Do not show a direct abrupt cut into the travel lane and do not show speed signs.",
    "R02_31": "Mountain-meeting invariant: on a single-lane narrow mountain road, the vehicle beside the rock wall stops and yields, while the vehicle beside the outer guardrail or cliff edge proceeds first. Make the rock-wall side and cliff side unmistakable.",
    "R04_01": "Probation-companion invariant: show a novice driver on an expressway with an experienced licensed companion seated in the front passenger seat. The companion represents at least three years of driving experience; do not depict a one-year rule.",
    "R04_03": "Probation-companion invariant: show a novice driver on an expressway with an experienced licensed companion seated in the front passenger seat. The companion represents at least three years of driving experience; do not depict a one-year rule.",
    "R04_04": "Probation-companion invariant: show a novice driver on an expressway with an experienced licensed companion seated in the front passenger seat. The companion represents at least three years of driving experience.",
    "R04_05": "Probation-sign invariant: use a rear three-quarter view of one passenger car. Place one large official-style yellow probation sign on the rear of the vehicle with the exact black Chinese text '实习'. Render only those two Chinese characters, correctly and legibly.",
    "R04_06": "Probation-sign invariant: use a rear three-quarter view of one passenger car. Place one large official-style yellow probation sign on the rear of the vehicle with the exact black Chinese text '实习'. Render only those two Chinese characters, correctly and legibly.",
    "R04_07": "Twelve-point invariant: show a novice driver surrendering a driving licence at a traffic-service counter after accumulating 12 points. A simple official notice may show only the exact Chinese text '12分' and '注销', rendered correctly; no other text.",
    "R04_08": "Lane-count invariant: show exactly three expressway travel lanes, with one blue circular 90 minimum-speed sign aligned directly above the middle lane. Show no other speed sign or number.",
    "R04_09": "Acceleration-lane invariant: show a slow lead car and a following car staying in single file inside the acceleration lane. The following car must not overtake or cross the solid/gore markings.",
    "R04_12": "Crosswalk invariant: show a car fully stopped before the stop line and zebra crossing while a pedestrian is actively crossing in front. The vehicle must wait until the pedestrian has completely passed.",
    "R06_01": "Aborted-overtake invariant: show the following car abandoning the pass, returning fully behind the lead car, slowing, and restoring a safe gap because the lead car did not yield. Do not show the cars side by side.",
    "R06_02": "Insufficient-gap invariant: show the following car staying fully behind the lead car because there is not enough safe lateral clearance to pass. Do not show a completed overtake.",
    "R06_03": "Yield-to-overtaking invariant: show the lead car slowing and moving close to the right edge of its lane while the rear car prepares to pass safely on the left.",
    "R06_04": "Yield-to-overtaking invariant: show exactly two same-direction travel lanes separated by one dashed WHITE lane divider. The lead car slows in the right lane and keeps close to the right edge; the rear car is in the left lane preparing to pass. Both cars travel in the same direction. Do not place either car across a yellow line, and do not show an oncoming vehicle.",
    "R06_05": "Yield-to-overtaking invariant: show the lead car slowing and moving close to the right edge of its lane, visibly opening safe passing space on the left for the rear car.",
    "R06_06": "Being-overtaken invariant: show one vehicle already passing on the left while the vehicle being passed reduces speed and keeps steadily to the right. It must not accelerate or drift left.",
    "R06_07": "Oncoming-traffic invariant: show an attempted left-side pass being abandoned immediately because an oncoming vehicle is approaching. The passing car returns behind the lead car; do not depict a collision or a successful pass.",
    "R06_08": "No-double-overtake invariant: the lead vehicle is already overtaking another vehicle on the left, while the test vehicle remains behind and does not start another pass.",
    "R06_09": "Left-turn invariant: show the lead vehicle with its left indicator on and beginning a left turn, while the following vehicle waits behind and does not overtake.",
    "R06_10": "No-double-overtake invariant: the lead vehicle is already overtaking another vehicle, while the following vehicle stays behind and does not initiate another pass.",
    "R06_11": "U-turn invariant: show the lead vehicle beginning a legal U-turn, while the following vehicle remains behind and does not try to pass.",
    "R06_13": "Left-side-passing invariant: show one safe, legal pass on the left of a slower vehicle, with a dashed yellow center line and ample lateral clearance. The opposite lane must be completely empty from foreground to horizon: absolutely no oncoming car, truck, motorcycle, bicycle, or distant vehicle anywhere.",
    "R06_14": "A/B identity invariant: show car A directly behind car B on a two-way road. A solid yellow center line is immediately to A's left, so A must stay behind B and must not cross the solid line. Put one clear Latin letter A on car A and one clear Latin letter B on car B; no other text.",
    "R06_15": "Left-side-passing invariant: show one safe, legal pass on the left of a slower vehicle, with a dashed yellow center line, long straight forward visibility, and ample lateral clearance. The opposite lane must be completely empty from foreground to horizon: absolutely no oncoming car, truck, motorcycle, bicycle, or distant vehicle anywhere.",
    "R06_16": "Police-vehicle invariant: use a one-lane-per-direction road. The lead vehicle is an on-duty Chinese traffic police car with red-and-blue emergency lights active. One passenger car follows centered directly behind it in the same lane at a safe distance. Do not put the passenger car beside the police car or in the opposite lane; no overtaking maneuver.",
    "R06_17": "Ambulance invariant: use a one-lane-per-direction road. The lead vehicle is an on-duty Chinese ambulance with emergency lights active. One passenger car follows centered directly behind it in the same lane at a safe distance. Do not put the passenger car beside the ambulance or in another lane; no overtaking maneuver.",
    "R06_18": "Fire-engine invariant: the lead vehicle is an on-duty Chinese fire engine with emergency lights active. The following passenger car keeps behind and does not overtake.",
    "R06_19": "Cautious-overtake invariant: even though the lead car slows and moves right, show the following car first maintaining a safe gap and confirming the road is clear; do not depict a sudden aggressive acceleration beside the lead car.",
    "R06_20": "Solid-line invariant: use a one-lane-per-direction road with one unbroken solid yellow center line. Show two same-direction passenger cars in single file on the right side of that line, one directly behind the other at a safe distance. Neither car may touch, cross, or straddle the yellow line, and no same-direction car may appear in the opposite lane.",
    "R06_24": "Busy-urban invariant: show a dense urban traffic stream with closely spaced vehicles and limited gaps; the test vehicle stays in lane and does not overtake.",
    "R06_25": "Crosswalk invariant: show a clearly marked zebra crossing ahead and the following vehicle staying behind the lead vehicle. No vehicle may overtake on or immediately before the crosswalk.",
    "R06_27": "Narrow-bridge-and-bend invariant: show a narrow bridge leading into a blind bend with restricted visibility; vehicles remain single file and no one overtakes.",
    "R06_28": "Blue-car invariant: show one blue car behind a slower vehicle on a straight two-way road. The yellow center line next to the blue car is dashed, the oncoming lane is completely clear, and sight distance is long, making a left-side pass legally possible. No collage or multiple numbered diagrams.",
    "R06_29": "Reference-answer invariant: recreate only the safe 51a geometry as one realistic scene, not a four-panel diagram. The following car is beside a dashed yellow center line, the oncoming lane is clear, and a safe left-side pass is possible. Show no text, panel label, or other case.",
    "R06_30": "Wait-for-current-pass invariant: show a vehicle in the left lane actively passing another car, while the test vehicle waits at a safe distance behind until the left-lane pass is finished. Do not show the test vehicle beginning a second pass.",
    "R06_31": "Railway-crossing invariant: show a city railway level crossing with no train visible, but both vehicles remain single file and no one overtakes on or near the crossing.",
    "R06_32": "Turn-signal invariant: use a rear three-quarter view of the test car behind a slower vehicle, with the test car's left turn indicator clearly flashing before any lane movement. Do not show the pass already completed.",
    "R06_33": "Alert-before-passing invariant: show a night or dim-light road with the following vehicle behind the lead car, left indicator active and headlights briefly flashing to alert both the lead car and rear traffic before passing. No vehicle has begun crossing the center line.",
    "R06_35": "No-center-line invariant: on a narrow two-way road with no painted center line, show the lead vehicle slowing and keeping close to the right edge after a rear vehicle signals intent to pass, leaving safe space on its left.",
    "R06_37": "A/C identity invariant: reproduce the reference relationship as one realistic overhead-oblique road scene. Car A follows car C in the same direction and must abandon passing C because an oncoming car occupies the opposite lane. Put one clear Latin letter A on car A and one clear Latin letter C on car C; no other text or letter.",
    "R06_38": "Tunnel invariant: inside a clearly recognizable road tunnel, show a following car staying behind a slow lead car. Its attempted left pass is prohibited; neither vehicle crosses the solid center or lane line.",
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
        if first["code"] in NUMBER_OVERRIDES:
            required_numbers = NUMBER_OVERRIDES[first["code"]]
        else:
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
        if first["code"] in SPECIAL_NOTES:
            prompt += "\n" + SPECIAL_NOTES[first["code"]]

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
