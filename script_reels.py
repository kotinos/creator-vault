import os
import time
import subprocess
import csv
import io
import logging
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from collections import deque
from script_analyzer import ScriptAnalysis, write_script_analysis_to_csv

load_dotenv()

# Configure the Gemini client
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")
genai.configure(api_key=api_key)

REELS_FOLDER = "reels"
TRANSCRIPTS_FOLDER = "transcripts"
LOGS_FOLDER = "script_analysis_logs"

def setup_logging():
    """Set up comprehensive logging for script analysis."""
    if not os.path.exists(LOGS_FOLDER):
        os.makedirs(LOGS_FOLDER)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"script_analysis_{timestamp}.log"
    log_path = os.path.join(LOGS_FOLDER, log_filename)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"=== SCRIPT ANALYSIS SESSION STARTED ===")
    logger.info(f"Log file: {log_path}")
    return logger

def log_analysis_details(logger, link, video_filename, transcript, raw_analysis_response):
    """Log comprehensive details for each video analysis."""
    logger.info("=" * 80)
    logger.info(f"ANALYZING VIDEO: {video_filename}")
    logger.info(f"SOURCE LINK: {link}")
    logger.info("=" * 80)
    
    logger.info("TRANSCRIPT:")
    logger.info("-" * 40)
    logger.info(transcript)
    logger.info("-" * 40)
    
    logger.info("RAW LLM ANALYSIS OUTPUT:")
    logger.info("-" * 40)
    logger.info(raw_analysis_response)
    logger.info("-" * 40)
    
    logger.info(f"END ANALYSIS FOR: {video_filename}")
    logger.info("=" * 80)
SCRIPT_ANALYSIS_PROMPT = """
**URGENT: STRICTLY ADHERE TO CSV FORMATTING. EACH ROW MUST HAVE EXACTLY 13 FIELDS.**

Analyze the provided video transcript for script effectiveness and compelling storytelling elements. Your goal is to understand what makes this script work and identify patterns that create engaging content.

Generate a single line of CSV output with the following fields, in this exact order, separated by commas:

**Fields (13 total, STRICT ORDER):**
1. **Video_Filename:** The filename of the video being analyzed.
2. **Overall_Message:** The core message or main takeaway of the script. What is the creator trying to communicate? **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
3. **Script_Purpose:** Why was this script created? What goal is it trying to achieve (educate, entertain, inspire, sell, etc.)? **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
4. **Tonality:** Describe the overall tone and voice of the script (conversational, authoritative, humorous, dramatic, etc.). **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
5. **Emotional_Arc:** Map the emotional journey of the script from beginning to end. How does it make the viewer feel and how do those emotions change? **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
6. **Hook_Effectiveness:** Analyze the opening hook. What technique is used and how effective is it at grabbing attention? **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
7. **Narrative_Flow:** Examine how ideas connect and transition. Is the logical progression clear and compelling? **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
8. **Transition_Quality:** Analyze how the script moves from one idea to the next. What techniques are used to maintain flow? **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
9. **Call_to_Action:** Identify and evaluate any calls to action. How clear and compelling are they? **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
10. **Recurring_Patterns:** Identify patterns, techniques, or structures that appear throughout the script (repetition, questions, storytelling devices, etc.). **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
11. **Line_by_Line_Analysis:** Provide detailed analysis of key lines explaining WHY each important line was said and its strategic purpose. **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**
12. **Effectiveness_Score:** A numerical rating from 1 to 10 for overall script effectiveness.
13. **Improvement_Suggestions:** Specific suggestions for how this script could be improved or what elements could be strengthened. **CRITICAL: If this contains commas, double quotes, or newlines, ENCLOSE THE ENTIRE FIELD IN STANDARD STRAIGHT DOUBLE QUOTES (`"`).**

**STRICT FORMATTING RULES:**
* **YOU MUST USE STANDARD STRAIGHT DOUBLE QUOTES (`"`) FOR QUOTING. NO CURLY QUOTES.**
* When a quoted field *itself* contains a literal double quote (`"`), **you MUST escape it by doubling it (`""`).**
* DO NOT include any header row in your output. Just provide the data row.
* Provide the output directly as a CSV line.

**Example of a CORRECTLY QUOTED field (note the straight quotes and doubled internal quote):**
`"The creator said, ""This changed my life!"" which creates emotional resonance."`

**Focus Areas for Analysis:**
- What makes the opening compelling?
- How does the script maintain engagement throughout?
- What emotional triggers are used?
- How does the structure support the message?
- What storytelling techniques create connection?
- How does word choice impact effectiveness?
- What patterns could be replicated in other scripts?
"""

