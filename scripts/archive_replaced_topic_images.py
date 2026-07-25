#!/usr/bin/env python3
"""Archive replaced special-topic source images without breaking active references."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUESTION_BANK = ROOT / "app" / "question-bank.json"
MANIFEST = ROOT / "ops" / "special-topic-image-pipeline.json"
DEFAULT_DESTINATION = ROOT / "public" / "question-images" / "旧图" / "专项题型类-T"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_destination(directory: Path, source: Path) -> Path:
    candidate = directory / source.name
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = directory / f"{source.stem}-{index}{source.suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        default=DEFAULT_DESTINATION,
        help="Archive folder; defaults to the question-images/旧图 folder.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Copy or move files. Without this flag the command is a dry run.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    questions = json.loads(QUESTION_BANK.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    approved = {
        item["code"]: item
        for item in manifest["items"]
        if item["status"] == "approved"
    }
    topic_questions = [
        item for item in questions if item.get("code") in approved
    ]

    references: dict[str, list[str]] = defaultdict(list)
    for question in questions:
        image = question.get("image", "")
        if image:
            references[image].append(question.get("code", question.get("id", "")))

    by_source: dict[str, list[dict]] = defaultdict(list)
    for question in topic_questions:
        old_image = approved[question["code"]].get("sourceImage", "")
        if old_image and old_image != approved[question["code"]]["outputImage"]:
            by_source[old_image].append(question)

    plan = []
    for old_image, items in sorted(by_source.items()):
        source = ROOT / "public" / old_image.lstrip("/")
        active_codes = references.get(old_image, [])
        action = "copy" if active_codes else "move"
        plan.append(
            {
                "source": source,
                "oldImage": old_image,
                "codes": [item["code"] for item in items],
                "newImages": [
                    approved[item["code"]]["outputImage"] for item in items
                ],
                "activeReferences": active_codes,
                "action": action,
            }
        )

    print(
        f"{'APPLY' if args.apply else 'DRY RUN'}: {len(plan)} unique old images; "
        f"{sum(item['action'] == 'move' for item in plan)} move, "
        f"{sum(item['action'] == 'copy' for item in plan)} copy because still referenced"
    )

    if not args.apply:
        for item in plan:
            print(
                f"{item['action']:4} {item['oldImage']} "
                f"codes={','.join(item['codes'])} "
                f"active={','.join(item['activeReferences']) or '-'}"
            )
        return

    args.destination.mkdir(parents=True, exist_ok=True)
    archive_items = []
    for item in plan:
        source = item["source"]
        if not source.is_file():
            archive_items.append(
                {
                    **{key: value for key, value in item.items() if key != "source"},
                    "status": "missing",
                }
            )
            continue
        destination = unique_destination(args.destination, source)
        file_hash = sha256(source)
        if item["action"] == "move":
            shutil.move(str(source), str(destination))
        else:
            shutil.copy2(source, destination)
        archive_items.append(
            {
                **{key: value for key, value in item.items() if key != "source"},
                "status": "archived",
                "archivePath": "/" + str(destination.relative_to(ROOT / "public")),
                "sha256": file_hash,
            }
        )

    index = {
        "category": "专项题型类-T",
        "archivedAt": str(date.today()),
        "destination": str(
            args.destination.relative_to(ROOT)
            if args.destination.is_relative_to(ROOT)
            else args.destination
        ),
        "items": archive_items,
    }
    (args.destination / "archive-index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote archive index with {len(archive_items)} entries.")


if __name__ == "__main__":
    main()
