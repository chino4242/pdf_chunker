# pdf_table_analyzer.py
#
# Description:
# This script processes a range of pages from a PDF. For each page, it extracts
# both the text and an image of the page. It then sends both to the multimodal
# Gemini 1.5 Flash model and asks it to generate a structured JSON object that
# combines the skill description from the text with the player data from the table.
#
# Dependencies:
# - PyMuPDF (fitz): pip install PyMuPDF
# - google-generativeai: pip install google-generativeai
# - Pillow: pip install Pillow
#
# How to Use:
# 1. Ensure you have a 64-bit version of Python and have set your GOOGLE_API_KEY.
# 2. Run the script from your terminal, providing the PDF filename, a start page,
#    and an end page.
#
# Example Command:
# python pdf_table_analyzer.py "My Document.pdf" 26 32
#

import google.generativeai as genai
from google.api_core import exceptions
import json
import os
import sys
import fitz  # PyMuPDF
from PIL import Image
import io
import time

def configure_gemini():
    """Configures the Gemini API with the key from environment variables."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("--- ERROR: GOOGLE_API_KEY environment variable not found. ---")
        return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("--- Gemini API configured successfully for multimodal analysis. ---")
    return model

def extract_page_content(pdf_path, page_number):
    """
    Extracts a single page from a PDF and returns it as both a PIL Image and text.
    """
    print(f"--- Extracting content for page {page_number} from '{pdf_path}'... ---")
    try:
        with fitz.open(pdf_path) as doc:
            if page_number > len(doc):
                print(f"  - Warning: Page number {page_number} is out of bounds.")
                return None, None
            
            page = doc.load_page(page_number - 1)
            
            # 1. Extract as Image
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # 2. Extract as Text
            text = page.get_text()
            
            print(f"--- Successfully extracted image and text for page {page_number}. ---")
            return image, text
            
    except Exception as e:
        print(f"--- ERROR: An unexpected error occurred while processing page {page_number}: {e} ---")
        return None, None

def analyze_page_with_gemini(model, image, text):
    """
    Sends the image and text of the page to Gemini and asks it to parse the data.
    Includes retry logic for rate limit errors.
    """
    if not image or not text:
        print("--- Missing image or text for analysis. ---")
        return None

    print("--- Sending page content to Gemini for analysis... ---")
    
    prompt = """
    You are a data extraction specialist. I am providing you with the text content and an image of a single page from a document.

    First, read the provided text to identify the primary skill being discussed (e.g., "Vision", "Elusiveness"). 
    
    Next, analyze the table in the provided image. The columns in the table represent ranked categories for that skill.
    
    Return a single JSON object with two keys:
    1. "skill": The name of the skill you identified from the text.
    2. "ratings": An object where each key is a column title from the table (e.g., "Star Caliber", "Starter Caliber") and the value is an array of the player names listed in that column.
    """
    
    try:
        response = model.generate_content([prompt, text, image])
        return response.text
    except exceptions.ResourceExhausted as e:
        print(f"--- RATE LIMIT HIT. Waiting for 65 seconds before retrying... ---")
        print(f"   - Error details: {e}")
        time.sleep(65)
        # Retry the request once after waiting
        try:
            print("--- Retrying API call... ---")
            response = model.generate_content([prompt, text, image])
            return response.text
        except Exception as retry_e:
            print(f"--- ERROR: An error occurred on retry: {retry_e} ---")
            return None
    except Exception as e:
        print(f"--- ERROR: An unexpected error occurred during Gemini API call: {e} ---")
        return None

def clean_and_parse_json(json_string):
    """
    Cleans markdown formatting from a JSON string and parses it.
    """
    # Remove markdown code block fences if they exist
    if json_string.strip().startswith("```json"):
        # Strip ```json from the beginning and ``` from the end
        cleaned_string = json_string.strip()[7:-3].strip()
    elif json_string.strip().startswith("```"):
        cleaned_string = json_string.strip()[3:-3].strip()
    else:
        cleaned_string = json_string.strip()
    
    return json.loads(cleaned_string)


def save_structured_data(all_skills_data, input_filename):
    """
    Saves the consolidated list of structured skill data to a single JSON file.
    """
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}_skills_analysis.json"
    
    print(f"--- Saving structured skills data to '{output_filename}'... ---")
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_skills_data, f, indent=4, ensure_ascii=False)
        print("--- Successfully saved structured data. ---")
    except Exception as e:
        print(f"--- ERROR: Could not save data to JSON file: {e} ---")


def main():
    """
    Main function to orchestrate the PDF table extraction pipeline for a range of pages.
    """
    if len(sys.argv) < 4:
        print("--- USAGE: python pdf_table_analyzer.py <pdf_file.pdf> <start_page> <end_page> ---")
        return

    pdf_path = sys.argv[1]
    try:
        start_page = int(sys.argv[2])
        end_page = int(sys.argv[3])
    except ValueError:
        print("--- ERROR: Start and end pages must be integer numbers. ---")
        return
    
    model = configure_gemini()
    if not model: return

    all_skills_analysis = []
    
    for page_num in range(start_page, end_page + 1):
        table_image, page_text = extract_page_content(pdf_path, page_num)
        if not table_image or not page_text: continue

        analysis_json_string = analyze_page_with_gemini(model, table_image, page_text)
        
        if analysis_json_string:
            try:
                # Clean the response and parse it into a dictionary
                data = clean_and_parse_json(analysis_json_string)
                all_skills_analysis.append(data)
            except json.JSONDecodeError:
                print(f"--- WARNING: Could not parse JSON from response for page {page_num}. Skipping. ---")
                print(f"--- Raw Response: ---\n{analysis_json_string}\n--------------------")
        
        # Proactively pause to respect API rate limits, but only if it's not the last page
        if (page_num - start_page + 1) % 14 == 0 and page_num < end_page:
            print(f"\n--- Processed 14 pages. Pausing for 65 seconds to respect rate limits... ---\n")
            time.sleep(65)

    if all_skills_analysis:
        save_structured_data(all_skills_analysis, pdf_path)
    else:
        print("--- No data was successfully analyzed. Output file will not be created. ---")

if __name__ == '__main__':
    main()

