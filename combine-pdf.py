import fitz  # PyMuPDF
import argparse
import os
import json
import sys


def add_section_page(doc, title):
    """Insert a new page with section title centered both vertically and horizontally."""
    page = doc.new_page()  # default: A4
    rect = page.rect
    fontsize = 36

    # Define a rectangle in the vertical middle of the page
    # making it "tall enough" for the text
    text_height = fontsize * 2
    center_rect = fitz.Rect(
        0,
        rect.height / 2 - text_height / 2,
        rect.width,
        rect.height / 2 + text_height / 2,
    )

    # Insert text in this centered rectangle
    page.insert_textbox(
        center_rect,
        title,
        fontsize=fontsize,
        align=1,  # center horizontally
    )
    return page.number


def merge_pdfs(input_dir, output_file, config_path=None):
    # Load configuration
    if config_path is None:
        config_path = os.path.join(input_dir, "settings.json")

    if not os.path.exists(config_path):
        print(f"[ERROR] No configuration file found at {config_path}")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = json.load(f)

    merged_doc = fitz.open()
    toc = []

    for section, files in config.items():
        print(f"[INFO] Adding section: {section}")

        # Insert section title page
        section_page_num = add_section_page(merged_doc, section)
        toc.append([1, section, section_page_num + 1])

        # Insert section files
        for filename in files:
            filepath = os.path.join(input_dir, filename)
            if not os.path.exists(filepath):
                print(f"[WARNING] File not found: {filepath}, skipping...")
                continue

            with fitz.open(filepath) as src_doc:
                merged_doc.insert_pdf(src_doc)

    # Apply TOC (outline/bookmarks)
    merged_doc.set_toc(toc)

    merged_doc.save(output_file)
    print(f"[SUCCESS] Merged PDF saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge PDFs into sectioned PDF with TOC."
    )
    parser.add_argument("input_dir", help="Directory containing PDF files")
    parser.add_argument("-o", "--output", required=True, help="Output PDF file path")
    parser.add_argument(
        "-c",
        "--config",
        help="Path to configuration JSON (default: settings.json in input_dir)",
    )
    args = parser.parse_args()

    merge_pdfs(args.input_dir, args.output, args.config)
