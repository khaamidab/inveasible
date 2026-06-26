# QR Stock Label Generator

Generate high-resolution QR code inventory labels from either a single label argument or a CSV file.

Each generated label:

* Encodes the label itself as the QR data
* Displays the label below the QR code
* Automatically adjusts text size to fit
* Uses a fixed physical label size (30mm × 40mm by default)
* Saves each image using the label as the filename
* Exports PNG files with embedded DPI information for printing

---

## Features

* Single label generation
* Batch generation from CSV
* Automatic font scaling for long labels
* High-resolution output (600 DPI by default)
* QR Error Correction Level H
* Sharp QR rendering using nearest-neighbor scaling
* Fixed physical label dimensions
* Inventory-friendly file naming

---

## Example

Input:

```text
MS-MS04-00
```

Generated:

```text
QR Data : MS-MS04-00
Text    : MS-MS04-00
File    : output/MS-MS04-00.png
```

Input:

```text
FS-TS061001A-00
```

Generated:

```text
QR Data : FS-TS061001A-00
Text    : FS-TS061001A-00
File    : output/FS-TS061001A-00.png
```

---

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

or

```bash
pip install qrcode[pil] pillow
```

---

## Project Structure

```text
qrgenerator/
│
├── qrgenerator.py
├── requirements.txt
├── stock.csv
│
└── output/
```

---

## Single Label Generation

Generate a single QR label:

```bash
python qrgenerator.py --label "MS-MS04-00"
```

Output:

```text
output/MS-MS04-00.png
```

---

## CSV Batch Generation

Create a CSV file:

```csv
label
MS-MS04-00
MS-MS04-01
MS-MS04-02
FS-TS061001A-00
```

Run:

```bash
python qrgenerator.py --csv stock.csv
```

Output:

```text
output/
├── MS-MS04-00.png
├── MS-MS04-01.png
├── MS-MS04-02.png
└── FS-TS061001A-00.png
```

---

## CSV Format

Required column:

```csv
label
```

Example:

```csv
label
MS-MS04-00
MS-MS04-01
FS-TS061001A-00
```

Only the `label` column is used.

The value becomes:

* QR Data
* Displayed Text
* Output Filename

---

## Label Specifications

Default configuration:

| Setting          | Value |
| ---------------- | ----- |
| Width            | 30 mm |
| Height           | 40 mm |
| DPI              | 600   |
| QR Area          | 85%   |
| Text Area        | 15%   |
| Error Correction | H     |
| Border           | 1     |
| Output Format    | PNG   |

---

## Output Resolution

Physical size:

```text
30 mm × 40 mm
```

Generated resolution at 600 DPI:

```text
709 × 944 px
```

Other common printer resolutions:

| DPI | Resolution   |
| --- | ------------ |
| 203 | 240 × 320 px |
| 300 | 354 × 472 px |
| 600 | 709 × 944 px |

---

## Printing Recommendations

### Thermal Label Printer

Most thermal printers use:

```text
203 DPI
```

or

```text
300 DPI
```

You can lower the DPI setting in the script if desired.

### Archive Quality

For master files:

```python
DPI = 600
```

This preserves maximum quality and allows printer software to scale down as needed.

---

## Long Label Support

The generator automatically shrinks the text if the label becomes longer.

Examples:

```text
MS-MS04-00
```

```text
FS-TS061001A-00
```

```text
FS-TS061001A-REV02-00
```

The font size is adjusted automatically so the text remains on a single line.

---

## Recommended Label Length

| Characters | Recommendation      |
| ---------- | ------------------- |
| ≤ 16       | Excellent           |
| 17–24      | Good                |
| 25–32      | Acceptable          |
| > 32       | Consider shortening |

---

## Configuration

Inside `qrgenerator.py`:

```python
LABEL_WIDTH_MM = 30
LABEL_HEIGHT_MM = 40

DPI = 600

QR_PERCENT_HEIGHT = 0.85
TEXT_PERCENT_HEIGHT = 0.15
```

Adjust these values to match your printer or sticker stock.

---

## Future Enhancements

Planned features:

* Automatic sequential label generation
* PDF sheet export
* Zebra ZPL export
* Code128 barcode support
* Multiple label templates
* Logo embedding
* GUI version
* Excel (.xlsx) import

Example future usage:

```bash
python qrgenerator.py \
    --prefix MS-MS04 \
    --start 0 \
    --end 999
```

Output:

```text
MS-MS04-000
MS-MS04-001
MS-MS04-002
...
MS-MS04-999
```

---

## License

Internal use / modify as needed.
