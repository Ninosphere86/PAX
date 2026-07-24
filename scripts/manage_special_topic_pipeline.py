#!/usr/bin/env python3
"""Manage the resumable image-production pipeline for special-topic questions."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
QUESTION_BANK = ROOT / "app" / "question-bank.json"
MANIFEST = ROOT / "ops" / "special-topic-image-pipeline.json"
CURRENT_BATCH = ROOT / "work" / "special-topic-current-batch.json"
IMAGE_DIR = ROOT / "public" / "question-images-topic-v2"
CATEGORY = "专项题型类-T"
VALID_STATUSES = {"pending", "generated", "approved", "redo", "review_required"}

SECTION_NOTES = {
    "T01": "Keep every tested distance, road type, parking position and vehicle direction exact.",
    "T02": "Use the question and correct answer as authority for eligibility, review period and consequence.",
    "T03": "Render LDW or ACC literally and never swap or misspell the acronym.",
    "T04": "Preserve the exact tested sign, road geometry, vehicle identity, manoeuvre, number and legal result.",
    "T05": "Preserve the exact licence, application, examination, validity-period and enforcement rule.",
}


def load_questions() -> list[dict]:
    questions = json.loads(QUESTION_BANK.read_text(encoding="utf-8"))
    return [item for item in questions if item.get("category") == CATEGORY]


def answer_text(question: dict) -> str:
    keys = [key for key in question.get("answer", "") if key in "ABCD"]
    return "；".join(
        question.get("options", {}).get(key, "")
        for key in keys
        if question.get("options", {}).get(key, "")
    )


def question_hash(question: dict) -> str:
    material = {
        "title": question.get("title", ""),
        "options": question.get("options", {}),
        "answer": question.get("answer", ""),
        "detailedExplanation": question.get("detailedExplanation", ""),
    }
    raw = json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def output_image(question: dict) -> str:
    filename = question["code"].lower().replace("_", "-") + "-v2.jpeg"
    return f"/question-images-topic-v2/{filename}"


def output_path(question: dict) -> Path:
    return ROOT / "public" / output_image(question).lstrip("/")


def load_manifest() -> dict | None:
    if not MANIFEST.is_file():
        return None
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(manifest: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sync_manifest() -> dict:
    questions = load_questions()
    previous = load_manifest()
    previous_items = {
        item["code"]: item for item in (previous or {}).get("items", [])
    }
    items = []

    for question in questions:
        code = question["code"]
        digest = question_hash(question)
        old = previous_items.get(code)
        if old:
            status = old["status"]
            if old.get("questionHash") != digest and status == "approved":
                status = "review_required"
            elif status == "pending" and output_path(question).is_file():
                status = "generated"
        else:
            status = "approved" if output_path(question).is_file() else "pending"

        items.append(
            {
                "code": code,
                "section": question["section"],
                "status": status,
                "outputImage": output_image(question),
                "sourceImage": question.get("image", ""),
                "questionHash": digest,
                "updatedAt": (old or {}).get("updatedAt", str(date.today())),
                "note": (old or {}).get("note", ""),
            }
        )

    manifest = {
        "category": CATEGORY,
        "schemaVersion": 1,
        "batchSize": 8,
        "updatedAt": str(date.today()),
        "items": items,
    }
    save_manifest(manifest)
    return manifest


def build_prompt(question: dict) -> str:
    return f"""Use case: photorealistic-natural
