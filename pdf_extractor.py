import pdfplumber
from mistralai import Mistral
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('MISTRAL_API_KEY')
client = Mistral(api_key=api_key)

def extract_text_from_pdf(pdf_document):
    all_text = ""
    
    with pdfplumber.open(pdf_document) as pdf:
        for idx, page in enumerate(pdf.pages, 1):
            all_text += f"\n\nPage {idx}\n"

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

def extract_text(pdf_document):
    all_text = f"# PDF: {os.path.basename(pdf_document)}\n"

    try:
        # Upload the PDF file directly with OCR purpose
        with open(pdf_document, "rb") as file:
            uploaded_file = client.files.upload(
                file={
                    "file_name": os.path.basename(pdf_document),
                    "content": file,
                },
                purpose="ocr"  # Changed from "document" to "ocr"
            )
        
        # Get signed URL for the uploaded file
        signed_url = client.files.get_signed_url(file_id=uploaded_file.id)
        
        # Process the PDF document directly
        response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",  # Changed from "pdf_url" to "document_url"
                "document_url": signed_url.url  # Changed key to match type
            }
        )

        # Append OCR results to all_text
        if response and hasattr(response, 'pages'):
            for i, page in enumerate(response.pages):
                all_text += f"\n\n### Page {i+1}\n"
                all_text += page.markdown + "\n\n"
                
    except Exception as e:
        all_text += f"\n\nError processing PDF: {str(e)}\n"

    return all_text