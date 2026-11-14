"""
YouTube Downloader Module
------------------------
This module handles the downloading of YouTube videos using yt-dlp.
It provides functionality to download videos and extract audio for transcription.
The module includes error handling for missing dependencies and download failures.
"""

import os
import shutil

from . import ui
from .progress import Spinner

try:
    import yt_dlp
except ImportError:
    raise ImportError(
        'yt-dlp is not installed. Please install it using: pip install -U "yt-dlp[default]"'
    )

# yt-dlp 2025.11.12+ requires an external JS runtime for YouTube.
_MIN_YTDLP_VERSION = (2025, 11, 12)

# JS runtimes supported by yt-dlp, in priority order.
_JS_RUNTIME_CANDIDATES = (
    ('deno', 'deno'),
    ('node', 'node'),
    ('quickjs', 'qjs'),
    ('bun', 'bun'),
)


def _size(num_bytes):
    """Format a byte count as '7.1 MB' or '850 KB'."""
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    return f"{num_bytes / 1024:.0f} KB"


class _DownloadDisplay:
    """
    Quiet display of a yt-dlp download: its log is hidden and a single live
    line shows the size, speed and remaining time (progress_hooks). Network
    retries and warnings are still shown, above that line (logger).
    """

    def __init__(self, verbose=False):
        self.verbose = verbose  # show all of yt-dlp's messages, as details
        self.state = {}
        self.spinner = Spinner(self._text)

    def _text(self, elapsed):
        st = self.state
        if not st:
            return f"Contacting YouTube... {ui.duration(elapsed)}"
        if st.get('status') == 'finished':
            return "Finishing..."
        done = st.get('downloaded_bytes') or 0
        total = st.get('total_bytes') or st.get('total_bytes_estimate')
        line = _size(done) + (f" / {_size(total)}" if total else "")
        if total:
            line = f"{min(done / total, 1):4.0%}  " + line
        if st.get('speed'):
            line += f"  {_size(st['speed'])}/s"
        if st.get('eta') is not None:
            line += f"  remaining ~{ui.duration(st['eta'])}"
        return line

    def hook(self, d):
        self.state = d

    # yt-dlp logger interface
    def debug(self, msg):
        if 'Got error' in msg or 'Retrying' in msg:  # network problems (e.g. ADSL)
            self.spinner.message(ui.style(msg.strip(), 'yellow'))
        elif self.verbose and (not msg.startswith('[download] ')
                               or msg.startswith(('[download] Destination', '[download] Sleeping'))):
            # yt-dlp's log, as details (its progress lines are shown by the spinner)
            self.spinner.message(ui.format_detail(msg, self.spinner.stream))

    info = debug

    def warning(self, msg):
        self.spinner.message(ui.style(msg.strip(), 'yellow'))

    def error(self, msg):
        pass  # raised as DownloadError and reported by the caller


def _short_error(error):
    """yt-dlp's error message without its 'ERROR: [youtube] <id>: ' prefix."""
    text = str(error).strip()
    if text.startswith('ERROR: '):
        text = text[len('ERROR: '):]
    if text.startswith('['):
        text = text.split(': ', 1)[-1] if ': ' in text else text
    return text.split(' Use --list-formats')[0].rstrip('. ')


def _is_forbidden(error_text):
    return 'HTTP Error 403' in error_text or '403: Forbidden' in error_text


# Errors about the video itself: another YouTube client would not help
_VIDEO_ERRORS = ('Video unavailable', 'This video is unavailable', 'Private video',
                 'is not a valid URL', 'Unsupported URL', 'has been removed',
                 'members-only', 'Sign in to confirm your age')


def _is_video_error(error_text):
    return any(marker in error_text for marker in _VIDEO_ERRORS)


def _parse_yt_dlp_version(version_string):
    parts = []
    for part in version_string.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


