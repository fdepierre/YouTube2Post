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


class TestEnvironment(unittest.TestCase):
    def test_detection(self):
        cases = [('win32', '10', {}, 'windows'), ('darwin', '24.0', {}, 'macos'),
                 ('linux', '6.18.58.1-microsoft-standard-WSL2', {}, 'wsl'),
                 ('linux', '6.8.0', {'WSL_DISTRO_NAME': 'Debian'}, 'wsl'),
                 ('linux', '6.8.0-generic', {}, 'linux')]
        for plat, release, env, expected in cases:
            with patch.object(cb.sys, 'platform', plat), \
                 patch.object(cb.platform, 'release', return_value=release), \
                 patch.dict(cb.os.environ, env, clear=True):
                self.assertEqual(cb.environment(), expected, (plat, release, env))


class TestWriteClipboard(unittest.TestCase):
    def _write(self, env, available):
        which = lambda exe: '/bin/' + exe if exe in available else None
        with patch.object(cb, 'environment', return_value=env), \
             patch.object(cb.shutil, 'which', side_effect=which), \
             patch.object(cb.subprocess, 'run', return_value=MagicMock(returncode=0)) as run:
            ok = cb.write_clipboard('/mnt/c/Été/a.txt')
        return ok, run

    def test_wsl_uses_windows_clipboard_in_utf16(self):
        ok, run = self._write('wsl', {'clip.exe', 'xclip'})
        self.assertTrue(ok)
        self.assertEqual(run.call_args.args[0], ['/bin/clip.exe'])
        self.assertEqual(run.call_args.kwargs['input'], '/mnt/c/Été/a.txt'.encode('utf-16le'))

    def test_linux_falls_back_to_xclip(self):
        ok, run = self._write('linux', {'xclip'})
        self.assertTrue(ok)
        self.assertEqual(run.call_args.args[0], ['/bin/xclip', '-selection', 'clipboard'])

    def test_nothing_available(self):
        ok, run = self._write('linux', set())
        self.assertFalse(ok)
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
