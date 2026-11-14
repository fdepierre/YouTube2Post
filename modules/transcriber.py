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
    from .sysinfo import LoadMonitor
except ImportError:  # imported as a top-level module (tests add modules/ to sys.path)
    from device_selector import select_device, save_result
    from progress import Spinner
    import ui
    from sysinfo import LoadMonitor


def _model_is_downloaded(model_name):
    """True if the Whisper model is already on disk (no download needed)."""
    if os.path.isdir(model_name):
        return True
    try:
        download_model(model_name, local_files_only=True)
        return True
    except Exception:
        return False


class ModelDownloadError(Exception):
    """The Whisper model could not be downloaded (network problem, not the GPU)."""


def _get_model(model_name, attempts=2):
    """Return the local path of the model, downloading it if needed (one retry)."""
    if os.path.isdir(model_name):
        return model_name
    if _model_is_downloaded(model_name):
        return download_model(model_name, local_files_only=True)
    print(f"  Downloading the {model_name} model (only the first time)...")
    for attempt in range(attempts):
        try:
            return download_model(model_name)  # resumes a partial download
        except Exception as e:
            reason = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
            if attempt + 1 < attempts:
                ui.warn(f"  Download interrupted ({reason}); trying again...")
            else:
                raise ModelDownloadError(reason) from e


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
        except ModelDownloadError as e:
            if device == 'cpu':
                raise
            # A network problem says nothing about the GPU: keep it for next time
            ui.warn(f"Could not download the {self.model_name} model ({e}); "
                    "using the CPU this time, the download will be tried again next time.")
            self._load('cpu', 'int8')
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
        # The first time, the model is downloaded (with Hugging Face's own
        # progress bars); loading it then takes a few seconds: show a spinner.
        model_path = _get_model(self.model_name)
        with Spinner(f"Loading {self.model_name} on {device.upper()}..."), LoadMonitor() as load:
            self.model = WhisperModel(model_path, device=device, compute_type=compute_type)
        if ui.verbose:
            import ctranslate2
            size = sum(os.path.getsize(os.path.join(root, name))
                       for root, _, names in os.walk(model_path) for name in names)
            ui.detail(f"Model files ({size / 1024 ** 3:.2f} GB): {model_path}")
            ui.detail(f"Precision {compute_type}, CTranslate2 {ctranslate2.__version__}"
                      + (f", {ctranslate2.get_cuda_device_count()} CUDA GPU(s)"
                         if device == 'cuda' else f", {os.cpu_count()} CPU threads available"))
            load.report()
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
        started = time.monotonic()
        with Spinner(progress) as spinner, LoadMonitor() as load:
            for segment in segments:
                texts.append(segment.text)
                elapsed = time.monotonic() - spinner.start
                state['position'] = segment.end
                done = min(segment.end / duration, 1.0) if duration else 0
                if done > 0.02:
                    state['eta'], state['at'] = elapsed / done - elapsed, elapsed
        if ui.verbose:
            self._transcription_details(info, duration, len(texts), time.monotonic() - started)
            load.report()
        return " ".join(texts)

    def _transcription_details(self, info, duration, segments, took):
        """Show the language confidence, speech share, segments and speed."""
        probability = getattr(info, 'language_probability', None)
        if isinstance(probability, (int, float)):
            ui.detail(f"Language {self.language} detected with {probability:.0%} confidence")
        speech = getattr(info, 'duration_after_vad', None)
        if duration and isinstance(speech, (int, float)):
            ui.detail(f"Speech kept after silence removal: {_hms(speech)} of {_hms(duration)} "
                      f"({speech / duration:.0%})")
        ui.detail(f"{segments} segments, batches of {self.BATCH_SIZE}"
                  + (f", {duration / took:.0f}x faster than real time" if duration and took else ""))

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