def create_folders():
    """Creates the reels, transcripts, and logs folders if they don't exist."""
    if not os.path.exists(REELS_FOLDER):
        os.makedirs(REELS_FOLDER)
    if not os.path.exists(TRANSCRIPTS_FOLDER):
        os.makedirs(TRANSCRIPTS_FOLDER)
    if not os.path.exists(LOGS_FOLDER):
        os.makedirs(LOGS_FOLDER)

def analyze_script(video_path, link=None, logger=None):
    """
    Analyzes a single video file for script effectiveness and returns analysis results.
    """
    filename = os.path.basename(video_path)
    print(f"Uploading {filename} for script analysis...")
    if logger:
        logger.info(f"Starting script analysis for: {filename}")
        logger.info(f"Video path: {video_path}")
        if link:
            logger.info(f"Source link: {link}")
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

        print(f"Analyzing script for {filename}...")
        if logger:
            logger.info(f"Sending transcript to AI for analysis: {filename}")
        
        analysis_response = model.generate_content([SCRIPT_ANALYSIS_PROMPT, transcript])

        print("\n--- Raw Script Analysis CSV from API ---")
        print(analysis_response.text)
        print("--- End of Raw Script Analysis CSV ---\n")
        
        if logger:
            log_analysis_details(logger, link, filename, transcript, analysis_response.text)

        # Normalize smart/curly quotes to straight quotes
        normalized_text = analysis_response.text.replace('"', '"').replace('"', '"')

        def fix_script_csv_line(line):
            """Parse CSV line with proper quote handling for script analysis."""
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
            
            if len(parts) != 13:
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
            
            return parts if len(parts) == 13 else None

        analysis_results = []
        for line in normalized_text.strip().split('\n'):
            if not line.strip():  # Skip empty lines
                continue
            # Skip header row if present
            if any(header in line.lower() for header in ('video_filename', 'overall_message')):
                continue
                
            try:
                fields = fix_script_csv_line(line)
                
                if fields and len(fields) == 13:
                    try:
                        analysis = ScriptAnalysis(
                            video_filename=fields[0],
                            overall_message=fields[1],
                            script_purpose=fields[2],
                            tonality=fields[3],
                            emotional_arc=fields[4],
                            hook_effectiveness=fields[5],
                            narrative_flow=fields[6],
                            transition_quality=fields[7],
                            call_to_action=fields[8],
                            recurring_patterns=fields[9],
                            line_by_line_analysis=fields[10],
                            effectiveness_score=str(fields[11]),
                            improvement_suggestions=fields[12]
                        )
                        analysis_results.append(analysis)
                        if logger:
                            logger.info(f"Successfully parsed analysis for {filename}")
                    except Exception as e:
                        print(f"[PARSE ERROR] Could not create ScriptAnalysis from fields: {fields}")
                        print(f"[PARSE ERROR] Exception details: {str(e)}")
                        if logger:
                            logger.error(f"Failed to create ScriptAnalysis for {filename}: {str(e)}")
                            logger.error(f"Raw fields: {fields}")
                        parse_error = True
                else:
                    print(f"[PARSE ERROR] Could not parse line (expected 13 fields, got {len(fields) if fields else 0}): {line}")
                    if logger:
                        logger.error(f"Parse error for {filename} - expected 13 fields, got {len(fields) if fields else 0}")
                        logger.error(f"Problematic line: {line}")
                    parse_error = True
            except Exception as e:
                print(f"[PARSE ERROR] Failed to process line: {line}")
                print(f"[PARSE ERROR] Exception details: {str(e)}")
                if logger:
                    logger.error(f"Exception processing line for {filename}: {str(e)}")
                    logger.error(f"Line content: {line}")
                parse_error = True
        
        print(f"Deleting {filename} from the File API...")
        genai.delete_file(video_file.name)
        print(f"Deleted {filename}.")
        if logger:
            logger.info(f"Completed analysis for {filename}. Results: {len(analysis_results)} parsed successfully, Parse errors: {parse_error}")
        return analysis_results, parse_error

    except Exception as e:
        print(f"An error occurred during script analysis of {filename}: {e}")
        if logger:
            logger.error(f"Critical error during analysis of {filename}: {str(e)}")
        return [], True

