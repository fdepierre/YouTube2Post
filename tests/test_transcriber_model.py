import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import transcriber as tr


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
            out = t.transcribe_audio(audio)
            with open(out, encoding='utf-8') as f:
                self.assertEqual(f.read(), 'hello world')
        self.assertEqual((t.device, t.model_name), ('cpu', 'base'))
        self.m['save'].assert_not_called()  # a one-off failure keeps the GPU for next runs


class TestModelLoadingDisplay(unittest.TestCase):
    def _load(self, downloaded):
        with patch.object(tr, 'WhisperModel'), patch.object(tr, 'BatchedInferencePipeline'), \
             patch.object(tr, 'select_device', return_value=('cuda', 'float16')), \
             patch.object(tr, '_model_is_downloaded', return_value=downloaded), \
             patch.object(tr, 'Spinner') as spinner, patch('builtins.print') as printed:
            tr.Transcriber(announce=False)
        return spinner, printed

    def test_spinner_while_loading_a_downloaded_model(self):
        spinner, _ = self._load(downloaded=True)
        spinner.assert_called_once_with('Loading large-v3-turbo on CUDA...')

    def test_no_spinner_over_the_first_download_progress_bars(self):
        spinner, printed = self._load(downloaded=False)
        spinner.assert_not_called()
        self.assertIn('Downloading the large-v3-turbo model', printed.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
