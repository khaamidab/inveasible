"""
Combine chat history CSV/XLSX files, split each chat room into a readable
.txt transcript, and sort the transcripts into "DPOTS" vs "non closing"
folders based on a DPOTS (closed/converted) lookup file.

Usage:
    python chat_exporter.py
    python chat_exporter.py --input-dir chat-history --dpots-file dpots.csv --output-dir "Chat Exports"
"""

import argparse
import glob
import os
import re
import sys

import pandas as pd

CHAT_COLUMNS = [
    "room_id",
    "channel",
    "customer_id",
    "customer_name",
    "agent_id",
    "agent_name",
    "sender_type",
    "outbound_type",
    "text_messages",
    "created_at",
]

STRING_DTYPES = {col: str for col in CHAT_COLUMNS if col != "created_at"}

INVALID_FILENAME_CHARS = re.compile(r'[\\/*?:"<>|\r\n]+')


def log(message):
    print(message, flush=True)


def clean(value):
    """Normalize a cell value to a stripped string, or '' if empty/NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def sanitize_filename(name):
    name = INVALID_FILENAME_CHARS.sub("_", name).strip(" .")
    return name if name else "unknown"


def normalize_phone(value):
    """Keep digits only so '+62...' / '62...' / '62...0' style variations still match."""
    return re.sub(r"\D", "", value or "")


# ---------------------------------------------------------------------------
# Step 1: Combine chat history files
# ---------------------------------------------------------------------------
def load_chat_history(input_dir):
    paths = sorted(
        glob.glob(os.path.join(input_dir, "*.csv"))
        + glob.glob(os.path.join(input_dir, "*.xlsx"))
        + glob.glob(os.path.join(input_dir, "*.xls"))
    )
    if not paths:
        log(f"No CSV/XLSX files found in '{input_dir}'.")
        sys.exit(1)

    log(f"Found {len(paths)} chat history file(s) in '{input_dir}'.")
    frames = []
    for i, path in enumerate(paths, start=1):
        log(f"  [{i}/{len(paths)}] Reading {os.path.basename(path)} ...")
        try:
            if path.lower().endswith(".csv"):
                df = pd.read_csv(path, dtype=STRING_DTYPES, encoding="utf-8")
            else:
                df = pd.read_excel(path, dtype=STRING_DTYPES, engine="openpyxl")
        except Exception as exc:
            log(f"      WARNING: could not read '{path}': {exc} -- skipping file.")
            continue

        missing_cols = [c for c in CHAT_COLUMNS if c not in df.columns]
        if missing_cols:
            log(f"      WARNING: '{path}' is missing columns {missing_cols} -- skipping file.")
            continue

        df = df[CHAT_COLUMNS]
        log(f"      -> {len(df):,} rows")
        frames.append(df)

    if not frames:
        log("No usable chat history data was loaded. Aborting.")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    log(f"Combined chat history: {len(combined):,} rows total.\n")
    return combined


# ---------------------------------------------------------------------------
# Step 2: Load DPOTS lookup
# ---------------------------------------------------------------------------
def load_dpots(dpots_path):
    log(f"Loading DPOTS list from '{dpots_path}' ...")

    raw = pd.read_csv(dpots_path, dtype=str, header=None)
    first_row = [clean(v).lower() for v in raw.iloc[0].tolist()]
    known_headers = {"customer_id", "room_id", "phone", "phone_number", "customer_phone"}
    has_header = any(v in known_headers for v in first_row)

    if has_header:
        df = pd.read_csv(dpots_path, dtype=str)
        df.columns = [c.strip().lower() for c in df.columns]
    else:
        ncols = raw.shape[1]
        if ncols == 1:
            df = raw.rename(columns={0: "customer_id"})
        else:
            df = raw.rename(columns={0: "customer_id", 1: "room_id"})

    dpots_room_ids = set()
    if "room_id" in df.columns:
        dpots_room_ids = {clean(v) for v in df["room_id"].tolist() if clean(v)}

    dpots_customer_ids = set()
    if "customer_id" in df.columns:
        dpots_customer_ids = {
            normalize_phone(clean(v)) for v in df["customer_id"].tolist() if clean(v)
        }

    log(
        f"Loaded {len(dpots_room_ids)} DPOTS room_id(s) and "
        f"{len(dpots_customer_ids)} DPOTS customer_id/phone number(s).\n"
    )
    return dpots_room_ids, dpots_customer_ids


# ---------------------------------------------------------------------------
# Step 3-5: Group, format, categorize and export
# ---------------------------------------------------------------------------
def display_name(row):
    if row["sender_type"] == "customer":
        return row["customer_name"] or row["sender_type"] or "unknown"
    return row["agent_name"] or row["sender_type"] or "unknown"


def export_chats(combined, dpots_room_ids, dpots_customer_ids, output_dir):
    dpots_dir = os.path.join(output_dir, "DPOTS")
    non_closing_dir = os.path.join(output_dir, "non closing")
    os.makedirs(dpots_dir, exist_ok=True)
    os.makedirs(non_closing_dir, exist_ok=True)

    for col in ("room_id", "customer_id", "customer_name", "agent_name", "sender_type", "text_messages"):
        combined[col] = combined[col].fillna("").astype(str).str.strip()

    combined["created_at"] = pd.to_datetime(combined["created_at"], errors="coerce")

    before = len(combined)
    combined = combined[combined["room_id"] != ""]
    dropped_missing_room = before - len(combined)
    if dropped_missing_room:
        log(f"Skipping {dropped_missing_room:,} row(s) with a missing room_id.")

    before = len(combined)
    combined = combined[combined["text_messages"] != ""]
    dropped_empty_text = before - len(combined)
    if dropped_empty_text:
        log(f"Skipping {dropped_empty_text:,} row(s) with an empty message.")

    room_ids = combined["room_id"].unique()
    total_rooms = len(room_ids)
    log(f"Exporting {total_rooms:,} chat room(s) ...\n")

    grouped = combined.groupby("room_id", sort=False)

    dpots_count = 0
    non_closing_count = 0
    skipped_rooms = 0
    progress_step = max(1, total_rooms // 20)

    for i, (room_id, group) in enumerate(grouped, start=1):
        try:
            group = group.sort_values("created_at", kind="mergesort", na_position="last")

            customer_ids_in_group = [c for c in group["customer_id"].tolist() if c]
            customer_id = customer_ids_in_group[0] if customer_ids_in_group else "unknown"

            is_dpots = room_id in dpots_room_ids or normalize_phone(customer_id) in dpots_customer_ids

            lines = []
            for _, row in group.iterrows():
                timestamp = row["created_at"]
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(timestamp) else "unknown time"
                name = display_name(row)
                lines.append(f"[{timestamp_str}] {name}: {row['text_messages']}")

            if not lines:
                skipped_rooms += 1
                continue

            filename = sanitize_filename(f"{customer_id} - {room_id}") + ".txt"
            target_dir = dpots_dir if is_dpots else non_closing_dir
            output_path = os.path.join(target_dir, filename)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            if is_dpots:
                dpots_count += 1
            else:
                non_closing_count += 1

        except Exception as exc:
            skipped_rooms += 1
            log(f"  WARNING: failed to export room_id '{room_id}': {exc}")
            continue

        if i % progress_step == 0 or i == total_rooms:
            log(f"  [{i:,}/{total_rooms:,}] rooms processed "
                f"(DPOTS: {dpots_count:,}, non closing: {non_closing_count:,})")

    log("\nDone!")
    log(f"  DPOTS transcripts:       {dpots_count:,} -> {dpots_dir}")
    log(f"  Non closing transcripts: {non_closing_count:,} -> {non_closing_dir}")
    if skipped_rooms:
        log(f"  Rooms skipped due to errors/no content: {skipped_rooms:,}")


def main():
    parser = argparse.ArgumentParser(description="Export chat history rooms into per-room .txt transcripts.")
    parser.add_argument("--input-dir", default="chat-history", help="Folder containing chat history CSV/XLSX files.")
    parser.add_argument("--dpots-file", default="dpots.csv", help="Path to the DPOTS lookup file.")
    parser.add_argument("--output-dir", default="Chat Exports", help="Folder to write exported transcripts into.")
    args = parser.parse_args()

    combined = load_chat_history(args.input_dir)
    dpots_room_ids, dpots_customer_ids = load_dpots(args.dpots_file)
    export_chats(combined, dpots_room_ids, dpots_customer_ids, args.output_dir)


if __name__ == "__main__":
    main()
