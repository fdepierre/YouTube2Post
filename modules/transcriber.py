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

from .device_selector import add_cuda_library_dirs, select_device, save_result
from .progress import Spinner
from . import ui
from .sysinfo import LoadMonitor

add_cuda_library_dirs()  # before faster-whisper loads CTranslate2 (GPU libraries from pip)

from faster_whisper import BatchedInferencePipeline, WhisperModel  # noqa: E402
from faster_whisper.utils import download_model  # noqa: E402


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


# The remaining time is overestimated on purpose: better to finish early
# than to show '0:00' while the work goes on.
ETA_MARGIN = 1.25


def remaining_estimate(elapsed, done, batch_time=0.0):
    """
    Estimate the seconds left when a `done` fraction took `elapsed` seconds:
    the linear estimate with a margin, and at least the time of one more
    batch while the work is not finished (progress comes batch by batch).
    """
    if done >= 1:
        return 0.0
    linear = elapsed / done - elapsed
    return max(linear, batch_time) * ETA_MARGIN


def next_countdown(shown, estimate):
    """
    The remaining time to show when a new estimate arrives while `shown` is
    displayed: the countdown never goes back up (it shows 'finishing...' if
    it reaches 0 first), unless the work clearly slowed down.
    """
    shown = max(shown, 0)
    if estimate > shown * 1.5 + 10:
        return estimate
    return min(estimate, shown)


def whisper_language(code):
    """
    The Whisper language for a language code from YouTube ('fr-FR' -> 'fr'),
    or None if there is none or Whisper does not know it.
    """
    from faster_whisper.tokenizer import _LANGUAGE_CODES
    base = (code or '').split('-')[0].split('_')[0].lower()
    return base if base in _LANGUAGE_CODES else None


def safe_file_name(title):
    """
    A file name safe on every system: letters (accents included), digits, '_'
    and '-' only, so a title cannot contain a path ('../', 'C:\\').
    """
    return re.sub(r'[^\w\-]', '_', title)[:50].strip('_') or 'transcript'


