import io
import os
import sys
import time
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

from progress import Spinner


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


class TestSpinner(unittest.TestCase):
    def test_spins_and_hides_then_restores_cursor(self):
        out = FakeTTY()
        with Spinner("Working...", interval=0.01, stream=out):
            time.sleep(0.1)
        text = out.getvalue()
        self.assertTrue(text.startswith('\033[?25l'))
        self.assertTrue(text.endswith('\033[?25h'))
        frames = {c for c in '|/-\\' if f'\r{c} Working...' in text}
        self.assertGreaterEqual(len(frames), 3)  # the character turns

    def test_live_text_and_final_line(self):
        out = io.StringIO()  # not a terminal: no cursor codes
        with Spinner(lambda elapsed: f"elapsed {elapsed:.2f}", interval=0.01, stream=out) as s:
            time.sleep(0.05)
            s.stop(keep="done")
        text = out.getvalue()
        self.assertNotIn('\033[', text)
        self.assertGreater(len(set(text.split('elapsed ')[1:])), 1)  # time is updated
        self.assertIn('\rdone', text)
        self.assertTrue(text.endswith('\n'))

    def test_cursor_restored_on_error(self):
        out = FakeTTY()
        with self.assertRaises(KeyboardInterrupt):
            with Spinner("x", interval=0.01, stream=out):
                raise KeyboardInterrupt
        self.assertTrue(out.getvalue().endswith('\033[?25h'))


if __name__ == '__main__':
    unittest.main()
