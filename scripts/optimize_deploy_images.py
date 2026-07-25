#!/usr/bin/env python3
"""Reduce only built site images so production stays within hosting limits."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CLIENT_DIR = ROOT / "dist" / "client"
IMAGE_PREFIX = "question-images"


def optimize(path: Path) -> tuple[int, int]:
    before = path.stat().st_size
    temporary = path.with_name(path.name + ".deploy-opt")

    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source)
        suffix = path.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            image.convert("RGB").save(
                temporary,
                format="JPEG",
                quality=80,
                optimize=True,
                progressive=True,
            )
        elif suffix == ".webp":
            image.convert("RGB").save(
                temporary,
                format="WEBP",
                quality=82,
                method=6,
            )
        elif suffix == ".png":
            image.save(temporary, format="PNG", optimize=True)
        else:
            return before, before

    after = temporary.stat().st_size
    if after < before:
        temporary.replace(path)
        return before, after
    temporary.unlink()
    return before, before


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-dir",
        type=Path,
        default=DEFAULT_CLIENT_DIR,
        help="Built client directory; defaults to dist/client.",
    )
    args = parser.parse_args()

    candidates = sorted(
        path
        for directory in args.client_dir.glob(f"{IMAGE_PREFIX}*")
        if directory.is_dir()
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    before_total = 0
    after_total = 0
    changed = 0
    for path in candidates:
        before, after = optimize(path)
        before_total += before
        after_total += after
        changed += after < before

    saved = before_total - after_total
    print(
        f"Optimized {changed}/{len(candidates)} deploy images: "
        f"{before_total / 1024 / 1024:.1f} MiB -> "
        f"{after_total / 1024 / 1024:.1f} MiB "
        f"(saved {saved / 1024 / 1024:.1f} MiB)"
    )


if __name__ == "__main__":
    main()
