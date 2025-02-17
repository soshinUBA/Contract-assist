import os
from dotenv import load_dotenv
from llama_parse import LlamaParse
load_dotenv(".env")

os.environ["LLAMA_CLOUD_API_KEY"] = os.getenv("LAMA_CLOUD_API_KEY")

file_path = "./Contracts/test/M00214389.pdf"
document = LlamaParse(result_type="markdown").load_data(file_path)

markdown_output = "\n\n".join([doc.text for doc in document])

output_md_file = "lama_contract.md"
with open(output_md_file, "w", encoding="utf-8") as f:
    f.write(markdown_output)

print(markdown_output)