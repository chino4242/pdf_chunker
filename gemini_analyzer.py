# gemini_analyzer.py
#
# Description:
# This script intelligently extracts player profiles from a specific page range of a PDF.
# It identifies each player based on a header pattern, sends the full profile to the
# Google Gemini API for analysis, and saves the structured results to a JSON file.
#
# Dependencies:
# - PyMuPDF (fitz): pip install PyMuPDF
# - google-generativeai: pip install google-generativeai
#
# How to Use:
# 1. Update the PLAYER_HEADER_REGEX variable below to match the header format in your PDF.
# 2. Run the script from your terminal:
#    python gemini_analyzer.py "My Document.pdf" 10 25 "Your prompt for Gemini."
#
# Example Command:
# python gemini_analyzer.py "RookieGuide.pdf" 18 146 "Summarize this player's strengths, weaknesses, and provide an NFL player comparison."
#

import google.generativeai as genai
from google.api_core import exceptions
import json
import os
import sys
import time
import fitz  # PyMuPDF
import re

# --- IMPORTANT: CONFIGURE THIS PATTERN ---
# This regular expression is used to find the start of each player's profile.
# It has been updated to match the format: "RB Chez Mellusi RSP Scouting Profile"
# The part in the parentheses `()` is what gets captured as the player's name.
PLAYER_HEADER_REGEX = r"(?:QB|RB|WR|TE)\s+([A-Z][a-zA-Z\s'\.-]+?)\s+RSP Scouting Profile"


def extract_text_from_pdf_section(pdf_path, start_page, end_page):
    """Extracts text content from a specific page range of a PDF file."""
    print(f"--- Extracting text from '{pdf_path}' (pages {start_page}-{end_page})... ---")
    try:
        with fitz.open(pdf_path) as doc:
            full_text = []
            for page_num in range(start_page - 1, end_page):
                if page_num >= len(doc): break
                page = doc.load_page(page_num)
                full_text.append(page.get_text())
            print("--- Text extraction complete. ---")
            return "\n".join(full_text)
    except Exception as e:
        print(f"--- ERROR: Could not read the PDF: {e} ---")
        return None

def split_text_by_player(text, pattern):
    """
    Splits the full text into a list of dictionaries, one for each player,
    based on a regex pattern that identifies player headers.
    """
    print("--- Splitting text by player profile... ---")
    
    # Use a capturing group for the player name within the delimiter pattern
    full_pattern = re.compile(pattern)
    # Split the text. Because the pattern has a capturing group, the captured names will be in the list.
    parts = full_pattern.split(text)
    
    player_profiles = []
    # The list 'parts' will be [intro, name1, content1, name2, content2, ...]
    # We start at index 1 and step by 2 to get each name/content pair.
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            player_name = parts[i].strip()
            # Ensure there is content available for the player
            if (i + 1) < len(parts):
                player_text = parts[i+1].strip()
                player_profiles.append({
                    "player_name": player_name,
                    "text": player_text
                })
            else: # Handle the case where the last player has no content after them
                player_profiles.append({
                    "player_name": player_name,
                    "text": ""
                })

    print(f"--- Successfully identified and split {len(player_profiles)} player profiles. ---")
    if player_profiles: print(f"  - First player found: {player_profiles[0]['player_name']}")
    return player_profiles


def configure_gemini():
    """Configures the Gemini API with the key from environment variables."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("--- ERROR: GOOGLE_API_KEY environment variable not found. ---")
        return None
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("--- Gemini API configured successfully. ---")
    return model

def analyze_players_with_gemini(model, player_profiles, user_prompt):
    """Sends each player's full profile to the Gemini API and collects the analysis."""
    if not player_profiles:
        print("--- No player profiles to analyze. ---")
        return []

    print(f"--- Starting analysis for {len(player_profiles)} players... ---")
    analyzed_players = []
    request_count = 0
    
    for i, profile in enumerate(player_profiles):
        player_text = profile.get("text", "")
        player_name = profile.get("player_name", f"Player {i+1}")
        full_prompt = f"{user_prompt}\n\n---\n\nPLAYER PROFILE:\n\"{player_name}\n{player_text}\""
        
        try:
            print(f"  - Analyzing profile for {player_name} ({i+1}/{len(player_profiles)})...")
            response = model.generate_content(full_prompt)
            request_count += 1
            profile['analysis'] = response.text
            analyzed_players.append(profile)

            if request_count % 14 == 0 and i < len(player_profiles) - 1:
                print("\n--- Pausing for 65 seconds to respect API rate limits... ---\n")
                time.sleep(65)

        except exceptions.ResourceExhausted:
            print(f"--- RATE LIMIT HIT on {player_name}. Waiting 65 seconds... ---")
            time.sleep(65)
            # Retry the same profile once after waiting
            try:
                response = model.generate_content(full_prompt)
                profile['analysis'] = response.text
                analyzed_players.append(profile)
            except Exception as retry_e:
                profile['analysis'] = f"Error after retry: {retry_e}"
                analyzed_players.append(profile)
        except Exception as e:
            print(f"--- ERROR analyzing {player_name}: {e} ---")
            profile['analysis'] = f"Error during analysis: {e}"
            analyzed_players.append(profile)
            
    print("--- Analysis complete. ---")
    return analyzed_players

def save_analysis_to_json(analysis, input_filename):
    """Saves the list of analyzed players to a new JSON file."""
    base_name = os.path.splitext(input_filename)[0]
    output_filename = f"{base_name}_player_analysis.json"
    
    print(f"--- Saving analysis to '{output_filename}'... ---")
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=4, ensure_ascii=False)
        print("--- Successfully saved analysis to JSON. ---")
    except Exception as e:
        print(f"--- ERROR: Could not save analysis to JSON file: {e} ---")

def main():
    """Main function to orchestrate the PDF processing pipeline."""
    if len(sys.argv) < 5:
        print("--- USAGE: python gemini_analyzer.py <pdf_file.pdf> <start_page> <end_page> \"<Your prompt>\" ---")
        return

    pdf_path, user_prompt = sys.argv[1], sys.argv[4]
    try:
        start_page, end_page = int(sys.argv[2]), int(sys.argv[3])
    except ValueError:
        print("--- ERROR: Start and end pages must be integer numbers. ---")
        return
    
    section_text = extract_text_from_pdf_section(pdf_path, start_page, end_page)
    if not section_text: return

    player_profiles = split_text_by_player(section_text, PLAYER_HEADER_REGEX)
    if not player_profiles: 
        print("--- Could not find any player profiles. Please check your PLAYER_HEADER_REGEX pattern. ---")
        return

    model = configure_gemini()
    if not model: return

    analysis_results = analyze_players_with_gemini(model, player_profiles, user_prompt)

    if analysis_results:
        save_analysis_to_json(analysis_results, pdf_path)

if __name__ == '__main__':
    main()
