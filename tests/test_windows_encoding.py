import builtins
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from modules import transcriber as tr

_real_open = builtins.open


def _windows_open(file, mode='r', *args, encoding=None, **kwargs):
    """open() as on Windows: text files default to cp1252, not UTF-8."""
    if 'b' not in mode and encoding is None:
        encoding = 'cp1252'
    return _real_open(file, mode, *args, encoding=encoding, **kwargs)


class TestWindowsEncoding(unittest.TestCase):
    def test_utf8_metadata_and_transcript_on_windows(self):
        # 'ŝ' is UTF-8 c5 9d, 'Ł' c5 81: 0x81 and 0x9d are undefined in cp1252
        # (the reported "'charmap' codec can't decode byte 0x81")
        title, text = 'Łódź — Rust ŝ “quotes”', 'Voilà: été, Łódź.'
        with tempfile.TemporaryDirectory() as d, \
             patch.object(tr, 'select_device', return_value=('cpu', 'int8')), \
             patch.object(tr, 'WhisperModel'), \
             patch.object(tr, 'BatchedInferencePipeline') as pipeline, \
             patch('builtins.open', _windows_open):
            pipeline.return_value.transcribe.return_value = (
                [MagicMock(text=text, end=1.0)], MagicMock(duration=1.0, language='fr'))
            json_file = os.path.join(d, 'a.info.json')
            with _real_open(json_file, 'w', encoding='utf-8') as f:
                json.dump({'title': title, 'uploader': 'Ŝ', 'description': 'ŝ'}, f, ensure_ascii=False)
            with patch('builtins.print'):
                t = tr.Transcriber(work_directory=d, announce=False)
                out = t.create_transcript_content(os.path.join(d, 'a.webm'), json_file, 'url')
            with _real_open(out, encoding='utf-8') as f:
                content = f.read()
        self.assertIn(title, content)
        self.assertIn(text, content)


if __name__ == '__main__':
    unittest.main()
