import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import io
from reels import download_and_analyze_reels, analyze_video, VisualSegmentAnalysis
from reels_analyzer import write_analysis_to_csv

class TestDownloadAndAnalyzeWorkflow(unittest.TestCase):

    @patch('reels.os.makedirs')
    @patch('reels.write_analysis_to_csv')
    @patch('reels.analyze_video')
    @patch('reels.subprocess.run')
    @patch('reels.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="http://example.com/reel1")
    def test_full_workflow(self, mock_open_file, mock_exists, mock_subprocess, mock_analyze_video, mock_write_csv, mock_makedirs):
        # --- ARRANGE ---
        
        # 1. Simulate the results for all os.path.exists checks in order of execution
        # - reels folder: False (in create_folders)
        # - transcripts folder: False (in create_folders)
        # - master_analysis.csv: False (doesn't exist)
        # - dummy_links.txt: True (so the function doesn't exit early)
        # - the video file: False (needs to be downloaded)
        mock_exists.side_effect = [False, False, False, True, False] 

        # 2. Mock the subprocess call that gets the video filename
        mock_subprocess.return_value.stdout = "Test-Video.mp4"

        # 3. Mock the analysis result that analyze_video will return
        mock_analysis_result = [
            VisualSegmentAnalysis(
                video_filename="Test-Video.mp4",
                segment_id="1", start_time="00:00:00.000", end_time="00:00:05.000",
                shot_type="B-roll", spoken_text="Hello world",
                visual_description="A cat playing with yarn.",
                inferred_purpose="To show cuteness.",
                effectiveness_rating=5, effectiveness_justification="Very cute."
            )
        ]
        mock_analyze_video.return_value = mock_analysis_result

        # --- ACT ---
        download_and_analyze_reels("dummy_links.txt")

        # --- ASSERT ---
        
        # 1. Check if it tried to get the video filename
        mock_subprocess.assert_any_call(
            ['yt-dlp', '--get-filename', '-o', 'reels/%(title)s.%(ext)s', "http://example.com/reel1"],
            capture_output=True, text=True, check=True
        )

        # 2. Check if it tried to download the video since it didn't exist
        mock_subprocess.assert_any_call(
            ['yt-dlp', '-o', 'reels/%(title)s.%(ext)s', "http://example.com/reel1"],
            check=True
        )

        # 3. Check if it called the analysis function for the video
        mock_analyze_video.assert_called_once_with('reels/Test-Video.mp4')

        # 4. Check if it tried to write the final results to the master CSV
        # The first argument to the first call of write_analysis_to_csv
        mock_write_csv.assert_called_once()
        self.assertEqual(len(mock_write_csv.call_args[0][0]), 1) # The list of results
        self.assertEqual(mock_write_csv.call_args[0][0][0].video_filename, "Test-Video.mp4")
        self.assertEqual(mock_write_csv.call_args[0][1], "master_analysis.csv") # The path

if __name__ == '__main__':
    unittest.main() 