import io
import os
import sys
import unittest
from unittest.mock import patch

from modules import ui


class TestStyle(unittest.TestCase):
    def test_no_color_when_not_a_terminal(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'stdout', io.StringIO()):
            self.assertEqual(ui.style('x', 'bold'), 'x')

    def test_force_color(self):
        with patch.dict(os.environ, {'FORCE_COLOR': '1'}, clear=True):
            self.assertEqual(ui.style('x', 'bold', 'cyan'), '\033[1;36mx\033[0m')

    def test_no_color_wins(self):
        with patch.dict(os.environ, {'FORCE_COLOR': '1', 'NO_COLOR': '1'}, clear=True):
            self.assertEqual(ui.style('x', 'red'), 'x')


class TestSteps(unittest.TestCase):
    def test_numbered_steps(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'stdout', out):
            steps = ui.Steps(['Load', 'Download', 'Transcribe'])
            steps.next()
            steps.next('https://youtu.be/x')
        self.assertEqual(out.getvalue(), '\n[1/3] Load\n\n[2/3] Download https://youtu.be/x\n')

    def test_done_shows_result_and_duration(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'stdout', out):
            steps = ui.Steps(['Download'])
            steps.next()
            steps.done('7.1 MB')
        self.assertTrue(out.getvalue().endswith('  ✓ 7.1 MB (0s)\n'))

    def test_duration(self):
        self.assertEqual([ui.duration(s) for s in (3.4, 65, 3723)], ['3s', '1:05', '1:02:03'])


class TestSavedFile(unittest.TestCase):
    def test_directory_and_file_on_separate_lines(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'stdout', out):
            ui.saved_file('Transcript saved to:', '/data/work/My_video_transcript.txt')
        self.assertEqual(out.getvalue(), '\nTranscript saved to:\n'
                                         '  Dir:  /data/work/\n'
                                         '  File: My_video_transcript.txt\n')


class TestDetail(unittest.TestCase):
    def test_only_in_verbose_mode(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'stdout', out):
            with patch.object(ui, 'verbose', False):
                ui.detail('hidden')
            with patch.object(ui, 'verbose', True):
                ui.detail('shown')
        self.assertEqual(out.getvalue(), '    · shown\n')


class TestFormatDetail(unittest.TestCase):
    def test_wraps_with_indent_and_shortens_home(self):
        class TTY(io.StringIO):
            def isatty(self):
                return True
        home = os.path.expanduser('~')
        text = 'Model files: ' + os.path.join(home, '.cache', 'x' * 60)
        with patch.dict(os.environ, {'NO_COLOR': '1'}), \
             patch.object(ui.shutil, 'get_terminal_size', return_value=os.terminal_size((50, 20))):
            lines = ui.format_detail(text, TTY()).split('\n')
        self.assertTrue(lines[0].startswith('    · Model files: ~/.cache/'))
        self.assertTrue(all(l.startswith('      ') for l in lines[1:]))
        self.assertTrue(all(len(l) <= 49 for l in lines))


if __name__ == '__main__':
    unittest.main()
