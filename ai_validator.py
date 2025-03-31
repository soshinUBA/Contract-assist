import fitz
import json
import os
 
def format_number(value):
    """Converts a numeric string to a comma-separated format (e.g., '1000' → '1,000')."""
    return "{:,}".format(int(value)) if value.isdigit() else value
 
def is_nearby(rect1, rect2, threshold=50):
    """Check if two rectangles are nearby within a given threshold."""
    return abs(rect1.y1 - rect2.y1) < threshold and abs(rect1.x0 - rect2.x0) < threshold
 
def find_text_and_draw(pdf_path, json_path):
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
        contract_folder = contract_number
        output_folder = os.path.join(contract_folder, "ai_validation")
    else:
        output_folder = "AI_Validation"  # Fallback if no contract number found
 
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
            found_items = {"fields": [], "values": []}
 
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
                
                for page in doc:
                    field_instances = page.search_for(field, quads=False)  # Find field
                    for inst in field_instances:
                        page.draw_rect(inst, color=(1, 0, 0), width=1.5)  # Red for fields
                        found_items["fields"].append(field)
                        field_found = True
 
                    value_instances = []
                    
                    if value == "0":
                        # Extract words from the page
                        words = page.get_text("words")
                        for w in words:
                            if w[4] == "0":  # Check exact match
                                zero_rect = fitz.Rect(w[:4])  # Get bounding box
 
                                # Check if a field is nearby
                                if any(is_nearby(zero_rect, fitz.Rect(f)) for f in field_instances):
                                    page.draw_rect(zero_rect, color=(0, 1, 0), width=1.5)  # Green for `0`
                                    value_instances.append(zero_rect)
                    else:
                        # Search for value (both original and comma-separated versions)
                        value_instances = page.search_for(value, quads=False) or page.search_for(value_with_commas, quads=False)
 
                    for inst in value_instances:
                        page.draw_rect(inst, color=(0, 1, 0), width=1.5)  # Green for values
                        found_items["values"].append(value)
                        value_found = True
                
                # Organize missing data into categories
                if field_found and not value_found:
                    missing_data["fields_found_but_values_missing"].append({
                        "field": field.strip(),
                        "value": value.strip()
                    })
                elif not field_found and value_found:
                    missing_data["values_found_but_fields_missing"].append({
                        "field": field.strip(),
                        "value": value.strip()
                    })
                elif not field_found and not value_found:
                    missing_data["both_fields_and_values_missing"].append({
                        "field": field.strip(),
                        "value": value.strip()
                    })
            
            # Save the modified PDF with bounding boxes
            output_pdf_path = os.path.join(output_folder, pdf_file)
            doc.save(output_pdf_path)
            doc.close()
 
    # Save missing fields/values to a JSON file with organized structure
    json_output_path = os.path.join(output_folder, "missing_data.json")
    with open(json_output_path, "w", encoding="utf-8") as json_file:
        json.dump(missing_data, json_file, indent=4)
 
    print(f"Processing complete. Annotated PDFs saved in '{output_folder}'. Missing data saved in '{json_output_path}'.")
 
# Example usage
pdf_folder = "Global Order Management & Royalty/English/Folders/M00200233"
json_file = "ExcelOutput/final_remapped_json_output.json"
find_text_and_draw(pdf_folder, json_file)