Asset type: 16:9 educational cover image for a Chinese driving-theory mini program
Input images: Image 1 is a visual reference only. Ignore any legacy detail that conflicts with the authoritative question and correct answer.
Question code: {question["code"]}
Authoritative question: {question["title"]}
Authoritative correct-answer meaning: {answer_text(question)}
Detailed legal explanation: {question.get("detailedExplanation", "")}
Primary request: Make the single tested rule immediately understandable at a 375px display width.
Section accuracy note: {SECTION_NOTES[question["section"]]}
Accuracy hierarchy: question and correct answer first; then exact sign/symbol, vehicle/person identity and direction, road geometry, number, distance and active state.
Composition: one coherent realistic 16:9 scene; keep the tested subject large and uncluttered.
Text constraints: render only test-critical digits, Chinese characters or acronyms. No decorative title, watermark, logo, invented plate, fake seal or unrelated English.
Avoid: collage unless the source is a choice panel; mirrored road relationships; swapped vehicles; changed signs; generic scenes; unsafe false behaviour presented as correct."""


def make_batch(section: str | None, limit: int, output: Path) -> list[dict]:
    manifest = sync_manifest()
    question_map = {item["code"]: item for item in load_questions()}
    candidates = [
        item
        for item in manifest["items"]
        if item["status"] in {"pending", "redo"}
        and (section is None or item["section"] == section)
    ][:limit]
    batch = []
    for item in candidates:
        question = question_map[item["code"]]
        batch.append(
            {
                "code": item["code"],
                "section": item["section"],
                "sourcePath": str(ROOT / "public" / item["sourceImage"].lstrip("/")),
                "outputPath": str(ROOT / "public" / item["outputImage"].lstrip("/")),
                "prompt": build_prompt(question),
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(batch, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return batch


def update_status(codes: list[str], status: str, note: str) -> dict:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    manifest = sync_manifest()
    requested = set(codes)
    found = set()
    for item in manifest["items"]:
        if item["code"] not in requested:
            continue
        item["status"] = status
        item["updatedAt"] = str(date.today())
        if note:
            item["note"] = note
        found.add(item["code"])
    missing = sorted(requested - found)
    if missing:
        raise ValueError("Unknown codes: " + ", ".join(missing))
    save_manifest(manifest)
    return manifest


def validate(codes: list[str] | None) -> list[str]:
    manifest = sync_manifest()
    selected = [
        item
        for item in manifest["items"]
        if (
            item["code"] in set(codes)
            if codes
            else item["status"] != "pending"
        )
    ]
    errors = []
    for item in selected:
        path = ROOT / "public" / item["outputImage"].lstrip("/")
        if not path.is_file():
            errors.append(f"{item['code']}: missing {path.relative_to(ROOT)}")
            continue
        with Image.open(path) as image:
            if image.size != (1280, 720):
                errors.append(f"{item['code']}: expected 1280x720, got {image.size}")
            if image.format != "JPEG":
                errors.append(f"{item['code']}: expected JPEG, got {image.format}")
    return errors


def print_summary(manifest: dict) -> None:
    counts: dict[str, dict[str, int]] = {}
    for item in manifest["items"]:
        section = counts.setdefault(item["section"], {})
        section[item["status"]] = section.get(item["status"], 0) + 1
    for section in sorted(counts):
        parts = " ".join(
            f"{status}={counts[section].get(status, 0)}"
            for status in sorted(VALID_STATUSES)
            if counts[section].get(status, 0)
        )
        print(f"{section}: {parts}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("sync")
    subparsers.add_parser("summary")

    next_parser = subparsers.add_parser("next")
    next_parser.add_argument("--section", choices=sorted(SECTION_NOTES))
    next_parser.add_argument("--limit", type=int, default=8)
    next_parser.add_argument("--output", type=Path, default=CURRENT_BATCH)

    mark_parser = subparsers.add_parser("mark")
    mark_parser.add_argument("status", choices=sorted(VALID_STATUSES))
    mark_parser.add_argument("codes", nargs="+")
    mark_parser.add_argument("--note", default="")

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("codes", nargs="*")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "sync":
        manifest = sync_manifest()
        print(f"Synced {len(manifest['items'])} questions to {MANIFEST.relative_to(ROOT)}")
        print_summary(manifest)
    elif args.command == "summary":
        print_summary(sync_manifest())
    elif args.command == "next":
        batch = make_batch(args.section, args.limit, args.output)
        print(f"Wrote {len(batch)} items to {args.output}")
        print(" ".join(item["code"] for item in batch))
    elif args.command == "mark":
        manifest = update_status(args.codes, args.status, args.note)
        print(f"Marked {len(args.codes)} item(s) as {args.status}")
        print_summary(manifest)
    elif args.command == "validate":
        errors = validate(args.codes or None)
        if errors:
            raise SystemExit("\n".join(errors))
        print(f"Validated {len(args.codes) if args.codes else 'all available'} image(s)")


if __name__ == "__main__":
    main()
