import os
import time
import subprocess
import csv
import io
import google.generativeai as genai
from dotenv import load_dotenv
from collections import deque
from reels_analyzer import VisualSegmentAnalysis, write_analysis_to_csv

load_dotenv()

# Configure the Gemini client
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=api_key)

REELS_FOLDER = "reels"
TRANSCRIPTS_FOLDER = "transcripts"
ANALYSIS_PROMPT = """
**URGENT: STRICTLY ADHERE TO CSV FORMATTING. EACH ROW MUST HAVE EXACTLY 9 FIELDS.**

Analyze the provided video clip and its accompanying transcript. Your goal is to identify and describe the visual footage shown during specific lines or phrases in the dialogue.

For each distinct visual segment (whether talking head or B-roll), generate a single line of output in CSV format. The CSV line **MUST** contain the following fields, in this exact order, separated by commas:

**Fields (9 total, STRICT ORDER):**
1.  **Video_Segment_ID:** A unique identifier for the current video segment (e.g., "{video_segment_id}").
2.  **Visual_Start_Timestamp:** The start time (in HH:MM:SS.ms format) within the video clip where this visual segment begins.
3.  **Visual_End_Timestamp:** The end time (in HH:MM:SS.ms format) within the video clip where this visual segment ends.
4.  **Shot_Type:** Categorize the shot as either "Talking Head" or "B-roll".
5.  **Spoken_Line_Phrase:** The exact text from the transcript that is being spoken when this visual segment is shown. **CRITICAL: If this text contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
6.  **Visual_Description:** A detailed visual description of *what* is shown. Be specific about subjects, actions, colors, framing, and any discernible mood or tone. For B-roll, be detailed about the content. For Talking Head, describe the framing, background, and presenter's demeanor if relevant. **CRITICAL: If this description contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
7.  **Inferred_Purpose_Connection:** Explain *why* this particular visual was chosen. What is its intended impact? How does it enhance or illustrate the spoken word? For Talking Head, this might be about direct address, personal connection, etc. For B-roll, how it illustrates or supports the narrative. **CRITICAL: If this explanation contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
8.  **Effectiveness_Rating:** A numerical rating from 1 to 5.
9.  **Effectiveness_Justification:** A brief justification for the effectiveness rating. **CRITICAL: If this justification contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**

**STRICT FORMATTING RULES:**
* Each visual segment MUST correspond to a single line in the output.
* **YOU MUST USE STANDARD STRAIGHT DOUBLE QUOTES (`"`) FOR QUOTING. NO CURLY QUOTES.**
* When a quoted field *itself* contains a literal double quote (`"`), **you MUST escape it by doubling it (`""`).**
* DO NOT include any header row in your output. Just provide the data rows.
* Strive for continuous coverage of the video segment; if there are gaps, it's fine, but identify all distinct visual changes.
* Provide the output directly as CSV lines, one per analysis result.

**Example of a CORRECTLY QUOTED field (note the straight quotes and doubled internal quote):**
`"The woman said, ""Hello!"" and smiled warmly."`
"""

def create_folders():
    """Creates the reels and transcripts folders if they don't exist."""
    if not os.path.exists(REELS_FOLDER):
        os.makedirs(REELS_FOLDER)
    if not os.path.exists(TRANSCRIPTS_FOLDER):
        os.makedirs(TRANSCRIPTS_FOLDER)

