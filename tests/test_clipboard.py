import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import clipboard as cb


class TestFindYoutubeUrl(unittest.TestCase):
    def test_share_url(self):
        url = 'https://youtu.be/FCmLuTENOp0?si=Wr_h7INW-2EpsbfB'
        self.assertEqual(cb.find_youtube_url(url + '\r\n'), url)

    def test_watch_url_inside_text(self):
        text = 'look at "https://www.youtube.com/watch?v=abc123&t=42s" please'
        self.assertEqual(cb.find_youtube_url(text), 'https://www.youtube.com/watch?v=abc123&t=42s')

    def test_shorts_and_mobile(self):
        self.assertEqual(cb.find_youtube_url('https://m.youtube.com/shorts/xyz'),
                         'https://m.youtube.com/shorts/xyz')

    def test_no_url(self):
        for text in (None, '', 'hello', 'https://www.youtube.com/', 'https://example.com/watch?v=1'):
            self.assertIsNone(cb.find_youtube_url(text))


class TestReadClipboard(unittest.TestCase):
    def test_uses_first_available_reader(self):
        which = lambda exe: '/bin/' + exe if exe in ('pbpaste', 'xclip') else None
        result = MagicMock(returncode=0, stdout='https://youtu.be/a\n'.encode())
        with patch.object(cb.shutil, 'which', side_effect=which), \
             patch.object(cb.subprocess, 'run', return_value=result) as run:
            self.assertEqual(cb.read_clipboard(), 'https://youtu.be/a\n')
        self.assertEqual(run.call_args[0][0], ['/bin/pbpaste'])

    def test_failing_reader_falls_through(self):
        which = lambda exe: '/bin/' + exe if exe in ('powershell.exe', 'xclip') else None
        ok = MagicMock(returncode=0, stdout=b'text')
        with patch.object(cb.shutil, 'which', side_effect=which), \
             patch.object(cb.subprocess, 'run',
                          side_effect=[subprocess.TimeoutExpired('ps', 5), ok]):
            self.assertEqual(cb.read_clipboard(), 'text')

    def test_no_reader_returns_none(self):
        with patch.object(cb.shutil, 'which', return_value=None):
            self.assertIsNone(cb.read_clipboard())
            self.assertIsNone(cb.youtube_url_from_clipboard())


if __name__ == '__main__':
    unittest.main()
