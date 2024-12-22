import json
import whisper
import os
import re
import torch

class Transcriber:
    def __init__(self, model_name='base', work_directory='.'):
        self.model_name = model_name
        self.work_directory = work_directory
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {self.device}")

    def transcribe_audio(self, audio_file):
        self.model = whisper.load_model(self.model_name).to(self.device)
        result = self.model.transcribe(audio_file)
        transcript_file = f"{audio_file}.txt"
        
        # Handle the result from whisper model
        if isinstance(result, dict) and 'text' in result:
            text = result['text']
        else:
            text = str(result)
        
        with open(transcript_file, "w") as f:
            f.write(text)
        return transcript_file

    def create_transcript_content(self, audio_file, json_file, youtube_url):
        with open(json_file, 'r') as f:
            data = json.load(f)
            title = data.get('title', 'Unknown Title')
            author = data.get('uploader', 'Unknown Author')
            description = data.get('description', 'No Description')

        transcript_file = self.transcribe_audio(audio_file)

        with open(transcript_file, 'r') as f:
            transcript_content = f.read()

        full_content = (
            f"The following text is the transcript of a YouTube video. The video title is \"{title}\" from {youtube_url}\n"
            f"The author is: {author}\n"
            f"The video description is: {description}\n\n"
            f"The following text is the transcript of the video:\n\n"
            f"{transcript_content}"
        )
        
        # Clean the title to create a safe file name
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:50]
        
        full_content_file = os.path.join(f"{self.work_directory}/{safe_title}_transcript.txt")
        with open(full_content_file, 'w') as f:
            f.write(full_content)

        return full_content_file
