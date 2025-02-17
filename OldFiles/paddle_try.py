import os
import csv
import cv2
import numpy as np
from pdf2image import convert_from_path
from paddleocr import PaddleOCR
pdf_path = "./Contracts/old/M00203557.pdf"

# Initialize OCR
ocr = PaddleOCR(use_angle_cls=True, lang='en')

# Convert PDF to images
images = convert_from_path(pdf_path)

# Open a CSV file to save the extracted table
output_file_path = "extracted_table_output.csv"
csv_file = open(output_file_path, "w", newline='', encoding="utf-8")
csv_writer = csv.writer(csv_file)

# Write header for the CSV
csv_writer.writerow(["Field", "Value"])

# Function to perform OCR on the entire page and attempt to extract field-value pairs
def extract_text_from_image(image_path, page_number):
    # Read the image
    img = cv2.imread(image_path)

    # Perform OCR on the entire image
    ocr_result = ocr.ocr(image_path)

    # Extract field-value pairs based on simple heuristics
    field_value_pairs = []

    # Go through OCR results and try to group text into field-value pairs
    for line in ocr_result:
        line_text = ' '.join([word_info[1][0] for word_info in line])

        # Use a heuristic: check if the line contains a colon, which is common in field-value pairs
        if ':' in line_text:
            parts = line_text.split(':', 1)  # Split into two parts: field and value
            field = parts[0].strip()         # Field part
            value = parts[1].strip()         # Value part
            field_value_pairs.append((field, value))
        else:
            # If the line doesn't contain a colon, treat it as a continuation of a previous field
            if field_value_pairs:
                field_value_pairs[-1] = (field_value_pairs[-1][0], field_value_pairs[-1][1] + " " + line_text)

    # Debug: print the detected field-value pairs for this page
    print(f"Detected field-value pairs on page {page_number}: {field_value_pairs}")

    # Write the field-value pairs to the CSV file
    for field, value in field_value_pairs:
        csv_writer.writerow([field, value])

# Process each page of the PDF
for i, image in enumerate(images):
    image_path = f"contract_images/page_{i+1}.png"
    image.save(image_path, "PNG")

    # Extract text and detect field-value pairs
    extract_text_from_image(image_path, i+1)

    print("\n" + "="*50 + f" End of page {i+1} " + "="*50 + "\n")

# Close the CSV file after the entire PDF is processed
csv_file.close()