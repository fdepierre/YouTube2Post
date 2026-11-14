import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from modules import transcriber as tr


def _segments(*texts):
    return [MagicMock(text=t) for t in texts]


class TestTranscriberModelChoice(unittest.TestCase):
    def setUp(self):
        self.patches = {
            'model': patch.object(tr, 'WhisperModel'),
            'pipeline': patch.object(tr, 'BatchedInferencePipeline'),
            'select': patch.object(tr, 'select_device'),
            'save': patch.object(tr, 'save_result'),
            'downloaded': patch.object(tr, '_model_is_downloaded', return_value=True),
            'download': patch.object(tr, 'download_model', side_effect=lambda name, **kw: name),
            'spinner': patch.object(tr, 'Spinner'),
        }
        self.m = {k: p.start() for k, p in self.patches.items()}

    def tearDown(self):
        for p in self.patches.values():
            p.stop()

    def test_gpu_uses_large_turbo_model(self):
        self.m['select'].return_value = ('cuda', 'float16')
        t = tr.Transcriber()
        self.assertEqual((t.device, t.model_name), ('cuda', 'large-v3-turbo'))
        self.m['model'].assert_called_once_with('large-v3-turbo', device='cuda', compute_type='float16')

    def test_cpu_uses_base_model(self):
        self.m['select'].return_value = ('cpu', 'int8')
        t = tr.Transcriber()
        self.assertEqual((t.device, t.model_name), ('cpu', 'base'))

    def test_explicit_model_is_used_on_any_device(self):
        self.m['select'].return_value = ('cuda', 'float16')
        self.assertEqual(tr.Transcriber(model_name='small').model_name, 'small')

    def test_gpu_load_failure_falls_back_to_cpu_base(self):
        self.m['select'].return_value = ('cuda', 'float16')
        self.m['model'].side_effect = [RuntimeError('no cuda'), MagicMock()]
        t = tr.Transcriber()
        self.assertEqual((t.device, t.model_name), ('cpu', 'base'))
        self.m['save'].assert_called_once_with('cpu')

    def test_gpu_transcription_failure_retries_on_cpu(self):
        self.m['select'].return_value = ('cuda', 'float16')
        gpu_pipe, cpu_pipe = MagicMock(), MagicMock()
        gpu_pipe.transcribe.side_effect = RuntimeError('CUDA out of memory')
        cpu_pipe.transcribe.return_value = (_segments('hello', 'world'), None)
        self.m['pipeline'].side_effect = [gpu_pipe, cpu_pipe]
        with tempfile.TemporaryDirectory() as d:
            audio = os.path.join(d, 'a.webm')
            t = tr.Transcriber(work_directory=d)
            self.assertEqual(t.transcribe_audio(audio), 'hello world')
        self.assertEqual((t.device, t.model_name), ('cpu', 'base'))
        self.m['save'].assert_not_called()  # a one-off failure keeps the GPU for next runs


class TestModelDownload(unittest.TestCase):
    def _load(self, downloaded, download):
        with patch.object(tr, 'WhisperModel') as model, patch.object(tr, 'BatchedInferencePipeline'), \
             patch.object(tr, 'select_device', return_value=('cuda', 'float16')), \
             patch.object(tr, 'save_result') as save, \
             patch.object(tr, '_model_is_downloaded', return_value=downloaded), \
             patch.object(tr, 'download_model', side_effect=download) as dl, \
             patch.object(tr, 'Spinner') as spinner, patch('builtins.print') as printed:
            t = tr.Transcriber(announce=False)
        return t, model, save, dl, spinner, printed

    def test_spinner_while_loading_a_downloaded_model(self):
        _, model, _, dl, spinner, _ = self._load(True, lambda name, **kw: '/cache/' + name)
        spinner.assert_called_once_with('Loading large-v3-turbo on CUDA...')
        dl.assert_called_once_with('large-v3-turbo', local_files_only=True)  # no network
        model.assert_called_once_with('/cache/large-v3-turbo', device='cuda', compute_type='float16')

    def test_first_run_downloads_then_loads(self):
        _, _, _, dl, _, printed = self._load(False, lambda name, **kw: '/cache/' + name)
        dl.assert_called_once_with('large-v3-turbo')
        self.assertIn('Downloading the large-v3-turbo model', printed.call_args_list[0].args[0])

    def test_interrupted_download_is_retried(self):
        outcomes = [ConnectionError('WinError 10054'), '/cache/large-v3-turbo']

        def download(name, **kw):
            outcome = outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        t, _, save, _, _, _ = self._load(False, download)
        self.assertEqual((t.device, t.model_name), ('cuda', 'large-v3-turbo'))
        save.assert_not_called()

    def test_failed_download_keeps_gpu_for_next_time(self):
        # Windows, 2026-11-14: the connection was reset while downloading
        def download(name, **kw):
            if name == 'large-v3-turbo':
                raise ConnectionError('[WinError 10054] connection reset')
            return '/cache/' + name
        t, _, save, _, _, _ = self._load(False, download)
        self.assertEqual((t.device, t.model_name), ('cpu', 'base'))
        save.assert_not_called()  # the GPU works: not recorded as 'cpu'


class TestRemainingEstimate(unittest.TestCase):
    def test_longer_than_linear(self):
        # half done in 60 s: linear says 60 s, the estimate leaves a margin
        self.assertEqual(tr.remaining_estimate(60, 0.5), 60 * tr.ETA_MARGIN)

    def test_at_least_one_batch_near_the_end(self):
        # 94% done in 122 s: linear says ~8 s, but the last batch takes ~10 s
        self.assertGreaterEqual(tr.remaining_estimate(122, 0.94, batch_time=10), 10)

    def test_countdown_does_not_go_back_up(self):
        # the 26:44 video: ~0:04 shown when the last batch arrived with ~0:10
        self.assertEqual(tr.next_countdown(4, 10), 4)
        self.assertEqual(tr.next_countdown(-2, 10), 0)  # stays on 'finishing...'
        self.assertEqual(tr.next_countdown(15, 12.9), 12.9)

    def test_countdown_goes_up_on_a_big_slowdown(self):
        self.assertEqual(tr.next_countdown(20, 60), 60)

    def test_finished(self):
        self.assertEqual(tr.remaining_estimate(100, 1.0, batch_time=10), 0)


if __name__ == '__main__':
    unittest.main()
