"""
YouTube Downloader Module
------------------------
This module handles the downloading of YouTube videos using yt-dlp.
It provides functionality to download videos and extract audio for transcription.
The module includes error handling for missing dependencies and download failures.
"""

import os
import shutil

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

    def __init__(self, tmp_directory='tmp'):
        """
        Initialize the YouTubeDownloader with a temporary directory.
        
        Args:
            tmp_directory (str): Path to temporary directory for downloads
            
        Raises:
            RuntimeError: If FFmpeg is not found in system PATH
        """
        self.tmp_directory = tmp_directory
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
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'{self.tmp_directory}/%(title)s.%(ext)s',
            'writeinfojson': True,
            'nocheckcertificate': True,
            'no_warnings': False,
            'quiet': False,
            'retries': 3,
            'extractor_retries': 3,
            # Allow fetching EJS challenge solvers if yt-dlp-ejs is not installed.
            'remote_components': ['ejs:github'],
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

    def download_audio(self, youtube_url):
        """
        Download audio from a YouTube video and extract metadata.
        
        This method downloads the best available audio quality from a YouTube video
        and extracts it to MP3 format. It also saves video metadata in JSON format.
        
        Args:
            youtube_url (str): URL of the YouTube video to download
            
        Returns:
            tuple: Paths to the (audio_file, json_file)
            
        Raises:
            Exception: If download fails or URL is invalid
        """
        installed_version = getattr(yt_dlp.version, '__version__', '0')
        if _parse_yt_dlp_version(installed_version) < _MIN_YTDLP_VERSION:
            print(
                f"Warning: yt-dlp {installed_version} is outdated. "
                f"YouTube downloads often fail with HTTP 403 on old versions. "
                f'Upgrade with: pip install -U "yt-dlp[default]"'
            )

        js_runtimes = self._detect_js_runtimes()
        if js_runtimes:
            available = ', '.join(
                f"{name} ({config['path']})" for name, config in js_runtimes.items()
            )
            print(f"Using JavaScript runtime(s) for YouTube: {available}")
        else:
            print(
                "Warning: no JavaScript runtime found (Deno recommended, Node also works). "
                "YouTube extraction without one is deprecated and often returns HTTP 403. "
                "See https://github.com/yt-dlp/yt-dlp/wiki/EJS"
            )

        last_error = None
        for ydl_opts in self._download_attempts(js_runtimes):
            player_client = (
                ydl_opts.get('extractor_args', {})
                .get('youtube', {})
                .get('player_client')
            )
            if player_client:
                print(f"Trying YouTube download with player_client={player_client[0]}")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
                last_error = None
                break
            except yt_dlp.utils.DownloadError as e:
                last_error = e
                error_text = str(e)
                if 'HTTP Error 403' not in error_text and '403: Forbidden' not in error_text:
                    raise Exception(
                        f'Error downloading the video: {error_text}. Please check if the URL is valid.'
                    )
                print(f"YouTube returned 403 Forbidden ({error_text}). Trying another client...")
            except Exception as e:
                raise Exception(f'Unexpected error while downloading: {str(e)}')

        if last_error is not None:
            hint = ''
            if not js_runtimes:
                hint = (
                    ' Install Deno (https://deno.com) or make sure Node.js is on PATH, '
                    'then run: pip install -U "yt-dlp[default]".'
                )
            raise Exception(
                f'Error downloading the video: {str(last_error)}. '
                f'Please check if the URL is valid.{hint}'
            )

        # Find the downloaded files
        audio_file = None
        json_file = None
        for file in os.listdir(self.tmp_directory):
            if file.endswith('.mp3'):
                audio_file = os.path.join(self.tmp_directory, file)
            elif file.endswith('.info.json'):
                json_file = os.path.join(self.tmp_directory, file)

        if not audio_file or not json_file:
            raise Exception('Failed to locate downloaded files')

        return audio_file, json_file
