import os
import shutil

try:
    import yt_dlp
except ImportError:
    raise ImportError(
        "yt-dlp is not installed. Please install it using: pip install yt-dlp"
    )

class YouTubeDownloader:
    def __init__(self, tmp_directory='tmp'):
        self.tmp_directory = tmp_directory
        os.makedirs(self.tmp_directory, exist_ok=True)
        
        # Check for FFmpeg availability
        if not shutil.which('ffmpeg'):
            raise RuntimeError(
                "FFmpeg is not found in system PATH. Please install FFmpeg:\n"
                "1. Download from https://ffmpeg.org/download.html\n"
                "2. Extract the files\n"
                "3. Add the bin folder to your system's PATH environment variable"
            )

    def download_audio(self, youtube_url):
        """
        Download audio and metadata from a YouTube video using yt-dlp.
        """
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'{self.tmp_directory}/%(title)s.%(ext)s',
            'writeinfojson': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
        except yt_dlp.utils.DownloadError as e:
            raise Exception(f'Error downloading the video: {str(e)}. Please check if the URL is valid.')
        except Exception as e:
            raise Exception(f'Unexpected error while downloading: {str(e)}')

        audio_file = None
        json_file = None
        for file in os.listdir(self.tmp_directory):
            if file.endswith('.mp3'):
                audio_file = os.path.join(self.tmp_directory, file)
            elif file.endswith('.json'):
                json_file = os.path.join(self.tmp_directory, file)

        if not audio_file or not json_file:
            raise Exception('Could not find downloaded files. Please ensure you have write permissions in the temporary directory.')
            
        return audio_file, json_file
