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
        "yt-dlp is not installed. Please install it using: pip install yt-dlp"
    )

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
        # Configure yt-dlp options for audio extraction
        ydl_opts = {
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
            # Use a modern user agent
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
        except yt_dlp.utils.DownloadError as e:
            raise Exception(f'Error downloading the video: {str(e)}. Please check if the URL is valid.')
        except Exception as e:
            raise Exception(f'Unexpected error while downloading: {str(e)}')

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