def transcript_path(work_directory, title, suffix='_transcript.txt'):
    """The path of the transcript file for a video or playlist title."""
    return os.path.join(work_directory, safe_file_name(title) + suffix)


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
        self.audio_duration, self.language, self.language_given = 0, None, False
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

    # Without a known language, it is detected on several 30 s pieces of the
    # audio, not only the first one: a French video detected as English is
    # transcribed translated into English
    DETECTION_SEGMENTS = 3

    def _transcribe_text(self, audio_file, language=None):
        """Transcribe the audio, in `language` if known (else it is detected)."""
        task = "speech detection" if language else "speech and language detection"
        with Spinner(f"Preparing audio (decoding, {task})...") as spinner:
            segments, info = self.pipeline.transcribe(
                audio_file, batch_size=self.BATCH_SIZE, language=language,
                language_detection_segments=self.DETECTION_SEGMENTS)
            spinner.stop(keep=f"  Audio prepared in {ui.clock(time.monotonic() - spinner.start)}")
        self.language_given = language is not None
        duration = getattr(info, 'duration', 0) or 0
        self.audio_duration, self.language = duration, getattr(info, 'language', None)
        if duration:
            print(f"  Transcribing {ui.clock(duration)} of audio (language: {getattr(info, 'language', '?')})...")

        # Segments are generated lazily, batch by batch (errors also surface
        # here, not in transcribe()). The spinner redraws the progress line
        # continuously from the position of the last segment received.
        # The remaining time is estimated once a whole batch has arrived (its
        # segments come one by one within a few milliseconds), then counts
        # down until the next one.
        state = {'position': 0.0, 'eta': None, 'at': 0.0, 'pending': None,
                 'batch_at': None, 'last': 0.0, 'batch_time': 0.0}

        def update_estimate(elapsed):
            pending = state['pending']
            if pending is None or elapsed - state['last'] < 0.15:
                return  # no new batch, or its segments are still arriving
            state['pending'] = None
            at, done, batch_time = pending
            estimate = remaining_estimate(at, done, batch_time)
            if state['eta'] is not None:
                estimate = next_countdown(state['eta'] - (at - state['at']), estimate)
            state['eta'], state['at'] = estimate, at

        def progress(elapsed):
            if not duration:
                return f"elapsed {ui.clock(elapsed)}"
            update_estimate(elapsed)
            done = min(state['position'] / duration, 1.0)
            line = f"{done:4.0%}  {ui.clock(state['position'])} / {ui.clock(duration)}  elapsed {ui.clock(elapsed)}"
            if state['eta'] is not None:
                left = state['eta'] - (elapsed - state['at'])
                # Longer than estimated (the GPU slows down as it heats up):
                # no '~0:00' while the work goes on
                line += f"  remaining ~{ui.clock(left)}" if left >= 1 else "  finishing..."
            return line

        texts = []
        started = time.monotonic()
        with Spinner(progress) as spinner, LoadMonitor() as load:
            for segment in segments:
                texts.append(segment.text)
                elapsed = time.monotonic() - started
                # The segments of a batch arrive together: a gap starts a new batch
                if state['batch_at'] is None or elapsed - state['last'] > 0.5:
                    if state['batch_at'] is not None:
                        state['batch_time'] = elapsed - state['batch_at']
                    state['batch_at'] = elapsed
                state['last'] = elapsed
                state['position'] = segment.end
                done = min(segment.end / duration, 1.0) if duration else 0
                if done > 0.02:
                    state['pending'] = (elapsed, done, state['batch_time'])
        if ui.verbose:
            self._transcription_details(info, duration, len(texts), time.monotonic() - started)
            load.report()
        return " ".join(texts)

    def _transcription_details(self, info, duration, segments, took):
        """Show the language confidence, speech share, segments and speed."""
        probability = getattr(info, 'language_probability', None)
        if self.language_given:
            ui.detail(f"Language {self.language} given by YouTube for this audio track")
        elif isinstance(probability, (int, float)):
            ui.detail(f"Language {self.language} detected with {probability:.0%} confidence")
        speech = getattr(info, 'duration_after_vad', None)
        if duration and isinstance(speech, (int, float)):
            ui.detail(f"Speech kept after silence removal: {ui.clock(speech)} of {ui.clock(duration)} "
                      f"({speech / duration:.0%})")
        ui.detail(f"{segments} segments, batches of {self.BATCH_SIZE}"
                  + (f", {duration / took:.0f}x faster than real time" if duration and took else ""))

    def transcribe_audio(self, audio_file, language=None):
        """
        Transcribe an audio file to text using Faster Whisper.

        Args:
            audio_file (str): Path to the audio file to transcribe
            language (str, optional): Whisper language code ('fr'), if known

        Returns:
            str: The transcript text
        """
        try:
            return self._transcribe_text(audio_file, language)
        except Exception as e:
            if self.device == 'cpu':
                raise
            # e.g. a GPU with too little memory for the large model
            ui.warn(f"GPU transcription failed ({e}); retrying on CPU.")
            del self.pipeline, self.model
            self._load('cpu', 'int8')
            print(f"Using device: {self.device} (model: {self.model_name})")
            return self._transcribe_text(audio_file, language)

    def transcript(self, audio_file, json_file, youtube_url):
        """
        Transcribe the audio and return (title, text): the transcript preceded
        by the video's metadata (title, URL, author, description).
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        title = data.get('title', 'Unknown Title')
        author = data.get('uploader', 'Unknown Author')
        description = data.get('description', 'No Description')

        # The language YouTube gives for the downloaded audio track is more
        # reliable than Whisper's detection (a French video with an English
        # word or music at the start was transcribed translated into English)
        transcript_content = self.transcribe_audio(audio_file, whisper_language(data.get('language')))
        return title, (
            f"The following text is the transcript of a YouTube video. The video title is \"{title}\" from {youtube_url}\n"
            f"The author is: {author}\n"
            f"The video description is: {description}\n\n"
            f"The following text is the transcript of the video:\n\n"
            f"{transcript_content}"
        )

    def create_transcript_content(self, audio_file, json_file, youtube_url):
        """
        Transcribe the audio and write the transcript, with the video's
        metadata, to <title>_transcript.txt in the work directory.

        Returns:
            str: Path to the transcript file
        """
        title, content = self.transcript(audio_file, json_file, youtube_url)
        path = transcript_path(self.work_directory, title)
        with open(path, "w", encoding='utf-8') as f:
            f.write(content)
        return path
