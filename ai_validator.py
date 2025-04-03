import fitz  # PyMuPDF
import json
import os

def format_number(value):
    """Converts a numeric string to a comma-separated format (e.g., '1000' → '1,000')."""
    return "{:,}".format(int(value)) if value.isdigit() else value

def is_nearby(rect1, rect2, threshold=50):
    """Check if two rectangles are nearby within a given threshold."""
    return abs(rect1.y1 - rect2.y1) < threshold and abs(rect1.x0 - rect2.x0) < threshold

def find_text_and_draw(pdf_path, json_path):
    # Read JSON file
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Extract contract number for naming the output folder
    contract_number = None
    for item in data:
        if item["Field"].lower() == "contract number":
            contract_number = item["Value"].strip()
            break

    # Define the full output path
    if contract_number:
        contract_folder = contract_number  # Folder named after contract number
        output_folder = os.path.join(contract_folder, "ai_validation")
    else:
        output_folder = "ai_validation"  # Fallback if no contract number found

    # Ensure folders exist
    os.makedirs(output_folder, exist_ok=True)

    # Store missing fields/values in categories
    missing_data = {
        "fields_found_but_values_missing": [],
        "values_found_but_fields_missing": [],
        "both_fields_and_values_missing": []
    }

    # Iterate through all PDFs in the folder
    for pdf_file in os.listdir(pdf_path):
        if pdf_file.endswith(".pdf"):
            pdf_full_path = os.path.join(pdf_path, pdf_file)
            doc = fitz.open(pdf_full_path)

            # Track found fields and values to ensure missing ones are correctly identified
            found_fields = set()
            found_values = set()

            # Flag to track contract number presence
            contract_number_found = False  

            # Iterate through each field and value pair
            for item in data:
                field = str(item["Field"]).strip()
                value = str(item["Value"]).strip()
                
                # Append a space for "yes" and "no"
                if field.lower() in ["yes", "no"]:
                    field = f" {field} "
                if value.lower() in ["yes", "no"]:
                    value = f" {value} "

                # Format numeric values with commas
                value_with_commas = format_number(value)

                field_found, value_found = False, False
                
                # Iterate through all pages
                for page in doc:
                    # Search for field
                    field_instances = page.search_for(field, quads=False)  
                    if field_instances:
                        field_found = True
                        found_fields.add(field)
                        for inst in field_instances:
                            page.draw_rect(inst, color=(1, 0, 0), width=1.5)  # Red for fields

                    value_instances = []
                    
                    if value.isdigit():  # Only process numeric values carefully
                        words = page.get_text("words")  # Extract words from page
                        for w in words:
                            word_text = w[4]
                            if word_text == value or word_text == value_with_commas:  # Exact match
                                word_rect = fitz.Rect(w[:4])  # Get bounding box

                                # Ensure it's not part of a bigger number (like '100' inside '10001')
                                surrounding_words = [
                                    w2[4] for w2 in words if is_nearby(fitz.Rect(w2[:4]), word_rect, threshold=5)
                                ]
                                if not any(word_text in w2 and word_text != w2 for w2 in surrounding_words):
                                    value_found = True
                                    found_values.add(value)
                                    page.draw_rect(word_rect, color=(0, 1, 0), width=1.5)  # Green for value

                    else:
                        # Search for value (both original and comma-separated versions)
                        value_instances = page.search_for(value, quads=False) or page.search_for(value_with_commas, quads=False)
                        if value_instances:
                            value_found = True
                            found_values.add(value)
                            for inst in value_instances:
                                page.draw_rect(inst, color=(0, 1, 0), width=1.5)  # Green for values
                
                # Handle "Contract Number" logic separately
                if field.lower() == "contract number":
                    if field_found:
                        contract_number_found = True  # Contract Number found, no need to search for "Contract #"
                    continue  

            # If contract number was not found, search for "Contract #"
            if not contract_number_found:
                for page in doc:
                    contract_number_instances = page.search_for("Contract #", quads=False)
                    if contract_number_instances:
                        contract_number_found = True  # Found "Contract #", don't write to JSON
                        for inst in contract_number_instances:
                            page.draw_rect(inst, color=(1, 0, 0), width=1.5)  # Red for contract number

            # Save the modified PDF with bounding boxes
            output_pdf_path = os.path.join(output_folder, pdf_file)
            doc.save(output_pdf_path)
            doc.close()

    # Identify truly missing fields and values
    for item in data:
        field = item["Field"].strip()
        value = item["Value"].strip()

        if field.lower() == "contract number":
            continue  # Skip contract number logic, already handled

        field_found = field in found_fields
        value_found = value in found_values

        # Only write missing data to JSON
        if field_found and not value_found:
            missing_data["fields_found_but_values_missing"].append({
                "field": field, 
                "value": value
            })
        elif not field_found and value_found:
            missing_data["values_found_but_fields_missing"].append({
                "field": field, 
                "value": value
            })
        elif not field_found and not value_found:
            missing_data["both_fields_and_values_missing"].append({
                "field": field, 
                "value": value
            })

    # Save missing fields/values to a JSON file with organized structure
    json_output_path = os.path.join(output_folder, "missing_data.json")

    # Only write JSON if there is actual missing data
    if any(missing_data.values()):  
        with open(json_output_path, "w", encoding="utf-8") as json_file:
            json.dump(missing_data, json_file, indent=4)
        print(f"Missing data saved in '{json_output_path}'.")
    else:
        print("No missing data. JSON file was not created.")

    print(f"Processing complete. Annotated PDFs saved in '{output_folder}'.")

# Example usage
# pdf_folder = "Global Order Management & Royalty/English/Folders/M00202119"
# json_file = "Output/final_remapped_json_output.json"
# find_text_and_draw(pdf_folder, json_file)
