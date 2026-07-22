#!/usr/bin/env python3
"""Build a deterministic, section-balanced, low-redundancy Subject 1 shortlist."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app" / "question-bank.json"
OUTPUT = ROOT / "app" / "featured-500.json"
TARGET = 500


def normalized_text(question: dict) -> str:
    options = "".join(question.get("options", {}).values())
    raw = question.get("title", "") + options + question.get("explanation", "")
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", raw.lower())


def shingles(text: str, width: int = 3) -> set[str]:
    if len(text) <= width:
        return {text} if text else set()
    return {text[index : index + width] for index in range(len(text) - width + 1)}


def similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def quality(question: dict) -> float:
    score = 0.0
    score += 0.45 if question.get("image") else 0.0
    score += min(len(question.get("detailedExplanation", "")), 240) / 600
    score += min(len(question.get("explanation", "")), 80) / 400
    score += 0.12 if question.get("difficulty") == "进阶" else 0.0
    return score


def largest_remainder_quotas(groups: dict[str, list[dict]], target: int) -> dict[str, int]:
    total = sum(len(items) for items in groups.values())
    exact = {key: target * len(items) / total for key, items in groups.items()}
    quotas = {key: min(len(groups[key]), max(1, math.floor(value))) for key, value in exact.items()}
    remaining = target - sum(quotas.values())
    order = sorted(groups, key=lambda key: (exact[key] - math.floor(exact[key]), len(groups[key]), key), reverse=True)
    cursor = 0
    while remaining > 0:
        key = order[cursor % len(order)]
        if quotas[key] < len(groups[key]):
            quotas[key] += 1
            remaining -= 1
        cursor += 1
    return quotas


def diverse_pick(items: list[dict], count: int) -> list[dict]:
    ranked = sorted(items, key=lambda item: (-quality(item), item["code"]))
    vectors = {item["code"]: shingles(normalized_text(item)) for item in ranked}
    chosen: list[dict] = []
    candidates = ranked[:]

    while candidates and len(chosen) < count:
        if not chosen:
            pick = candidates[0]
        else:
            def candidate_score(item: dict) -> tuple[float, float, str]:
                maximum = max(similarity(vectors[item["code"]], vectors[selected["code"]]) for selected in chosen)
                # Diversity dominates; completeness breaks close ties.
                return (1.0 - maximum + quality(item) * 0.08, quality(item), item["code"])

            pick = max(candidates, key=candidate_score)
        chosen.append(pick)
        candidates.remove(pick)
    return chosen


def main() -> None:
    questions = json.loads(SOURCE.read_text(encoding="utf-8"))
    subject_one = [
        item for item in questions
        if item.get("status") == "已发布" and not item.get("category", "").startswith("科四")
    ]
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in subject_one:
        groups[item["section"]].append(item)

    quotas = largest_remainder_quotas(groups, TARGET)
    selected: list[dict] = []
    for section in sorted(groups):
        selected.extend(diverse_pick(groups[section], quotas[section]))
    selected.sort(key=lambda item: item["code"])

    if len(selected) != TARGET or len({item["code"] for item in selected}) != TARGET:
        raise RuntimeError(f"Expected {TARGET} unique questions, got {len(selected)}")

    payload = {
        "name": "科目一精选500",
        "version": "2026-07-22",
        "method": "按科目一章节比例配额，并以题干、选项和解析的中文三字片段相似度进行最远点抽样，降低重复考点。",
        "count": TARGET,
        "sectionCounts": dict(sorted(Counter(item["section"] for item in selected).items())),
        "codes": [item["code"] for item in selected],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {TARGET} questions across {len(groups)} sections")


if __name__ == "__main__":
    main()
