import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import youtube_downloader as yd


class TestDownloadDisplay(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'NO_COLOR': '1'})
        self.env.start()
        self.d = yd._DownloadDisplay()

    def tearDown(self):
        self.env.stop()

    def test_before_download(self):
        self.assertEqual(self.d._text(4.2), 'Contacting YouTube... 4s')

    def test_progress_line(self):
        self.d.hook({'status': 'downloading', 'downloaded_bytes': 3 * 2**20,
                     'total_bytes': 12 * 2**20, 'speed': 450 * 1024, 'eta': 20})
        self.assertEqual(self.d._text(5), ' 25%  3.0 MB / 12.0 MB  450 KB/s  remaining ~20s')

    def test_estimated_total_and_finish(self):
        self.d.hook({'status': 'downloading', 'downloaded_bytes': 500 * 1024,
                     'total_bytes_estimate': 2**20})
        self.assertEqual(self.d._text(1), ' 49%  500 KB / 1.0 MB')
        self.d.hook({'status': 'finished'})
        self.assertEqual(self.d._text(1), 'Finishing...')

    def test_only_network_problems_and_warnings_are_shown(self):
        with patch.object(self.d.spinner, 'message') as message:
            self.d.debug('[youtube] abc: Downloading webpage')
            self.d.debug('[download] Got error: Network is unreachable. Retrying (1/3)...')
            self.d.warning('Some warning')
            self.d.error('ERROR: reported by the caller')
        self.assertEqual([c.args[0] for c in message.call_args_list],
                         ['[download] Got error: Network is unreachable. Retrying (1/3)...',
                          'Some warning'])


if __name__ == '__main__':
    unittest.main()