def analyze_video(video_path, link=None):
    """
    Analyzes a single video file and returns a list of analysis results and a parse error flag.
    """
    filename = os.path.basename(video_path)
    print(f"Uploading {filename} for analysis...")
    parse_error = False
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        video_file = genai.upload_file(path=video_path)

        # Wait for the file to be processed, with a timeout.
        print("Processing video...")
        processing_start_time = time.time()
        while video_file.state.name == "PROCESSING":
            if time.time() - processing_start_time > 300: # 5-minute timeout
                raise TimeoutError("Video processing timed out after 5 minutes.")
            time.sleep(10)
            video_file = genai.get_file(video_file.name)
        
        if video_file.state.name == "FAILED":
            raise ValueError(f"Video processing failed: {video_file.state.name}")

        print("Video processed successfully.")
        
        # Step 1: Get or generate the transcript
        transcript_filename = os.path.splitext(filename)[0] + "_transcript.txt"
        transcript_path = os.path.join(TRANSCRIPTS_FOLDER, transcript_filename)
        transcript = ""

        if os.path.exists(transcript_path):
            print(f"Loading existing transcript for {filename}...")
            with open(transcript_path, "r", encoding='utf-8') as f:
                transcript = f.read()
        else:
            print(f"Transcribing {filename}...")
            transcript_response = model.generate_content(["Transcribe this video.", video_file])
            transcript = transcript_response.text if transcript_response.text else ""

            if transcript:
                # Save the full transcript
                with open(transcript_path, "w", encoding='utf-8') as f:
                    f.write(transcript)
                print(f"Full transcript saved to {transcript_path}")

        if not transcript:
            print(f"Could not generate or load transcript for {filename}. Skipping analysis.")
            genai.delete_file(video_file.name)
            return [], False

        print(f"Analyzing B-roll for {filename}...")
        
        # Step 2: Analyze the video with the transcript
        analysis_response = model.generate_content([ANALYSIS_PROMPT, transcript, video_file])

        print("\n--- Raw Analysis CSV from API ---")
        print(analysis_response.text)
        print("--- End of Raw Analysis CSV ---\n")

        # Normalize smart/curly quotes to straight quotes
        normalized_text = analysis_response.text.replace('"', '"').replace('"', '"')

        def extract_fields_pattern_matching(line):
            """Fallback method using pattern matching to extract fields."""
            # Expected pattern: id, start, end, type, text, desc, purpose, rating, justification
            fields = []
            
            # First extract the easy fields (first 4 and rating)
            parts = line.split(',')
            if len(parts) < 4:
                return None
                
            # Extract first 4 fields
            fields.extend([p.strip() for p in parts[:4]])
            
            # Find the effectiveness rating (should be a single digit 1-5)
            rating_idx = None
            for i, part in enumerate(parts[4:], 4):
                if part.strip().isdigit() and 1 <= int(part.strip()) <= 5:
                    rating_idx = i
                    break
                    
            if rating_idx is None:
                return None
                
            # Extract the spoken text (everything between shot type and next quote)
            spoken_text = ','.join(parts[4:rating_idx]).strip()
            if spoken_text.startswith('"'):
                spoken_text = spoken_text[1:]
            if spoken_text.endswith('"'):
                spoken_text = spoken_text[:-1]
            fields.append(spoken_text)
            
            # Extract visual description (between spoken text and purpose)
            desc_start = rating_idx
            for i in range(rating_idx, len(parts)):
                if '"purpose"' in parts[i].lower() or '"serves"' in parts[i].lower():
                    desc_start = i
                    break
            visual_desc = ','.join(parts[4:desc_start]).strip()
            fields.append(visual_desc)
            
            # Extract purpose (between desc and rating)
            purpose = ','.join(parts[desc_start:rating_idx]).strip()
            fields.append(purpose)
            
            # Add rating
            fields.append(parts[rating_idx].strip())
            
            # Extract justification (everything after rating)
            justification = ','.join(parts[rating_idx+1:]).strip()
            if justification.startswith('"'):
                justification = justification[1:]
            if justification.endswith('"'):
                justification = justification[:-1]
            fields.append(justification)
            
            return fields if len(fields) == 9 else None

        def fix_csv_line(line):
            """First attempt with quote-based parsing."""
            parts = []
            current_part = []
            in_quotes = False
            chars = list(line)
            
            i = 0
            while i < len(chars):
                char = chars[i]
                if char == '"':
                    if i + 1 < len(chars) and chars[i + 1] == '"':  # Handle escaped quotes
                        current_part.append('""')
                        i += 2
                        continue
                    in_quotes = not in_quotes
                    current_part.append(char)
                elif char == ',' and not in_quotes:
                    parts.append(''.join(current_part))
                    current_part = []
                else:
                    current_part.append(char)
                i += 1
            
            if current_part:
                parts.append(''.join(current_part))
            
            # If we don't have exactly 9 fields, try to fix common issues
            if len(parts) != 9:
                # Combine adjacent unquoted fields that were incorrectly split
                fixed_parts = []
                i = 0
                while i < len(parts):
                    part = parts[i].strip()
                    # If this part starts with a quote but doesn't end with one,
                    # keep combining with next parts until we find the closing quote
                    if part.startswith('"') and not part.endswith('"'):
                        combined = part
                        j = i + 1
                        while j < len(parts):
                            combined += "," + parts[j]
                            if parts[j].strip().endswith('"'):
                                break
                            j += 1
                        fixed_parts.append(combined)
                        i = j + 1
                    else:
                        fixed_parts.append(part)
                        i += 1
                parts = fixed_parts
            
            return parts if len(parts) == 9 else None

        analysis_results = []
        for line in normalized_text.strip().split('\n'):
            if not line.strip():  # Skip empty lines
                continue
            # Skip header row if present
            if any(header in line.lower() for header in ('segment_id', 'video_segment_id')):
                continue
                
            try:
                # First try quote-based parsing
                fields = fix_csv_line(line)
                
                # If that fails, try pattern matching
                if fields is None:
                    print("[DEBUG] Quote-based parsing failed, trying pattern matching...")
                    fields = extract_fields_pattern_matching(line)
                
                if fields and len(fields) == 9:
                    try:
                        # Map the CSV fields to VisualSegmentAnalysis attributes
                        analysis = VisualSegmentAnalysis(
                            video_filename=filename,  # Add the filename explicitly
                            segment_id=str(fields[0]),  # Ensure segment_id is string
                            start_time=fields[1],
                            end_time=fields[2],
                            shot_type=fields[3],
                            spoken_text=fields[4],
                            visual_description=fields[5],
                            inferred_purpose=fields[6],
                            effectiveness_rating=str(fields[7]),  # Keep as string
                            effectiveness_justification=fields[8]
                        )
                        analysis_results.append(analysis)
                    except Exception as e:
                        print(f"[PARSE ERROR] Could not create VisualSegmentAnalysis from fields: {fields}")
                        print(f"[PARSE ERROR] Exception details: {str(e)}")
                        parse_error = True
                else:
                    print(f"[PARSE ERROR] Could not parse line using either method: {line}")
                    parse_error = True
            except Exception as e:
                print(f"[PARSE ERROR] Failed to process line: {line}")
                print(f"[PARSE ERROR] Exception details: {str(e)}")
                parse_error = True
        print(f"Deleting {filename} from the File API...")
        genai.delete_file(video_file.name)
        print(f"Deleted {filename}.")
        return analysis_results, parse_error

    except Exception as e:
        print(f"An error occurred during analysis of {filename}: {e}")
        return [], True


