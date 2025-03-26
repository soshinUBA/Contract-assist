import os
import fitz  # PyMuPDF
import pandas as pd
import re
import json

class PDFBoundingBoxDrawer:
    def __init__(self, pdf_folder, excel_path, base_output_dir):
        self.pdf_folder = pdf_folder
        self.pdf_paths = self.get_pdf_files()
        self.excel_path = excel_path

        # Create a unique output folder using the input folder's name
        folder_name = os.path.basename(os.path.normpath(pdf_folder))  # Extract folder name
        self.output_dir = os.path.join(base_output_dir, folder_name)
        os.makedirs(self.output_dir, exist_ok=True)  # Create if it doesn’t exist

        self.unmatched_data = {
            "missing_pairs": set(),
            "missing_values": set()
        }

    def get_pdf_files(self):
        """Retrieve all PDF files from the specified folder."""
        return [os.path.join(self.pdf_folder, f) for f in os.listdir(self.pdf_folder) if f.lower().endswith(".pdf")]

    def format_number(self, value):
        """Convert numeric values to a comma-separated format (e.g., 2500000 → 2,500,000)."""
        if isinstance(value, (int, float)) or re.fullmatch(r"\d+", str(value)):
            formatted_value = f"{int(value):,} "
            return " 0 " if formatted_value.strip() == "0" else formatted_value
        return value + " " if value.lower() in ["no", "yes"] else value

    def extract_fields_and_values(self):
        """Extract fields and values from Excel, formatting numbers properly."""
        df = pd.read_excel(self.excel_path, header=None)
        field_value_map = {}
        for _, row in df.iterrows():
            row_data = row.dropna().astype(str).str.strip().tolist()
            if len(row_data) >= 2:
                field = row_data[0]
                value = self.format_number(row_data[1])
                field_value_map[field] = value
        return field_value_map

    def normalize_text(self, text):
        """Normalize text by converting to lowercase and stripping spaces."""
        return text.strip().lower() if isinstance(text, str) else text

    def draw_bounding_boxes_in_pdfs(self):
        """Draw bounding boxes and track unmatched field-value pairs."""
        if not self.pdf_paths:
            print("No PDF files found in the folder.")
            return []

        field_value_map = self.extract_fields_and_values()
        modified_pdfs = []

        for pdf_path in self.pdf_paths:
            print(f"Processing: {pdf_path}")  # Debugging output

            doc = fitz.open(pdf_path)
            for page in doc:
                for field, value in field_value_map.items():
                    normalized_field = self.normalize_text(field)
                    normalized_value = self.normalize_text(value)

                    field_matches = page.search_for(field)
                    if field_matches:
                        for field_rect in field_matches:
                            page.draw_rect(field_rect, color=(1, 0, 0), width=2)

                            # Adjust search region dynamically
                            search_region = fitz.Rect(
                                field_rect.x0, field_rect.y0, field_rect.x1 + 300, field_rect.y1 + 50
                            )
                            value_matches = page.search_for(value, clip=search_region)

                            if value_matches:
                                for value_rect in value_matches:
                                    page.draw_rect(value_rect, color=(0, 1, 0), width=2)
                            else:
                                # Extract text from region before marking missing
                                found_similar = any(
                                    self.normalize_text(page.get_text("text", clip=v)) == normalized_value
                                    for v in page.search_for(value)
                                )
                                if not found_similar:
                                    self.unmatched_data["missing_values"].add((field, value.strip() if isinstance(value, str) else value))
                    else:
                        value_matches = page.search_for(value)
                        if value_matches:
                            for value_rect in value_matches:
                                page.draw_rect(value_rect, color=(0, 1, 0), width=2)
                        else:
                            # Extract text from regions before marking as missing
                            found_field = any(
                                self.normalize_text(page.get_text("text", clip=f)) == normalized_field
                                for f in page.search_for(field)
                            )
                            found_value = any(
                                self.normalize_text(page.get_text("text", clip=v)) == normalized_value
                                for v in page.search_for(value)
                            )

                            if not found_field and not found_value:
                                self.unmatched_data["missing_pairs"].add((field, value.strip() if isinstance(value, str) else value))
            
            output_pdf_path = os.path.join(self.output_dir, os.path.basename(pdf_path))
            doc.save(output_pdf_path)
            doc.close()
            modified_pdfs.append(output_pdf_path)

        unmatched_json_path = os.path.join(self.output_dir, "unmatched_data.json")
        with open(unmatched_json_path, "w") as json_file:
            json.dump({
                "missing_pairs": list(self.unmatched_data["missing_pairs"]),
                "missing_values": list(self.unmatched_data["missing_values"])
            }, json_file, indent=4, default=str)

        return modified_pdfs

# Example Usage
if __name__ == "__main__":
    pdf_folder = "Contracts/Global Order Management & Royalty/English/Folders/M00202119"  # Folder containing PDFs
    excel_file = "ExcelOutput/COMPLETED Tapestry, Inc  Other 07 15 2021_data.xlsx"
    base_output_folder = "validated_directory"  # Base directory for all outputs

    drawer = PDFBoundingBoxDrawer(pdf_folder, excel_file, base_output_folder)
    modified_pdfs = drawer.draw_bounding_boxes_in_pdfs()

    print("Modified PDFs saved at:", drawer.output_dir)