"""
Batch-rename all files in a folder to a sequential "<prefix><sep><number>.<ext>"
pattern, e.g. "closed_wins_dp_or_ots 42.txt", "closed_wins_dp_or_ots 43.txt", ...

Reusable across different folders/batches by passing different arguments --
nothing about the naming scheme is hardcoded.

Usage:
    python rename_files.py "C:\\path\\to\\folder" --prefix "closed_wins_dp_or_ots" --start 42

Useful options:
    --sep " "        Text between prefix and number (default: single space)
    --pad 0           Zero-pad the number to this width (e.g. 3 -> 042). 0 = no padding.
    --ext .txt        Only rename files with this extension (default: all files)
    --sort name|mtime How to order files before numbering them (default: name)
    --log rename_log.csv  Where to write the old-name -> new-name mapping (for undo)

Without --apply, this only prints a preview (dry run). Pass --apply to
actually rename the files.
"""

import argparse
import csv
import os
import sys


def collect_files(folder, ext_filter, sort_mode, exclude_name=None):
    entries = [
        f for f in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, f)) and f != exclude_name
    ]
    if ext_filter:
        ext_filter = ext_filter.lower()
        if not ext_filter.startswith("."):
            ext_filter = "." + ext_filter
        entries = [f for f in entries if os.path.splitext(f)[1].lower() == ext_filter]

    if sort_mode == "mtime":
        entries.sort(key=lambda f: os.path.getmtime(os.path.join(folder, f)))
    else:
        entries.sort(key=str.lower)

    return entries


def build_plan(folder, files, prefix, sep, start, pad):
    plan = []
    number = start
    for old_name in files:
        ext = os.path.splitext(old_name)[1]
        number_str = str(number).zfill(pad) if pad else str(number)
        new_name = f"{prefix}{sep}{number_str}{ext}"
        plan.append((old_name, new_name))
        number += 1
    return plan


def main():
    parser = argparse.ArgumentParser(description="Sequentially rename files in a folder.")
    parser.add_argument("folder", help="Folder containing the files to rename.")
    parser.add_argument("--prefix", required=True, help='Filename prefix, e.g. "closed_wins_dp_or_ots"')
    parser.add_argument("--start", type=int, default=1, help="Starting number (default: 1)")
    parser.add_argument("--sep", default=" ", help='Text between prefix and number (default: " ")')
    parser.add_argument("--pad", type=int, default=0, help="Zero-pad number width, 0 = no padding (default: 0)")
    parser.add_argument("--ext", default=None, help='Only rename files with this extension, e.g. ".txt"')
    parser.add_argument("--sort", choices=["name", "mtime"], default="name", help="Order files by name or modified time (default: name)")
    parser.add_argument("--log", default="rename_log.csv", help="CSV file to record old->new name mapping (default: rename_log.csv)")
    parser.add_argument("--apply", action="store_true", help="Actually perform the rename (default is a dry run preview only)")
    args = parser.parse_args()

    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        print(f"Folder not found: {folder}")
        sys.exit(1)

    files = collect_files(folder, args.ext, args.sort, exclude_name=args.log)
    if not files:
        print(f"No matching files found in '{folder}'.")
        sys.exit(0)

    print(f"Found {len(files)} file(s) in '{folder}' (sorted by {args.sort}).")
    plan = build_plan(folder, files, args.prefix, args.sep, args.start, args.pad)

    # Guard against collisions: a target name that already exists on disk
    # (and isn't itself part of this rename batch), or duplicate targets.
    existing = set(os.listdir(folder))
    old_names = {old for old, _ in plan}
    seen_targets = {}
    problems = []
    for old_name, new_name in plan:
        if new_name in seen_targets:
            problems.append(f"Duplicate target name '{new_name}' for '{old_name}' and '{seen_targets[new_name]}'")
        seen_targets[new_name] = old_name
        if new_name in existing and new_name not in old_names and new_name != old_name:
            problems.append(f"Target '{new_name}' already exists and is not part of this rename batch")

    if problems:
        print("\nRefusing to proceed -- found problem(s):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    print("\nPreview:")
    for old_name, new_name in plan:
        marker = "  (unchanged)" if old_name == new_name else ""
        print(f"  {old_name}  ->  {new_name}{marker}")

    if not args.apply:
        print(f"\nDry run only -- no files were renamed. Re-run with --apply to perform the rename.")
        return

    log_path = os.path.join(folder, args.log)
    renamed = 0
    with open(log_path, "w", newline="", encoding="utf-8") as log_file:
        writer = csv.writer(log_file)
        writer.writerow(["old_name", "new_name"])
        for old_name, new_name in plan:
            if old_name == new_name:
                continue
            old_path = os.path.join(folder, old_name)
            new_path = os.path.join(folder, new_name)
            os.rename(old_path, new_path)
            writer.writerow([old_name, new_name])
            renamed += 1
            print(f"  Renamed: {old_name} -> {new_name}")

    print(f"\nDone! Renamed {renamed} file(s). Mapping log written to '{log_path}'.")


if __name__ == "__main__":
    main()
