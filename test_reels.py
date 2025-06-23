import unittest
from unittest.mock import patch, call
import os
from reels import download_reels

class TestReelsDownloader(unittest.TestCase):

    def setUp(self):
        self.links_file = "test_reels_links.txt"
        with open(self.links_file, "w") as f:
            f.write("https://www.instagram.com/reel/C1ABCDEFG\n")
            f.write("https://www.instagram.com/reel/C2HIJKLMN\n")

    def tearDown(self):
        os.remove(self.links_file)

    @patch('reels.os.system')
    @patch('reels.time.sleep')
    def test_download_reels(self, mock_sleep, mock_system):
        download_reels(self.links_file)

        expected_system_calls = [
            call("yt-dlp https://www.instagram.com/reel/C1ABCDEFG"),
            call("yt-dlp https://www.instagram.com/reel/C2HIJKLMN")
        ]
        mock_system.assert_has_calls(expected_system_calls, any_order=False)

        expected_sleep_calls = [
            call(10),
            call(10)
        ]
        mock_sleep.assert_has_calls(expected_sleep_calls)
        
        # Check that os.system and time.sleep were called for each link
        self.assertEqual(mock_system.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)

if __name__ == '__main__':
    unittest.main() 