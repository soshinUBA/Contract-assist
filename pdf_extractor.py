import pdfplumber

def extract_text_from_pdf(pdf_document):
    all_text = ""
    
    with pdfplumber.open(pdf_document) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()

                    # Convert potential headers (short uppercase lines)
                    if len(line) < 50 and line.isupper():
                        all_text += f"## {line}\n\n"
                    elif line.startswith("- ") or line.startswith("* "):
                        all_text += f"{line}\n"
                    elif ":" in line:  # Bold key-value pairs
                        key, value = line.split(":", 1)
                        all_text += f"**{key.strip()}**: {value.strip()}\n\n"
                    else:
                        all_text += f"{line}  \n"  # Ensuring Markdown line breaks
            
            # Extract tables (if any) from the page
            tables = page.extract_tables()
            for table in tables:
                if table and len(table[0]) > 0:
                    # Fix: Handle None values in header
                    header = " | ".join([str(cell) if cell is not None else "" for cell in table[0]])
                    separator = " | ".join(["---"] * len(table[0]))

                    all_text += f"\n{header}\n{separator}\n"

                    for row in table[1:]:  # Skip header row
                        # Fix: Handle None values in table rows
                        formatted_row = " | ".join([str(cell) if cell is not None else "" for cell in row])
                        all_text += f"{formatted_row}\n"
    
    return all_text