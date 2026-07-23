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
    "R09_01": "Meeting-traffic invariant: show a narrow two-way road with bare continuous asphalt from one natural road edge to the other. Absolutely no painted center line, lane divider, edge line, shoulder line, arrow, or road marking of any kind. Two opposing passenger cars approach slowly, each keeping close to its own right road edge, with safe lateral clearance.",
    "R09_02": "False-statement correction: on an unmarked shared road, show the passenger car traveling in the road's middle zone rather than hugging the right edge. Pedestrians and bicycles use both outer edges. Show no painted center line, lane line, bicycle lane, sidewalk, or curb-separated path.",
    "R09_03": "Shared-road invariant: show one passenger car centered in the middle zone of a broad unmarked shared road, leaving generous space on both outer edges for pedestrians and bicycles. No painted center line, lane line, bicycle lane, sidewalk, or curb-separated path.",
    "R09_04": "Shared-road invariant: show one passenger car centered in the middle zone of a broad unmarked shared road, leaving generous space on both outer edges for pedestrians and bicycles. No painted center line, lane line, bicycle lane, sidewalk, or curb-separated path.",
    "R09_05": "False-statement correction: show the passenger car traveling in the road's middle zone, not on the left side. Pedestrians and bicycles remain near both outer edges. Show absolutely no painted center line or lane divider.",
    "R09_06": "Shared-road invariant: show one passenger car centered in the middle zone of a broad unmarked shared road, with pedestrians or bicycles safely using both outer edges. No painted center line, lane line, bicycle lane, sidewalk, or curb-separated path.",
    "R09_07": "Unmarked-road invariant: show one passenger car traveling in the middle zone of a road with no center line, no lane division, no bicycle lane, and no sidewalk. Keep both road edges visibly available to pedestrians or bicycles.",
    "R09_08": "Full-sharing invariant: show one passenger car in the road's middle zone, bicycles and pedestrians using both outer road edges, and no painted center line, motor-vehicle lane, bicycle lane, sidewalk, or curb-separated path.",
    "R09_09": "Full-sharing invariant: show one passenger car in the road's middle zone, bicycles and pedestrians using both outer natural road edges. Use bare continuous asphalt from edge to edge: absolutely no painted center line, lane divider, edge line, shoulder line, arrow, or marking of any kind, and no sidewalk or curb-separated path.",
    "R10_01": "Zipper-merge invariant: show exactly two slow same-direction lanes narrowing into one. At the merge point, vehicles enter one at a time in strict left-right alternation, with safe gaps and no side-by-side squeeze.",
    "R10_02": "Unsignalized-junction invariant: show a congested intersection with no traffic light and two slow vehicle streams taking turns one vehicle at a time. No vehicle blocks the crossing.",
    "R10_03": "Zipper-merge invariant: show exactly two slow same-direction lanes narrowing into one. At the merge point, one vehicle from the left lane enters, then one from the right lane, with clear alternating gaps.",
    "R10_04": "Zipper-merge invariant: show exactly two slow same-direction lanes narrowing into one. Vehicles enter one at a time in orderly left-right alternation; no racing, shoulder driving, or side-by-side squeeze.",
    "R10_05": "Right-lane-ending invariant: show exactly two same-direction lanes, with the RIGHT lane visibly narrowing ahead but still open at the two cars' current position. A car remains fully inside the right travel lane before the taper, slows, and yields to a car in the left lane, which proceeds first into the remaining lane. Neither car may enter any hatched gore, striped exclusion zone, shoulder, or closed lane. Do not reverse the yielding relationship.",
    "R10_06": "Right-turn-queue invariant: at a signalized intersection, show a right-turn lane whose front vehicle is stopped for the signal. Every following vehicle waits in a single orderly line behind it; no one uses the shoulder or crosses the line to bypass.",
    "R10_07": "Queue invariant: show a clearly congested road with all vehicles stopped or crawling in an orderly single-file queue. The test vehicle stays in line with a safe gap and does not change lanes or use the shoulder.",
    "R10_08": "Slow-traffic invariant: show a long line of slow vehicles moving in order. The test vehicle follows the same lane at a safe distance without overtaking, weaving, or shoulder driving.",
    "R10_09": "Intersection-merge invariant: immediately before a congested junction, exactly two same-direction lanes reduce to one. Vehicles from the two lanes enter the junction one at a time in strict alternation.",
    "R10_10": "Queue invariant: show stopped or crawling traffic in one lane. The test vehicle remains in sequence behind the lead vehicle with a safe gap; no overtaking, weaving, or shoulder use.",
    "R10_11": "Blocked-intersection invariant: use a slightly elevated rear-oblique view so road geometry is unmistakable. Show traffic backed up across the far side. The complete test vehicle—from rear bumper through front bumper—is stopped at least one full vehicle length BEFORE a thick stop line; the entire stop line and the entire zebra crossing are visible in front of the car. No tire or bumper touches the line or crosswalk, and the intersection remains empty in front of the test car.",
    "R10_12": "Outside-intersection invariant: show a queue beyond a congested junction while the test vehicle and following vehicles form an orderly queue entirely before the stop line, outside the intersection.",
    "R10_13": "Cut-in-safety invariant: show a congested queue with one other car forcing diagonally into the test vehicle's gap. The test vehicle slows or stops to create space and avoid contact; no collision or aggressive blocking.",
    "R10_14": "Congestion-approach invariant: show the test vehicle decelerating and stopping behind a visible traffic queue, maintaining a safe gap and staying in its lane.",
    "R10_15": "Green-but-blocked invariant: use a slightly elevated rear-oblique view. Show a clearly green signal while the far side is fully congested. The complete test vehicle—from rear bumper through front bumper—is stopped at least one full vehicle length BEFORE a thick stop line; the entire stop line and zebra crossing are visible in front of it. No part of the vehicle touches the line, crosswalk, or intersection.",
    "R10_16": "Expressway-queue invariant: show a slow or stopped expressway queue. The test vehicle follows in sequence with a safe gap and both rear amber hazard indicators flashing simultaneously. It remains in a travel lane and does not enter the emergency lane.",
    "R10_17": "Prohibited-cut-in invariant: show a congested queue and one car attempting a forceful diagonal cut-in across a lane divider, making the disruptive behavior unmistakable. Other cars brake safely; no collision and no vehicle drives on the shoulder.",
    "R10_18": "Outside-intersection invariant: show a blocked junction with queued traffic on the far side. The test vehicle is stopped fully before the stop line, leaving the whole intersection clear.",
    "R10_19": "Expressway-slow-traffic invariant: show a slow-moving expressway traffic stream. The test vehicle follows the lane flow with a visibly safe gap, no weaving, no overtaking, and no emergency-lane use.",
    "R10_20": "Wait-for-clear-and-green invariant: use a slightly elevated rear-oblique view. Show a green signal but a still-blocked road beyond the junction. The complete straight-going test vehicle—from rear bumper through front bumper—is stopped at least one full vehicle length BEFORE a thick stop line; the entire stop line and zebra crossing are visible in front of it. No part touches the line, crosswalk, or intersection.",
    "R11_01": "Crosswalk-approach invariant: show a passenger car visibly slowing before a zebra crossing while the driver checks both sides for pedestrians and bicycles. The car remains behind the stop line and crosswalk.",
    "R11_02": "Disabled-pedestrian invariant: show a driver slowing and leaving generous space for one visibly mobility-impaired pedestrian using a wheelchair or walking aid near the roadway. No horn use, intimidation, or close pass.",
    "R11_03": "Emergency-vehicle-yield invariant: show one on-duty emergency vehicle with red-and-blue lights active approaching from behind while ordinary cars and nearby pedestrians move aside to create a clear central passage. No one follows the emergency vehicle.",
    "R11_04": "Safe-cut-in-response invariant: in slow congested traffic, show another car forcing diagonally into the test vehicle's gap while the test vehicle brakes and yields enough space to prevent contact.",
    "R11_05": "Reversing-yield invariant: show a passenger car reversing slowly from a parking space or driveway, then stopping completely because a through vehicle is passing behind it. Brake lamps are on; no collision.",
    "R11_06": "Pedestrian-crossing invariant: show one pedestrian actively crossing in front of the test vehicle. The vehicle is fully stopped with a clear safety gap and does not edge forward.",
    "R11_07": "Sudden-pedestrian invariant: show a pedestrian unexpectedly entering the road ahead while the test vehicle brakes sharply but safely, remaining well short of the pedestrian. No collision or dramatic skid.",
    "R11_08": "A-car invariant: show one test passenger car clearly marked with the Latin letter A approaching a pedestrian crossing the road. Car A slows or stops and yields. No B marker or other text.",
    "R11_09": "Crowded-intersection invariant: show a busy unsignalized or low-speed intersection with many pedestrians and bicycles near the crossing. The test vehicle approaches slowly with ample stopping space.",
    "R11_10": "A-car-ambulance invariant: use a high rear-oblique or overhead view showing both vehicles' full orientation. Both vehicles point in exactly the SAME forward direction. Mark the ordinary passenger car with one large high-contrast Latin letter A on its roof. The ambulance is physically BEHIND car A, not ahead or alongside, and approaches with emergency lights active. Car A slows and pulls to the right edge to open a passage. No other letter or text.",
    "R11_11": "Crosswalk-yield invariant: show pedestrians actively crossing at the junction while the test vehicle slows to a full stop before the stop line and zebra crossing. Keep the entire vehicle outside the crossing.",
    "R11_12": "Crosswalk-yield invariant: show pedestrians actively crossing at the junction while the test vehicle slows to a full stop before the stop line and zebra crossing. Keep the entire vehicle outside the crossing.",
    "R11_13": "Road-maintenance-vehicle invariant: use a one-lane-per-direction road with one visible yellow center line. An on-duty road-maintenance truck with amber lights is driving against normal traffic physically on the TEST VEHICLE'S side of the yellow line, approaching the test vehicle head-on because of active work. The test vehicle is pulled fully to its right edge and stopped to yield. The truck must not remain in its normal opposing lane.",
    "R11_14": "No-crosswalk-pedestrian invariant: at an intersection with absolutely no zebra crossing, show a pedestrian crossing the roadway. The test vehicle slows or stops at a safe distance and yields.",
    "R11_15": "Wrong-way-ambulance-yield invariant: show an on-duty ambulance with emergency lights approaching in the opposite direction within the test vehicle's lane to reach an emergency. The test vehicle pulls to the right edge and slows or stops to create a clear passage.",
    "R11_16": "False-statement correction: even though the pedestrian is crossing improperly outside a crosswalk, show the test vehicle slowing or stopping and yielding safely. Do not depict the driver refusing to yield.",
    "R11_17": "Bicycle-conflict invariant: show a green signal for the test vehicle but a bicycle or electric bicycle entering its path unexpectedly. The test vehicle stops and yields rather than competing for space.",
    "R11_18": "Roundabout-safety invariant: show the test car already circulating in a roundabout but braking to avoid another car forcing its way in. Priority does not justify a collision.",
    "R11_19": "Emergency-vehicle-yield invariant: show an on-duty fire engine, ambulance, or rescue vehicle with active emergency lights while ordinary traffic moves aside and creates a clear route.",
    "R11_20": "Bicycle-lane-yield invariant: use a high rear-oblique or overhead view so orientation is certain. The ordinary car and emergency vehicle point in exactly the SAME forward direction, with the emergency vehicle physically BEHIND the ordinary car and approaching with active lights. The empty red bicycle lane lies on the ordinary car's right. The ordinary car cautiously moves partly into that empty bicycle lane to open a passage; it does not enter the sidewalk. No oncoming emergency vehicle.",
    "R11_21": "Return-after-yield invariant: show the emergency vehicle already safely passing ahead while ordinary cars merge back into their original lane in order. Maintain a large gap; no car follows closely in the emergency vehicle's wake.",
    "R11_22": "Roundabout-priority invariant: show the test car stopped at a roundabout entrance while a vehicle already circulating inside passes first. Preserve Chinese right-hand traffic and a counterclockwise roundabout flow.",
    "R11_23": "Right-turn-versus-left-turn invariant: at an intersection, the test vehicle intends to turn right and waits while the opposing vehicle completes a left turn first. Make both turn paths and the yielding order visually unambiguous.",
    "R11_24": "Turn-yields-to-straight invariant: at an unsignalized intersection, show one turning car stopped or slowing while an opposing straight-going vehicle proceeds first. Do not reverse the priority.",
    "R11_25": "Right-side-priority invariant: at an unsignalized intersection, show the test vehicle yielding to a vehicle approaching from its right. The right-side vehicle proceeds first; do not depict the test vehicle as having priority.",
    "R11_26": "A/B priority invariant: use a high overhead-oblique view. Put one large high-contrast Latin letter A on the roof of the straight-going vehicle and one large high-contrast Latin letter B on the roof of the turning vehicle. Both letters must be fully readable at thumbnail size. A proceeds straight first while B is stopped before its turn. No other text or letter.",
    "R11_27": "A/B priority invariant: use a high overhead-oblique view. Put one large high-contrast Latin letter A on the roof of the straight-going vehicle and one large high-contrast Latin letter B on the roof of the turning vehicle. A is already proceeding straight through the junction. B is stopped before A's lane but is visibly angled about 45 degrees into a turn, with front wheels turned and its turn indicator illuminated; B must not look like a straight cross-traffic vehicle. Both letters must be readable. No other text.",
    "R11_28": "A/B priority invariant: use a high overhead-oblique view. Put one large high-contrast Latin letter A on the roof of the vehicle traveling straight and one large high-contrast Latin letter B on the roof of the other vehicle. B is visibly angled on a curved turning path with its turn indicator on and is stopped before entering A's path. A proceeds straight first. No other text.",
    "R11_29": "A-car priority invariant: use a high overhead-oblique view. Put one large high-contrast Latin letter A on the roof of the straight-going vehicle, which is already moving through the junction. The other vehicle remains entirely BEHIND its stop line and outside A's travel path, but is visibly angled about 45 degrees for a turn, with front wheels turned and turn indicator illuminated. It must not enter, cross, or finish the turn before A. No B marker or other text.",
    "R11_30": "A/B turn-priority invariant: use a high overhead-oblique view. Put one large high-contrast Latin letter A on the roof of the RIGHT-turning vehicle and one large high-contrast Latin letter B on the roof of the opposing LEFT-turning vehicle. Both letters must be readable. A is stopped before its right turn while B completes the left turn first. No other text.",
    "R11_31": "Give-way-sign invariant: show one correct Chinese inverted triangular red-border yield sign with a white center and the exact single black Chinese character '让'. The test vehicle clearly decelerates before the junction. Show no other text or sign.",
    "R11_32": "Stop-sign invariant: show one correct red octagonal Chinese stop sign with the exact single white Chinese character '停'. The test vehicle makes a complete stop before the line; merely slowing is not enough. Show no other text.",
    "R11_33": "Crosswalk-stop invariant: show a pedestrian actively on the zebra crossing while the test car is fully stopped before the stop line with a safe gap.",
    "R11_34": "Pedestrian-priority invariant: show pedestrians actively crossing on a zebra crossing and the vehicle fully stopped before it, clearly yielding their right of way.",
    "R11_35": "Obstacle-priority invariant: show roadwork or a fixed obstacle blocking the ONCOMING vehicle's lane, while the test vehicle's lane is unobstructed. The oncoming vehicle stops behind the obstacle and the unobstructed test vehicle proceeds first.",
    "R11_36": "Slope-meeting invariant: on a steep narrow road, show the downhill vehicle already descending the slope. The uphill vehicle has not started climbing and waits at the bottom, allowing the descending vehicle to pass first.",
    "R11_37": "Obstacle-priority invariant: show roadwork or a fixed obstacle blocking the TEST vehicle's lane. The test vehicle stops behind the obstacle while the opposing vehicle in the unobstructed lane proceeds first.",
    "R11_38": "School-bus invariant: show exactly three same-direction travel lanes. A yellow school bus is stopped in the far-right lane with red warning lights active while students board or alight on the curb side. Vehicles behind the bus in the right lane and in the adjacent middle lane are fully stopped; a vehicle in the far-left lane passes only at very low speed. No vehicle passes beside boarding children.",
    "R11_39": "Narrow-road-courtesy invariant: on a visibly narrow two-way segment, both opposing drivers slow early; one pulls to the side and stops while the other passes carefully. No squeezing or aggressive priority claim.",
    "R11_40": "Crosswalk-courtesy invariant: show the test car slowing and stopping before a zebra crossing to allow pedestrians to cross, with a generous safety gap.",
    "R11_41": "Right-side-priority invariant: at an unsignalized intersection, show the test vehicle stopped while a vehicle approaching from the road on its right proceeds first.",
    "R11_42": "Right-turn-yields-to-left-turn invariant: at an unsignalized intersection, show the right-turning vehicle waiting while the opposing left-turning vehicle completes its turn first. This corrects the false claim that the left-turner must yield to the right-turner.",
    "R11_43": "Watering-truck invariant: show an on-duty street-watering truck moving slowly ahead with amber warning lights and visible low spray close to the road surface. The following car slows and keeps a safe distance; it does not accelerate past through the spray.",
    "R11_44": "Mountain-meeting invariant: on a single-lane narrow mountain road with no center line, show the vehicle beside the rock wall stopped and yielding while the vehicle beside the outer guardrail or cliff edge proceeds first.",
    "R11_45": "Main-road-priority invariant: show a smaller auxiliary road joining a wide busy main road. The auxiliary-road car stops before the merge and yields while faster main-road traffic passes first. Keep the road hierarchy unmistakable.",
    "R11_46": "Turn-yields-to-straight-and-pedestrian invariant: at an unsignalized intersection, show one turning vehicle stopped while a straight-going vehicle and a crossing pedestrian proceed first. The turning car yields to both.",
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
