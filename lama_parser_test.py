import os
from dotenv import load_dotenv
from llama_parse import LlamaParse
import pandas as pd

load_dotenv(".env")

os.environ["LLAMA_CLOUD_API_KEY"] = os.getenv("LAMA_CLOUD_API_KEY")
# File Path
pdf_documents = ["./Contracts/test/M00214389.pdf"]  # Add more PDFs to list if needed

# Initialize LlamaParse
parser = LlamaParse(result_type="markdown")
all_text = ""

for pdf_document in pdf_documents:
    document = parser.load_data(pdf_document)  # Process PDF with LlamaParse
    markdown_output = "\n\n".join([doc.text for doc in document])

output_md_file = "lama_contract.md"
with open(output_md_file, "w", encoding="utf-8") as f:
    f.write(markdown_output)

print(markdown_output)