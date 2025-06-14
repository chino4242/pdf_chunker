# gemini_analyzer.py
#
# Description:
# This script reads a JSON file of text chunks (created by pdf_chunker.py),
# sends each chunk to the Google Gemini API with a user-defined prompt,
# and saves the results into a new JSON file.
#
# Dependencies:
# - google-generativeai: The official Google client library for the Gemini API.
#   Install it using pip: pip install google-generativeai
#
# Setup:
# 1. Get a Gemini API key from Google AI Studio: https://makersuite.google.com/
# 2. Set your API key as an environment variable. In your terminal, run:
#    (For Windows)
#    set GOOGLE_API_KEY="YOUR_API_KEY"
#    (For macOS/Linux)
#    export GOOGLE_API_KEY="YOUR_API_KEY"
#
# How to Use:
# 1. Save this script as `gemini_analyzer.py`.
# 2. Run the script from your terminal, providing two arguments:
#    - The path to your `_chunks.json` file.
#    - The prompt you want to ask Gemini, enclosed in quotes.
#
# Example Command:
# python gemini_analyzer.py your_document_chunks.json "Summarize the key points of the following text in five bullet points."
#

import google.generativeai as genai
import json
import os
import sys
import time

def configure_gemini():
    """
    Configures the Gemini API with the key from environment variables.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("--- ERROR: GOOGLE_API_KEY environment variable not found. ---")
        print("--- Please get a key from Google AI Studio and set the environment variable. ---")
        return None
    
    genai.configure(api_key=api_key)
    # Using gemini-1.5-flash as it's fast and has a large context window.
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("--- Gemini API configured successfully. ---")
    return model

def analyze_chunks_with_gemini(model, chunks, user_prompt):
    """
    Sends each text chunk to the Gemini API and collects the analysis.
    """
    if not chunks:
        print("--- No chunks to analyze. ---")
        return []

    print(f"--- Starting analysis for {len(chunks)} chunks... ---")
    analyzed_chunks = []
    
    for i, chunk in enumerate(chunks):
        chunk_text = chunk.get("text", "")
        chunk_id = chunk.get("chunk_id", i + 1)
        
        # Construct the full prompt for the API call
        full_prompt = f"{user_prompt}\n\n---\n\nTEXT TO ANALYZE:\n\"{chunk_text}\""
        
        try:
            print(f"  - Analyzing chunk {chunk_id}/{len(chunks)}...")
            response = model.generate_content(full_prompt)
            
            # Add the analysis to the chunk object
            chunk['analysis'] = response.text
            analyzed_chunks.append(chunk)

            # Be a good citizen and avoid hitting rate limits.
            time.sleep(1) 

        except Exception as e:
            print(f"--- ERROR: An error occurred while analyzing chunk {chunk_id}: {e} ---")
            chunk['analysis'] = f"Error during analysis: {e}"
            analyzed_chunks.append(chunk)
            continue
            
    print("--- Analysis complete. ---")
    return analyzed_chunks

def save_analysis_to_json(analysis, input_filename):
    """
    Saves the list of analyzed chunks to a new JSON file.
    """
    base_name = os.path.splitext(input_filename)[0].replace("_chunks", "")
    output_filename = f"{base_name}_analysis.json"
    
    print(f"--- Saving analysis to '{output_filename}'... ---")
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=4, ensure_ascii=False)
        print("--- Successfully saved analysis to JSON. ---")
    except Exception as e:
        print(f"--- ERROR: Could not save analysis to JSON file: {e} ---")

def main():
    """
    Main function to orchestrate the analysis pipeline.
    """
    if len(sys.argv) < 3:
        print("--- USAGE: python gemini_analyzer.py <chunks_file.json> \"<Your prompt for Gemini>\" ---")
        return

    chunks_file_path = sys.argv[1]
    user_prompt = sys.argv[2]
    
    # 1. Configure the Gemini API model
    model = configure_gemini()
    if not model:
        return

    # 2. Load the text chunks from the JSON file
    try:
        with open(chunks_file_path, 'r', encoding='utf-8') as f:
            chunks_to_analyze = json.load(f)
    except FileNotFoundError:
        print(f"--- ERROR: The file '{chunks_file_path}' was not found. ---")
        return
    except json.JSONDecodeError:
        print(f"--- ERROR: The file '{chunks_file_path}' is not a valid JSON file. ---")
        return

    # 3. Analyze the chunks with Gemini
    analysis_results = analyze_chunks_with_gemini(model, chunks_to_analyze, user_prompt)

    # 4. Save the results to a new JSON file
    if analysis_results:
        save_analysis_to_json(analysis_results, chunks_file_path)

if __name__ == '__main__':
    main()
