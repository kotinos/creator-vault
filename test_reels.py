import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
from reels import transcribe_videos_in_directory

class TestVideoTranscriber(unittest.TestCase):

    @patch('reels.genai.delete_file')
    @patch('reels.genai.upload_file')
    @patch('reels.genai.GenerativeModel')
    @patch('reels.os.path.isdir')
    @patch('reels.os.listdir')
    def test_transcribe_videos_in_directory(self, mock_listdir, mock_isdir, mock_gen_model, mock_upload_file, mock_delete_file):
        # Arrange
        test_directory = "test_videos"
        mock_isdir.return_value = True
        mock_listdir.return_value = ["video1.mp4", "video2.mp4", "not_a_video.txt"]

        # Mock the Gemini API responses
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "uploaded_file_name"
        mock_upload_file.return_value = mock_uploaded_file

        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is a transcript."
        mock_model_instance.generate_content.return_value = mock_response
        mock_gen_model.return_value = mock_model_instance

        # Act
        with patch("builtins.open", mock_open()) as mock_file:
            transcribe_videos_in_directory(test_directory)

        # Assert
        self.assertEqual(mock_upload_file.call_count, 2)
        mock_upload_file.assert_any_call(path=os.path.join(test_directory, "video1.mp4"))
        mock_upload_file.assert_any_call(path=os.path.join(test_directory, "video2.mp4"))
        
        self.assertEqual(mock_gen_model.call_count, 2)
        self.assertEqual(mock_model_instance.generate_content.call_count, 2)

        self.assertEqual(mock_file.call_count, 2)
        mock_file.assert_any_call(os.path.join(test_directory, "video1.txt"), "w")
        mock_file.assert_any_call(os.path.join(test_directory, "video2.txt"), "w")
        
        handle = mock_file()
        handle.write.assert_any_call("This is a transcript.")

        self.assertEqual(mock_delete_file.call_count, 2)
        mock_delete_file.assert_any_call("uploaded_file_name")

if __name__ == '__main__':
    unittest.main() 