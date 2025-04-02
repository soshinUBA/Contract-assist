import pandas as pd
import regex as re
import os
from dotenv import load_dotenv
from anonymizer import EntityAnonymizer
from pdf_extractor import extract_text_from_pdf, extract_text
from prompt_loader import PROMPT_MANAGER
from helpers import count_tokens, get_pdfs_from_folder, extract_docx_content, get_document_name, save_text_to_file, get_model, is_scanned_pdf_from_text
import json_repair
import asyncio
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv(".env")

def process_pdfs(pdf_documents):
    """Extract text from PDFs, handling both regular and scanned PDFs"""
    all_text = ""
    
    print("############# Starting PDF Processing ######################")
    try:
        for pdf_document in pdf_documents:
            try:
                # First try regular text extraction
                text = extract_text_from_pdf(pdf_document)
                
                # Check if it's likely a scanned PDF
                if is_scanned_pdf_from_text(text):
                    print(f"Scanned PDF detected in {pdf_document}, attempting OCR...")
                    text = extract_text(pdf_document)
                    if not text:
                        print(f"OCR extraction failed for {pdf_document}")
                        continue
                
                if not text:
                    print(f"No text extracted from {pdf_document}, skipping")
                    continue
                    
                all_text += text + "\n\n"
                
            except Exception as e:
                print(f"Error processing PDF {pdf_document}: {str(e)}")
                continue
        
        if not all_text:
            print("No valid text extracted from any PDF documents")
            return None
            
        return all_text
    except Exception as e:
        print(f"Error in PDF processing: {str(e)}")
        return None
    
def anonymize_contract_text(all_text, document_name):
    """Anonymize the contract text and save the results."""
    try:
        anonymizer = EntityAnonymizer()
        anonymized_text, mapping, validated_entities = anonymizer.anonymize_text(all_text)
        
        # Save anonymized text and mapping
        try:
            os.makedirs("./Output", exist_ok=True)
            output_filename = f"./Output/{document_name}_Output.txt"
            save_text_to_file(anonymized_text, output_filename)
            save_text_to_file(str(mapping), f"./Output/{document_name}_mappings.txt")
        except Exception as e:
            print(f"Error saving anonymized files: {str(e)}")
        
        print("\nMapping Dictionary:")
        for original, dummy in mapping.items():
            print(f"{original} → {dummy}")
        
        return anonymized_text, mapping
    except Exception as e:
        print(f"Error in text anonymization: {str(e)}")
        return all_text, {}  # Return original text if anonymization fails

def get_ai_response(all_text):
    """Get AI model response for field extraction."""
    print("############# Starting AI Processing ######################")
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
    try:
        client = get_model()
        response = client.invoke(
            input=[
                {
                    "role": PROMPT_MANAGER.get_prompt('FIELD_EXTRACTION', 'role'), 
                    "content": PROMPT_MANAGER.get_prompt('FIELD_EXTRACTION', 'content')
                },
                {
                    "role": PROMPT_MANAGER.get_prompt('DOCUMENT_PROMPT', 'role'),
                    "content": PROMPT_MANAGER.get_prompt('DOCUMENT_PROMPT', 'content',json_sample_output=sample_output, all_text=all_text)
                }
            ]
        )
        
        print("#####")
        print(response)
        print("#####")
        
        return response
    except Exception as e:
        print(f"Error in AI processing: {str(e)}")
        return None

def get_ai_merge_response(list_of_chunk_output):
    """Get AI model response from chunks ouput."""
    print("############# Starting AI Processing ######################")
    try:
        client = get_model()
        response = client.invoke(
            input=[
                {
                    "role": PROMPT_MANAGER.get_prompt('CHUNK_MERGING_PROMPT_SYSTEM', 'role'), 
                    "content": PROMPT_MANAGER.get_prompt('CHUNK_MERGING_PROMPT_SYSTEM', 'content')
                },
                {
                    "role": PROMPT_MANAGER.get_prompt('CHUNK_MERGING_PROMPT_USER', 'role'),
                    "content": PROMPT_MANAGER.get_prompt('CHUNK_MERGING_PROMPT_USER', 'content', list_of_chunk_output=list_of_chunk_output)
                }
            ]
        )
        
        print("#####")
        print(response)
        print("#####")
        
        return response
    except Exception as e:
        print(f"Error in AI processing: {str(e)}")
        return None

def parse_response_to_df(response_content, mapping=None):
    fields_to_unmask = ["Customer Name", "Customer Contact Email", "Customer Contact First Name", "Customer Contact Last Name", "Primary Licensed Monotype Fonts User Email", "Binding Obligations(Sub-licensing/Transfer Entities)","Past Use Asset"]
    try:
        if not response_content:
            print("Empty response content received")
            return pd.DataFrame({"Field": [], "Value": [], "Reason for value": []})
        output_msg = json_repair.loads(response_content)
        if len(output_msg) == 48:
            first_name = next((entry["Value"] for entry in output_msg if entry["Field"] == "Customer Contact First Name"), None)
            last_name = next((entry["Value"] for entry in output_msg if entry["Field"] == "Customer Contact Last Name"), None)
            full_name = f"{first_name} {last_name}" if first_name and last_name else None
            reverse_mapping = {v: k for k, v in mapping.items()}
            for entry in output_msg:
                field_name = entry["Field"]
                if field_name in fields_to_unmask:
                    if entry['Value'] in reverse_mapping:
                        entry['Value'] = reverse_mapping[entry['Value']]
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
                        with open("./Output/final_remapped_json_output.json", "w", encoding="utf-8") as f:
                            json.dump(output_msg, f, indent=4, ensure_ascii=False)
                        df = pd.DataFrame(output_msg)
                        return df
        else:
            print("Output Fields length did not match")
            return pd.DataFrame({"Field": [], "Value": [], "Reason for value": []})

    except Exception as e:
        print(f"Error parsing response to DataFrame: {str(e)}")
        # Return empty DataFrame as fallback
        return pd.DataFrame({"Field": [], "Value": [], "Reason for value": []})
    
