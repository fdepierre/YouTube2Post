"""Real transcription of a short English clip (on the GPU if it works, else the CPU)."""

import os
import unittest
import unittest.mock

from modules.transcriber import Transcriber

AUDIO = os.path.join(os.path.dirname(__file__), 'test_transcriber.mp3')


class TestTranscriber(unittest.TestCase):
    def test_transcribe_audio_content(self):
        with unittest.mock.patch('builtins.print'):
            text = Transcriber(announce=False).transcribe_audio(AUDIO).lower()
        for word in ['grow', 'weed', 'english', 'minute', 'quickly']:
            self.assertIn(word, text)


if __name__ == '__main__':
    unittest.main()
