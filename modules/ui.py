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
import time

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


def duration(seconds):
    """Format seconds as '3s', '1:05' or '1:02:03'."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class Steps:
    """
    Print the main steps of a run, numbered ('[2/4] Downloading the audio'),
    and their result once done ('  ✔ 7.1 MB downloaded (3s)').
    """

    def __init__(self, names):
        self.names = list(names)
        self.current = 0
        self.started = None

    def next(self, detail=''):
        """Print the next step, with an optional detail after its name."""
        self.current += 1
        self.started = time.monotonic()
        name = self.names[self.current - 1]
        number = style(f"[{self.current}/{len(self.names)}]", 'bold', 'cyan')
        print(f"\n{number} {style(name, 'bold')}"
              + (f" {style(detail, 'dim')}" if detail else ""))

    def done(self, result):
        """Print the result of the current step with its duration."""
        took = duration(time.monotonic() - self.started)
        print(f"  {style('✔', 'bold', 'green')} {result} {style(f'({took})', 'dim')}")
