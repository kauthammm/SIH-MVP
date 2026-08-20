#!/usr/bin/env python3
"""Deduplicate CSV files: exact row match across all columns, first row kept."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(r"d:\Sih")
ENCODINGS = ("utf-8", "utf-8-sig", "latin-1")


def csv_files(root: Path) -> list[Path]:
    skip_parts = {"node_modules", ".git", "__pycache__", ".venv", "venv"}
    out: list[Path] = []
    for p in root.rglob("*.csv"):
        if any(part in skip_parts for part in p.parts):
            continue
        if p.name.endswith("_cleaned.csv"):
            continue
        out.append(p)
    return sorted(out)


def detect_encoding(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ENCODINGS:
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, "all encodings failed")


def process_file(path: Path) -> dict:
    result = {
        "path": path,
        "before": 0,
        "after": 0,
        "removed": 0,
        "skipped": False,
        "skip_reason": "",
        "error": False,
    }

    if path.stat().st_size == 0:
        result["skipped"] = True
        result["skip_reason"] = "empty file (0 bytes)"
        return result

    try:
        encoding = detect_encoding(path)
    except UnicodeDecodeError as e:
        result["skipped"] = True
        result["skip_reason"] = f"encoding error: {e}"
        result["error"] = True
        return result

    out_path = path.with_name(f"{path.stem}_cleaned{path.suffix}")

    try:
        with path.open("r", encoding=encoding, newline="") as f:
            reader = csv.reader(f)
            try:
                rows = list(reader)
            except csv.Error as e:
                result["skipped"] = True
                result["skip_reason"] = f"csv parse error: {e}"
                result["error"] = True
                return result
    except OSError as e:
        result["skipped"] = True
        result["skip_reason"] = str(e)
        result["error"] = True
        return result

    if not rows:
        result["skipped"] = True
        result["skip_reason"] = "empty file (0 bytes)"
        return result

    header = rows[0]
    data_rows = rows[1:]
    result["before"] = len(data_rows)

    if result["before"] == 0:
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
        result["after"] = 0
        result["removed"] = 0
        return result

    seen: set[tuple] = set()
    unique_rows: list[list[str]] = []
    for row in data_rows:
        key = tuple(row)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    result["after"] = len(unique_rows)
    result["removed"] = result["before"] - result["after"]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(unique_rows)

    return result


def main() -> None:
    files = csv_files(ROOT)
    total_before = 0
    total_after = 0
    total_removed = 0
    processed = 0
    dup_files: list[tuple[str, int]] = []
    skipped: list[tuple[str, str]] = []

    for path in files:
        r = process_file(path)
        if r["skipped"]:
            skipped.append((str(path.relative_to(ROOT)), r["skip_reason"]))
            if r["skip_reason"].startswith("empty file"):
                processed += 1
            continue

        processed += 1
        total_before += r["before"]
        total_after += r["after"]
        total_removed += r["removed"]
        if r["removed"] > 0:
            dup_files.append((str(path.relative_to(ROOT)), r["removed"]))

    print(f"Total CSV files processed: {processed}")
    print(f"Total rows before deduplication: {total_before}")
    print(f"Total rows after deduplication: {total_after}")
    print(f"Total duplicate rows removed: {total_removed}")
    print("Files with duplicates:")
    if dup_files:
        for name, count in dup_files:
            print(f"  {name}: {count}")
    else:
        print("  (none)")
    if skipped:
        print("Skipped files:")
        for name, reason in skipped:
            print(f"  {name}: {reason}")


if __name__ == "__main__":
    main()
