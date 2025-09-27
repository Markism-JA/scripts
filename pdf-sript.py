import fitz  # PyMuPDF
import argparse

A4_WIDTH = 595.28  # points (8.27 inches)
A4_HEIGHT = 841.89  # points (11.69 inches)


def split_pdf(input_file, output_file):
    doc = fitz.open(input_file)
    new_doc = fitz.open()

    for page in doc:
        rect = page.rect
        mid_x = rect.width / 2

        # Left half
        left_rect = fitz.Rect(0, 0, mid_x, rect.height)
        left_page = new_doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        left_page.show_pdf_page(left_page.rect, doc, page.number, clip=left_rect)

        # Right half
        right_rect = fitz.Rect(mid_x, 0, rect.width, rect.height)
        right_page = new_doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        right_page.show_pdf_page(right_page.rect, doc, page.number, clip=right_rect)

    new_doc.save(output_file)
    print(f"[SUCCESS] Saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split PDF pages into left and right halves."
    )
    parser.add_argument("input_file", help="Path to the input PDF file")
    parser.add_argument("output_file", help="Path to the output PDF file")
    args = parser.parse_args()

    split_pdf(args.input_file, args.output_file)
