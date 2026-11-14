"""
System Information Module
-------------------------
Hardware description and load measurements for the verbose mode (-v), with
no extra dependency: /proc on Linux/WSL, the registry and Win32 API on
Windows, sysctl on macOS, and nvidia-smi (installed with the NVIDIA driver)
for the GPU.
"""

import os
import platform
import shutil
import subprocess
import sys
import threading
import time

try:
    from . import ui
    from .clipboard import environment
except ImportError:  # imported as a top-level module (tests add modules/ to sys.path)
    import ui
    from clipboard import environment


def _run(args, timeout=5):
    """Return the stdout of a command, or '' if it fails."""
    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout, check=False,
                                stdin=subprocess.DEVNULL)
        return result.stdout.decode('utf-8', 'replace').strip() if result.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def _gb(num_bytes):
    return f"{num_bytes / 1024 ** 3:.1f} GB"


# --- CPU and RAM ---------------------------------------------------------------

def cpu_info():
    """Return (model name, physical cores or None, logical threads)."""
    threads = os.cpu_count() or 0
    name, cores = platform.processor() or 'unknown CPU', None
    if sys.platform.startswith('linux'):
        try:
            with open('/proc/cpuinfo', encoding='utf-8') as f:
                text = f.read()
            pairs = set()
            physical = core = None
            for line in text.splitlines():
                key, _, value = line.partition(':')
                key, value = key.strip(), value.strip()
                if key == 'model name':
                    name = value
                elif key == 'physical id':
                    physical = value
                elif key == 'core id':
                    core = value
                    pairs.add((physical, core))
            cores = len(pairs) or None
        except OSError:
            pass
    elif sys.platform == 'win32':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
            name = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
        except OSError:
            pass
    elif sys.platform == 'darwin':
        name = _run(['sysctl', '-n', 'machdep.cpu.brand_string']) or name
        cores = int(_run(['sysctl', '-n', 'hw.physicalcpu']) or 0) or None
    return ' '.join(name.split()), cores, threads


def ram_info():
    """Return (total bytes, available bytes or None), or (None, None)."""
    if sys.platform.startswith('linux'):
        values = {}
        try:
            with open('/proc/meminfo', encoding='utf-8') as f:
                for line in f:
                    key, _, value = line.partition(':')
                    values[key] = int(value.split()[0]) * 1024
        except (OSError, ValueError, IndexError):
            return None, None
        return values.get('MemTotal'), values.get('MemAvailable')
    if sys.platform == 'win32':
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullTotalPhys, status.ullAvailPhys
        return None, None
    if sys.platform == 'darwin':
        total = _run(['sysctl', '-n', 'hw.memsize'])
        return (int(total) if total.isdigit() else None), None
    return None, None


def windows_host_ram():
    """In WSL, the RAM of the Windows host (the WSL VM only gets part of it)."""
    text = _run(['powershell.exe', '-NoProfile', '-Command',
                 '(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory'])
    return int(text) if text.isdigit() else None


def process_running(name):
    """
    True if a process with this name runs here, False if not, None if unknown.
    On Linux/WSL the /proc names are read; WSL does not see Windows processes.
    """
    if sys.platform.startswith('linux'):
        try:
            entries = [e for e in os.listdir('/proc') if e.isdigit()]
        except OSError:
            return None
        for entry in entries:
            try:
                with open(f'/proc/{entry}/comm', encoding='utf-8') as f:
                    if f.read().strip() == name:
                        return True
            except OSError:
                continue
        return False
    if sys.platform == 'win32':
        text = _run(['tasklist', '/FO', 'CSV', '/NH', '/FI', f'IMAGENAME eq {name}.exe'])
        return f'"{name}.exe"'.lower() in text.lower() if text else None
    return None


# --- GPU -------------------------------------------------------------------------

_GPU_FIELDS = ('name', 'memory.total', 'memory.used', 'driver_version',
               'temperature.gpu', 'utilization.gpu')


def gpu_status():
    """Return a dict for the first NVIDIA GPU (memory in MiB), or None."""
    if not shutil.which('nvidia-smi'):
        return None
    text = _run(['nvidia-smi', f"--query-gpu={','.join(_GPU_FIELDS)}",
                 '--format=csv,noheader,nounits'])
    if not text:
        return None
    values = [v.strip() for v in text.splitlines()[0].split(',')]
    if len(values) != len(_GPU_FIELDS):
        return None
    status = dict(zip(_GPU_FIELDS, values))
    for key in ('memory.total', 'memory.used', 'temperature.gpu', 'utilization.gpu'):
        try:
            status[key] = float(status[key])
        except ValueError:
            status[key] = None
    return status


