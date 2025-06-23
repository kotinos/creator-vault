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

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

REELS_FOLDER = "reels"
TRANSCRIPTS_FOLDER = "transcripts"
ANALYSIS_PROMPT = """
Analyze the provided video clip and its accompanying transcript. Your goal is to identify and describe the visual footage shown during specific lines or phrases in the dialogue.

For each distinct visual segment (whether talking head or B-roll), generate a single line of output in CSV format. The CSV line should contain the following fields, in this exact order, separated by commas:

**Fields:**
1.  **Video_Segment_ID:** A unique identifier for the current video segment (e.g., "{video_segment_id}").
2.  **Visual_Start_Timestamp:** The start time (in HH:MM:SS.ms format) within the video clip where this visual segment begins.
3.  **Visual_End_Timestamp:** The end time (in HH:MM:SS.ms format) within the video clip where this visual segment ends.
4.  **Shot_Type:** Categorize the shot as either "Talking Head" or "B-roll".
5.  **Spoken_Line_Phrase:** The exact text from the transcript that is being spoken when this visual segment is shown. *If the text contains commas, enclose the entire field in double quotes.*
6.  **Visual_Description:** A detailed visual description of *what* is shown. Be specific about subjects, actions, colors, framing, and any discernible mood or tone. For B-roll, be detailed about the content. For Talking Head, describe the framing, background, and presenter's demeanor if relevant. *If the description contains commas, enclose the entire field in double quotes.*
7.  **Inferred_Purpose_Connection:** Explain *why* this particular visual was chosen. What is its intended impact? How does it enhance or illustrate the spoken word? For Talking Head, this might be about direct address, personal connection, etc. For B-roll, how it illustrates or supports the narrative. *If the explanation contains commas, enclose the entire field in double quotes.*
8.  **Effectiveness_Rating:** A numerical rating from 1 to 5 (1 = very ineffective, 5 = highly effective).
9.  **Effectiveness_Justification:** A brief justification for the effectiveness rating. *If the justification contains commas, enclose the entire field in double quotes.*

**Important Notes:**
* Ensure each visual segment (whether Talking Head or B-roll) corresponds to a single line in the output.
* If a field naturally contains commas, you **must** enclose that entire field in double quotes (`"`).
* Do not include a header row in your output. Just provide the data rows.
* Strive for continuous coverage of the video segment; if there are gaps, it's fine, but identify all distinct visual changes.
* Provide the output directly as CSV lines, one per analysis result.
"""

def create_folders():
    """Creates the reels and transcripts folders if they don't exist."""
    if not os.path.exists(REELS_FOLDER):
        os.makedirs(REELS_FOLDER)
    if not os.path.exists(TRANSCRIPTS_FOLDER):
        os.makedirs(TRANSCRIPTS_FOLDER)

def analyze_video(video_path):
    """
    Analyzes a single video file and returns a list of analysis results.
    """
    filename = os.path.basename(video_path)
    print(f"Uploading {filename} for analysis...")
    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        video_file = genai.upload_file(path=video_path)

        # Wait for the file to be processed.
        print("Processing video...")
        while video_file.state.name == "PROCESSING":
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
            return []

        print(f"Analyzing B-roll for {filename}...")
        
        # Step 2: Analyze the video with the transcript
        analysis_response = model.generate_content([ANALYSIS_PROMPT, transcript, video_file])

        analysis_results = []
        if analysis_response.text:
            # Use io.StringIO to treat the string response as a file
            csv_file = io.StringIO(analysis_response.text)
            csv_reader = csv.reader(csv_file)
            
            for row in csv_reader:
                if len(row) == 9: # Ensure the row has the correct number of columns
                    analysis = VisualSegmentAnalysis(
                        video_filename=filename,
                        segment_id=row[0],
                        start_time=row[1],
                        end_time=row[2],
                        shot_type=row[3],
                        spoken_text=row[4],
                        visual_description=row[5],
                        inferred_purpose=row[6],
                        effectiveness_rating=int(row[7]),
                        effectiveness_justification=row[8]
                    )
                    analysis_results.append(analysis)
            
        print(f"Deleting {filename} from the File API...")
        genai.delete_file(video_file.name)
        print(f"Deleted {filename}.")
        return analysis_results

    except Exception as e:
        print(f"An error occurred during analysis of {filename}: {e}")
        return []


def download_and_analyze_reels(links_file):
    create_folders()

    master_csv_path = "master_analysis.csv"
    all_analysis_results = []
    analyzed_videos = set()

    # Load existing analysis results if the master file exists
    if os.path.exists(master_csv_path):
        with open(master_csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Recreate the VisualSegmentAnalysis object from the row
                try:
                    all_analysis_results.append(VisualSegmentAnalysis(**row))
                    analyzed_videos.add(row['video_filename'])
                except (TypeError, KeyError) as e:
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
            # Get the filename yt-dlp would use
            filename_process = subprocess.run(
                ['yt-dlp', '--get-filename', '-o', f'{REELS_FOLDER}/%(title)s.%(ext)s', link],
                capture_output=True, text=True, check=True
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
                    ['yt-dlp', '-o', f'{REELS_FOLDER}/%(title)s.%(ext)s', link],
                    check=True
                )
                print("Download complete.")
            else:
                print(f"Video {video_filename} already exists, proceeding to analysis.")
            
            new_results = analyze_video(video_path)
            if new_results:
                all_analysis_results.extend(new_results)
                # Write the master CSV after each successful analysis to save progress
                write_analysis_to_csv(all_analysis_results, master_csv_path)

        except subprocess.CalledProcessError as e:
            print(f"Failed to process {link}. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred with link {link}: {e}")

if __name__ == "__main__":
    download_and_analyze_reels("reels_links.txt")







