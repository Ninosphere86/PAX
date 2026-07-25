#!/usr/bin/env python3
"""Manage the resumable image-production pipeline for registration questions."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
QUESTION_BANK = ROOT / "app" / "question-bank.json"
MANIFEST = ROOT / "ops" / "registration-image-pipeline.json"
CURRENT_BATCH = ROOT / "work" / "registration-current-batch.json"
IMAGE_DIR = ROOT / "public" / "question-images-registration-v2"
LOCAL_ARCHIVE_ROOT = ROOT.parent / "题库图片" / "旧图"
ARCHIVE_DIR = LOCAL_ARCHIVE_ROOT / "登记管理类-M"
CATEGORY = "登记管理类-M"
VALID_STATUSES = {"pending", "generated", "approved", "redo", "review_required"}

SECTION_NOTES = {
    "M01": (
        "Registration and road-use rules: preserve the exact vehicle status, service-office "
        "step, road type, emergency-lane geometry, warning distance and legal consequence."
    ),
    "M02": (
        "Scrapped and assembled vehicles: distinguish assembled, suspected-scrapped and "
        "legally scrapped vehicles, and show the exact enforcement or cancellation outcome."
    ),
    "M03": (
        "Replacement, filing and review rules: distinguish driving licence, vehicle licence, "
        "registration certificate and number plate, and preserve the correct office and timing."
    ),
}

CAPTIONS = {
    "M01_01": "未注册车辆｜凭临时行驶车号牌上路",
    "M01_02": "高速故障｜开双闪｜来车方向150米外设警告标志",
    "M01_03": "转让登记前｜违法行为和交通事故先处理完毕",
    "M01_04": "依法查封、扣押｜不予办理注册登记",
    "M01_05": "被盗抢骗车辆｜不予办理注册登记",
    "M01_06": "车型或技术参数不符公告｜不予办理注册登记",
}

SPECIAL_NOTES = {
    "M01_01": (
        "Show a newly purchased passenger car without a permanent metal plate at a Chinese "
        "vehicle-service exit. A temporary paper permit is visibly mounted inside the windscreen. "
        "Do not show a borrowed or permanent plate."
    ),
    "M01_02": (
        "Show one disabled passenger car fully inside a correctly proportioned expressway "
        "emergency lane with hazard lights on. Put one warning triangle at least 150 metres behind "
        "the car in the direction of approaching traffic. Occupants wait safely beyond the guardrail."
    ),
    "M01_03": (
        "Show one coherent Chinese vehicle-transfer service scene: the transfer application is "
        "paused until both an outstanding traffic-violation record and an accident case are cleared. "
        "Use visual status symbols, not invented legal documents."
    ),
    "M01_04": (
        "Show a clearly identified seized passenger car in an official impound area, secured by "
        "a wheel clamp and evidence seal, while registration processing is stopped."
    ),
    "M01_05": (
        "Show a recovered stolen passenger car in a police evidence area, with an investigator "
        "checking the vehicle identity. Registration processing must be visibly blocked."
    ),
    "M01_06": (
        "Show a vehicle inspection bay where an inspector compares the actual model/VIN and "
        "technical specification with an approved product record and finds a mismatch. Do not "
        "change this into a routine maintenance scene."
    ),
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
    return f"/question-images-registration-v2/{filename}"


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
            status = "generated" if output_path(question).is_file() else "pending"

        items.append(
            {
                "code": code,
                "section": question["section"],
                "status": status,
                "outputImage": output_image(question),
                "sourceImage": (old or {}).get("sourceImage", question.get("image", "")),
                "questionHash": digest,
                "updatedAt": (old or {}).get("updatedAt", str(date.today())),
                "note": (old or {}).get("note", ""),
            }
        )

    manifest = {
        "category": CATEGORY,
        "schemaVersion": 1,
        "batchSize": 6,
        "updatedAt": str(date.today()),
        "items": items,
    }
    save_manifest(manifest)
    return manifest


def build_prompt(question: dict) -> str:
    prompt = f"""Use case: photorealistic-natural
