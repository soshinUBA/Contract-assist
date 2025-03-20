import pandas as pd
import regex as re
import os
from dotenv import load_dotenv
from anonymizer import EntityAnonymizer
from pdf_extractor import extract_text_from_pdf
from prompt_loader import PROMPT_MANAGER
from helpers import count_tokens, get_pdfs_from_folder, extract_docx_content, get_document_name, save_text_to_file, get_model

load_dotenv(".env")

def process_pdfs(pdf_documents):
    """Extract text from PDFs and verify content length."""
    all_text = ""
    
    print("############# Starting PDF Processing ######################")
    try:
        for pdf_document in pdf_documents:
            try:
                text = extract_text_from_pdf(pdf_document)
                if len(text) <= 800:
                    print(f"Image file detected or minimal text in {pdf_document}, skipping")
                    continue
                all_text += text
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

def get_ai_response(faq_doc, all_text):
    """Get AI model response for field extraction."""
    print("############# Starting AI Processing ######################")
    
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
                    "content": PROMPT_MANAGER.get_prompt('DOCUMENT_PROMPT', 'content', faq_doc=faq_doc, all_text=all_text)
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

def parse_response_to_dataframe(response_content, mapping=None):
    """Parse the AI response into a structured DataFrame."""
    try:
        if not response_content:
            print("Empty response content received")
            return pd.DataFrame({"Field": [], "Value": [], "Reason for value": []})
            
        # Remove separator lines and extract rows
        lines = [line for line in response_content.splitlines() if '----' not in line]
        lines = [line for line in lines if not re.match(r'^\|\s*-+\s*\|\s*-+\s*\|\s*-+\s*\|$', line)]

        fields, values, reasons = [], [], []

        # Process each line into components
        for line in lines[1:]:  # Skip header row
            if '|' in line:
                parts = line.split('|')[1:4]  # Split into Field, Value, and Reason
                if len(parts) == 3:
                    fields.append(parts[0].strip())
                    values.append(parts[1].strip())
                    reasons.append(parts[2].strip())

        # De-anonymize specific fields if mapping is provided
        if mapping and len(values) > 12:
            try:
                indices_to_check = [8, 10, 11, 12]
                reverse_mapping = {v: k for k, v in mapping.items()}

                for i in indices_to_check:
                    if i < len(values) and values[i] in reverse_mapping:
                        values[i] = reverse_mapping[values[i]]
            except Exception as e:
                print(f"Error during de-anonymization: {str(e)}")

        # Create DataFrame
        data = {
            "Field": fields,
            "Value": values,
            "Reason for value": reasons
        }
        
        return pd.DataFrame(data)
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

def contract_assist(contract_path):
    """Main function to process contract documents and extract fields."""
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
        
        # Get FAQ document
        try:
            word_doc = "./FAQ_document_48_fields.docx"
            faq_doc = extract_docx_content(word_doc)
            print(faq_doc)
            
            # Save FAQ content for reference
            save_text_to_file(faq_doc, "faq.txt")
        except Exception as e:
            print(f"Error extracting FAQ document: {str(e)}")
            print("Proceeding without FAQ guidance")
            faq_doc = "FAQ document not available"
        
        # Process PDFs
        all_text = process_pdfs(pdf_documents)
        if all_text is None:
            return None
        
        # Save original text
        try:
            save_text_to_file(all_text, "contract_b4.txt")
        except Exception as e:
            print(f"Error saving original text: {str(e)}")
        
        # Check token limit
        try:
            token_text += all_text
            token_count = count_tokens(token_text)
            if token_count > 120000:
                print(f"Token limit exceeded ({token_count} tokens). Exiting the code.")
                return None
        except Exception as e:
            print(f"Error counting tokens: {str(e)}")
            print("Proceeding without token check")
        
        # Get document name for file naming
        try:
            pdf_document = pdf_documents[0]
            document_name = get_document_name(pdf_document)
        except Exception as e:
            print(f"Error getting document name: {str(e)}")
            document_name = "unknown_document"
        
        # Anonymize text
        anonymized_text, mapping = anonymize_contract_text(all_text, document_name)
        try:
            save_text_to_file(anonymized_text, "contract_anonymized.txt")
        except Exception as e:
            print(f"Error saving anonymized text: {str(e)}")
        
        # Get AI response
        response = get_ai_response(faq_doc, anonymized_text)
        if response is None:
            print("Failed to get AI response, exiting")
            return None
        
        # Parse response into DataFrame
        df = parse_response_to_dataframe(response.content, mapping)
        
        # Save outputs
        excel_path = save_output_files(response.content, document_name, df)
        
        return excel_path
    except Exception as e:
        print(f"Unhandled error in contract_assist: {str(e)}")
        return None