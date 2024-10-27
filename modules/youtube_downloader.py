import os
import subprocess

class YouTubeDownloader:
    def __init__(self, tmp_directory='tmp'):
        self.tmp_directory = tmp_directory
        os.makedirs(self.tmp_directory, exist_ok=True)

    def download_audio(self, youtube_url):
        """
        Download audio and metadata from a YouTube video using yt-dlp.
        """
        try:
            subprocess.run(
                ['yt-dlp', '-x', '--audio-format', 'mp3', '--write-info-json',
                 '-o', f'{self.tmp_directory}/%(title)s.%(ext)s', youtube_url],
                check=True
            )
        except subprocess.CalledProcessError:
            raise Exception('Error downloading the audio.')

        audio_file = None
        json_file = None
        for file in os.listdir(self.tmp_directory):
            if file.endswith('.mp3'):
                audio_file = os.path.join(self.tmp_directory, file)
            elif file.endswith('.json'):
                json_file = os.path.join(self.tmp_directory, file)

        return audio_file, json_file
