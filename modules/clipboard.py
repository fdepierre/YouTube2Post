"""
Clipboard Module
----------------
Reads a YouTube URL from the system clipboard, so the program can be started
without pasting the URL. Works on Windows, WSL, macOS and Linux with the tools
each system already provides; if none is available it simply returns None.
"""

import re
import shutil
import subprocess

# Clipboard readers in priority order. powershell.exe comes first so that WSL
# reads the Windows clipboard (where the browser copies the URL).
_READERS = (
    ('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', 'Get-Clipboard']),
    ('pbpaste', []),
    ('wl-paste', ['--no-newline']),
    ('xclip', ['-selection', 'clipboard', '-o']),
    ('xsel', ['--clipboard', '--output']),
)

_YOUTUBE_URL = re.compile(
    r'https?://(?:(?:www|m|music)\.)?'
    r'(?:youtube\.com/(?:watch\?|shorts/|live/)|youtu\.be/)'
    r'[^\s"\'<>]+'
)


def read_clipboard(timeout=5):
    """Return the clipboard text, or None if it cannot be read."""
    for executable, args in _READERS:
        path = shutil.which(executable)
        if not path:
            continue
        try:
            result = subprocess.run(
                [path, *args], stdin=subprocess.DEVNULL, capture_output=True,
                timeout=timeout, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            return result.stdout.decode('utf-8', errors='replace')
    return None


def find_youtube_url(text):
    """Return the first YouTube video URL found in text, or None."""
    match = _YOUTUBE_URL.search(text or '')
    return match.group(0) if match else None


def youtube_url_from_clipboard():
    """Return the YouTube URL currently in the clipboard, or None."""
    return find_youtube_url(read_clipboard())
