"""
Device Selector Module
----------------------
Chooses the device (CPU or CUDA GPU) used by Faster Whisper.

CPU always works, so it is the safe default. On the first run on a given
machine/environment, a short GPU test is performed: a tiny Whisper model is
loaded on CUDA and transcribes one second of silence. The test runs in a
separate process so that a broken CUDA install (missing cuBLAS/cuDNN, driver
mismatch, crash) can never take the main program down.

The result is cached in ~/.cache/yt2post/device.json and reused on later runs.
The cache is tied to the machine and Python environment, so the test runs again
automatically if either changes. Delete the cache file to force a new test.

Set the environment variable YT2POST_DEVICE=cpu (or cuda) to skip detection.
"""

import json
import os
import platform
import subprocess
import sys

CACHE_FILE = os.path.join(os.path.expanduser("~"), ".cache", "yt2post", "device.json")

CPU = ("cpu", "int8")
CUDA = ("cuda", "float16")

# Runs in a child process: exit code 0 means faster-whisper works on the GPU.
_PROBE_CODE = """
import numpy as np
from faster_whisper import WhisperModel
model = WhisperModel("tiny", device="cuda", compute_type="float16")
segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32))
list(segments)
"""


def _fingerprint():
    """Identify the machine + Python environment the cached result applies to."""
    try:
        import ctranslate2
        ct2_version = ctranslate2.__version__
    except ImportError:
        ct2_version = None
    return {
        "host": platform.node(),
        "python": sys.executable,
        "ctranslate2": ct2_version,
    }


def _read_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_result(device):
    """Store the chosen device for this machine/environment."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"device": device, **_fingerprint()}, f, indent=2)
    except OSError:
        pass  # Caching is an optimisation only; never fail because of it.


def gpu_works(timeout=180):
    """Return True if faster-whisper can actually transcribe on CUDA."""
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() == 0:
            return False
    except Exception:
        return False
    try:
        result = subprocess.run(
            [sys.executable, "-c", _PROBE_CODE],
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def select_device():
    """
    Return (device, compute_type) for WhisperModel.

    Order: YT2POST_DEVICE override, then cached result, then a one-time GPU test.
    """
    forced = os.environ.get("YT2POST_DEVICE", "").strip().lower()
    if forced == "cpu":
        return CPU
    if forced == "cuda":
        return CUDA

    cache = _read_cache()
    if cache and all(cache.get(k) == v for k, v in _fingerprint().items()):
        return CUDA if cache.get("device") == "cuda" else CPU

    print("First run on this computer: testing whether the GPU can be used for transcription...")
    device = "cuda" if gpu_works() else "cpu"
    print(f"GPU test result: {'GPU available' if device == 'cuda' else 'GPU not usable, using CPU'} "
          f"(saved in {CACHE_FILE})")
    save_result(device)
    return CUDA if device == "cuda" else CPU