def download_and_analyze_script_reels(links_file):
    create_folders()
    logger = setup_logging()

    master_csv_path = "master_script_analysis.csv"
    all_analysis_results = []
    analyzed_videos = set()
    failed_links = []  # Track failed URLs
    
    logger.info(f"Starting script analysis session with links file: {links_file}")
    logger.info(f"Master CSV output: {master_csv_path}")

    # Load existing analysis results if the master file exists
    if os.path.exists(master_csv_path):
        with open(master_csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    all_analysis_results.append(ScriptAnalysis(**row))
                    analyzed_videos.add(row['video_filename'])
                except (TypeError, KeyError, ValueError) as e:
                    print(f"Skipping malformed row in master script CSV: {row}. Error: {e}")
        print(f"Loaded {len(all_analysis_results)} existing script analysis results.")

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
                print(f"Skipping {video_filename}, already analyzed in master script CSV.")
                logger.info(f"Skipping already analyzed video: {video_filename}")
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
                logger.info(f"Downloading video from: {link}")
                subprocess.run(
                    ['yt-dlp', '-o', output_template, link],
                    check=True, timeout=300 # 5-minute timeout for download
                )
                print("Download complete.")
                logger.info(f"Download completed: {video_filename}")
            else:
                print(f"Video {video_filename} already exists, proceeding to script analysis.")
                logger.info(f"Using existing video file: {video_filename}")
            
            new_results, parse_error = analyze_script(video_path, link, logger)
            if new_results:
                print("\n--- New Script Analysis Results ---")
                for result in new_results:
                    print(result)
                print("--- End of New Script Analysis ---\n")
                
                if parse_error:
                    print(f"WARNING: Skipping CSV write for {video_filename} due to parse errors")
                    failed_links.append(link)
                else:
                    all_analysis_results.extend(new_results)
                    print(f"DEBUG: About to append {len(new_results)} script results for {video_filename} to CSV")
                    write_script_analysis_to_csv(new_results, master_csv_path)
            elif parse_error:
                failed_links.append(link)

        except subprocess.CalledProcessError as e:
            print(f"Failed to process {link}. Error: {e}")
            logger.error(f"Subprocess error for {link}: {str(e)}")
            failed_links.append(link)
        except (subprocess.TimeoutExpired, TimeoutError) as e:
            print(f"Timeout occurred while processing {link}: {e}. Skipping.")
            logger.error(f"Timeout error for {link}: {str(e)}")
            failed_links.append(link)
        except Exception as e:
            print(f"An unexpected error occurred with link {link}: {e}")
            logger.error(f"Unexpected error for {link}: {str(e)}")
            failed_links.append(link)

    # After processing all links, print failed URLs
    if failed_links:
        print("\nThe following URLs failed during script analysis:")
        logger.info("FAILED LINKS SUMMARY:")
        for url in failed_links:
            print(url)
            logger.info(f"FAILED: {url}")
    else:
        print("\nAll videos processed successfully for script analysis!")
        logger.info("All videos processed successfully!")
    
    logger.info(f"=== SCRIPT ANALYSIS SESSION COMPLETED ===")
    logger.info(f"Total videos processed: {len(all_analysis_results)}")
    logger.info(f"Failed links: {len(failed_links)}")
    logger.info(f"Master CSV: {master_csv_path}")
    logger.info(f"Logs saved in: {LOGS_FOLDER}")

if __name__ == "__main__":
    download_and_analyze_script_reels("reels_links.txt")
