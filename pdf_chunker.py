# pdf_chunker.py
#
# Description:
# This script extracts text from a PDF file and splits it into smaller, overlapping chunks.
# The output is a JSON file containing the text chunks, which can then be used as input
# for language models like Google's Gemini.
#
# Dependencies:
# - PyPDF2: A library for reading and manipulating PDF files.
#   Install it using pip: pip install PyPDF2
#
# How to Use:
# 1. Save this script as `pdf_chunker.py`.
# 2. Make sure you have PyPDF2 installed (`pip install PyPDF2`).
# 3. Place the PDF you want to process in the same directory as this script.
# 4. Run the script from your terminal, providing the PDF filename as an argument:
#    python pdf_chunker.py your_document.pdf
#
# 5. The script will generate a new file named `your_document_chunks.json`.

import json
import os
import sys
import PyPDF2

def extract_text_from_pdf(pdf_path):
    """
    Extracts all text content from a given PDF file.
    """
    print(f"--- Extracting text from '{pdf_path}'... ---")
    try:
        with open(pdf_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            full_text = []
            for page_num, page in enumerate(reader.pages):
                full_text.append(page.extract_text())
                print(f"  - Extracted text from page {page_num + 1}")
            
            print("--- Text extraction complete. ---")
            return "\n".join(full_text)
    except FileNotFoundError:
        print(f"--- ERROR: The file '{pdf_path}' was not found. ---")
        return None
    except Exception as e:
        print(f"--- ERROR: An unexpected error occurred while reading the PDF: {e} ---")
        return None

def split_text_into_chunks(text, chunk_size=2000, chunk_overlap=200):
    """
    Splits a long text into smaller, overlapping chunks.

    Args:
        text (str): The full text to be chunked.
        chunk_size (int): The desired character length of each chunk.
        chunk_overlap (int): The number of characters to overlap between consecutive chunks
                             to maintain context.

    Returns:
        list[dict]: A list of chunk objects.
    """
    if not text:
        return []

    print(f"--- Splitting text into chunks (size: {chunk_size}, overlap: {chunk_overlap})... ---")
    
    chunks = []
    start_index = 0
    chunk_id = 1
    
    while start_index < len(text):
        end_index = start_index + chunk_size
        chunk_content = text[start_index:end_index]
        
        chunks.append({
            "chunk_id": chunk_id,
            "text": chunk_content
        })
        
        # Move the start index for the next chunk, accounting for the overlap
        start_index += chunk_size - chunk_overlap
        chunk_id += 1

    print(f"--- Text successfully split into {len(chunks)} chunks. ---")
    return chunks

def save_chunks_to_json(chunks, input_filename):
    """
    Saves the list of text chunks to a JSON file.
    """
    # Create an output filename based on the input PDF name
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}_chunks.json"
    
    print(f"--- Saving chunks to '{output_filename}'... ---")
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, indent=4, ensure_ascii=False)
        print("--- Successfully saved chunks to JSON. ---")
    except Exception as e:
        print(f"--- ERROR: Could not save chunks to JSON file: {e} ---")

def main():
    """
    Main function to orchestrate the PDF processing pipeline.
    """
    # Check if a filename was provided as a command-line argument
    if len(sys.argv) < 2:
        print("--- USAGE: python pdf_chunker.py <your_pdf_filename.pdf> ---")
        return

    pdf_path = sys.argv[1]
    
    # 1. Extract text from the PDF
    full_text = extract_text_from_pdf(pdf_path)
    
    if full_text:
        # 2. Split the text into chunks
        text_chunks = split_text_into_chunks(full_text)
        
        # 3. Save the chunks to a JSON file
        if text_chunks:
            save_chunks_to_json(text_chunks, pdf_path)

if __name__ == '__main__':
    main()
