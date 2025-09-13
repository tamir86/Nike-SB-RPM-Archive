"""
log_models.py
===================

This script automates the process of building a Nike SB RPM backpack archive from
photographs.  When you download product photos into a folder and run this
script with the keyword ``log!``, the script examines the filenames, extracts
the Nike style and colour codes, looks up the associated product information
from a simple CSV database, and writes the results to a new CSV file.

The script expects image files to be named using the following strict format:

    STYLECODE-COLORCODE_descriptor_index.ext

Where ``STYLECODE`` is a six‑digit Nike style code and ``COLORCODE`` is a three‑
digit colour code.  For example, the filename ``BA2449-089_front_01.jpg``
contains the style code ``BA2449`` and colour code ``089``.  Nike uses this
six‑digit/two‑digit format widely; according to Tempo.co, the first six
characters in a nine‑character UPC identify the style, and the last three
characters identify the colour【623886238471741†L101-L105】.

To provide product details, you must supply a CSV file named
``model_data.csv`` in the same directory.  This file should contain one row per
style/colour combination with the following columns:

    style_code, color_code, name, color_name, release_date, notes

For example:

    style_code,color_code,name,color_name,release_date,notes
    BA2449,089,SB RPM Backpack,Elephant Print,2013-05-01,Part of the "Elephant Pack" collection

The script scans the specified image directory for files matching the naming
pattern, looks up each unique style/colour combination in ``model_data.csv``,
and writes a row for each match to ``archive_output.csv``.  Duplicate
combinations are ignored to prevent multiple rows for the same product.

Usage
-----

Run the script from the command line with the keyword ``log!`` and provide the
path to the directory containing your images.  For example:

    python log_models.py log! --images ./downloads

If you omit the ``--images`` flag, the script defaults to the current
directory.  The output file ``archive_output.csv`` will be written to the
working directory.

Limitations
-----------

This script does not fetch product information from the internet.  It relies on
the ``model_data.csv`` file that you maintain.  Before running the script, be
sure to add an entry to ``model_data.csv`` for each style/colour combination
you plan to log.
"""

import argparse
import csv
import os
from collections import OrderedDict


def parse_identifier(filename: str) -> str | None:
    """Extract the full style/colour code from an image filename.

    Filenames must follow the pattern ``IDENTIFIER_descriptor.ext`` where
    ``IDENTIFIER`` has the form ``AA0000-000`` (two letters, four digits,
    a dash, and three digits).  Returns the identifier string on success
    or ``None`` if the filename does not match the expected pattern.
    """
    base = os.path.basename(filename)
    # Split on underscore to isolate the identifier portion (e.g. "BA2449-089" from
    # "BA2449-089_front_01.jpg").
    if "_" not in base:
        return None
    identifier = base.split("_")[0]
    # Validate the identifier: two letters, four digits, dash, three digits
    if len(identifier) != 10 or identifier[6] != '-':
        return None
    prefix = identifier[:2]
    series = identifier[2:6]
    color = identifier[7:]
    if not (prefix.isalpha() and series.isdigit() and color.isdigit()):
        return None
    return identifier


def load_model_data(csv_path: str) -> dict[str, dict[str, str]]:
    """Load model details from ``model_data.csv``.

    Returns a dictionary keyed by the full identifier string (e.g., ``BA2449-089``)
    containing the entire row of product details.  If multiple rows share the
    same identifier, later entries overwrite earlier ones.
    """
    data: dict[str, dict[str, str]] = {}
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            required_fields = {"identifier", "title", "date", "description"}
            missing = required_fields - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    f"The CSV file is missing required columns: {', '.join(sorted(missing))}")
            for row in reader:
                key = row["identifier"].strip()
                data[key] = row
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Could not find '{csv_path}'. Please create this file with product details.")
    return data


def build_archive(images_dir: str, model_data: dict[str, dict[str, str]], output_path: str) -> None:
    """
    Recursively scan ``images_dir`` for image files, look up each unique
    identifier in ``model_data``, and write the results to ``output_path``.

    This function walks through all subdirectories under ``images_dir`` so you
    can organise your photos into separate folders per model.  Only files with
    valid image extensions (jpg, jpeg, png, webp) are considered.
    """
    # Use an ordered dict to preserve insertion order and avoid duplicates
    archive_entries: OrderedDict[str, dict[str, str]] = OrderedDict()

    # Walk through all directories and files
    for root, _, files in os.walk(images_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            identifier = parse_identifier(fname)
            if identifier is None:
                continue
            # Skip files whose identifier is not in the model data
            if identifier not in model_data:
                continue
            # Avoid adding duplicates: if this identifier has already been logged, skip
            if identifier in archive_entries:
                continue
            archive_entries[identifier] = model_data[identifier]

    if not archive_entries:
        print("No matching product entries found. Did you populate model_data.csv?")
        return

    # Write the collected entries to CSV
    fieldnames = ["identifier", "title", "date", "description"]
    with open(output_path, "w", newline='', encoding='utf-8') as out_file:
        writer = csv.DictWriter(out_file, fieldnames=fieldnames)
        writer.writeheader()
        for details in archive_entries.values():
            writer.writerow({field: details.get(field, "") for field in fieldnames})
    print(f"Archive created: {output_path} (entries: {len(archive_entries)})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automate logging of Nike SB RPM backpack models based on image filenames.")
    parser.add_argument("command", help="Use 'log!' to trigger archiving.")
    parser.add_argument("--images", default=".", help="Directory containing the downloaded images.")
    parser.add_argument(
        "--model-csv",
        default="model_data.csv",
        help="CSV file containing product details (default: model_data.csv).",
    )
    parser.add_argument(
        "--output",
        default="archive_output.csv",
        help="Output CSV file to write the archive (default: archive_output.csv).",
    )
    args = parser.parse_args()
    if args.command.strip().lower() != "log!":
        print("Unknown command. Use 'log!' to trigger the logging operation.")
        return
    model_data = load_model_data(args.model_csv)
    build_archive(args.images, model_data, args.output)


if __name__ == "__main__":
    main()