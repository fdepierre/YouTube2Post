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
from faster_whisper import BatchedInferencePipeline, WhisperModel

try:
    from .device_selector import select_device, save_result
except ImportError:  # imported as a top-level module (tests add modules/ to sys.path)
    from device_selector import select_device, save_result

class Transcriber:
    """
    A class to handle audio transcription using Faster Whisper.
    
    This class provides methods to transcribe audio files and create formatted
    transcript content that includes video metadata.
    
    Attributes:
        model_name (str): Name of the Whisper model in use (chosen per device
            unless given explicitly)
        work_directory (str): Directory for storing output files
        device (str): Computing device to use (CPU/CUDA)
        compute_type (str): Computation type for the model
    """

    BATCH_SIZE = 16
    # The GPU can afford the much more accurate model (18 min of audio in ~30 s
    # on an RTX 2060, ~4 GB VRAM); on CPU it would be several times slower, so
    # CPUs keep the fast 'base' model.
    GPU_MODEL = 'large-v3-turbo'
    CPU_MODEL = 'base'

    def __init__(self, model_name=None, work_directory='.'):
        """
        Initialize the Transcriber with specified model and working directory.

        Args:
            model_name (str, optional): Whisper model to use on every device.
                If None, GPU_MODEL is used on GPU and CPU_MODEL on CPU.
            work_directory (str): Directory for storing output files
        """
        self.requested_model = model_name
        self.work_directory = work_directory
        # Use the GPU only if a one-time test proved it works; CPU otherwise
        device, compute_type = select_device()
        try:
            self._load(device, compute_type)
        except Exception as e:
            if device == 'cpu':
                raise
            # GPU worked before but not now (driver/library change): fall back to CPU
            print(f"GPU initialisation failed ({e}); falling back to CPU.")
            save_result('cpu')
            self._load('cpu', 'int8')
        print(f"Using device: {self.device} (model: {self.model_name})")

    def _load(self, device, compute_type):
        """Load the Whisper model suited to the device."""
        self.device, self.compute_type = device, compute_type
        self.model_name = self.requested_model or (
            self.GPU_MODEL if device == 'cuda' else self.CPU_MODEL
        )
        self.model = WhisperModel(self.model_name, device=device, compute_type=compute_type)
        # Batched inference transcribes several audio chunks at once:
        # measured ~4x faster on GPU and ~2x faster on CPU, with the same output.
        self.pipeline = BatchedInferencePipeline(model=self.model)

    def _transcribe_text(self, audio_file):
        segments, _ = self.pipeline.transcribe(audio_file, batch_size=self.BATCH_SIZE)
        # Segments are generated lazily: errors surface while joining them
        return " ".join(segment.text for segment in segments)

    def transcribe_audio(self, audio_file):
        """
        Transcribe an audio file to text using Faster Whisper.

        Args:
            audio_file (str): Path to the audio file to transcribe

        Returns:
            str: Path to the generated transcript file
        """
        try:
            text = self._transcribe_text(audio_file)
        except Exception as e:
            if self.device == 'cpu':
                raise
            # e.g. a GPU with too little memory for the large model
            print(f"GPU transcription failed ({e}); retrying on CPU.")
            del self.pipeline, self.model
            self._load('cpu', 'int8')
            print(f"Using device: {self.device} (model: {self.model_name})")
            text = self._transcribe_text(audio_file)
        transcript_file = f"{audio_file}.txt"
        
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
