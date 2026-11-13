"""
Clipboard Module
----------------
Reads a YouTube URL from the system clipboard, so the program can be started
without pasting the URL. Works on Windows, WSL, macOS and Linux with the tools
each system already provides; if none is available it simply returns None.
"""

import os
import platform
import re
import shutil
import subprocess
import sys

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


# Clipboard writers per environment: (executable, arguments, text encoding).
# Windows' clip.exe expects UTF-16LE (without BOM) to keep accents.
_WRITERS = {
    'windows': (('clip.exe', [], 'utf-16le'),),
    'wsl': (('clip.exe', [], 'utf-16le'),),  # the Windows clipboard, shared with Windows Terminal
    'macos': (('pbcopy', [], 'utf-8'),),
    'linux': (
        ('wl-copy', [], 'utf-8'),
        ('xclip', ['-selection', 'clipboard'], 'utf-8'),
        ('xsel', ['--clipboard', '--input'], 'utf-8'),
    ),
}


def environment():
    """Return where the program runs: 'windows', 'wsl', 'macos' or 'linux'."""
    if sys.platform == 'win32':
        return 'windows'
    if sys.platform == 'darwin':
        return 'macos'
    if os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower():
        return 'wsl'
    return 'linux'


def write_clipboard(text, timeout=5):
    """Copy text to the clipboard of the current environment; return True on success."""
    for executable, args, encoding in _WRITERS[environment()]:
        path = shutil.which(executable)
        if not path:
            continue
        try:
            # No pipes left open: xclip and wl-copy keep running in the
            # background to serve the clipboard.
            result = subprocess.run(
                [path, *args], input=text.encode(encoding), stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=timeout, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            return True
    return False


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