class YouTubeDownloader:
    """
    A class to handle YouTube video downloads and audio extraction.
    
    This class provides methods to download YouTube videos and extract their audio
    content for transcription purposes. It includes error handling for missing
    dependencies and ensures proper directory structure.
    
    Attributes:
        tmp_directory (str): Directory for temporary storage of downloaded files
    """

    def __init__(self, tmp_directory='tmp', verbose=False):
        """
        Initialize the YouTubeDownloader with a temporary directory.
        
        Args:
            tmp_directory (str): Path to temporary directory for downloads
            verbose (bool): Also show yt-dlp's log, as detail lines
            
        Raises:
            RuntimeError: If FFmpeg is not found in system PATH
        """
        self.tmp_directory = tmp_directory
        self.verbose = verbose
        self.info = None  # metadata of the last downloaded video
        os.makedirs(self.tmp_directory, exist_ok=True)
        
        # Verify FFmpeg installation
        if not shutil.which('ffmpeg'):
            raise RuntimeError(
                "FFmpeg is not found in system PATH. Please install FFmpeg:\n"
                "1. Download from https://ffmpeg.org/download.html\n"
                "2. Extract the files\n"
                "3. Add the bin folder to your system's PATH environment variable"
            )

    def _detect_js_runtimes(self):
        """Return yt-dlp js_runtimes for every supported runtime on PATH."""
        runtimes = {}
        for name, executable in _JS_RUNTIME_CANDIDATES:
            path = shutil.which(executable)
            if path:
                runtimes[name] = {'path': path}
        return runtimes

    def _base_ydl_opts(self, js_runtimes):
        """Build shared yt-dlp options for audio extraction."""
        opts = {
            # Keep YouTube's original audio (Opus/AAC): faster-whisper reads it
            # directly, so converting to MP3 would only cost time.
            # Whisper downsamples to 16 kHz mono, so a ~50 kbps stream gives the
            # same transcript as ~130 kbps at 2.5x less download (matters on ADSL).
            # Prefer the original-language track: some videos also carry
            # YouTube auto-dubbed tracks in other languages.
            'format': (
                'bestaudio[format_note*=original][abr<=64]'
                '/bestaudio[format_note*=original]'
                '/bestaudio[abr<=64]'
                '/bestaudio/best'
            ),
            'outtmpl': f'{self.tmp_directory}/%(title)s.%(ext)s',
            'writeinfojson': True,
            # TLS certificates are checked (yt-dlp's default): YouTube's player
            # script is run in Deno/Node to solve its challenges, so it must
            # come from the genuine YouTube. The solver itself comes from the
            # yt-dlp-ejs package (installed by yt-dlp[default]), not
            # downloaded from GitHub at run time.
            'no_warnings': False,
            'quiet': False,
            'retries': 3,
            'extractor_retries': 3,
        }
        if js_runtimes:
            opts['js_runtimes'] = js_runtimes
        return opts

    def _download_attempts(self, js_runtimes):
        """Yield yt-dlp option sets, starting with JS-enabled clients then fallbacks."""
        base = self._base_ydl_opts(js_runtimes)
        if js_runtimes:
            yield dict(base)
            fallback_clients = (
                ['web'],
                ['android'],
                ['tv'],
            )
        else:
            # Without a JS runtime, the default android_vr client often 403s.
            fallback_clients = (
                ['android'],
                ['tv'],
                ['web'],
            )
        for clients in fallback_clients:
            attempt = dict(base)
            attempt['extractor_args'] = {'youtube': {'player_client': clients}}
            yield attempt

    def downloaded_size(self, audio_file):
        """Return a short summary of a downloaded file: '7.1 MB'."""
        return _size(os.path.getsize(audio_file))

    def download_audio(self, youtube_url):
        """
        Download audio from a YouTube video and extract metadata.
        
        This method downloads the best available audio quality from a YouTube video
        in its original format (Opus/AAC, no conversion). It also saves video metadata in JSON format.
        
        Args:
            youtube_url (str): URL of the YouTube video to download
            
        Returns:
            tuple: Paths to the (audio_file, json_file)
            
        Raises:
            Exception: If download fails or URL is invalid
        """
        installed_version = getattr(yt_dlp.version, '__version__', '0')
        if _parse_yt_dlp_version(installed_version) < _MIN_YTDLP_VERSION:
            ui.warn(
                f"Warning: yt-dlp {installed_version} is outdated. "
                f"YouTube downloads often fail with HTTP 403 on old versions. "
                f'Upgrade with: pip install -U "yt-dlp[default]"'
            )

        js_runtimes = self._detect_js_runtimes()
        if js_runtimes:
            ui.detail("JavaScript runtime(s) for YouTube: " + ', '.join(
                f"{name} ({config['path']})" for name, config in js_runtimes.items()))
        else:
            ui.warn(
                "Warning: no JavaScript runtime found (Deno recommended, Node also works). "
                "YouTube extraction without one is deprecated and often returns HTTP 403. "
                "See https://github.com/yt-dlp/yt-dlp/wiki/EJS"
            )

        display = _DownloadDisplay(verbose=self.verbose)
        say = display.spinner.message
        errors = []
        info = None
        with display.spinner:
            for ydl_opts in self._download_attempts(js_runtimes):
                ydl_opts.update(quiet=True, noprogress=True, logger=display,
                                progress_hooks=[display.hook])
                client = (ydl_opts.get('extractor_args', {})
                          .get('youtube', {}).get('player_client') or ['default'])[0]
                # A 403 is often temporary: retry the same client once
                tries = 2 if client == 'default' else 1
                for attempt in range(tries):
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(youtube_url, download=True)
                        break
                    except yt_dlp.utils.DownloadError as e:
                        error_text = _short_error(e)
                        if _is_video_error(error_text):
                            raise Exception(f'Error downloading the video: {error_text}. '
                                            'Please check if the URL is valid.')
                        errors.append(error_text)
                        retry = attempt + 1 < tries and _is_forbidden(error_text)
                        say(ui.style(f"Download failed with the {client} YouTube client "
                                     f"({error_text}). "
                                     + ("Trying again..." if retry else "Trying another client..."),
                                     'yellow'))
                        if not retry:
                            break
                    except Exception as e:
                        raise Exception(f'Unexpected error while downloading: {str(e)}')
                if info is not None:
                    break

        if info is None:
            hint = ''
            if not js_runtimes:
                hint = (
                    ' Install Deno (https://deno.com) or make sure Node.js is on PATH, '
                    'then run: pip install -U "yt-dlp[default]".'
                )
            else:
                hint = ' YouTube may be blocking downloads for now: try again later, or update yt-dlp.'
            raise Exception(
                f'Error downloading the video with every YouTube client '
                f'(first error: {errors[0] if errors else "unknown"}).{hint}'
            )

        # yt-dlp reports the exact paths it wrote
        downloads = info.get('requested_downloads') or [{}]
        audio_file = downloads[0].get('filepath')
        json_file = os.path.splitext(audio_file)[0] + '.info.json' if audio_file else None

        if not (audio_file and os.path.exists(audio_file) and os.path.exists(json_file)):
            raise Exception('Failed to locate downloaded files')

        self.info = info
        abr = info.get('abr') if ui.verbose else None
        ui.detail(f"Audio format {info.get('format_id')}: {info.get('acodec')} "
                  + (f"{abr:.0f} kbps " if abr else "") + f"in .{info.get('ext')}"
                  + (f", language {info['language']}" if info.get('language') else ""))

        return audio_file, json_file
