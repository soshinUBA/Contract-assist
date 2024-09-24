import openai
import pdfplumber
import docx

pdf_document = "./M00209635.pdf"
word_doc = "./FAQ document.docx"
all_text = ""
# Load the .docx file
doc = docx.Document(word_doc)
for para in doc.paragraphs:
    print(para.text)

# Extract and print the tables
for table in doc.tables:
    for row in table.rows:
        for cell in row.cells:
            print(cell.text, end=" | ")
        print()

print("############# Starting PDF ######################")

with pdfplumber.open(pdf_document) as pdf:
    for page in pdf.pages:
        # Extract text
        text = page.extract_text()
        if text:
            all_text += text + "\n"  # Append the text and add newline

        # Extract tables (if any)
        tables = page.extract_tables()
        for table in tables:
            # Dynamically generate the header and separator based on the number of columns
            if table and len(table[0]) > 0:  # Ensure the table has at least one row
                num_columns = len(table[0])
                header = " | ".join([f"Column {i + 1}" for i in range(num_columns)])
                separator = " | ".join(["---"] * num_columns)

                # Append the header and separator to the output
                all_text += f"{header}\n{separator}\n"

                # Append each row of the table
                for row in table:
                    formatted_row = " | ".join([cell if cell else "" for cell in row])
                    all_text += f"{formatted_row}\n"
print(all_text)


# openai.api_key = "sk-monotypeserviceaccount1-Sl9Ip87qn9fbJOdAgE4jT3BlbkFJaQ9we33NEBuZsgCbTRPO"
#
# def get_chatgpt_response(prompt, model="gpt-4", max_tokens=150):
#     try:
#         response = openai.ChatCompletion.create(
#             model=model,
#             messages=[{"role": "user", "content": prompt}],
#             max_tokens=max_tokens
#         )
#         return response['choices'][0]['message']['content']
#     except Exception as e:
#         return f"An error occurred: {str(e)}"
#
# # Example prompt to send to ChatGPT
# prompt = "Explain how machine learning works in simple terms."
# result = get_chatgpt_response(prompt)
#
# # Print the response
# print("ChatGPT response:", result)
