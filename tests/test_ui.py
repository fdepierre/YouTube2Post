import io
import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import ui


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


if __name__ == '__main__':
    unittest.main()
