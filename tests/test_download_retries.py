import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import youtube_downloader as yd

DownloadError = yd.yt_dlp.utils.DownloadError
FORBIDDEN = DownloadError('ERROR: unable to download video data: HTTP Error 403: Forbidden')
NO_FORMAT = DownloadError('ERROR: [youtube] abc: Requested format is not available. Use --list-formats ...')
UNAVAILABLE = DownloadError('ERROR: [youtube] abc: Video unavailable. This video is not available')


class TestDownloadRetries(unittest.TestCase):
    def run_download(self, outcomes):
        """outcomes: one per YoutubeDL attempt, an exception or 'ok'. Returns the clients tried."""
        tried = []
        tmp = tempfile.mkdtemp()
        audio = os.path.join(tmp, 'a.webm')
        for name in ('a.webm', 'a.info.json'):
            open(os.path.join(tmp, name), 'w').close()

        def make_ydl(opts):
            tried.append((opts.get('extractor_args', {}).get('youtube', {})
                          .get('player_client') or ['default'])[0])
            outcome = outcomes[len(tried) - 1]
            ydl = MagicMock()
            ydl.__enter__.return_value = ydl
            if outcome == 'ok':
                ydl.extract_info.return_value = {'requested_downloads': [{'filepath': audio}]}
            else:
                ydl.extract_info.side_effect = outcome
            return ydl

        with patch.object(yd.shutil, 'which', side_effect=lambda exe: '/bin/' + exe
                          if exe in ('ffmpeg', 'node') else None), \
             patch.object(yd.yt_dlp, 'YoutubeDL', side_effect=make_ydl), \
             patch('builtins.print'), \
             patch.dict(os.environ, {'NO_COLOR': '1'}):
            downloader = yd.YouTubeDownloader(tmp_directory=tmp, verbose=True)
            try:
                result = downloader.download_audio('https://youtu.be/abc')
            except Exception as e:
                result = e
        return tried, result

    def test_reported_case_falls_through_to_android(self):
        # WSL, 2026-11-14: 403 on the default client, then 'web' has no audio
        tried, result = self.run_download([FORBIDDEN, FORBIDDEN, NO_FORMAT, 'ok'])
        self.assertEqual(tried, ['default', 'default', 'web', 'android'])
        self.assertTrue(result[0].endswith('a.webm'))

    def test_temporary_403_is_retried_once(self):
        tried, result = self.run_download([FORBIDDEN, 'ok'])
        self.assertEqual(tried, ['default', 'default'])
        self.assertNotIsInstance(result, Exception)

    def test_format_error_is_not_retried_on_same_client(self):
        tried, _ = self.run_download([NO_FORMAT, 'ok'])
        self.assertEqual(tried, ['default', 'web'])

    def test_unavailable_video_stops_at_once(self):
        tried, result = self.run_download([UNAVAILABLE])
        self.assertEqual(tried, ['default'])
        self.assertIn('Video unavailable', str(result))

    def test_every_client_fails(self):
        tried, result = self.run_download([FORBIDDEN, FORBIDDEN, NO_FORMAT, NO_FORMAT, NO_FORMAT])
        self.assertEqual(tried, ['default', 'default', 'web', 'android', 'tv'])
        self.assertIn('every YouTube client', str(result))
        self.assertIn('first error: unable to download video data: HTTP Error 403', str(result))


if __name__ == '__main__':
    unittest.main()
