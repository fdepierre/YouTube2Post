import io
import time
import unittest

from modules.progress import Spinner


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
        frames = {c for c in '|/-\\' if f'\033[K{c} Working...' in text}
        self.assertGreaterEqual(len(frames), 3)  # the character turns

    def test_live_text_and_final_line(self):
        out = FakeTTY()
        with Spinner(lambda elapsed: f"elapsed {elapsed:.2f}", interval=0.01, stream=out) as s:
            time.sleep(0.05)
            s.stop(keep="done")
        text = out.getvalue()
        self.assertGreater(len(set(text.split('elapsed ')[1:])), 1)  # time is updated
        self.assertIn('done\n', text)

    def test_no_animation_when_not_a_terminal(self):
        out = io.StringIO()  # e.g. redirected to a log file
        with Spinner("Working...", interval=0.01, stream=out) as s:
            time.sleep(0.05)
            s.message("a warning")
            s.stop(keep="done")
        self.assertEqual(out.getvalue(), "a warning\ndone\n")

    def test_message_is_printed_above_the_line(self):
        out = FakeTTY()
        with Spinner("Working...", interval=0.01, stream=out) as s:
            time.sleep(0.03)
            s.message("Retrying (1/3)...")
            time.sleep(0.03)
        text = out.getvalue()
        self.assertIn('\r\033[KRetrying (1/3)...\n', text)
        self.assertGreater(text.index('Working...', text.index('Retrying')), 0)  # redrawn after

    def test_cursor_restored_on_error(self):
        out = FakeTTY()
        with self.assertRaises(KeyboardInterrupt):
            with Spinner("x", interval=0.01, stream=out):
                raise KeyboardInterrupt
        self.assertTrue(out.getvalue().endswith('\033[?25h'))


if __name__ == '__main__':
    unittest.main()
