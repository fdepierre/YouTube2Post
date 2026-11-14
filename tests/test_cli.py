"""
End-to-end tests: run yt2post.py as a user does, in a separate process, with
the answers typed on stdin.

Each test runs a copy of the program in a temporary directory, so its tmp/
and work/ directories (and config.json) are never the real ones. Tests that
need the network (YouTube) or Ollama are skipped when it is not available.
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.request

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEST_MP3 = os.path.join(PROJECT_DIR, 'tests', 'test_transcriber.mp3')
TEST_TRANSCRIPT = os.path.join(PROJECT_DIR, 'tests', 'test_chat.txt')
SHORT_VIDEO = 'https://www.youtube.com/watch?v=v4t0E3S1N1k'
EXPECTED_WORDS = ['grow', 'weed', 'english', 'minute']


def _online(url, timeout=5):
    try:
        urllib.request.urlopen(url, timeout=timeout).close()
        return True
    except Exception:
        return False


def _ollama_has_model():
    try:
        with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3) as r:
            return b'"name"' in r.read()
    except Exception:
        return False


class CliTestCase(unittest.TestCase):
    """Run a copy of the program in a temporary directory."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.app = os.path.join(self._dir.name, 'app')
        # Only what the program needs to run
        shutil.copytree(os.path.join(PROJECT_DIR, 'modules'), os.path.join(self.app, 'modules'),
                        ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('yt2post.py', 'config.json'):
            shutil.copy(os.path.join(PROJECT_DIR, name), self.app)
        self.work = os.path.join(self.app, 'work')

    def tearDown(self):
        self._dir.cleanup()

    def run_cli(self, *args, stdin='', env=None, timeout=600):
        """Run yt2post.py from another directory; return (exit code, output)."""
        environment = {**os.environ, 'NO_COLOR': '1', **(env or {})}
        result = subprocess.run(
            [sys.executable, os.path.join(self.app, 'yt2post.py'), *args],
            input=stdin, capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=timeout, cwd=self._dir.name, env=environment)
        return result.returncode, result.stdout + result.stderr

    def transcripts(self):
        return glob.glob(os.path.join(self.work, '*_transcript.txt'))

    def assert_transcript(self, output):
        """One transcript in work/, with the expected words and its path printed."""
        files = self.transcripts()
        self.assertEqual(len(files), 1, output)
        with open(files[0], encoding='utf-8') as f:
            text = f.read().lower()
        for word in EXPECTED_WORDS:
            self.assertIn(word, text)
        self.assertIn('Transcript saved to:', output)
        self.assertIn(os.path.basename(files[0]), output)
        return files[0]


class TestArguments(CliTestCase):
    def test_no_option_shows_help(self):
        code, out = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn('usage: yt2post.py', out)

    def test_help(self):
        code, out = self.run_cli('-h')
        self.assertEqual(code, 0)
        for option in ('--transcribe', '--chat', '--full', '--model-select', '--verbose'):
            self.assertIn(option, out)

    def test_chat_needs_a_transcript(self):
        code, out = self.run_cli('-c')
        self.assertEqual(code, 2)
        self.assertIn('-c needs the transcript file', out)
        code, out = self.run_cli('-c', 'missing.txt')
        self.assertEqual(code, 2)
        self.assertIn('transcript file not found', out)


class TestTranscribeLocalMp3(CliTestCase):
    def test_file_typed_when_clipboard_has_no_url(self):
        # No clipboard tool on the PATH: the program asks for the input
        code, out = self.run_cli('-t', stdin=TEST_MP3 + '\n', env={'PATH': ''})
        self.assertEqual(code, 0, out)
        self.assertIn('No YouTube URL in the clipboard', out)
        self.assertIn('[1/2] Loading the transcription model', out)
        self.assertIn('[2/2] Transcribing the audio', out)
        self.assertIn('of audio transcribed (en)', out)
        self.assertNotIn('System', out)  # no details without -v
        path = self.assert_transcript(out)
        with open(path, encoding='utf-8') as f:
            self.assertIn(TEST_MP3, f.read())  # the source, in the header

    def test_verbose_with_file_argument(self):
        code, out = self.run_cli('-v', '-t', TEST_MP3)
        self.assertEqual(code, 0, out)
        self.assertNotIn('No YouTube URL in the clipboard', out)
        for line in ('System', 'CPU:', 'RAM:', 'GPU:', 'Model files', 'Language en detected',
                     'segments, batches of 16'):
            self.assertIn(line, out)
        self.assert_transcript(out)

    def test_nothing_typed(self):
        code, out = self.run_cli('-t', stdin='\n', env={'PATH': ''})
        self.assertEqual(code, 1)
        self.assertIn('No input given', out)
        self.assertEqual(self.transcripts(), [])


@unittest.skipUnless(_online('https://www.youtube.com'), 'no access to YouTube')
class TestTranscribeYouTube(CliTestCase):
    def test_download_and_transcribe(self):
        code, out = self.run_cli('-t', SHORT_VIDEO)
        self.assertEqual(code, 0, out)
        for line in ('[1/3] Loading the transcription model',
                     '[2/3] Downloading the audio from YouTube', '[3/3] Transcribing the audio'):
            self.assertIn(line, out)
        path = self.assert_transcript(out)
        with open(path, encoding='utf-8') as f:
            self.assertIn(SHORT_VIDEO, f.read())

    def test_unavailable_video(self):
        code, out = self.run_cli('-t', 'https://www.youtube.com/watch?v=xxxxxxxxxxx')
        self.assertEqual(code, 1)
        self.assertIn('Error', out)
        self.assertEqual(self.transcripts(), [])


@unittest.skipUnless(_ollama_has_model(), 'Ollama is not running or has no model')
class TestChat(CliTestCase):
    def test_chat_about_a_transcript(self):
        # -m always lists the models: Enter takes the default one
        code, out = self.run_cli('-m', '-c', TEST_TRANSCRIPT,
                                 stdin='\nWhat does "grow like a weed" mean? One sentence.\nexit\n')
        self.assertEqual(code, 0, out)
        self.assertIn('[1/2] Choosing the Ollama model', out)
        self.assertIn('[2/2] Chatting about the transcript', out)
        self.assertIn('Chat session started', out)
        self.assertIn('Assistant: Goodbye!', out)
        answer = out.split('Assistant: ')[1].lower()  # the first answer
        self.assertTrue(answer.strip() and 'goodbye' not in answer, out)

    @unittest.skipUnless(_online('https://www.youtube.com'), 'no access to YouTube')
    def test_full(self):
        code, out = self.run_cli('-m', '-f', SHORT_VIDEO,
                                 stdin='\nSummarize the video in one sentence.\nexit\n')
        self.assertEqual(code, 0, out)
        for line in ('[1/5] Choosing the Ollama model', '[2/5] Loading the transcription model',
                     '[3/5] Downloading the audio from YouTube', '[4/5] Transcribing the audio',
                     '[5/5] Chatting about the transcript', 'Assistant: Goodbye!'):
            self.assertIn(line, out)
        self.assert_transcript(out)


if __name__ == '__main__':
    unittest.main()