def save_output_files(response_content, document_name, df):
    """Save the output files (text response and Excel)."""
    try:
        # Create output directories if they don't exist
        os.makedirs("./Output", exist_ok=True)
        os.makedirs("./ExcelOutput", exist_ok=True)
        
        # Save raw response
        output_filename = f"./Output/{document_name}_Output_2.txt"
        save_text_to_file(response_content, output_filename)
        
        # Save Excel file
        excel_path = f'./ExcelOutput/{document_name}_data.xlsx'
        df.to_excel(excel_path, index=False)
        
        print(f"Data has been exported to {excel_path}")
        return excel_path
    except Exception as e:
        print(f"Error saving output files: {str(e)}")
        return None

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

async def chunk_content_to_token_limit(content, token_limit_value):
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

def chunk_process(pdf_documents, document_name, token_limit_value):
    try:
        addendum_contracts = {}
        original_contracts = []

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
        all_text = ""

        # Put all the contracts in all_text, then anonymize it all, do the recursive function, will get list of chunks, we will send these chunks to gpt, get the results and put the results in list, then finally send it again to gpt to merge it.
        for contract in original_contracts:
            all_text = all_text + " \n" + contract

        for addendum_dict in sorted_addendums:
            addendum_number, addendum_text = list(addendum_dict.items())[0]
            all_text = all_text + " \n" + addendum_text

        anonymized_text, mapping = anonymize_contract_text(all_text, document_name)
        list_of_chunks = asyncio.run(chunk_content_to_token_limit(anonymized_text, token_limit_value))
        chunk_ai_output = []
        chunk_number = 0

        for chunk in list_of_chunks:
            chunk_number +=1
            response = get_ai_response(chunk)
            if response is None:
                print("Failed to get AI response, exiting")
                return None
            save_text_to_file(str(response.content), f"./Output/chunk_json_output{chunk_number}.txt")
            output_msg = json_repair.loads(response.content)
            chunk_ai_output.append(output_msg)

        response = get_ai_merge_response(chunk_ai_output)
        if response is None:
            print("Failed to get AI response, exiting")
            return None
        
        # Parse response into DataFrame
        df = parse_response_to_df(response.content, mapping)
        
        # Save outputs
        excel_path = save_output_files(response.content, document_name, df)
        
        return excel_path
    except Exception as e:
        print("Error while chunking content:", e)
        exit()


def contract_assist(contract_path):
    """Main function to process contract documents and extract fields."""
    token_limit_value = 100000
    try:
        # Check token limit
        token_text = PROMPT_MANAGER.get_prompt('FIELD_EXTRACTION', 'content')
        
        # Get PDF documents
        try:
            if os.path.isfile(contract_path):
                pdf_documents = [contract_path]
            else:
                pdf_documents = get_pdfs_from_folder(contract_path)
                if not pdf_documents:
                    print(f"No PDF documents found in {contract_path}")
                    return None
                print("Running for these PDFs: ", pdf_documents)
        except Exception as e:
            print(f"Error getting PDF documents: {str(e)}")
            return None
        
        # Process PDFs
        all_text = process_pdfs(pdf_documents)
        if all_text is None:
            return None
        
        # Save original text
        try:
            save_text_to_file(all_text, "contract_b4.txt")
        except Exception as e:
            print(f"Error saving original text: {str(e)}")
                
        # Get document name for file naming
        try:
            pdf_document = pdf_documents[0]
            document_name = get_document_name(pdf_document)
        except Exception as e:
            print(f"Error getting document name: {str(e)}")
            document_name = "unknown_document"
        
        # Check token limit
        try:
            token_text += all_text
            token_count = count_tokens(token_text)
            if token_count > token_limit_value:
                print(f"Token limit exceeded ({token_count} tokens). Chunking Process started")
                return chunk_process(pdf_documents, document_name, token_limit_value)
        except Exception as e:
            print(f"Error counting tokens: {str(e)}")
            print("Proceeding without token check")

        # Anonymize text
        anonymized_text, mapping = anonymize_contract_text(all_text, document_name)
        try:
            save_text_to_file(anonymized_text, "contract_anonymized.txt")
        except Exception as e:
            print(f"Error saving anonymized text: {str(e)}")
        
        # Get AI response
        response = get_ai_response(anonymized_text)
        if response is None:
            print("Failed to get AI response, exiting")
            return None
        
        # Parse response into DataFrame
        df = parse_response_to_df(response.content, mapping)
        
        # Save outputs
        excel_path = save_output_files(response.content, document_name, df)
        
        return excel_path
    except Exception as e:
        print(f"Unhandled error in contract_assist: {str(e)}")
        return None