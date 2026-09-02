"""
Generate WhatsApp re-engagement blast lists (H1, H2, H7, H15, H30, H60, H90)
from chat-conversation-export CSVs in blast/input, matching the column
layout of the existing blast/output/*.xls samples:

    phone_number | full_name | customer_name | company

"HN" means contacts whose conversation started exactly N days before the
blast date (created_at date == blast_date - N days), still needing a
follow-up. See README notes below / conversation for how this was derived
from the existing 31 Aug H1.xls / H2.xls samples.

Usage:
    python generate_blast.py --date 01-09-2026
"""

import argparse
import datetime
import glob
import os

import pandas as pd
import xlwt

MONTH_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

REQUIRED_COLUMNS = ["room_id", "name", "handler", "status", "created_at", "tag"]

TAG_EXCLUDE_BASE = {"g3", "g5", "vip", "purchase", "dpots"}
TAG_EXCLUDE_EXTENDED = TAG_EXCLUDE_BASE | {"low intent", "nyasar"}
STATUS_EXCLUDE = {"unassigned", "resolved"}

# (label, days before blast date, apply extended tag list + status filter)
CATEGORIES = [
    ("H1", 1, False),
    ("H2", 2, False),
    ("H7", 7, True),
    ("H15", 15, True),
    ("H30", 30, True),
    ("H60", 60, True),
    ("H90", 90, True),
]

OUTPUT_COLUMNS = ["phone_number", "full_name", "customer_name", "company"]


def log(message):
    print(message, flush=True)


def parse_blast_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%d-%m-%Y").date()
    except ValueError:
        raise SystemExit(f"Invalid --date '{date_str}'. Expected format: DD-MM-YYYY, e.g. 01-09-2026")


def date_label(d):
    return f"{d.day} {MONTH_ABBR[d.month]}"


def load_input(input_dir):
    if not os.path.isdir(input_dir):
        raise SystemExit(f"Input folder not found: '{input_dir}'.")

    paths = sorted(glob.glob(os.path.join(input_dir, "*.csv")))
    if not paths:
        raise SystemExit(f"No CSV files found in '{input_dir}'.")

    log(f"Found {len(paths)} input CSV file(s) in '{input_dir}'.")
    frames = []
    for path in paths:
        log(f"  Reading {os.path.basename(path)} ...")
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception as exc:
            log(f"    WARNING: could not read '{path}': {exc} -- skipping file.")
            continue

        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            log(f"    WARNING: '{path}' is missing required column(s) {missing} -- skipping file.")
            continue

        frames.append(df)

    if not frames:
        raise SystemExit("No usable input data was loaded (see warnings above).")

    combined = pd.concat(frames, ignore_index=True)

    before = len(combined)
    combined = combined.drop_duplicates(subset=["room_id"], keep="first")
    dropped = before - len(combined)
    if dropped:
        log(f"  Dropped {dropped} duplicate room_id row(s) found across input file(s).")

    combined["created_date"] = pd.to_datetime(combined["created_at"], errors="coerce").dt.date
    unparsed = int(combined["created_date"].isna().sum())
    if unparsed:
        log(f"  WARNING: {unparsed} row(s) have an unparseable created_at and will be ignored.")
        combined = combined[combined["created_date"].notna()]

    log(f"Loaded {len(combined):,} usable conversation rows.\n")
    return combined


def split_tags(tag_value):
    if tag_value is None or (isinstance(tag_value, float) and pd.isna(tag_value)):
        return []
    text = str(tag_value).strip()
    if not text or text.lower() == "nan":
        return []
    return [t.strip().lower() for t in text.split(",") if t.strip()]


def has_excluded_tag(tag_value, exclude_set):
    return any(t in exclude_set for t in split_tags(tag_value))


def is_excluded_status(status_value, exclude_set):
    if status_value is None or (isinstance(status_value, float) and pd.isna(status_value)):
        return False
    return str(status_value).strip().lower() in exclude_set


def build_output_rows(subset):
    rows = []
    skipped_missing_phone = 0
    seen_phones = set()
    duplicate_phone = 0
    for _, row in subset.iterrows():
        phone = "" if pd.isna(row["handler"]) else str(row["handler"]).strip()
        if not phone:
            skipped_missing_phone += 1
            continue
        if phone in seen_phones:
            duplicate_phone += 1
            continue
        seen_phones.add(phone)
        name = "" if pd.isna(row["name"]) else str(row["name"]).strip()
        rows.append((phone, name, name))
    return rows, skipped_missing_phone, duplicate_phone


