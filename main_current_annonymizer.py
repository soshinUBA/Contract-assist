from openai import OpenAI
import docx
from dotenv import load_dotenv
import os
import pandas as pd
import regex as re
from anonymizer import EntityAnonymizer
from pdf_extractor import extract_text_from_pdf
import tiktoken
from langchain_openai import ChatOpenAI


load_dotenv(".env")

def count_tokens(text, model="gpt-4o"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)

def get_pdfs_from_folder(folder_path):
    """Returns a list of PDF file paths from the given folder."""
    if folder_path.lower().endswith('.pdf'):
        return [folder_path]
    
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    return pdf_files

def contract_assist(contract_path):
    token_text = """YOU WILL BE HEAVILY PENALIZED FOR NOT FOLLOWING INSTRUCTIONS. 
                    - Upon receiving a user inquiry, you **must** directly search the document and return answers for all 24 fields in the required format. 
                    - **Do not** engage in a back-and-forth conversation, explain what you are doing, or restate the user's query.
                    - Your response **must only be the final answer** in tabular form, with the 24 field names and corresponding values. Do **not** return intermediate questions, commentary, or processing steps.
                    - If a field is not found, respond with 'Not found on this document' for that specific field. 
                    - Do **not** start by saying 'Let's search for this first' or any variation. Simply return the completed table at the end.
                    - You are **not allowed** to ask questions. Only perform the task as instructed and return the output in one go.
                    Strict rules to follow:
                        1. Ask no questions or restate no queries. Your task is to **silently** process the document and deliver the final output.
                        2. Return only the final table with answers for all 24 fields. Intermediate steps or explanations will lead to penalties.
                        3. Format your response in this table structure: 'Field, Value, Reason for value' (where applicable).
                        4. If the information is not found in the document, write 'Not found on this document' for that field.
                        5. Always adhere strictly to these instructions and focus solely on delivering the expected tabular output.
    
                    "Monotype Fonts Pro" IS NOT "Monotype Fonts Support" DO NOT CONFUSE THEM.
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "Monotype Fonts Preferred Service​"
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "Monotype Fonts Pro"
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "All Font Software available on Monotype Fonts during the Term."
                    Ensure that you:
                    Search the specific customer’s PDF for each field’s answer. Do not refer to other documents or sources.
                    Do not send any results until all 24 questions have been answered. Ensure accuracy is maintained for each answer, and if any information is not found in the document, respond with "Not found on this document."
                    Do not provide partial or incomplete answers. Ensure both "Name Fonts" and "Material Number" are fully answered before presenting the response. DO NOT GIVE random sentences as answers or incomplete values or "refer to the documents" or "and more" or "etc" type of values
                    Note: customer_name is a placeholder for the actual customer name provided in the user’s query. Ensure all answers are specific to the customer referenced in the query.
                    Important Addendum Consideration:
                    In your investigation, always review any addendums related to the contract. Addendums modify specific terms in the original contract and supersede any corresponding terms in the original document. If an addendum alters a term or clause, the addendum takes precedence. For any terms not mentioned in the addendum, the original contract remains in effect. Ensure you cross-check the contract and addendum carefully to provide the most accurate and up-to-date information.
                    Process:
                    For each of the following questions, search the entire customer’s PDF document for the field seperately else you will be heavily penalized.
                    Do not guess or assume answers. If the answer is not available, respond with "Not found on this document." 
                    #####
                    Questions for Each Field:
                    1.	Contract Start Date: "What is the contract start date for customer_name? If no contract start date is mentioned Identify the Effective Date based on the date below the signatures of both parties. If the dates differ, use the latest date as the Effective Date.""
                    2.	Contract End Date: "What is the contract end date for customer_name?"
                    3.	Contract Number: "What is the unique contract number for customer_name?"
                    4.	Contract Type: "What is the contract type for customer_name? The classificaiton for the Contract Type field SHOULD ONLY BE ONE OF THE FOLLOWING, (*License and Order Form, Monotype Enterprise License, Web Server License Agreement, Monotype Fonts - Agency Pitch,Publisher Package, Monotype Fonts – Design,EZQ, Monotype Mosaic agreement, Monotype Design and Deploy Agreement,Font Software License Agreement, OEM Software License Agreement). Look for exact or close matches to these terms in the document title or header. For example, if 'License and Order Form' appears in the title, classify as 'License and Order Form'. If 'Design and Deploy License and Order Form' appears, classify as 'Monotype Design and Deploy Agreement'. Do NOT invent new classifications or combine terms. If none of these exact classifications appear in the document, identify the closest match from this list based on the document header/title.""
                    5.	Offline Contract: Default is "Yes", unless specified "Online". "Is this an offline contract for customer_name? (Store 'Yes' if no indication of being online)."
                    6.	Territory: "What is the country listed in the address for customer_name? (The country should not be abbreviated and is found ONLY IN THE CUSTOMER ADDRESS. DO NOT TAKE ANY OTHER ADDRESS OTHER THAN THE CUSTOMER)."
                    7.  Agreement Level: "Return Original if there is no addendum found, else return Addendum"
                    8.  Contracting Entity: "What is the entity that made the document? The answer is company name and it is found in the beginning of the page right before the address phone and fax. If none is found return Not found on the document. If you are getting 'Monotype Ltd' the output should be replaced with 'Monotype Limited'" 
                    9: Customer Name: "What is the entity name agreeing to the contract?"
                    10. Customer Contact Email: "What is the customer contact email?"
                    11. Customer Contact First Name: "What is the customer contact's first name"
                    12. Customer Contact Last Name: "What is the customer contact's last name"
                    13. Primary Licensed Monotype Fonts User Email: "What is the primary licensed user's emai?"
                    14. Web Page Views: "What is the Licensed Page Views (Web Page Content) for customer_name? Search your knowledge (This can be found in the License Usage per Term section)"
                    15. Digital Ad Views: "What is the Licensed Impressions (Digital Marketing Communications) for customer_name? Search your knowledge (This can be found in the License Usage per Term section)"
                    16. Licensed Applications: "How many Licensed Applications does customer have (DO NOT FETCH Software Products)? (Do not confuse it with other licensed components like Licensed Software Products, or licensed desktop application else you will be heavily penalized) "
                    17. Registered Users: "What is the Aggregate registered users? This is only found Licensed Application and no where else."
                    18.	Commercial Documents: "What is the upper limit for licensed commercial documents for customer_name?"
                    19.	Licensed Externally Accessed Servers: "How many Externally Accessed Servers can the customer have?"
                    20.	Licensed Monotype Fonts User: "What is the total number of Monotype fonts users for customer_name?"
                    21. Licensed Desktop Users: "How many Licensed Desktop Users can the customer_name have?
                    22. Additional Desktop User Count: "How many Additional Licensed Desktop Users (which are not Licensed Monotype Fonts Users) can the customer_name have? DO NOT COUFUSE THIS WITH "Licensed Desktop Users" THEY ARE NOT THE SAME"
                    23. Production font: "How many production fonts does customer have in contract as well as addendum, if present?" Select the Production Font Integer with the latest date. However, if the contract end date is beyond 2024, select the font Integer that came first. Follow The financial year that starts from April to March. The answer is only found in the "License Usage per Term" section DO NOT LOOK FOR THE ANSWER IN "Add-On Font Software".
                    24. Company Desktop License: "Return with only YES or NO for this field, is the customer allowed to have Licensed Desktop Users?"
                    25.	Monotype Font Support: "{Which Monotype fonts support level did 'customer_name' choose: basic, premier, elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 3. If "Monotype Font Support" is not explicitly mentioned the answer should be "Not found on the document" else it should be the value under "Monotype Fonts Support". DO NOT RETURN "Yes" or "No" for this field}"
                    26. Font Name (Add-On Fonts): "What are the Font names located in Add-On Fonts table? For this field, only look for the answer in the Add-on Fonts Software table"
                    27. Material Number (Add-On Fonts): "What are the material numbers located in Add-On Fonts table? For this field, only look for the answer in the Add-on Fonts Software table"
                    28. Named Fonts Fonts Name: List all the font names for 'customer_name'. Do not include any incomplete values, vague statements or sentances such as 'refer to the documents', 'and more', 'All Font Software available on Monotype Fonts during the Term.', etc else you be very heavily penalized. Return only the exact font names. Do not take the answer from Add On Fonts Software, for this field" 
                    29: Named Fonts Material Number : Return this only if the "Named Fonts Fonts Name" field has an output. "What are the material numbers for customer_name?. GIVE ALL THE VALUES, DO NOT GIVE PARTIAL VALUES, For this Field DO NOT TAKE ANSWER FROM ADD ON FONTS SOFTWARE TABLE" 
                    30. Swapping Allowed: "{"Can production fonts be swapped for 'customer_name'? Answer strictly based on the Production Fonts field in the License for Monotype Fonts License Terms. determine the frequency of swapping strictly based on the License Terms. Only answer 'Quarterly,' 'Annually,' or 'Bi-Yearly' if a specific frequency is explicitly mentioned, else 'Not found on the document', Do not infer the answer."}"
                    31. Reporting days: "How many days does customer_name have to report their usage of the font software as Production Fonts? Focus only on the reporting days explicitly mentioned for reporting Production Fonts usage after receiving the list of downloaded Font Software. Exclude any references to providing information upon request or disputing inaccuracies. Include any additional days granted only if they follow a formal notice. Provide the result in the format 'X days and Y additional days' if applicable, or just 'X days' if no additional days are mentioned"
                    32. Brand & License Protection: "Which field did the customer pick for Brands & License Protection, 'Yes' or 'No'"
                    33. Binding Obligations(Sub-licensing/Transfer Entities): "Who are the entities that have sublicense rights granted? Answer can be found in E. SUBLICENSE RIGHTS. or in Binding Obligation."
                    34. Past Usage Term(Dates): "What is the past usage terms from the customer (only give dates, if it exist)?"  
                    35. Past Use Font Name: "What are the past use Font names the customer had ? Only accept answers that are listed in Past Use Term"
                    36. Past Use Asset: "What was the website/app name/digital ads/server the font was used on? Answer can be found in the Past Use Application table"
                    37. Past Use Material Number: "What are the past use Font names the customer had ? Only accept answers that are listed in Past Use Term"
                    38. Auto Renewal: "Return Yes if the contract will renew automatically after contract end date, else return No."
                    39. Renewal Period: "What is the Additional year periods for which the contract will renew automatically for unless unless either party provides written notice of termination?"
                    40. Plus Inventory: "In Add-On Inventory Sets, is Plus selected? Return Yes if it is selected, No if it is not selected"
                    41. Adobe Originals: "In Add-On Inventory Sets, is Adobe Originals selected? Return Yes if it is selected, No if it is not selected"
                    42. Go Forward Assests: "What are the names of the website/app name/digital ads/server in which the font software will be used going forward?"
                    43. Monotype Fonts Plan: "{Which Monotype fonts plan  did 'customer_name' choose: App Kit , Standard , Pro, Unlimited or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 4. If "Monotype Fonts Plan" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
                    44. Onboarding: "{Which Onbording did 'customer_name' choose: basic, premier, elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 3. If "Onboarding" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
                    45. Monotype Single Sign-On:  "{Which Single Sign-On Option  did 'customer_name' choose: Yes or No?" DON'T GIVE ANY ANSWER APART FORM 2. If "Single Sign-On Option" is not explicitly mentioned the answer should be "Not found on the document".}"
                    46. Customer Success Plan: "{Which Customer Success plan  did 'customer_name' choose: Basic , Enhanced , Premier, Elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 4. If "Customer Success Plan" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
                    47. Studio Services: "{Which Studio Services did 'customer_name' choose: Yes or No?" DON'T GIVE ANY ANSWER APART FORM 2. If "Studio Services" is not explicitly mentioned the answer should be "Not found on the document".}"
                    48. Monotype Font/User Management: "{Which Font/User Management did 'customer_name' choose: basic, premier, elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 3. If "Font/User Management" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
    
                    #####
                    IMPORTANT POINTS: 
                    * LICENSED APPLICATION AND LICENSED SOFTWARE PRODUCT ARE DIFFERENT.
                    1. PROCESS for each answer Separately else you will be very heavily penalized.
                    2. Important point: "Always refer to Documents before answering Questions"
                    3. USE MEDIUM CHUNKING SIZE else you will be heavily penalized
                    4. YOU ARE NOT ALLOWED TO REFER TO ANY EXTERNAL SOURCES
                    5. Important Point: "PRODUCTION FONTS, PRODUCTION SOFTWARE ARE SAME AND CAN BE REFERRED VICE VERSA."
                    7. YOU CANNOT CHANGE THE INFORMATION, ELSE YOU WILL BE HEAVILY PENAILZED.
                    8. WHILE FETCHING MULTIPLE CONTRACTS DATA, YOU SHOULD UNDERSTAND AND FETCH DATA FROM ALL CONTRACTS INDIVISUALLY.
                    9. Signing and preparation of contract are different things. It should be treated differently.
                    10. ALWAYS SEARCH YOUR KNOWLEDGE BEFORE ANSWERING THE QUESTION
                    11. Always Answer in SHORT EXCEPT FOR THE FOLLOWING FIELDS, Name Fonts, Material Number, Production Font and Reporting. For these 4 fields your answer can be LONG
                    12. The Contract's Date whose termination date is before today's date is expired.
                    13. YOU CANNOT MAKE ANY ASSUMPTIONS.
                    15. ALWAYS present fields, their values and their reasons in a clear tabular format. Ensure that all answers are contained within the table and not outside of it.
                    16. Your output should EXACTLY BE THE 47 fields MENTIONED or you will be penalized. A sample output for the 47 fields from the FAQ document. Ensure that all answers are specific to the correct customer and contract in question.
                    17. For the fields Web Page Views, Digital Ad Views, Licensed Applications, Registered Users, Commercial Documents, Licensed Externally Accessed Servers, Licensed Monotype Fonts User, Licensed Desktop Users, Additional Desktop User Count, Production font, return only the precise numerical value (fully written out, no abbreviations like "mill" or "k") or exact text from the document with no additional words, units, or explanations. Numbers should be written in full form (example: "8500000" not "8.5 mill"; "2000" not "2k").
                    18. YOU SHOULD FOLLOW ALL ABOVE MENTIONED POINTS ELSE YOU WILL BE PENAILZED HEAVILY
                    sample output format, Field,Value,Reason for value"""

    pdf_documents = get_pdfs_from_folder(contract_path)
    print("Running for these pdfs, ", pdf_documents)

    word_doc = "./FAQ_document_48_fields.docx"
    all_text = ""
    faq_doc = ""
    run_open_ai = True

    anonymizer = EntityAnonymizer()

    # Load the .docx file
    doc = docx.Document(word_doc)
    for para in doc.paragraphs:
        faq_doc += para.text + "\n"

    # Extract and store tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                faq_doc += cell.text + " | "
            faq_doc += "\n"

    print(faq_doc)
    with open("faq.txt", "w") as f:
        f.write(faq_doc)

    print("############# Starting PDF  Processing ######################")

    # Open the PDF file
    for pdf_document in pdf_documents:
        text1 = extract_text_from_pdf(pdf_document)
        if len(text1) <= 800:
            print("Image file detected, skipping")
            exit()
        all_text += text1

    with open("contract_b4.txt", "w", encoding="utf-8") as f:
        f.write(all_text)

    token_text += all_text
    token_count = count_tokens(token_text)
    if token_count > 120000:
        print("Token limit execeeded, Exiting the code.")
        exit()

    anonymized_text, mapping, validated_entities = anonymizer.anonymize_text(all_text)
    with open("contract_anonymized.txt", "w", encoding="utf-8") as f:
        f.write(anonymized_text)

    #Saving anonymized text file
    pdf_document = pdf_documents[0]
    base_name = os.path.basename(pdf_document)
    document_name = os.path.splitext(base_name)[0]
    file_path = f'./ExcelOutput/{document_name}_data.xlsx'
    output_filename = f"./Output/{document_name}_Output.txt"
    with open(output_filename, "w", encoding="utf-8") as file:
        file.write(anonymized_text)
    with open(f"./Output/{document_name}_mappings.txt", "w", encoding="utf-8") as file:
        file.write(str(mapping))
    print("Message content saved successfully!")

    print("\nMapping Dictionary:")
    for original, dummy in mapping.items():
        print(f"{original} → {dummy}")

    print("############# Starting Openai Processing ######################")


    if run_open_ai:
        client = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            max_tokens=3500,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        response = client.invoke(
            input=[
                {"role": "system", "content": """
                    YOU WILL BE HEAVILY PENALIZED FOR NOT FOLLOWING INSTRUCTIONS. 
                    - Upon receiving a user inquiry, you **must** directly search the document and return answers for all 24 fields in the required format. 
                    - **Do not** engage in a back-and-forth conversation, explain what you are doing, or restate the user's query.
                    - Your response **must only be the final answer** in tabular form, with the 24 field names and corresponding values. Do **not** return intermediate questions, commentary, or processing steps.
                    - If a field is not found, respond with 'Not found on this document' for that specific field. 
                    - Do **not** start by saying 'Let's search for this first' or any variation. Simply return the completed table at the end.
                    - You are **not allowed** to ask questions. Only perform the task as instructed and return the output in one go.
                    Strict rules to follow:
                        1. Ask no questions or restate no queries. Your task is to **silently** process the document and deliver the final output.
                        2. Return only the final table with answers for all 24 fields. Intermediate steps or explanations will lead to penalties.
                        3. Format your response in this table structure: 'Field, Value, Reason for value' (where applicable).
                        4. If the information is not found in the document, write 'Not found on this document' for that field.
                        5. Always adhere strictly to these instructions and focus solely on delivering the expected tabular output.
    
                    "Monotype Fonts Pro" IS NOT "Monotype Fonts Support" DO NOT CONFUSE THEM.
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "Monotype Fonts Preferred Service​"
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "Monotype Fonts Pro"
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "All Font Software available on Monotype Fonts during the Term."
                    Ensure that you:
                    Search the specific customer’s PDF for each field’s answer. Do not refer to other documents or sources.
                    Do not send any results until all 24 questions have been answered. Ensure accuracy is maintained for each answer, and if any information is not found in the document, respond with "Not found on this document."
                    Do not provide partial or incomplete answers. Ensure both "Name Fonts" and "Material Number" are fully answered before presenting the response. DO NOT GIVE random sentences as answers or incomplete values or "refer to the documents" or "and more" or "etc" type of values
                    Note: customer_name is a placeholder for the actual customer name provided in the user’s query. Ensure all answers are specific to the customer referenced in the query.
                    Important Addendum Consideration:
                    In your investigation, always review any addendums related to the contract. Addendums modify specific terms in the original contract and supersede any corresponding terms in the original document. If an addendum alters a term or clause, the addendum takes precedence. For any terms not mentioned in the addendum, the original contract remains in effect. Ensure you cross-check the contract and addendum carefully to provide the most accurate and up-to-date information.
                    Process:
                    For each of the following questions, search the entire customer’s PDF document for the field seperately else you will be heavily penalized.
                    Do not guess or assume answers. If the answer is not available, respond with "Not found on this document." 
                    #####
                    Questions for Each Field:
                    1.	Contract Start Date: "What is the contract start date for customer_name? If no contract start date is mentioned Identify the Effective Date based on the date below the signatures of both parties. If the dates differ, use the latest date as the Effective Date.""
                    2.	Contract End Date: "What is the contract end date for customer_name?"
                    3.	Contract Number: "What is the unique contract number for customer_name?"
                    4.	Contract Type: "What is the contract type for customer_name? The classificaiton for the Contract Type field SHOULD ONLY BE ONE OF THE FOLLOWING, (*License and Order Form, Monotype Enterprise License, Web Server License Agreement, Monotype Fonts - Agency Pitch,Publisher Package, Monotype Fonts – Design,EZQ, Monotype Mosaic agreement, Monotype Design and Deploy Agreement,Font Software License Agreement, OEM Software License Agreement). Look for exact or close matches to these terms in the document title or header. For example, if 'License and Order Form' appears in the title, classify as 'License and Order Form'. If 'Design and Deploy License and Order Form' appears, classify as 'Monotype Design and Deploy Agreement'. Do NOT invent new classifications or combine terms. If none of these exact classifications appear in the document, identify the closest match from this list based on the document header/title.""
                    5.	Offline Contract: Default is "Yes", unless specified "Online". "Is this an offline contract for customer_name? (Store 'Yes' if no indication of being online)."
                    6.	Territory: "What is the country listed in the address for customer_name? (The country should not be abbreviated and is found ONLY IN THE CUSTOMER ADDRESS. DO NOT TAKE ANY OTHER ADDRESS OTHER THAN THE CUSTOMER)."
                    7.  Agreement Level: "Return Original if there is no addendum found, else return Addendum"
                    8.  Contracting Entity: "What is the entity that made the document? The answer is company name and it is found in the beginning of the page right before the address phone and fax. If none is found return Not found on the document. If you are getting 'Monotype Ltd' the output should be replaced with 'Monotype Limited'" 
                    9: Customer Name: "What is the entity name agreeing to the contract?"
                    10. Customer Contact Email: "What is the customer contact email?"
                    11. Customer Contact First Name: "What is the customer contact's first name"
                    12. Customer Contact Last Name: "What is the customer contact's last name"
                    13. Primary Licensed Monotype Fonts User Email: "What is the primary licensed user's emai?"
                    14. Web Page Views: "What is the Licensed Page Views (Web Page Content) for customer_name? Search your knowledge (This can be found in the License Usage per Term section)"
                    15. Digital Ad Views: "What is the Licensed Impressions (Digital Marketing Communications) for customer_name? Search your knowledge (This can be found in the License Usage per Term section)"
                    16. Licensed Applications: "How many Licensed Applications does customer have (DO NOT FETCH Software Products)? (Do not confuse it with other licensed components like Licensed Software Products, or licensed desktop application else you will be heavily penalized) "
                    17. Registered Users: "What is the Aggregate registered users? This is only found Licensed Application and no where else."
                    18.	Commercial Documents: "What is the upper limit for licensed commercial documents for customer_name?"
                    19.	Licensed Externally Accessed Servers: "How many Externally Accessed Servers can the customer have?"
                    20.	Licensed Monotype Fonts User: "What is the total number of Monotype fonts users for customer_name?"
                    21. Licensed Desktop Users: "How many Licensed Desktop Users can the customer_name have?
                    22. Additional Desktop User Count: "How many Additional Licensed Desktop Users (which are not Licensed Monotype Fonts Users) can the customer_name have? DO NOT COUFUSE THIS WITH "Licensed Desktop Users" THEY ARE NOT THE SAME"
                    23. Production font: "How many production fonts does customer have in contract as well as addendum, if present?" Select the Production Font Integer with the latest date. However, if the contract end date is beyond 2024, select the font Integer that came first. Follow The financial year that starts from April to March. The answer is only found in the "License Usage per Term" section DO NOT LOOK FOR THE ANSWER IN "Add-On Font Software".
                    24. Company Desktop License: "Return with only YES or NO for this field, is the customer allowed to have Licensed Desktop Users?"
                    25.	Monotype Font Support: "{Which Monotype fonts support level did 'customer_name' choose: basic, premier, elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 3. If "Monotype Font Support" is not explicitly mentioned the answer should be "Not found on the document" else it should be the value under "Monotype Fonts Support". DO NOT RETURN "Yes" or "No" for this field}"
                    26. Font Name (Add-On Fonts): "What are the Font names located in Add-On Fonts table? For this field, only look for the answer in the Add-on Fonts Software table"
                    27. Material Number (Add-On Fonts): "What are the material numbers located in Add-On Fonts table? For this field, only look for the answer in the Add-on Fonts Software table"
                    28. Named Fonts Fonts Name: List all the font names for 'customer_name'. Do not include any incomplete values, vague statements or sentances such as 'refer to the documents', 'and more', 'All Font Software available on Monotype Fonts during the Term.', etc else you be very heavily penalized. Return only the exact font names. Do not take the answer from Add On Fonts Software, for this field" 
                    29: Named Fonts Material Number : Return this only if the "Named Fonts Fonts Name" field has an output. "What are the material numbers for customer_name?. GIVE ALL THE VALUES, DO NOT GIVE PARTIAL VALUES, For this Field DO NOT TAKE ANSWER FROM ADD ON FONTS SOFTWARE TABLE" 
                    30. Swapping Allowed: "{"Can production fonts be swapped for 'customer_name'? Answer strictly based on the Production Fonts field in the License for Monotype Fonts License Terms. determine the frequency of swapping strictly based on the License Terms. Only answer 'Quarterly,' 'Annually,' or 'Bi-Yearly' if a specific frequency is explicitly mentioned, else 'Not found on the document', Do not infer the answer."}"
                    31. Reporting days: "How many days does customer_name have to report their usage of the font software as Production Fonts? Focus only on the reporting days explicitly mentioned for reporting Production Fonts usage after receiving the list of downloaded Font Software. Exclude any references to providing information upon request or disputing inaccuracies. Include any additional days granted only if they follow a formal notice. Provide the result in the format 'X days and Y additional days' if applicable, or just 'X days' if no additional days are mentioned"
                    32. Brand & License Protection: "Which option did the customer select for Brands & License Protection: 'Yes' or 'No'? Please give value as per selected checkbox."
                    33. Binding Obligations(Sub-licensing/Transfer Entities): "Who are the entities that have sublicense rights granted? Answer can be found in E. SUBLICENSE RIGHTS. or in Binding Obligation."
                    34. Past Usage Term(Dates): "What is the past usage terms from the customer (only give dates, if it exist)?"  
                    35. Past Use Font Name: "What are the past use Font names the customer had ? Only accept answers that are listed in Past Use Term"
                    36. Past Use Asset: "What was the website/app name/digital ads/server the font was used on? Answer can be found in the Past Use Application table"
                    37. Past Use Material Number: "What are the past use Font names the customer had ? Only accept answers that are listed in Past Use Term"
                    38. Auto Renewal: "Return Yes if the contract will renew automatically after contract end date, else return No."
                    39. Renewal Period: "What is the Additional year periods for which the contract will renew automatically for unless unless either party provides written notice of termination?"
                    40. Plus Inventory: "In Add-On Inventory Sets, is Plus selected? Return Yes if it is selected, No if it is not selected"
                    41. Adobe Originals: "In Add-On Inventory Sets, is Adobe Originals selected? Return Yes if it is selected, No if it is not selected"
                    42. Go Forward Assests: "What are the names of the website/app name/digital ads/server in which the font software will be used going forward?"
                    43. Monotype Fonts Plan: "{Which Monotype fonts plan  did 'customer_name' choose: App Kit , Standard , Pro, Unlimited or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 4. If "Monotype Fonts Plan" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
                    44. Onboarding: "{Which Onbording did 'customer_name' choose: basic, premier, elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 3. If "Onboarding" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
                    45. Monotype Single Sign-On:  "Which option did 'customer_name' select for Single Sign-On: 'Yes' or 'No'? Please respond in the appropriate language format and indicate the selected checkbox. If 'Single Sign-On' is not explicitly mentioned in the document, respond with 'Not found on the document'"
                    46. Customer Success Plan: "{Which Customer Success plan  did 'customer_name' choose: Basic , Enhanced , Premier, Elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 4. If "Customer Success Plan" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
                    47. Studio Services: "{Which Studio Services did 'customer_name' choose: Yes or No?" DON'T GIVE ANY ANSWER APART FORM 2. If "Studio Services" is not explicitly mentioned the answer should be "Not found on the document".}"
                    48. Monotype Font/User Management: "{Which Font/User Management did 'customer_name' choose: basic, premier, elite or "Not found on the document" ? DON'T GIVE ANY ANSWER APART FORM THESE 3. If "Font/User Management" is not explicitly mentioned the answer should be "Not found on the document". DO NOT RETURN "Yes" or "No" for this field}"
                    
                    #####
                    IMPORTANT POINTS: 
                    * LICENSED APPLICATION AND LICENSED SOFTWARE PRODUCT ARE DIFFERENT.
                    1. PROCESS for each answer Separately else you will be very heavily penalized.
                    2. Important point: "Always refer to Documents before answering Questions"
                    3. USE MEDIUM CHUNKING SIZE else you will be heavily penalized
                    4. YOU ARE NOT ALLOWED TO REFER TO ANY EXTERNAL SOURCES
                    5. Important Point: "PRODUCTION FONTS, PRODUCTION SOFTWARE ARE SAME AND CAN BE REFERRED VICE VERSA."
                    7. YOU CANNOT CHANGE THE INFORMATION, ELSE YOU WILL BE HEAVILY PENAILZED.
                    8. WHILE FETCHING MULTIPLE CONTRACTS DATA, YOU SHOULD UNDERSTAND AND FETCH DATA FROM ALL CONTRACTS INDIVISUALLY.
                    9. Signing and preparation of contract are different things. It should be treated differently.
                    10. ALWAYS SEARCH YOUR KNOWLEDGE BEFORE ANSWERING THE QUESTION
                    11. Always Answer in SHORT EXCEPT FOR THE FOLLOWING FIELDS, Name Fonts, Material Number, Production Font and Reporting. For these 4 fields your answer can be LONG
                    12. The Contract's Date whose termination date is before today's date is expired.
                    13. YOU CANNOT MAKE ANY ASSUMPTIONS.
                    15. ALWAYS present fields, their values and their reasons in a clear tabular format. Ensure that all answers are contained within the table and not outside of it.
                    16. Your output should EXACTLY BE THE 47 fields MENTIONED or you will be penalized. A sample output for the 47 fields from the FAQ document. Ensure that all answers are specific to the correct customer and contract in question.
                    17. For the fields Web Page Views, Digital Ad Views, Licensed Applications, Registered Users, Commercial Documents, Licensed Externally Accessed Servers, Licensed Monotype Fonts User, Licensed Desktop Users, Additional Desktop User Count, Production font, return only the precise numerical value (fully written out, no abbreviations like "mill" or "k") or exact text from the document with no additional words, units, or explanations. Numbers should be written in full form (example: "8500000" not "8.5 mill"; "2000" not "2k").
                    18. YOU SHOULD FOLLOW ALL ABOVE MENTIONED POINTS ELSE YOU WILL BE PENAILZED HEAVILY
                    sample output format, Field,Value,Reason for value
                """},
                {
                    "role": "user",
                    "content": f""" 
                        This is the faq document: {faq_doc}.
                        ######
                        Give me the details of the contract below:
    
                        {all_text} 
                    """
                }
            ]
        )

        print("#####")
        print(response)
        print("#####")

        message = response.content
        pdf_document = pdf_documents[0]

        # Extract the base name of the file (e.g., M00217189.pdf)
        base_name = os.path.basename(pdf_document)

        # Remove the .pdf extension to get just the document name (e.g., M00217189)
        document_name = os.path.splitext(base_name)[0]

        # Create the desired output file name (e.g., M00217189_Output.txt)
        output_filename = f"./Output/{document_name}_Output_2.txt"
        with open(output_filename, "w", encoding="utf-8") as file:
            file.write(message)  # Assuming 'message' contains the content you want to write

        print("Message content saved successfully!")
        print(response.content)

        # Step 1: Parse the content into a structured format (table)
        lines = [line for line in response.content.splitlines() if '----' not in line]  # Remove separator lines
        lines = [line for line in lines if not re.match(r'^\|\s*-+\s*\|\s*-+\s*\|\s*-+\s*\|$', line)]

        fields, values, reasons = [], [], []

        for line in lines[1:]:  # Start from index 1 to skip the column headers
            if '|' in line:  # Ensure it's a valid row
                parts = line.split('|')[1:4]  # Split into Field, Value, and Reason
                if len(parts) == 3:  # Ensure there are exactly three parts
                    fields.append(parts[0].strip())
                    values.append(parts[1].strip())
                    reasons.append(parts[2].strip())

        # Primary email,customer name, first name, last name, customer emails Map it
            # Ensure email logic works correctly
        if len(values) > 12:
            indices_to_check = [8, 10, 11, 12]

            reverse_mapping = {v: k for k, v in mapping.items()}

            # Iterate through specified indices and replace values if found
            for i in indices_to_check:
                if values[i] in reverse_mapping:
                    values[i] = reverse_mapping[values[i]]

        # Step 2: Create a DataFrame
        data = {
            "Field": fields,
            "Value": values,
            "Reason for value": reasons
        }
        df = pd.DataFrame(data)

        # Step 3: Export to Excel
        df.to_excel(file_path, index=False)

        print(f"Data has been exported to {file_path}")
    return file_path