# --- Summary -----------------------------------------------------------------------

def system_details():
    """Return the lines describing the computer, for the verbose mode."""
    env = environment()
    context = {'wsl': f"WSL ({os.environ.get('WSL_DISTRO_NAME', 'Linux')})",
               'windows': 'Windows', 'macos': 'macOS', 'linux': 'Linux'}[env]
    lines = [f"{context}: {platform.system()} {platform.release()}, "
             f"Python {platform.python_version()} ({sys.executable})"]

    name, cores, threads = cpu_info()
    lines.append(f"CPU: {name}, " + (f"{cores} cores / " if cores else "") + f"{threads} threads")

    total, available = ram_info()
    if total:
        line = f"RAM: {_gb(total)}" + (f" ({_gb(available)} available)" if available else "")
        if env == 'wsl':
            host = windows_host_ram()
            line += " for the WSL VM" + (f", of {_gb(host)} on the Windows host" if host else "")
        lines.append(line)

    gpu = gpu_status()
    if gpu:
        line = f"GPU: {gpu['name']}"
        if gpu['memory.total']:
            line += f", {gpu['memory.total'] / 1024:.1f} GB memory"
            if gpu['memory.used'] is not None:
                line += f" ({gpu['memory.used'] / 1024:.1f} GB in use)"
        line += f", driver {gpu['driver_version']}"
        if gpu['temperature.gpu'] is not None:
            line += f", {gpu['temperature.gpu']:.0f}°C"
        lines.append(line)
    else:
        lines.append("GPU: no NVIDIA GPU found (nvidia-smi not available)")
    return lines


# --- Load measurements ----------------------------------------------------------

class LoadMonitor:
    """
    Measure the load during a step, in verbose mode only: the average number
    of CPU threads busy in this program, and the GPU usage, memory and
    temperature (whole card, sampled with nvidia-smi in the background).
    """

    def __init__(self, interval=0.5, cpu=True):
        self.interval = interval
        self.cpu = cpu
        self.enabled = False
        self.samples = []
        self._stop = threading.Event()
        self._thread = None

    def _sample(self):
        gpu = gpu_status()
        if gpu:
            self.samples.append(gpu)

    def _run(self):
        while not self._stop.wait(self.interval):
            self._sample()

    def __enter__(self):
        self.enabled = ui.verbose
        if self.enabled:
            self.start, self.times = time.monotonic(), os.times()
            if shutil.which('nvidia-smi'):
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
        return self

    def __exit__(self, *exc):
        if not self.enabled:
            return
        self._stop.set()
        if self._thread:
            self._thread.join()
            if not self.samples:  # step shorter than one interval
                self._sample()
        self.elapsed = time.monotonic() - self.start
        now = os.times()
        self.cpu_seconds = (now.user - self.times.user) + (now.system - self.times.system)

    def lines(self):
        """Return the measured load as detail lines."""
        if not self.enabled:
            return []
        lines = []
        if self.cpu and self.elapsed > 0:
            threads = os.cpu_count() or 0
            lines.append(f"CPU: {self.cpu_seconds / self.elapsed:.1f} of {threads} threads busy "
                         "on average (this program)")
        usage = [s['utilization.gpu'] for s in self.samples if s['utilization.gpu'] is not None]
        memory = [s['memory.used'] for s in self.samples if s['memory.used'] is not None]
        temps = [s['temperature.gpu'] for s in self.samples if s['temperature.gpu'] is not None]
        if usage:
            line = f"GPU: {sum(usage) / len(usage):.0f}% busy on average (peak {max(usage):.0f}%)"
            if memory:
                total = self.samples[0]['memory.total']
                line += f", memory peak {max(memory) / 1024:.1f}" + (
                    f" of {total / 1024:.1f} GB" if total else " GB")
            if temps:
                line += f", {max(temps):.0f}°C max"
            lines.append(line + " (whole card)")
        return lines

    def report(self):
        """Print the measured load as detail lines."""
        for line in self.lines():
            ui.detail(line)
