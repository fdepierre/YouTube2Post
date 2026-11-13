"""
Audio Transcription Module
-------------------------
This module handles the transcription of audio files using the Faster Whisper model.
It provides functionality to convert speech to text and format the output with
metadata from the source video.
"""

import contextlib
import json
import os
import re
import time

try:
    from .device_selector import add_cuda_library_dirs
except ImportError:  # imported as a top-level module (tests add modules/ to sys.path)
    from device_selector import add_cuda_library_dirs
add_cuda_library_dirs()  # before faster-whisper loads CTranslate2 (Windows GPU)

from faster_whisper import BatchedInferencePipeline, WhisperModel
from faster_whisper.utils import download_model

try:
    from .device_selector import select_device, save_result
    from .progress import Spinner
    from . import ui
except ImportError:  # imported as a top-level module (tests add modules/ to sys.path)
    from device_selector import select_device, save_result
    from progress import Spinner
    import ui


def _model_is_downloaded(model_name):
    """True if the Whisper model is already on disk (no download needed)."""
    if os.path.isdir(model_name):
        return True
    try:
        download_model(model_name, local_files_only=True)
        return True
    except Exception:
        return False


def _hms(seconds):
    """Format seconds as m:ss or h:mm:ss."""
    seconds = int(seconds)
    h, rest = divmod(seconds, 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


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

    def __init__(self, model_name=None, work_directory='.', announce=True):
        """
        Initialize the Transcriber with specified model and working directory.

        Args:
            model_name (str, optional): Whisper model to use on every device.
                If None, GPU_MODEL is used on GPU and CPU_MODEL on CPU.
            work_directory (str): Directory for storing output files
            announce (bool): Print the device and model in use (the caller
                may prefer to show them itself)
        """
        self.requested_model = model_name
        self.work_directory = work_directory
        # Duration (s) and language of the last transcribed audio
        self.audio_duration, self.language = 0, None
        # Use the GPU only if a one-time test proved it works; CPU otherwise
        device, compute_type = select_device()
        try:
            self._load(device, compute_type)
        except Exception as e:
            if device == 'cpu':
                raise
            # GPU worked before but not now (driver/library change): fall back to CPU
            ui.warn(f"GPU initialisation failed ({e}); falling back to CPU.")
            save_result('cpu')
            self._load('cpu', 'int8')
        if announce:
            print(f"Using device: {self.device} (model: {self.model_name})")

    def _load(self, device, compute_type):
        """Load the Whisper model suited to the device."""
        self.device, self.compute_type = device, compute_type
        self.model_name = self.requested_model or (
            self.GPU_MODEL if device == 'cuda' else self.CPU_MODEL
        )
        # Loading takes a few seconds: show a spinner. On the first run the
        # model is downloaded instead, with Hugging Face's own progress bars.
        if _model_is_downloaded(self.model_name):
            waiting = Spinner(f"Loading {self.model_name} on {device.upper()}...")
        else:
            print(f"  Downloading the {self.model_name} model (only the first time)...")
            waiting = contextlib.nullcontext()
        with waiting:
            self.model = WhisperModel(self.model_name, device=device, compute_type=compute_type)
        # Batched inference transcribes several audio chunks at once:
        # measured ~4x faster on GPU and ~2x faster on CPU, with the same output.
        self.pipeline = BatchedInferencePipeline(model=self.model)

    def _transcribe_text(self, audio_file):
        with Spinner("Preparing audio (decoding, speech and language detection)...") as spinner:
            segments, info = self.pipeline.transcribe(audio_file, batch_size=self.BATCH_SIZE)
            spinner.stop(keep=f"  Audio prepared in {_hms(time.monotonic() - spinner.start)}")
        duration = getattr(info, 'duration', 0) or 0
        self.audio_duration, self.language = duration, getattr(info, 'language', None)
        if duration:
            print(f"  Transcribing {_hms(duration)} of audio (language: {getattr(info, 'language', '?')})...")

        # Segments are generated lazily, batch by batch (errors also surface
        # here, not in transcribe()). The spinner redraws the progress line
        # continuously from the position of the last segment received.
        # The remaining time is estimated when a batch arrives, then counts
        # down until the next one (instead of growing while waiting for it).
        state = {'position': 0.0, 'eta': None, 'at': 0.0}

        def progress(elapsed):
            if not duration:
                return f"elapsed {_hms(elapsed)}"
            done = min(state['position'] / duration, 1.0)
            line = f"{done:4.0%}  {_hms(state['position'])} / {_hms(duration)}  elapsed {_hms(elapsed)}"
            if state['eta'] is not None:
                line += f"  remaining ~{_hms(max(state['eta'] - (elapsed - state['at']), 0))}"
            return line

        texts = []
        with Spinner(progress) as spinner:
            for segment in segments:
                texts.append(segment.text)
                elapsed = time.monotonic() - spinner.start
                state['position'] = segment.end
                done = min(segment.end / duration, 1.0) if duration else 0
                if done > 0.02:
                    state['eta'], state['at'] = elapsed / done - elapsed, elapsed
        return " ".join(texts)

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
            ui.warn(f"GPU transcription failed ({e}); retrying on CPU.")
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
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            title = data.get('title', 'Unknown Title')
            author = data.get('uploader', 'Unknown Author')
            description = data.get('description', 'No Description')

        # Generate the transcript
        transcript_file = self.transcribe_audio(audio_file)

        # Read the transcript content
        with open(transcript_file, 'r', encoding='utf-8') as f:
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
