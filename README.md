# Creator Vault

This script helps you download Instagram Reels for analysis. The goal is to use these reels to accelerate learning by analyzing other creators' content, with the help of Gemini AI.

## How it works

1.  Add a list of Instagram Reel URLs to `reels_links.txt`.
2.  Run either the `reels.py` script for B-roll analysis or `script_reels.py` for script analysis.
3.  The script will download each reel one by one, with a 10-second delay between each download.

## B-Roll Analysis for Compelling Storytelling
**Overall Goal:** To understand the relationship between spoken script and effective B-roll, enabling the generation of impactful B-roll suggestions for various narratives.

## Script Analysis for Compelling Content Creation
**Overall Goal:** To analyze script effectiveness, tonality, emotional arcs, and storytelling patterns that make reels engaging and compelling. This module identifies what makes scripts work and provides insights for creating better content.

## Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/kotinos/creator-vault.git
    cd creator-vault
    ```

2.  Create a virtual environment and install the dependencies:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

    ```cmd
    python -m venv venv
    venv\Scripts\activate
    python reels_analyzer.py
    ```

## Usage

1.  Add the URLs of the Instagram Reels you want to download to the `reels_links.txt` file, with one URL per line.

2.  Run the desired analysis script:

    **For B-roll analysis:**
    ```bash
    python reels.py
    ```
    This generates `master_analysis.csv` with visual segment analysis.

    **For script analysis:**
    ```bash
    python script_reels.py
    ```
    This generates `master_script_analysis.csv` with comprehensive script effectiveness analysis.

The downloaded reels will be saved in the project directory.

## Script Analysis Features

The script analysis module (`script_reels.py`) provides comprehensive analysis of video scripts including:

- **Tonality Analysis:** Overall tone and voice of the script
- **Emotional Arc:** Emotional journey from beginning to end
- **Hook Effectiveness:** Analysis of opening techniques and attention-grabbing methods
- **Narrative Flow:** How ideas connect and transition logically
- **Transition Quality:** Techniques used to maintain flow between ideas
- **Call to Action:** Evaluation of CTAs and their effectiveness
- **Recurring Patterns:** Identification of storytelling devices, repetition, and structural elements
- **Line-by-Line Analysis:** Strategic purpose behind key lines and phrases
- **Cross-Video Patterns:** Elements that consistently appear across effective content
- **Improvement Suggestions:** Specific recommendations for script enhancement

### Script Analysis Output

The script analysis generates a CSV file (`master_script_analysis.csv`) and comprehensive logs in the `script_analysis_logs/` folder.

### Logging and Raw Data

Each script analysis session creates detailed logs that include:
- **Source Link**: The original Instagram reel URL
- **Full Transcript**: Complete video transcript used for analysis  
- **Raw LLM Output**: Unprocessed AI analysis response before CSV parsing
- **Parse Status**: Success/failure details for CSV generation
- **Error Details**: Comprehensive error information if parsing fails

Logs are saved as timestamped files in `script_analysis_logs/script_analysis_YYYYMMDD_HHMMSS.log` and are human-readable for easy review.

### CSV Output Fields

The CSV file contains the following fields:
- `video_filename`: Name of the analyzed video file
- `overall_message`: Core message or main takeaway
- `script_purpose`: Goal the script is trying to achieve
- `tonality`: Overall tone and voice description
- `emotional_arc`: Emotional journey mapping
- `hook_effectiveness`: Opening hook analysis
- `narrative_flow`: Logical progression evaluation
- `transition_quality`: Flow maintenance techniques
- `call_to_action`: CTA identification and evaluation
- `recurring_patterns`: Storytelling patterns and devices
- `line_by_line_analysis`: Strategic analysis of key lines
- `effectiveness_score`: Numerical rating (1-10)
- `improvement_suggestions`: Specific enhancement recommendations     
