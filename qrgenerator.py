import argparse
import csv
import os

import qrcode
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# ==========================================
# CONFIG
# ==========================================

OUTPUT_DIR = "output"

LABEL_WIDTH_MM = 30
LABEL_HEIGHT_MM = 40

DPI = 600

QR_PERCENT_HEIGHT = 0.85
TEXT_PERCENT_HEIGHT = 0.15

FONT_FILE = "C:/Windows/Fonts/consolab.ttf"

# ==========================================


def mm_to_px(mm, dpi):
    return int(mm / 25.4 * dpi)


LABEL_WIDTH_PX = mm_to_px(LABEL_WIDTH_MM, DPI)
LABEL_HEIGHT_PX = mm_to_px(LABEL_HEIGHT_MM, DPI)


def fit_font(draw, text, max_width):

    font_size = 48

    while font_size >= 10:

        try:
            font = ImageFont.truetype(
                FONT_FILE,
                font_size
            )
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox(
            (0, 0),
            text,
            font=font
        )

        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            return font

        font_size -= 1

    return font


def create_qr_image(data):

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=1
    )

    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    return img.convert("RGB")


def generate_label(label):

    canvas = Image.new(
        "RGB",
        (
            LABEL_WIDTH_PX,
            LABEL_HEIGHT_PX
        ),
        "white"
    )

    qr_img = create_qr_image(label)

    qr_area_height = int(
        LABEL_HEIGHT_PX * QR_PERCENT_HEIGHT
    )

    text_area_height = LABEL_HEIGHT_PX - qr_area_height

    qr_target_size = min(
        LABEL_WIDTH_PX,
        qr_area_height
    )

    qr_img = qr_img.resize(
        (
            qr_target_size,
            qr_target_size
        ),
        Image.Resampling.NEAREST
    )

    qr_x = (
        LABEL_WIDTH_PX - qr_target_size
    ) // 2

    qr_y = (
        qr_area_height - qr_target_size
    ) // 2

    canvas.paste(
        qr_img,
        (
            qr_x,
            qr_y
        )
    )

    draw = ImageDraw.Draw(canvas)

    font = fit_font(
        draw,
        label,
        LABEL_WIDTH_PX - 20
    )

    bbox = draw.textbbox(
        (0, 0),
        label,
        font=font
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    text_x = (
        LABEL_WIDTH_PX - text_width
    ) // 2

    text_y = (
        qr_area_height
        + (
            text_area_height
            - text_height
        ) // 2
    )

    draw.text(
        (
            text_x,
            text_y
        ),
        label,
        fill="black",
        font=font
    )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    filename = os.path.join(
        OUTPUT_DIR,
        f"{label}.png"
    )

    canvas.save(
        filename,
        dpi=(DPI, DPI)
    )

    print(
        f"Created: {filename}"
    )


def process_csv(csv_file):

    with open(
        csv_file,
        newline="",
        encoding="utf-8-sig"
    ) as f:

        reader = csv.DictReader(f)

        if "label" not in reader.fieldnames:
            raise ValueError(
                "CSV must contain 'label' column"
            )

        for row in reader:

            label = row["label"].strip()

            if label:
                generate_label(label)


def main():

    parser = argparse.ArgumentParser(
        description="QR Stock Label Generator"
    )

    parser.add_argument(
        "--label",
        type=str,
        help="Generate a single label"
    )

    parser.add_argument(
        "--csv",
        type=str,
        help="Generate labels from CSV"
    )

    args = parser.parse_args()

    if args.label:
        generate_label(args.label)

    elif args.csv:
        process_csv(args.csv)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()