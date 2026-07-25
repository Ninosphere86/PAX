#!/usr/bin/env python3
"""Normalize generated registration images and add deterministic teaching captions."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "work" / "registration-current-batch.json"
RAW_DIR = ROOT / "work" / "registration-raw"
FONT = Path("/System/Library/Fonts/Hiragino Sans GB.ttc")
OUTPUT_SIZE = (1280, 720)


def find_raw(code: str) -> Path:
    stem = code.lower().replace("_", "-")
    candidates = [
        RAW_DIR / f"{stem}{suffix}"
        for suffix in (".png", ".jpeg", ".jpg", ".webp")
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"No raw image found for {code} in {RAW_DIR}")


def fitted_font(draw: ImageDraw.ImageDraw, text: str, max_width: int) -> ImageFont.FreeTypeFont:
    for size in range(46, 31, -1):
        font = ImageFont.truetype(str(FONT), size=size, index=0)
        if draw.textlength(text, font=font) <= max_width:
            return font
    return ImageFont.truetype(str(FONT), size=31, index=0)


def finalize(item: dict) -> None:
    source = find_raw(item["code"])
    destination = Path(item["outputPath"])
    destination.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as raw:
        normalized = ImageOps.exif_transpose(raw).convert("RGB")
        canvas = ImageOps.fit(
            normalized,
            OUTPUT_SIZE,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.40),
        )

    overlay = Image.new("RGBA", OUTPUT_SIZE, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle((0, 566, 1280, 720), fill=(9, 24, 45, 235))
    overlay_draw.rectangle((0, 566, 1280, 574), fill=(36, 153, 255, 255))
    overlay_draw.rounded_rectangle(
        (48, 610, 174, 676),
        radius=18,
        fill=(36, 153, 255, 255),
    )

    code_font = ImageFont.truetype(str(FONT), size=28, index=0)
    caption = item["caption"]
    caption_font = fitted_font(overlay_draw, caption, 1000)
    overlay_draw.text(
        (111, 641),
        item["code"],
        font=code_font,
        anchor="mm",
        fill=(255, 255, 255, 255),
    )
    overlay_draw.text(
        (212, 643),
        caption,
        font=caption_font,
        anchor="lm",
        fill=(255, 255, 255, 255),
    )

    final = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    final.save(destination, format="JPEG", quality=91, optimize=True, progressive=True)
    print(f"{item['code']}: {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")


def build_contact_sheet(items: list[dict], destination: Path) -> None:
    columns = min(3, len(items))
    tile_width = 480
    image_height = 270
    label_height = 42
    rows = math.ceil(len(items) / columns)
    sheet = Image.new(
        "RGB",
        (columns * tile_width, rows * (image_height + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.truetype(str(FONT), size=24, index=0)

    for index, item in enumerate(items):
        row, column = divmod(index, columns)
        x = column * tile_width
        y = row * (image_height + label_height)
        with Image.open(item["outputPath"]) as source:
            preview = ImageOps.fit(
                source.convert("RGB"),
                (tile_width, image_height),
                method=Image.Resampling.LANCZOS,
            )
        sheet.paste(preview, (x, y))
        draw.text(
            (x + 14, y + image_height + 7),
            item["code"],
            fill=(17, 30, 21),
            font=label_font,
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, format="JPEG", quality=88, optimize=True)
    print(f"Contact sheet: {destination.relative_to(ROOT)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("codes", nargs="*", help="Question codes; defaults to every item in the batch")
    parser.add_argument(
        "--sheet",
        type=Path,
        help="Contact-sheet output path; defaults to work/registration-review-<first>-<last>.jpg",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    batch = json.loads(BATCH.read_text(encoding="utf-8"))
    requested = set(args.codes)
    selected = [
        item for item in batch if not requested or item["code"] in requested
    ]
    missing = requested - {item["code"] for item in selected}
    if missing:
        raise ValueError("Unknown batch codes: " + ", ".join(sorted(missing)))
    for item in selected:
        finalize(item)
    default_sheet = (
        ROOT
        / "work"
        / f"registration-review-{selected[0]['code']}-{selected[-1]['code']}.jpg"
    )
    build_contact_sheet(selected, args.sheet or default_sheet)


if __name__ == "__main__":
    main()