def download_and_analyze_reels(links_file):
    create_folders()

    master_csv_path = "master_analysis.csv"
    all_analysis_results = []
    analyzed_videos = set()
    failed_links = []  # Track failed URLs

    # Load existing analysis results if the master file exists
    if os.path.exists(master_csv_path):
        with open(master_csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Recreate the VisualSegmentAnalysis object from the row
                try:
                    all_analysis_results.append(VisualSegmentAnalysis(**row))
                    analyzed_videos.add(row['video_filename'])
                except (TypeError, KeyError, ValueError) as e:
                    print(f"Skipping malformed row in master CSV: {row}. Error: {e}")
        print(f"Loaded {len(all_analysis_results)} existing analysis results.")

    if not os.path.exists(links_file):
        print(f"Error: {links_file} not found.")
        return

    with open(links_file, 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    # Rate limiting parameters
    requests_per_minute = 10
    time_window = 60  # seconds
    request_timestamps = deque()

    for link in links:
        try:
            # Use yt-dlp's default naming convention: Title [ID].ext
            output_template = f'{REELS_FOLDER}/%(title)s [%(id)s].%(ext)s'
            
            # Get the filename yt-dlp would use
            filename_process = subprocess.run(
                ['yt-dlp', '--get-filename', '-o', output_template, link],
                capture_output=True, text=True, check=True, timeout=60 # 60-second timeout
            )
            video_filename = os.path.basename(filename_process.stdout.strip())
            
            if video_filename in analyzed_videos:
                print(f"Skipping {video_filename}, already analyzed in master CSV.")
                continue

            # Enforce rate limit before processing the video
            current_time = time.time()
            while len(request_timestamps) >= requests_per_minute:
                time_since_oldest_request = current_time - request_timestamps[0]
                if time_since_oldest_request > time_window:
                    request_timestamps.popleft()
                else:
                    wait_time = time_window - time_since_oldest_request
                    print(f"Rate limit reached. Waiting for {wait_time:.2f} seconds...")
                    time.sleep(wait_time)
                    current_time = time.time()  # Update current time after waiting
            
            request_timestamps.append(time.time())

            video_path = os.path.join(REELS_FOLDER, video_filename)

            if not os.path.exists(video_path):
                print(f"Downloading {link}...")
                subprocess.run(
                    ['yt-dlp', '-o', output_template, link],
                    check=True, timeout=300 # 5-minute timeout for download
                )
                print("Download complete.")
            else:
                print(f"Video {video_filename} already exists, proceeding to analysis.")
            
            new_results, parse_error = analyze_video(video_path, link)
            if new_results:
                print("\n--- New Analysis Results ---")
                for result in new_results:
                    print(result)
                print("--- End of New Analysis ---\n")
                
                if parse_error:
                    print(f"WARNING: Skipping CSV write for {video_filename} due to parse errors")
                    failed_links.append(link)
                else:
                    all_analysis_results.extend(new_results)
                    print(f"DEBUG: About to append {len(new_results)} results for {video_filename} to CSV")
                    write_analysis_to_csv(new_results, master_csv_path)
            elif parse_error:
                failed_links.append(link)

        except subprocess.CalledProcessError as e:
            print(f"Failed to process {link}. Error: {e}")
            failed_links.append(link)
        except (subprocess.TimeoutExpired, TimeoutError) as e:
            print(f"Timeout occurred while processing {link}: {e}. Skipping.")
            failed_links.append(link)
        except Exception as e:
            print(f"An unexpected error occurred with link {link}: {e}")
            failed_links.append(link)

    # After processing all links, print failed URLs
    if failed_links:
        print("\nThe following URLs failed during analysis:")
        for url in failed_links:
            print(url)
    else:
        print("\nAll videos processed successfully!")

if __name__ == "__main__":
    download_and_analyze_reels("reels_links.txt")







