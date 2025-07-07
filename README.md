# Creator Vault

This script helps you download Instagram Reels for analysis. The goal is to use these reels to accelerate learning by analyzing other creators' content, with the help of Gemini AI.

## How it works

1.  Add a list of Instagram Reel URLs to `reels_links.txt`.
2.  Run the `reels.py` script.
3.  The script will download each reel one by one, with a 10-second delay between each download.

## B-Roll Analysis for Compelling Storytelling
**Overall Goal:** To understand the relationship between spoken script and effective B-roll, enabling the generation of impactful B-roll suggestions for various narratives. 

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

2.  Run the script:
    ```bash
    python reels.py
    ```

The downloaded reels will be saved in the project directory. 
