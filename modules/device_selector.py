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

The CUDA libraries faster-whisper needs (cuBLAS, cuDNN) can be installed with
pip (nvidia-cublas-cu12, nvidia-cudnn-cu12). On Windows they are not found by
default: add_cuda_library_dirs() makes them findable.
"""

import glob
import json
import os
import platform
import subprocess
import sys

try:
    from . import ui
except ImportError:  # imported as a top-level module (tests add modules/ to sys.path)
    import ui

# pip packages providing the CUDA libraries used by faster-whisper
CUDA_LIBRARY_PACKAGES = ("nvidia-cublas-cu12", "nvidia-cudnn-cu12")


def add_cuda_library_dirs():
    """
    On Windows, make the CUDA DLLs installed by pip (site-packages/nvidia/*/bin)
    findable by CTranslate2. Call before loading a model on the GPU. No effect
    elsewhere: on Linux the libraries are found through LD_LIBRARY_PATH.
    """
    if sys.platform != "win32":
        return
    for site_dir in sys.path:
        for dll_dir in glob.glob(os.path.join(site_dir, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(dll_dir)
            except OSError:
                continue
            # cuDNN loads its sub-libraries itself, through PATH
            if dll_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")

CACHE_FILE = os.path.join(os.path.expanduser("~"), ".cache", "yt2post", "device.json")

CPU = ("cpu", "int8")
CUDA = ("cuda", "float16")

# Runs in a child process: exit code 0 means faster-whisper works on the GPU.
_PROBE_CODE = """
import glob, os, sys
if sys.platform == "win32":  # same as add_cuda_library_dirs()
    for site_dir in sys.path:
        for dll_dir in glob.glob(os.path.join(site_dir, "nvidia", "*", "bin")):
            os.add_dll_directory(dll_dir)
            os.environ["PATH"] = dll_dir + os.pathsep + os.environ.get("PATH", "")
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
    # Installing the CUDA libraries later must trigger a new GPU test
    from importlib.metadata import PackageNotFoundError, version
    cuda_libraries = {}
    for package in CUDA_LIBRARY_PACKAGES:
        try:
            cuda_libraries[package] = version(package)
        except PackageNotFoundError:
            cuda_libraries[package] = None
    return {
        "host": platform.node(),
        "python": sys.executable,
        "ctranslate2": ct2_version,
        "cuda_libraries": cuda_libraries,
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


def gpu_test(timeout=300):
    """
    Test whether faster-whisper can actually transcribe on CUDA.

    Returns (works, reason): reason explains a failure in a few words, and is
    'timeout' when the test took too long (e.g. the first load of freshly
    installed CUDA libraries, scanned by an antivirus): worth trying again.
    """
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() == 0:
            return False, "no CUDA GPU found"
    except Exception as e:
        return False, f"CTranslate2 error: {e}"
    try:
        result = subprocess.run(
            [sys.executable, "-c", _PROBE_CODE],
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except OSError as e:
        return False, str(e)
    if result.returncode == 0:
        return True, ""
    lines = result.stderr.decode("utf-8", "replace").strip().splitlines()
    return False, lines[-1] if lines else f"exit code {result.returncode}"


def gpu_works(timeout=300):
    """Return True if faster-whisper can actually transcribe on CUDA."""
    return gpu_test(timeout)[0]


def select_device():
    """
    Return (device, compute_type) for WhisperModel.

    Order: YT2POST_DEVICE override, then cached result, then a one-time GPU test.
    """
    forced = os.environ.get("YT2POST_DEVICE", "").strip().lower()
    if forced in ("cpu", "cuda"):
        ui.detail(f"Device {forced} forced by YT2POST_DEVICE")
        return CPU if forced == "cpu" else CUDA

    cache = _read_cache()
    if cache and all(cache.get(k) == v for k, v in _fingerprint().items()):
        ui.detail(f"Device {cache.get('device')} from the GPU test saved in {CACHE_FILE} "
                  "(delete it to test again)")
        return CUDA if cache.get("device") == "cuda" else CPU

    print("First run on this computer: testing whether the GPU can be used for transcription...")
    works, reason = gpu_test()
    if reason == "timeout":
        # Not a verdict: the next run tests again
        print("GPU test took too long; using CPU this time, the test will run again next time.")
        return CPU
    device = "cuda" if works else "cpu"
    print(f"GPU test result: {'GPU available' if works else f'GPU not usable ({reason}), using CPU'} "
          f"(saved in {CACHE_FILE})")
    save_result(device)
    return CUDA if works else CPU
