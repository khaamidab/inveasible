# Inventory & CRM Utility Scripts

A collection of Python command-line tools for inventory labeling and customer-chat data processing.

| Script | Purpose |
| --- | --- |
| [`qrgenerator.py`](#qrgeneratorpy--qr-stock-label-generator) | Generate printable QR code stock labels |
| [`xls-splitter.py`](#xls-splitterpy--split-large-xlsx-files) | Split a large XLSX file into smaller parts |
| [`chat_exporter.py`](#chat_exporterpy--chat-history-transcript-exporter) | Turn chat history exports into per-room `.txt` transcripts, sorted by DPOTS status |
| [`generate_blast.py`](#generate_blastpy--whatsapp-re-engagement-blast-lists) | Build H1–H90 WhatsApp re-engagement blast lists (Qontak) |
| [`rename_files.py`](#rename_filespy--sequential-batch-rename) | Sequentially rename all files in a folder |

---

## Installation

Requires Python 3.8+.

```bash
pip install "qrcode[pil]" pillow pandas openpyxl xlwt
```

| Package | Used by |
| --- | --- |
| `qrcode[pil]`, `pillow` | `qrgenerator.py` |
| `pandas`, `openpyxl` | `xls-splitter.py`, `chat_exporter.py` |
| `pandas`, `xlwt` | `generate_blast.py` |
| *(standard library only)* | `rename_files.py` |

> `requirements.txt` currently lists only the `qrgenerator.py` dependencies.

---

## Project Structure

```text
qrcode-gen/
├── qrgenerator.py
├── xls-splitter.py
├── chat_exporter.py
├── generate_blast.py
├── rename_files.py
├── requirements.txt
│
├── input/
│   └── skulist.csv          # label list for qrgenerator.py
├── output/                  # generated QR label PNGs
│
├── chat-history/            # chat history CSV/XLSX exports (chat_exporter.py input)
├── dpots.csv                # DPOTS (closed/converted) lookup (chat_exporter.py input)
├── Chat Exports/            # chat_exporter.py output
│   ├── DPOTS/
│   └── non closing/
│
└── blast/
    ├── input/               # Qontak conversation export CSVs (generate_blast.py input)
    └── output/              # generated blast .xls files
```

---

## `qrgenerator.py` — QR Stock Label Generator

Generates high-resolution QR code labels, either one at a time or in bulk from a CSV.

Each label:

* Encodes the label text as the QR data
* Prints the label text below the QR code, auto-shrinking the font to fit on one line
* Has a fixed physical size (30 mm × 30 mm by default)
* Is saved as `output/<label>.png` with DPI metadata embedded for printing

### Usage

Single label:

```bash
python qrgenerator.py --label "MS-04-00"
```

```text
Created: output/MS-04-00.png
```

Batch from CSV:

```bash
python qrgenerator.py --csv input/skulist.csv
```

```text
output/
├── MS-04-00.png
├── MS-06-00.png
├── MB-04-00.png
└── FS-1A-00.png
```

If both `--label` and `--csv` are given, only `--label` is used. With no arguments the help text is shown.

### CSV Format

A single required column named `label`:

```csv
label
MS-04-00
MS-06-00
MB-04-00
FS-1A-00
```

* Blank rows are skipped.
* The value becomes the QR data, the printed text **and** the output filename, so avoid characters that are invalid in filenames (`/ \ : * ? " < > |`).
* UTF-8 files with or without BOM (e.g. saved from Excel) are supported.

### Configuration

Edit the constants at the top of `qrgenerator.py`:

```python
OUTPUT_DIR = "output"

LABEL_WIDTH_MM = 30
LABEL_HEIGHT_MM = 30

DPI = 600

QR_PERCENT_HEIGHT = 0.85   # share of label height for the QR code
TEXT_PERCENT_HEIGHT = 0.15 # share of label height for the text

FONT_FILE = "C:/Windows/Fonts/consolab.ttf"  # Consolas Bold
```

| Setting | Default |
| --- | --- |
| Label size | 30 mm × 30 mm |
| DPI | 600 |
| QR / text area | 85% / 15% |
| Error correction | H (~30% damage tolerance) |
| QR border | 1 module |
| Scaling | Nearest-neighbor (keeps QR edges sharp) |
| Output | PNG |

> **Font:** `FONT_FILE` points to a Windows font. On macOS/Linux, change it to a TTF on your system. If the font cannot be loaded, Pillow's small built-in font is used and auto-sizing has no effect.

### Output Resolution

Pixel size = `mm / 25.4 × DPI` (rounded down).

| DPI | 30 × 30 mm | Typical use |
| --- | --- | --- |
| 203 | 239 × 239 px | Thermal label printers |
| 300 | 354 × 354 px | Thermal / office printers |
| 600 | 708 × 708 px | Default — archive-quality master files |

Keeping `DPI = 600` for master files lets printer software scale down as needed.

### Label Length

The font starts at 48 px and shrinks (down to 10 px) until the text fits the label width.

| Characters | Readability |
| --- | --- |
| ≤ 16 | Excellent |
| 17–24 | Good |
| 25–32 | Acceptable |
| > 32 | Consider shortening |

---

## `xls-splitter.py` — Split Large XLSX Files

Splits a large Excel file into several smaller files with a fixed number of rows each. The header row is repeated in every part.

```bash
python xls-splitter.py data.xlsx
python xls-splitter.py data.xlsx --chunk-size 20000
```

| Argument | Default | Description |
| --- | --- | --- |
| `file` | *(required)* | Input `.xlsx` file |
| `--chunk-size` | `40000` | Rows per output file |

Output files are written **next to the input file**:

```text
data_part_1.xlsx
data_part_2.xlsx
...
```

> Only the first sheet is read. Formatting and formulas are not preserved (values only).

---

## `chat_exporter.py` — Chat History Transcript Exporter

Combines chat history exports, writes one readable `.txt` transcript per chat room, and sorts transcripts into **DPOTS** (closed/converted) vs **non closing** folders.

```bash
python chat_exporter.py
python chat_exporter.py --input-dir chat-history --dpots-file dpots.csv --output-dir "Chat Exports"
```

| Argument | Default | Description |
| --- | --- | --- |
| `--input-dir` | `chat-history` | Folder of chat history `.csv` / `.xlsx` / `.xls` files |
| `--dpots-file` | `dpots.csv` | DPOTS lookup CSV |
| `--output-dir` | `Chat Exports` | Where transcripts are written |

### Input: chat history files

Every file in `--input-dir` must contain these columns (extra columns are ignored; files missing any are skipped with a warning):

```text
room_id, channel, customer_id, customer_name, agent_id, agent_name,
sender_type, outbound_type, text_messages, created_at
```

### Input: DPOTS lookup

A CSV of closed/converted customers. Accepted layouts:

* **With header** — columns `customer_id` and/or `room_id` (headers `phone`, `phone_number`, `customer_phone` are also recognized for header detection).
* **Without header** — 1 column = `customer_id`, 2 columns = `customer_id, room_id`.

A room is classified as DPOTS if its `room_id` **or** its customer phone number matches. Phone numbers are compared by digits only, so `+62812…` and `62812…` match.

### Output

```text
Chat Exports/
├── DPOTS/
│   └── <customer_id> - <room_id>.txt
└── non closing/
    └── <customer_id> - <room_id>.txt
```

Each transcript is sorted by time:

```text
[2026-07-01 10:15:02] Budi: Halo, mau tanya harga
[2026-07-01 10:16:40] Agent Sarah: Halo kak, ...
```

Rows with a missing `room_id` or empty message are skipped. Existing files with the same name are overwritten.

---

## `generate_blast.py` — WhatsApp Re-engagement Blast Lists

Builds follow-up contact lists for Qontak WhatsApp blasts. **HN** = contacts whose conversation started exactly **N days before** the blast date.

```bash
python generate_blast.py --date 01-09-2026
```

| Argument | Default | Description |
| --- | --- | --- |
| `--date` | *(required)* | Blast date, `DD-MM-YYYY` |
| `--input-dir` | `blast/input` | Folder of Qontak conversation export `.csv` files |
| `--output-dir` | `blast/output` | Where `.xls` files are written |

Default folders are resolved relative to the script's location, not the current directory.

### Input

All `.csv` files in the input folder are combined (duplicate `room_id`s are dropped). Required columns:

```text
room_id, name, handler, status, created_at, tag
```

`handler` holds the customer's phone number; `tag` is a comma-separated list.

### Filtering rules

| List | Source date | Excluded tags | Excluded statuses |
| --- | --- | --- | --- |
| H1 | blast date − 1 day | `g3`, `g5`, `vip`, `purchase`, `dpots` | — |
| H2 | blast date − 2 days | same as H1 | — |
| H7, H15, H30, H60, H90 | blast date − N days | H1 tags + `low intent`, `nyasar` | `unassigned`, `resolved` |

Tag and status matching is case-insensitive. Rows without a phone number, and duplicate phone numbers within the same list, are skipped.

### Output

One `.xls` file per list, named `<D Mon> <HN>.xls`, e.g. for `--date 01-09-2026`:

```text
blast/output/
├── 1 Sep H1.xls
├── 1 Sep H2.xls
├── 1 Sep H7.xls
└── ...
```

Columns (all stored as text so phone numbers are not converted to numbers):

| phone_number | full_name | customer_name | company |
| --- | --- | --- | --- |
| 62812… | Budi | Budi | 1 Sep H1 |

Lists with no remaining contacts are not created. A per-list summary (before filtering, excluded by tag/status, final count) is printed at the end.

---

## `rename_files.py` — Sequential Batch Rename

Renames every file in a folder to `<prefix><sep><number>.<ext>`, keeping each file's extension. **Dry run by default.**

```bash
# Preview only
python rename_files.py "need-rename/DPOTS/filtered" --prefix "closed_wins_dp_or_ots" --start 42

# Actually rename
python rename_files.py "need-rename/DPOTS/filtered" --prefix "closed_wins_dp_or_ots" --start 42 --apply
```

Result: `closed_wins_dp_or_ots 42.txt`, `closed_wins_dp_or_ots 43.txt`, …

| Argument | Default | Description |
| --- | --- | --- |
| `folder` | *(required)* | Folder containing the files |
| `--prefix` | *(required)* | Filename prefix |
| `--start` | `1` | First number |
| `--sep` | `" "` (space) | Text between prefix and number |
| `--pad` | `0` | Zero-pad width (`3` → `042`); `0` = no padding |
| `--ext` | all files | Only rename files with this extension, e.g. `.txt` |
| `--sort` | `name` | Numbering order: `name` (case-insensitive) or `mtime` (oldest first) |
| `--log` | `rename_log.csv` | Old → new name mapping, written into the folder |
| `--apply` | off | Perform the rename (otherwise preview only) |

Safety:

* Refuses to run if a target name already exists outside the batch, or two files would get the same name.
* With `--apply`, writes `rename_log.csv` (`old_name,new_name`) into the folder so the rename can be reversed.
* Subfolders are not touched.

> **Tip:** re-running on a folder that already uses the same prefix can make a file's new name equal another file's current name. Rename into a different prefix first, or use a fresh `--start` range that doesn't overlap existing numbers.

---

## License

See [LICENSE](LICENSE).
