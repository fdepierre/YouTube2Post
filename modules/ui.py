"""
UI Module
---------
Colours and numbered steps for the console output ("[2/4] Downloading...").

Colours are used only on a terminal, and can be turned off with the standard
NO_COLOR environment variable (or forced with FORCE_COLOR), like Python's own
coloured --help.
"""

import os
import shutil
import sys
import textwrap
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


def _enable_windows_ansi():
    """
    Turn on ANSI escape codes (colours, cursor) in the Windows console, through
    the console API rather than the usual os.system('') trick, which starts
    a shell (cmd.exe) for nothing.
    """
    import ctypes
    kernel32 = ctypes.windll.kernel32
    enable_virtual_terminal_processing = 0x0004
    for std_handle in (-11, -12):  # stdout, stderr
        handle = kernel32.GetStdHandle(std_handle)
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):  # a console, not a file
            kernel32.SetConsoleMode(handle, mode.value | enable_virtual_terminal_processing)


if sys.platform == 'win32':
    _enable_windows_ansi()


def style(text, *styles):
    """Return text wrapped in the given styles (e.g. 'bold', 'cyan'), if colours are on."""
    if not styles or not use_color():
        return text
    codes = ';'.join(_CODES[s] for s in styles)
    return f"\033[{codes}m{text}\033[0m"


def success(text):
    print(style(text, 'bold', 'green'))


def saved_file(title, path):
    """Print where a file was saved, directory and file name on separate lines."""
    directory, name = os.path.split(os.path.abspath(path))
    print(f"\n{style(title, 'bold', 'green')}")
    print(f"  {style('Dir: ', 'dim')} {directory}{os.sep}")
    print(f"  {style('File:', 'dim')} {style(name, 'bold')}")


# Set from the command line (-v): show the technical details of each step
verbose = False


_DETAIL_PREFIX = "    · "


def short_path(text):
    """Shorten the home directory to '~' in text (paths are long)."""
    home = os.path.expanduser("~")
    return text.replace(home + os.sep, "~" + os.sep) if home not in ("", os.sep) else text


def format_detail(text, stream=None):
    """
    Return '    · text' dimmed, with the home directory shortened. On a terminal,
    long lines are wrapped to its width with the same indentation (instead
    of continuing at the start of the next line).
    """
    stream = stream or sys.stdout
    text = short_path(str(text).strip())
    if hasattr(stream, 'isatty') and stream.isatty():
        width = shutil.get_terminal_size((100, 20)).columns - 1
        lines = textwrap.wrap(text, width=max(width, 40), initial_indent=_DETAIL_PREFIX,
                              subsequent_indent=" " * len(_DETAIL_PREFIX),
                              break_long_words=True, break_on_hyphens=False) or [_DETAIL_PREFIX]
        text = "\n".join(lines)
    else:
        text = _DETAIL_PREFIX + text
    return style(text, 'dim')


def detail(text):
    """Print a technical detail, only in verbose mode."""
    if verbose:
        print(format_detail(text))


def note(text):
    """Print a secondary confirmation: '  ✓ text' (dimmed)."""
    print(f"  {style('✓', 'green')} {style(text, 'dim')}")


def warn(text):
    print(style(text, 'yellow'))


def error(text):
    print(style(text, 'bold', 'red'))


def clock(seconds):
    """Format seconds as '0:03', '1:05' or '1:02:03' (truncated): positions and times."""
    h, rest = divmod(int(seconds), 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def duration(seconds):
    """Format seconds as '3s', '1:05' or '1:02:03' (truncated): how long a step took."""
    return f"{int(seconds)}s" if seconds < 60 else clock(seconds)


class Steps:
    """
    Print the main steps of a run, numbered ('[2/4] Downloading the audio'),
    and their result once done ('  ✓ 7.1 MB downloaded (3s)').
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
        print(f"  {style('✓', 'bold', 'green')} {result} {style(f'({took})', 'dim')}")
