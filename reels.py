import os
import time
import subprocess
import csv
import io
import google.generativeai as genai
from dotenv import load_dotenv
from reels_analyzer import VisualSegmentAnalysis, write_analysis_to_csv

load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])

REELS_FOLDER = "reels"
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

def create_reels_folder():
    if not os.path.exists(REELS_FOLDER):
        os.makedirs(REELS_FOLDER)

def analyze_video(video_path):
    """
    Analyzes a single video file by transcribing and then performing B-roll analysis.
    """
    filename = os.path.basename(video_path)
    print(f"Uploading {filename} for analysis...")
    try:
        video_file = genai.upload_file(path=video_path)

        # Step 1: Transcribe the video
        print(f"Transcribing {filename}...")
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        transcript_response = model.generate_content(["Transcribe this video.", video_file])
        transcript = transcript_response.text if transcript_response.text else ""

        if not transcript:
            print(f"Could not generate transcript for {filename}. Skipping analysis.")
            genai.delete_file(video_file.name)
            return

        print(f"Transcription complete. Analyzing B-roll for {filename}...")
        
        # Step 2: Analyze the video with the transcript
        analysis_response = model.generate_content([ANALYSIS_PROMPT, transcript, video_file])

        if analysis_response.text:
            analysis_results = []
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
            
            if analysis_results:
                csv_filename = os.path.splitext(filename)[0] + "_analysis.csv"
                csv_path = os.path.join(REELS_FOLDER, csv_filename)
                write_analysis_to_csv(analysis_results, csv_path)
        else:
            print(f"Could not generate analysis for {filename}")

        print(f"Deleting {filename} from the File API...")
        genai.delete_file(video_file.name)
        print(f"Deleted {filename}.")

    except Exception as e:
        print(f"An error occurred during analysis of {filename}: {e}")


def download_and_analyze_reels(links_file):
    create_reels_folder()

    if not os.path.exists(links_file):
        print(f"Error: {links_file} not found.")
        return

    with open(links_file, 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    for link in links:
        try:
            # Get the filename yt-dlp would use
            filename_process = subprocess.run(
                ['yt-dlp', '--get-filename', '-o', f'{REELS_FOLDER}/%(title)s.%(ext)s', link],
                capture_output=True, text=True, check=True
            )
            video_filename = os.path.basename(filename_process.stdout.strip())
            video_path = os.path.join(REELS_FOLDER, video_filename)

            if os.path.exists(video_path):
                print(f"Skipping {video_filename}, already exists.")
                continue

            print(f"Downloading {link}...")
            subprocess.run(
                ['yt-dlp', '-o', f'{REELS_FOLDER}/%(title)s.%(ext)s', link],
                check=True
            )
            print("Download complete.")
            
            analyze_video(video_path)

            print("Waiting for 10 seconds...")
            time.sleep(10)

        except subprocess.CalledProcessError as e:
            print(f"Failed to process {link}. Error: {e}")
        except Exception as e:
            print(f"An unexpected error occurred with link {link}: {e}")

if __name__ == "__main__":
    download_and_analyze_reels("reels_links.txt") 