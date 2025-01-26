"""
Audio Transcription Module
-------------------------
This module handles the transcription of audio files using the Faster Whisper model.
It provides functionality to convert speech to text and format the output with
metadata from the source video.
"""

import json
import os
import re
import torch
from faster_whisper import WhisperModel

class Transcriber:
    """
    A class to handle audio transcription using Faster Whisper.
    
    This class provides methods to transcribe audio files and create formatted
    transcript content that includes video metadata.
    
    Attributes:
        model_name (str): Name of the Whisper model to use (default: 'base')
        work_directory (str): Directory for storing output files
        device (str): Computing device to use (CPU/CUDA)
        compute_type (str): Computation type for the model
    """

    def __init__(self, model_name='base', work_directory='.'):
        """
        Initialize the Transcriber with specified model and working directory.
        
        Args:
            model_name (str): Name of the Whisper model to use
            work_directory (str): Directory for storing output files
        """
        self.model_name = model_name
        self.work_directory = work_directory
        # Force CPU usage to avoid CUDA compatibility issues
        self.device = 'cpu'
        self.compute_type = "int8"
        print(f"Using device: {self.device} (forced to avoid CUDA issues)")
        # Initialize the model in constructor
        self.model = WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)

    def transcribe_audio(self, audio_file):
        """
        Transcribe an audio file to text using Faster Whisper.
        
        Args:
            audio_file (str): Path to the audio file to transcribe
            
        Returns:
            str: Path to the generated transcript file
        """
        # Transcribe the audio
        segments, _ = self.model.transcribe(audio_file)
        transcript_file = f"{audio_file}.txt"
        
        # Combine all segments into one text
        text = " ".join([segment.text for segment in segments])
        
        # Write the transcript to a file with UTF-8 encoding
        with open(transcript_file, "w", encoding='utf-8') as f:
            f.write(text)
        return transcript_file

    def create_transcript_content(self, audio_file, json_file, youtube_url):
        """
        Create a formatted transcript that includes video metadata.
        
        Args:
            audio_file (str): Path to the audio file
            json_file (str): Path to the JSON file containing video metadata
            youtube_url (str): URL of the source YouTube video
            
        Returns:
            str: Path to the final transcript file with metadata
        """
        # Read metadata from JSON file
        with open(json_file, 'r') as f:
            data = json.load(f)
            title = data.get('title', 'Unknown Title')
            author = data.get('uploader', 'Unknown Author')
            description = data.get('description', 'No Description')

        # Generate the transcript
        transcript_file = self.transcribe_audio(audio_file)

        # Read the transcript content
        with open(transcript_file, 'r') as f:
            transcript_content = f.read()

        # Create the full content with metadata
        full_content = (
            f"The following text is the transcript of a YouTube video. The video title is \"{title}\" from {youtube_url}\n"
            f"The author is: {author}\n"
            f"The video description is: {description}\n\n"
            f"The following text is the transcript of the video:\n\n"
            f"{transcript_content}"
        )
        
        # Create a safe filename from the title
        safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', title)[:50]
        
        # Write the full content to a new file in the work directory
        final_transcript_file = os.path.join(self.work_directory, f"{safe_title}_transcript.txt")
        with open(final_transcript_file, "w", encoding='utf-8') as f:
            f.write(full_content)
            
        return final_transcript_file