def write_blast_file(output_path, rows, company_label):
    wb = xlwt.Workbook(encoding="utf-8")
    sheet = wb.add_sheet("blast")

    text_style = xlwt.easyxf(num_format_str="@")  # force text, avoid Excel auto-numifying long ids

    for col, header in enumerate(OUTPUT_COLUMNS):
        sheet.write(0, col, header)

    for r, (phone, full_name, customer_name) in enumerate(rows, start=1):
        sheet.write(r, 0, phone, text_style)
        sheet.write(r, 1, full_name, text_style)
        sheet.write(r, 2, customer_name, text_style)
        sheet.write(r, 3, company_label, text_style)

    widths = [len(h) for h in OUTPUT_COLUMNS]
    for phone, full_name, customer_name in rows:
        widths[0] = max(widths[0], len(phone))
        widths[1] = max(widths[1], len(full_name))
        widths[2] = max(widths[2], len(customer_name))
    widths[3] = max(widths[3], len(company_label))
    for col, w in enumerate(widths):
        sheet.col(col).width = min(int((w + 2) * 256), 256 * 60)

    wb.save(output_path)


def process_category(df, label, days, apply_extended, blast_date, output_dir, dlabel):
    source_date = blast_date - datetime.timedelta(days=days)
    subset = df[df["created_date"] == source_date]
    total_before = len(subset)

    excluded_by_tag = 0
    excluded_by_status = 0
    rows, skipped_missing_phone, duplicate_phone = [], 0, 0

    if total_before:
        tag_exclude_set = TAG_EXCLUDE_EXTENDED if apply_extended else TAG_EXCLUDE_BASE
        tag_mask = subset["tag"].apply(lambda t: has_excluded_tag(t, tag_exclude_set))
        excluded_by_tag = int(tag_mask.sum())
        remaining = subset[~tag_mask]

        if apply_extended and len(remaining):
            status_mask = remaining["status"].apply(lambda s: is_excluded_status(s, STATUS_EXCLUDE))
            excluded_by_status = int(status_mask.sum())
            remaining = remaining[~status_mask]

        if len(remaining):
            rows, skipped_missing_phone, duplicate_phone = build_output_rows(remaining)

    company_label = f"{dlabel} {label}"
    output_path = os.path.join(output_dir, f"{company_label}.xls")
    file_written = False
    if rows:
        write_blast_file(output_path, rows, company_label)
        file_written = True

    return {
        "label": label,
        "source_date": source_date,
        "total_before": total_before,
        "excluded_by_tag": excluded_by_tag,
        "excluded_by_status": excluded_by_status,
        "skipped_missing_phone": skipped_missing_phone,
        "duplicate_phone": duplicate_phone,
        "final": len(rows),
        "apply_extended": apply_extended,
        "output_path": output_path,
        "file_written": file_written,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate H1/H2/H7/H15/H30/H60/H90 blast lists.")
    parser.add_argument("--date", required=True, help="Blast date, format DD-MM-YYYY, e.g. 01-09-2026")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parser.add_argument("--input-dir", default=os.path.join(script_dir, "blast", "input"))
    parser.add_argument("--output-dir", default=os.path.join(script_dir, "blast", "output"))
    args = parser.parse_args()

    blast_date = parse_blast_date(args.date)
    dlabel = date_label(blast_date)

    os.makedirs(args.output_dir, exist_ok=True)

    df = load_input(args.input_dir)

    results = []
    for label, days, apply_extended in CATEGORIES:
        result = process_category(df, label, days, apply_extended, blast_date, args.output_dir, dlabel)
        results.append(result)
        if result["file_written"]:
            log(f"Generated {os.path.basename(result['output_path'])} ({result['final']} contacts)")
        else:
            log(f"Skipped {os.path.basename(result['output_path'])} -- no contacts left after filtering, file not created.")

    log("\n" + "=" * 50)
    log(f"Blast Date: {blast_date.strftime('%d-%m-%Y')}\n")
    for r in results:
        log(r["label"])
        log(f"Source Date: {r['source_date'].strftime('%d-%m-%Y')}")
        log(f"Total Contacts Before Filtering: {r['total_before']}")
        log(f"Excluded by Tag: {r['excluded_by_tag']}")
        if r["apply_extended"]:
            log(f"Excluded by Status: {r['excluded_by_status']}")
        if r["skipped_missing_phone"]:
            log(f"Skipped (missing phone number): {r['skipped_missing_phone']}")
        if r["duplicate_phone"]:
            log(f"Skipped (duplicate phone number, same file): {r['duplicate_phone']}")
        log(f"Final Output: {r['final']}")
        if not r["file_written"]:
            log("File not created (no contacts left after filtering).")
        log("")


if __name__ == "__main__":
    main()
