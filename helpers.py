from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
import tiktoken
import docx
import re
import string
load_dotenv()

def get_model():
    client = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            openai_api_version=os.getenv("OPENAI_API_VERSION"),
            temperature=0,
        )
    return client

def count_tokens(text, model="gpt-4o"):
    """Count the number of tokens in the text for the specified model."""
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)


def get_pdfs_from_folder(folder_path):
    """Returns a list of PDF file paths from the given folder."""
    if folder_path.lower().endswith('.pdf'):
        return [folder_path]
    
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    return pdf_files


def extract_docx_content(file_path):
    """Extract text content from a Word document."""
    doc_content = ""
    doc = docx.Document(file_path)
    
    # Extract paragraphs
    for para in doc.paragraphs:
        doc_content += para.text + "\n"

    # Extract tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                doc_content += cell.text + " | "
            doc_content += "\n"
            
    return doc_content


def get_document_name(file_path):
    """Extract the base document name from a file path without extension."""
    base_name = os.path.basename(file_path)
    document_name = os.path.splitext(base_name)[0]
    return document_name


def save_text_to_file(text, file_path):
    """Save text content to a file with proper encoding."""
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(text)
    return file_path

def is_scanned_pdf_from_text(extracted_text, cid_threshold=5):
    scanned_pages = 0
    pages = extracted_text.split("\n\nPage ")

    for page in pages:
        page_content = page.strip()
        if page_content.lower().startswith("page "):
            page_content = page_content[6:].strip()

        if len(page_content) < 200:
            scanned_pages += 1

    cid_count = len(re.findall(r'\(cid:\d+\)', extracted_text))

    return scanned_pages > 2 or cid_count >= cid_threshold