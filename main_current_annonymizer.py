from openai import OpenAI
import docx
from dotenv import load_dotenv
import os
import pandas as pd
import regex as re
from anonymizer import EntityAnonymizer
from pdf_extractor import extract_text_from_pdf
import tiktoken
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from collections import defaultdict
import json_repair
import asyncio
import json
load_dotenv(".env")

token_limit = 15000

def count_tokens(text, model="gpt-4o"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    return len(tokens)

def extract_first_addendum_number(text):
    """
    Finds the first occurrence of 'Addendum No. X' in the text and returns the addendum number.
    """
    words = text.split()
    for i, word in enumerate(words):
        if word.lower() == "addendum" and i + 2 < len(words) and words[i + 1].lower() == "no.":
            try:
                return int(words[i + 2])
            except ValueError:
                return None  # In case it's not a valid number
    return None  # Return None if no valid addendum number is found

def get_pdfs_from_folder(folder_path):
    """Returns a list of PDF file paths from the given folder."""
    if folder_path.lower().endswith('.pdf'):
        return [folder_path]
    
    pdf_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    return pdf_files

async def chunk_content_to_token_limit(content, token_limit_value=token_limit):
    try:
        number = 0
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=token_limit_value,  # Targeted for GPT-4o
            chunk_overlap=1500,  # Overlap to prevent abrupt breaks
            length_function=lambda text: count_tokens(text)  # Ensures it counts GPT-4o tokens
        )
        chunks = text_splitter.split_text(content)

        for chunk in chunks:
            number += 1
            chunk_token_length = count_tokens(chunk)
            print(f"Chunk {number} - Token Length: {chunk_token_length}")
            print(f"Chunk {number} - String Length: {len(chunk)}")
            with open(f"./Output/chunk{number}.txt", "w", encoding="utf-8") as f:
                f.write(chunk)
        
        return chunks
    except Exception as e:
        print("Error while chunking content:", e)
        exit()

