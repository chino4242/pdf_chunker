# consolidate_analysis.py
#
# Description:
# This script finds all `_player_analysis.json` files within a specified directory,
# reads them, and consolidates their contents into a single JSON lookup file.
# The final output maps a cleansed player name to their corresponding AI-generated analysis.
#
# How to Use:
# 1. Place all your analysis files (e.g., "QB_player_analysis.json", "RB_player_analysis.json")
#    into a single directory. Let's call it `analysis_results`.
# 2. Add any known name discrepancies to the PLAYER_NAME_ALIASES map below.
# 3. Run the script from your terminal, providing the path to that directory.
#
# Example Command:
# python consolidate_analysis.py ./analysis_results
#

import json
import os
import sys
import re

# --- THIS IS THE FIX: Add a dictionary for manual name corrections ---
# Add any names here that are different in your analysis files compared to the official data.
# The key is the name from the analysis file, and the value is the name to use for matching.
PLAYER_NAME_ALIASES = {
    "cam ward": "cameron ward",
    "horace bru mccoy": "bru mccoy",
    # Add more aliases here as needed, e.g.:
    # "mitchell trubisky": "mitch trubisky",
}


def cleanse_name(name):
    """
    Cleanses player names for consistent matching, handling common suffixes.
    """
    if not isinstance(name, str):
        return ""
    
    cleaned_name = name.lower()
    
    suffixes_to_remove = [' iii', ' iv', ' ii', ' jr', ' sr', ' v']
    for suffix in suffixes_to_remove:
        if cleaned_name.endswith(suffix):
            cleaned_name = cleaned_name[:-len(suffix)].strip()
            break
            
    cleaned_name = re.sub(r"[^\w\s']", '', cleaned_name)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    return cleaned_name


def consolidate_analysis_files(directory_path):
    """
    Finds, reads, and consolidates all player analysis JSON files in a directory.
    """
    abs_directory_path = os.path.abspath(directory_path)
    print(f"--- Searching for analysis files in directory: '{abs_directory_path}' ---")
    
    all_player_analyses = []
    try:
        found_files = False
        for filename in os.listdir(abs_directory_path):
            if filename.endswith("_player_analysis.json"):
                found_files = True
                file_path = os.path.join(abs_directory_path, filename)
                print(f"  - Reading file: {filename}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_player_analyses.extend(data)
                    else:
                        print(f"    - Warning: File '{filename}' does not contain a valid list. Skipping.")
        
        if not found_files:
            print("  - No files ending with '_player_analysis.json' were found in this directory.")

    except FileNotFoundError:
        print(f"--- ERROR: The directory '{abs_directory_path}' was not found. ---")
        return None
    except Exception as e:
        print(f"--- ERROR: An unexpected error occurred: {e} ---")
        return None

    print(f"--- Found a total of {len(all_player_analyses)} player analyses to consolidate. ---")
    return all_player_analyses


def create_analysis_lookup(player_analyses):
    """
    Creates a dictionary mapping a cleansed player name to their analysis text.
    """
    if not player_analyses:
        return {}
        
    lookup_map = {}
    for item in player_analyses:
        player_name = item.get("player_name")
        analysis_text = item.get("analysis")
        
        if player_name and analysis_text:
            # First, cleanse the name from the analysis file
            cleaned_name = cleanse_name(player_name)
            
            # Check if this cleansed name has a known alias
            if cleaned_name in PLAYER_NAME_ALIASES:
                # If it does, use the official (aliased) name for the lookup key
                final_key_name = PLAYER_NAME_ALIASES[cleaned_name]
                print(f"  - Applying alias: '{cleaned_name}' -> '{final_key_name}'")
            else:
                # Otherwise, use the cleansed name as is
                final_key_name = cleaned_name

            lookup_map[final_key_name] = analysis_text
            
    print(f"--- Created a lookup map with {len(lookup_map)} unique player entries. ---")
    return lookup_map


def save_consolidated_analysis(lookup_map, directory_path):
    """
    Saves the consolidated analysis lookup map to a new JSON file.
    """
    output_path = os.path.join(directory_path, "consolidated_analysis.json")
    print(f"--- Saving consolidated analysis to '{output_path}'... ---")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(lookup_map, f, indent=4, ensure_ascii=False)
        print("--- Successfully saved consolidated analysis. ---")
    except Exception as e:
        print(f"--- ERROR: Could not save the consolidated file: {e} ---")


def main():
    """
    Main function to orchestrate the consolidation process.
    """
    if len(sys.argv) < 2:
        print("--- USAGE: python consolidate_analysis.py <path_to_analysis_directory> ---")
        return

    analysis_dir = sys.argv[1]

    # 1. Read all analysis files and combine them
    all_analyses = consolidate_analysis_files(analysis_dir)
    
    if all_analyses:
        # 2. Create the final lookup map
        analysis_lookup = create_analysis_lookup(all_analyses)
        
        # 3. Save the result to a new file
        if analysis_lookup:
            save_consolidated_analysis(analysis_lookup, analysis_dir)
    else:
        # Add a clear message if no data was found to process
        print("\n--- No analysis data found. Exiting without creating a new file. ---")


if __name__ == '__main__':
    main()