Asset type: 16:9 educational cover image for a Chinese driving-theory mini program
Question code: {question["code"]}
Authoritative question: {question["title"]}
Authoritative correct-answer meaning: {answer_text(question)}
Detailed legal explanation: {question.get("detailedExplanation", "")}
Primary request: Make the single tested rule immediately understandable at a 375px display width.
Section accuracy note: {SECTION_NOTES[question["section"]]}
Style: polished realistic editorial photography in contemporary China, believable people, vehicles, roads and service environments.
Composition: one coherent scene, medium-wide 16:9 framing, tested subject large and clear, important action in the upper 76 percent, quiet lower area reserved for a deterministic caption.
Accuracy hierarchy: question and correct answer first; then vehicle/person identity, road geometry, number, distance, document type and legal result.
Text constraints: generate no readable words, digits, licence-plate number, official seal, logo or watermark. Exact Chinese teaching text will be added later as a deterministic overlay.
Avoid: collage, split-screen poster, mirrored road relationships, swapped vehicle identity, generic stock scene, fake official branding, distorted hands, unsafe false behaviour presented as correct."""
    if question["code"] in SPECIAL_NOTES:
        prompt += "\nQuestion-specific invariant: " + SPECIAL_NOTES[question["code"]]
    return prompt


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
                "caption": CAPTIONS.get(item["code"], question.get("explanation", "")),
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
    requested = set(codes or [])
    selected = [
        item
        for item in manifest["items"]
        if item["code"] in requested if codes
    ] if codes else [
        item for item in manifest["items"] if item["status"] != "pending"
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


def apply_approved() -> int:
    manifest = sync_manifest()
    approved = {
        item["code"]: item
        for item in manifest["items"]
        if item["status"] == "approved"
    }
    missing = [
        item["outputImage"]
        for item in approved.values()
        if not (ROOT / "public" / item["outputImage"].lstrip("/")).is_file()
    ]
    if missing:
        raise RuntimeError("Approved images are missing:\n" + "\n".join(missing))

    questions = json.loads(QUESTION_BANK.read_text(encoding="utf-8"))
    updated = 0
    for question in questions:
        item = approved.get(question.get("code"))
        if not item or question.get("image") == item["outputImage"]:
            continue
        question["image"] = item["outputImage"]
        question["updatedAt"] = str(date.today())
        updated += 1
    QUESTION_BANK.write_text(
        json.dumps(questions, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return updated


def archive_replaced(apply: bool) -> list[dict]:
    manifest = sync_manifest()
    approved = {
        item["code"]: item
        for item in manifest["items"]
        if item["status"] == "approved"
    }
    questions = json.loads(QUESTION_BANK.read_text(encoding="utf-8"))
    references: dict[str, list[str]] = defaultdict(list)
    for question in questions:
        image = question.get("image", "")
        if image:
            references[image].append(question.get("code", question.get("id", "")))

    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in approved.values():
        if item["sourceImage"] and item["sourceImage"] != item["outputImage"]:
            grouped[item["sourceImage"]].append(item)

    index_path = ARCHIVE_DIR / "archive-index.json"
    previous_records = {}
    if index_path.is_file():
        previous_index = json.loads(index_path.read_text(encoding="utf-8"))
        previous_records = {
            item["oldImage"]: item
            for item in previous_index.get("items", [])
            if item.get("status") == "archived" and item.get("archivePath")
        }

    plan = []
    for old_image, items in sorted(grouped.items()):
        source = ROOT / "public" / old_image.lstrip("/")
        active_codes = references.get(old_image, [])
        action = "copy" if active_codes else "move"
        record = {
            "oldImage": old_image,
            "codes": [item["code"] for item in items],
            "newImages": [item["outputImage"] for item in items],
            "activeReferences": active_codes,
            "action": action,
        }
        if apply:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            previous = previous_records.get(old_image)
            previous_destination = None
            if previous:
                saved_path = previous["archivePath"]
                if saved_path.startswith("/question-images/旧图/"):
                    previous_destination = (
                        LOCAL_ARCHIVE_ROOT
                        / saved_path.removeprefix("/question-images/旧图/")
                    )
                else:
                    candidate = Path(saved_path)
                    previous_destination = (
                        candidate
                        if candidate.is_absolute()
                        else ROOT.parent / candidate
                    )
            if previous_destination and previous_destination.is_file():
                record["archivePath"] = str(
                    previous_destination.relative_to(ROOT.parent)
                )
                record["sha256"] = hashlib.sha256(
                    previous_destination.read_bytes()
                ).hexdigest()
                record["status"] = "archived"
                plan.append(record)
                continue

            destination = ARCHIVE_DIR / source.name
            index = 2
            while destination.exists() and source.exists():
                destination = ARCHIVE_DIR / f"{source.stem}-{index}{source.suffix}"
                index += 1
            if source.is_file():
                if action == "move":
                    shutil.move(str(source), str(destination))
                else:
                    shutil.copy2(source, destination)
                record["archivePath"] = str(destination.relative_to(ROOT.parent))
                record["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
                record["status"] = "archived"
            else:
                record["status"] = "missing"
        plan.append(record)

    if apply:
        index_path.write_text(
            json.dumps(
                {
                    "category": CATEGORY,
                    "archivedAt": str(date.today()),
                    "items": plan,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return plan


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
    subparsers.add_parser("apply")

    next_parser = subparsers.add_parser("next")
    next_parser.add_argument("--section", choices=sorted(SECTION_NOTES))
    next_parser.add_argument("--limit", type=int, default=6)
    next_parser.add_argument("--output", type=Path, default=CURRENT_BATCH)

    mark_parser = subparsers.add_parser("mark")
    mark_parser.add_argument("status", choices=sorted(VALID_STATUSES))
    mark_parser.add_argument("codes", nargs="+")
    mark_parser.add_argument("--note", default="")

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("codes", nargs="*")

    archive_parser = subparsers.add_parser("archive")
    archive_parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "sync":
        manifest = sync_manifest()
        print(f"Synced {len(manifest['items'])} questions")
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
    elif args.command == "apply":
        print(f"Applied {apply_approved()} approved image reference(s)")
    elif args.command == "archive":
        plan = archive_replaced(args.apply)
        action = "Applied" if args.apply else "Planned"
        print(f"{action} archive for {len(plan)} unique source image(s)")


if __name__ == "__main__":
    main()
