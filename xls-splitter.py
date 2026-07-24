import pandas as pd
import argparse
import os

parser = argparse.ArgumentParser(description="Split a large XLSX file into smaller parts")
parser.add_argument("file", help="Path to the input XLSX file")
parser.add_argument("--chunk-size", type=int, default=40000, help="Number of rows per file (default: 40000)")
args = parser.parse_args()

input_path = os.path.abspath(args.file)
output_dir = os.path.dirname(input_path)
base_name = os.path.splitext(os.path.basename(input_path))[0]

print(f"Reading {input_path}...")
df = pd.read_excel(input_path, engine="openpyxl")
total_rows = len(df)
total_parts = -(-total_rows // args.chunk_size)  # ceiling division
print(f"Splitting {total_rows:,} rows into {total_parts} files...\n")

for i in range(0, total_rows, args.chunk_size):
    chunk = df[i:i + args.chunk_size]
    part_num = (i // args.chunk_size) + 1
    output_path = os.path.join(output_dir, f"{base_name}_part_{part_num}.xlsx")
    chunk.to_excel(output_path, index=False)
    print(f"  [{part_num}/{total_parts}] Rows {i+1:,}–{i+len(chunk):,} → {output_path}")

print("\nDone!")