def contract_assist(contract_path):
    sample_output = [
        {"Field": "Contract Start Date", "Value": "3/1/2022", "Reason for value": ""},
        {"Field": "Contract End Date", "Value": "2/28/2025", "Reason for value": ""},
        {"Field": "Contract Number", "Value": "M00207675", "Reason for value": ""},
        {"Field": "Contract Number", "Value": "License Order Form", "Reason for value": ""},
        {"Field": "Contract Name(Agreement Classification)", "Value": "", "Reason for value": ""},
        {"Field": "Agreement Level", "Value": "", "Reason for value": ""},
        {"Field": "Territory", "Value": "United States", "Reason for value": ""},
        {"Field": "Contracting Entity", "Value": "", "Reason for value": ""},
        {"Field": "Customer Name", "Value": "Entertainment Innovations Inc.", "Reason for value": ""},
        {"Field": "Customer Contact Email", "Value": "", "Reason for value": ""},
        {"Field": "Customer Contact First Name", "Value": "", "Reason for value": ""},
        {"Field": "Customer Contact Last Name", "Value": "", "Reason for value": ""},
        {"Field": "Primary User Email", "Value": "Email Address: david.johnson@entertainmentinnovations.com", "Reason for value": ""},
        {"Field": "Web Page Views", "Value": "", "Reason for value": ""},
        {"Field": "Digital Ad Views", "Value": "", "Reason for value": ""},
        {"Field": "Licensed Applications", "Value": "", "Reason for value": ""},
        {"Field": "Registered Users", "Value": "", "Reason for value": ""},
        {"Field": "Commercial Documents", "Value": "", "Reason for value": ""},
        {"Field": "Licensed Externally Accessed Servers", "Value": "", "Reason for value": ""},
        {"Field": "Licensed User Count", "Value": "20", "Reason for value": ""},
        {"Field": "Licensed Desktop Users", "Value": "", "Reason for value": ""},
        {"Field": "Additional User Count", "Value": "", "Reason for value": ""},
        {"Field": "Production Fonts", "Value": "", "Reason for value": ""},
        {"Field": "Company Desktop License", "Value": "", "Reason for value": ""},
        {"Field": "Monotype Font Support", "Value": "Basic/Premier/Elite/Not found in the document", "Reason for value": ""},
        {"Field": "Font Name (Add-On Fonts)", "Value": "", "Reason for value": ""},
        {"Field": "Material Number (Add-On Fonts)", "Value": "", "Reason for value": ""},
        {"Field": "Font Name (Named Fonts)", "Value": "", "Reason for value": ""},
        {"Field": "Material Number (Named Fonts)", "Value": "", "Reason for value": ""},
        {"Field": "Swapping Allowed", "Value": "Yes/No", "Reason for value": ""},
        {"Field": "Reporting Days", "Value": "", "Reason for value": ""},
        {"Field": "Brand and License Protection", "Value": "", "Reason for value": ""},
        {"Field": "Binding Obligations", "Value": "", "Reason for value": ""},
        {"Field": "Past Usage Term (Dates)", "Value": "", "Reason for value": ""},
        {"Field": "Past Use Font Name", "Value": "", "Reason for value": ""},
        {"Field": "Past Use Assets", "Value": "", "Reason for value": ""},
        {"Field": "Past Use Font Material Number", "Value": "", "Reason for value": ""},
        {"Field": "Auto-Renewal", "Value": "", "Reason for value": ""},
        {"Field": "Renewal Period", "Value": "Not found on this document", "Reason for value": ""},
        {"Field": "Plus Inventory", "Value": "Yes/No", "Reason for value": ""},
        {"Field": "Adobe Originals", "Value": "Yes/No", "Reason for value": ""},
        {"Field": "Go-Forward Assets", "Value": "Not found on this document", "Reason for value": ""},
        {"Field": "Monotype Fonts Plan", "Value": "App Kit/Standard/Pro/Unlimited/Not Found in the Document", "Reason for value": ""},
        {"Field": "Onboarding", "Value": "Basic/Premier/Elite/Not found in the document", "Reason for value": ""},
        {"Field": "Monotype Single Sign-On", "Value": "Yes/No/Not Found in the Document", "Reason for value": ""},
        {"Field": "Customer Success Plan", "Value": "Basic/Enhanced/Premier/Elite/Not Found in the Document", "Reason for value": ""},
        {"Field": "Studio Services", "Value": "Yes/No/Not Found in the Document", "Reason for value": ""},
        {"Field": "Font User Management", "Value": "Basic/Premier/Elite/Not Found in the Document", "Reason for value": ""}
    ]

    fields_to_unmask = ["Customer Name", "Customer Contact Email", "Customer Contact First Name", "Customer Contact Last Name", "Primary Licensed Monotype Fonts User Email", "Binding Obligations(Sub-licensing/Transfer Entities)","Past Use Asset"]

    token_text = """YOU WILL BE HEAVILY PENALIZED FOR NOT FOLLOWING INSTRUCTIONS. 
                    - Upon receiving a user inquiry, you **must** directly search the document and return answers for all 48 fields in the required format. 
                    - **Do not** engage in a back-and-forth conversation, explain what you are doing, or restate the user's query.
                    - Your response **must only be the final answer** in json format, with the 48 field names and corresponding values. Do **not** return intermediate questions, commentary, or processing steps.
                    - If a field is not found, respond with 'Not found on this document' for that specific field. 
                    - Do **not** start by saying 'Let's search for this first' or any variation. Simply return the completed table at the end.
                    - You are **not allowed** to ask questions. Only perform the task as instructed and return the output in one go.
                    Strict rules to follow:
                        1. Ask no questions or restate no queries. Your task is to **silently** process the document and deliver the final output.
                        2. Return only the final table with answers for all 48 fields. Intermediate steps or explanations will lead to penalties.
                        3. Format your response in this table structure: 'Field, Value, Reason for value' (where applicable).
                        4. If the information is not found in the document, write 'Not found on this document' for that field.
                        5. Always adhere strictly to these instructions and focus solely on delivering the expected json output.
    
                    "Monotype Fonts Pro" IS NOT "Monotype Fonts Support" DO NOT CONFUSE THEM.
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "Monotype Fonts Preferred Service​"
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "Monotype Fonts Pro"
                    "YOU WILL BE HEAVILY PENALIZED IF YOU RETURN THIS RESULT "All Font Software available on Monotype Fonts during the Term."
                    Ensure that you:
                    Search the specific customer’s PDF for each field’s answer. Do not refer to other documents or sources.
                    Do not send any results until all 48 questions have been answered. Ensure accuracy is maintained for each answer, and if any information is not found in the document, respond with "Not found on this document."
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
                    31. Reporting days: "How many days does customer_name have to report their usage of the font software as Production Fonts? Focus only on the reporting days explicitly mentioned for reporting Production Fonts usage after receiving the list of downloaded Font Software. Exclude any references to providing information upon request or disputing inaccuracies. Include any additional days granted only if they follow a formal notice. Provide the result in the format 'X days and Y additional days' if applicable, or just 'X days' if no additional days are mentioned. Do not confuse this with invoice date"
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
                    6. Font Software and Production fonts are the same. So, for example, when the reference made to “Production font” or “Font Software” it is the same thing.
                    7. YOU CANNOT CHANGE THE INFORMATION, ELSE YOU WILL BE HEAVILY PENAILZED.
                    8. WHILE FETCHING MULTIPLE CONTRACTS DATA, YOU SHOULD UNDERSTAND AND FETCH DATA FROM ALL CONTRACTS INDIVISUALLY.
                    9. Signing and preparation of contract are different things. It should be treated differently.
                    10. ALWAYS SEARCH YOUR KNOWLEDGE BEFORE ANSWERING THE QUESTION
                    11. Always Answer in SHORT EXCEPT FOR THE FOLLOWING FIELDS, Name Fonts, Material Number, Production Font and Reporting. For these 4 fields your answer can be LONG
                    12. The Contract's Date whose termination date is before today's date is expired.
                    13. YOU CANNOT MAKE ANY ASSUMPTIONS.
                    15. ALWAYS present fields, their values and their reasons in a clear json format. Ensure that all answers are contained within the json and not outside of it.
                    16. Your output should EXACTLY BE THE 48 fields MENTIONED or you will be penalized. Your json response should follow the structure of the sample output. Ensure that all answers are specific to the correct customer and contract in question.
                    17. For the fields Web Page Views, Digital Ad Views, Licensed Applications, Registered Users, Commercial Documents, Licensed Externally Accessed Servers, Licensed Monotype Fonts User, Licensed Desktop Users, Additional Desktop User Count, Production font, return only the precise numerical value (fully written out, no abbreviations like "mill" or "k") or exact text from the document with no additional words, units, or explanations. Numbers should be written in full form (example: "8500000" not "8.5 mill"; "2000" not "2k").
                    18. YOU SHOULD FOLLOW ALL ABOVE MENTIONED POINTS ELSE YOU WILL BE PENAILZED HEAVILY.
                    """
    
    token_text_og = token_text
    pdf_documents = get_pdfs_from_folder(contract_path)
    print("Running for these pdfs, ", pdf_documents)

    all_text = ""
    run_open_ai = True

    anonymizer = EntityAnonymizer()

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
    token_text = token_text_og #make token text back to the original

    #If content is over 100 000
    if token_count > token_limit:
        print("Token limit execeeded")
        addendum_contracts = {}
        original_contracts = []
        contract_chunks_output = []
        for pdf_document in pdf_documents:
            pdf_text = extract_text_from_pdf(pdf_document)  # Extract text
            addendum_count = pdf_text.strip().lower().count("addendum")  # Count "Addendum" occurrences

            if addendum_count < 5:
                original_contracts.append(pdf_text)  # Classify as original contract
            else:
                addendum_number = extract_first_addendum_number(pdf_text)  # Extract addendum number
                if addendum_number is not None:
                    # Ensure the addendum_number is a string for consistent handling
                    addendum_number = str(addendum_number)

                    # Check if addendum_number already exists
                    sub_index = 1
                    while f"{addendum_number}.{sub_index}" in addendum_contracts:
                        sub_index += 1
                    unique_addendum_number = f"{addendum_number}.{sub_index}" if addendum_number in addendum_contracts else addendum_number
                    
                    # Store in dictionary with unique key
                    addendum_contracts[unique_addendum_number] = pdf_text

        # Convert dictionary to sorted list
        sorted_addendums = [{key: addendum_contracts[key]} for key in sorted(addendum_contracts, key=lambda x: tuple(map(int, x.split('.'))))]

        for addendum in sorted_addendums:
            print(list(addendum.keys())[0])

        #Chunking the contracts and addendums
        all_text_chunks = []
        all_text = ""

        # Put all the contracts in all_text, then anonymize it all, do the recursive function, will get list of chunks, we will send these chunks to gpt, get the results and put the results in list, then finally send it again to gpt to merge it.
        for contract in original_contracts:
            all_text = all_text + " \n" + contract

        for addendum_dict in sorted_addendums:
            addendum_number, addendum_text = list(addendum_dict.items())[0]
            all_text = all_text + " \n" + addendum_text

        pdf_document = pdf_documents[0]
        base_name = os.path.basename(pdf_document)
        document_name = os.path.splitext(base_name)[0]
        file_path = f'./ExcelOutput/{document_name}_data.xlsx'
        output_filename = f"./Output/{document_name}_Output.txt"
        anonymized_text, mapping, validated_entities = anonymizer.anonymize_text(all_text)
        list_of_chunks = asyncio.run(chunk_content_to_token_limit(anonymized_text))
        chunk_ai_output = []
        chunk_number = 0
        for chunk in list_of_chunks:
            chunk_number +=1
            if run_open_ai:
                client = AzureChatOpenAI(
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                    openai_api_version=os.getenv("OPENAI_API_VERSION"),
                    temperature=0,
                )

                response = client.invoke(
                    input=[
                        {"role": "system", "content": token_text},
                        {
                            "role": "user",
                            "content": f""" 
                            Sample Output: {sample_output}
                                ######
                                Give me the details of the contract below:
            
                                {chunk}
                            """
                        }
                    ]
                )

                print("#####")
                print(response)
                print("#####")

                message = response.content
                with open(f"./Output/chunk_json_output{chunk_number}.txt", "w", encoding="utf-8") as f:
                    f.write(str(message))
                output_msg = json_repair.loads(message)
                chunk_ai_output.append(output_msg)

        #Send the list of chunks ai output to get a merged output
        if run_open_ai:
                client = AzureChatOpenAI(
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                    openai_api_version=os.getenv("OPENAI_API_VERSION"),
                    temperature=0,
                )

                response = client.invoke(
                    input=[
                        {"role": "system", "content": """
                            You will be given a list of JSON data, where each JSON object contains **48 fields** extracted from a contract. 

                            All the JSON data belong to the **same company** and represent **different parts of the contract, including the main agreement and its addendums**. These documents were **chunked into 100,000-token segments** due to processing limitations and were analyzed separately. 

                            Your task is to **merge all the JSON objects together** to form **one final, complete JSON output** while ensuring that the values from the addendums are prioritized if they update the original contract.

                            ---

                            ### **🔹 Important Instructions**
                            1. **Accurate Merging (Prioritizing Addendum Updates)**:
                            - Ensure that all fields from the main contract and addendums are correctly merged without duplication.
                            - **If a value is stated to be updated in an addendum, that updated value must be taken instead of the original contract value**.
                            - Maintain the correct **hierarchy and relationship** between the main contract and its addendums.

                            2. **Handling "Not found on the document" Values**:
                            - If a field appears in multiple JSON objects and one of the values is `"Not found on the document"`, discard it and use the correct value if available.
                            - If all occurrences of a field contain `"Not found on the document"`, then leave it as `"Not found on the document"`.
                            - If an **addendum explicitly updates a field**, ensure the final output reflects **that updated value** rather than the original contract's value.

                            3. **Consistency & Logical Structure**:
                            - Ensure **only the most relevant and up-to-date information** is retained.
                            - If an addendum modifies a value (e.g., **Contract End Date** is extended), the **latest addendum value must be used** in the final output.
                            - Contract Start Date must always reflect the original contract's start date, not any modified date from an addendum. Always prioritize the earliest start date from the original contract, disregarding any changes introduced by addendums. If you are unable to find the original start date, Pick the contract start date that is the earliest.
                            - Avoid redundant, conflicting, or outdated values from previous contract versions.
                         
                            4. **Final Output**:
                            - The merged JSON should **retain only the most complete and accurate** values from all JSON objects.
                            - Ensure that all fields are **formatted consistently and logically organized**.
                            - The response must contain only the final JSON output, with no additional text, explanations, or formatting.

                            """},
                        {
                            "role": "user",
                            "content": f""" 
                                This is the list containg all the json data for this company, {chunk_ai_output}.
                                Merge them and return a single json data like the one in the list. The response must contain only the final JSON output, with no additional text, explanations, or formatting.                 
                            """
                        }
                    ]
                )

                print("#####")
                print(response)
                print("#####")

                message = response.content
                with open("./Output/final_json_output.txt", "w", encoding="utf-8") as f:
                    f.write(str(message))
                output_msg = json_repair.loads(message)

                
                if len(output_msg) == 48:
                    print("perfect amount")
                    first_name = next((entry["Value"] for entry in output_msg if entry["Field"] == "Customer Contact First Name"), None)
                    last_name = next((entry["Value"] for entry in output_msg if entry["Field"] == "Customer Contact Last Name"), None)
                    full_name = f"{first_name} {last_name}" if first_name and last_name else None

                    reverse_mapping = {v: k for k, v in mapping.items()}
                    for entry in output_msg:
                        field_name = entry["Field"]
                        if field_name in fields_to_unmask:
                            if entry['Value'] in reverse_mapping:
                                entry['Value'] = reverse_mapping[entry['Value']]
                                print(entry['Value'])
                            elif field_name in ["Customer Contact First Name", "Customer Contact Last Name"]:
                                if full_name and full_name in reverse_mapping:
                                    # Get the original full name from reverse_mapping
                                    original_full_name = reverse_mapping[full_name]
                                    original_parts = original_full_name.split(" ", 1)  # Split into first and last

                                    if field_name == "Customer Contact First Name":
                                        entry["Value"] = original_parts[0]  # Take first part
                                        print(f"Updated First Name: {entry['Value']}")
                                    elif field_name == "Customer Contact Last Name" and len(original_parts) > 1:
                                        entry["Value"] = original_parts[1]  # Take second part
                                        print(f"Updated Last Name: {entry['Value']}")
                            elif field_name == "Past Use Asset":
                                original_values = [val.strip() for val in entry["Value"].split(",")]  # Split and strip whitespace
                                
                                # Replace if in reverse_mapping
                                updated_values = [
                                    reverse_mapping[val] if val in reverse_mapping else val
                                    for val in original_values
                                ]

                                # Join back to a single comma-separated string
                                entry["Value"] = ", ".join(updated_values)
                else:
                    print("Output Fields length did not match")

                with open("./Output/final_remapped_json_output.json", "w", encoding="utf-8") as f:
                    json.dump(output_msg, f, indent=4, ensure_ascii=False)
                df = pd.DataFrame(output_msg)
                df.to_excel(file_path, index=False)
                        
                print(f"Data has been exported to {file_path}")
        return file_path

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
        client = AzureChatOpenAI(
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                    openai_api_version=os.getenv("OPENAI_API_VERSION"),
                    temperature=0,
        )

        response = client.invoke(
            input=[
                {"role": "system", "content": token_text},
                {
                    "role": "user",
                    "content": f""" 
                        Sample Output: {sample_output}
                        ######
                        Give me the details of the contract below:
    
                        {anonymized_text} 
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

        message = response.content
        with open("./Output/final_json_output.txt", "w", encoding="utf-8") as f:
            f.write(str(message))
        output_msg = json_repair.loads(message)

        
        if len(output_msg) == 48:
            print("perfect amount")
            first_name = next((entry["Value"] for entry in output_msg if entry["Field"] == "Customer Contact First Name"), None)
            last_name = next((entry["Value"] for entry in output_msg if entry["Field"] == "Customer Contact Last Name"), None)
            full_name = f"{first_name} {last_name}" if first_name and last_name else None

            reverse_mapping = {v: k for k, v in mapping.items()}
            for entry in output_msg:
                field_name = entry["Field"]
                if field_name in fields_to_unmask:
                    if entry['Value'] in reverse_mapping:
                        entry['Value'] = reverse_mapping[entry['Value']]
                        print(", ",entry['Value'])
                    elif field_name in ["Customer Contact First Name", "Customer Contact Last Name"]:
                        if full_name and full_name in reverse_mapping:
                            # Get the original full name from reverse_mapping
                            original_full_name = reverse_mapping[full_name]
                            original_parts = original_full_name.split(" ", 1)  # Split into first and last

                            if field_name == "Customer Contact First Name":
                                entry["Value"] = original_parts[0]  # Take first part
                                print(f"Updated First Name: {entry['Value']}")
                            elif field_name == "Customer Contact Last Name" and len(original_parts) > 1:
                                entry["Value"] = original_parts[1]  # Take second part
                                print(f"Updated Last Name: {entry['Value']}")
                    elif field_name == "Past Use Asset":
                                print("Value is ",entry["Value"])
                                original_values = [val.strip() for val in entry["Value"].split(",")]  # Split and strip whitespace
                                
                                # Replace if in reverse_mapping
                                updated_values = [
                                    reverse_mapping[val] if val in reverse_mapping else val
                                    for val in original_values
                                ]

                                # Join back to a single comma-separated string
                                entry["Value"] = ", ".join(updated_values)
                                print(f"Updated Past Use Asset: {entry['Value']}")                       
        else:
            print("Output Fields length did not match")

        with open("./Output/final_remapped_json_output.json", "w", encoding="utf-8") as f:
            json.dump(output_msg, f, indent=4, ensure_ascii=False)
        df = pd.DataFrame(output_msg)
        df.to_excel(file_path, index=False)
                
        print(f"Data has been exported to {file_path}")
    return file_path