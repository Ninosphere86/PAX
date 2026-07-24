#!/usr/bin/env python3
"""Build a labelled contact sheet for question-bank image review."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--width", type=int, default=480)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    font = ImageFont.load_default(size=24)
    image_height = round(args.width * 9 / 16)
    label_height = 44
    rows = math.ceil(len(args.images) / args.columns)
    sheet = Image.new(
        "RGB",
        (args.columns * args.width, rows * (image_height + label_height)),
        "white",
    )
    draw = ImageDraw.Draw(sheet)

    for index, path in enumerate(args.images):
        row, column = divmod(index, args.columns)
        x = column * args.width
        y = row * (image_height + label_height)
        with Image.open(path) as source:
            image = source.convert("RGB")
            image.thumbnail((args.width, image_height))
            sheet.paste(image, (x, y))
        label = path.stem.removesuffix("-v2").replace("-", "_").upper()
        draw.text((x + 12, y + image_height + 8), label, fill="black", font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=88)


if __name__ == "__main__":
    main()
