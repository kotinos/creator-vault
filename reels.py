import os
import time

def download_reels(links_file):
    if not os.path.exists(links_file):
        print(f"Error: {links_file} not found.")
        return

    with open(links_file, 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    for link in links:
        print(f"Downloading {link}...")
        os.system(f"yt-dlp {link}")
        print("Download complete. Waiting for 10 seconds...")
        time.sleep(10)

if __name__ == "__main__":
    download_reels("reels_links.txt") 