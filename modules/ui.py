"""
UI Module
---------
Colours and numbered steps for the console output ("[2/4] Downloading...").

Colours are used only on a terminal, and can be turned off with the standard
NO_COLOR environment variable (or forced with FORCE_COLOR), like Python's own
coloured --help.
"""

import os
import sys

_CODES = {
    'bold': '1', 'dim': '2', 'red': '31', 'green': '32', 'yellow': '33',
    'blue': '34', 'magenta': '35', 'cyan': '36',
}


def use_color(stream=None):
    """True if ANSI colours should be written to the stream."""
    stream = stream or sys.stdout
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('FORCE_COLOR'):
        return True
    if os.environ.get('TERM') == 'dumb':
        return False
    return hasattr(stream, 'isatty') and stream.isatty()


if sys.platform == 'win32':  # turn on ANSI escape codes in the Windows console
    os.system('')


def style(text, *styles):
    """Return text wrapped in the given styles (e.g. 'bold', 'cyan'), if colours are on."""
    if not styles or not use_color():
        return text
    codes = ';'.join(_CODES[s] for s in styles)
    return f"\033[{codes}m{text}\033[0m"


def success(text):
    print(style(text, 'bold', 'green'))


def warn(text):
    print(style(text, 'yellow'))


def error(text):
    print(style(text, 'bold', 'red'))


class Steps:
    """Print the main steps of a run, numbered: '[2/4] Downloading the audio'."""

    def __init__(self, names):
        self.names = list(names)
        self.current = 0

    def next(self, detail=''):
        """Print the next step, with an optional detail after its name."""
        self.current += 1
        name = self.names[self.current - 1]
        number = style(f"[{self.current}/{len(self.names)}]", 'bold', 'cyan')
        print(f"\n{number} {style(name, 'bold')}"
              + (f" {style(detail, 'dim')}" if detail else ""))
