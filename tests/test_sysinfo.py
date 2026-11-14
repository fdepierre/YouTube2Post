import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import sysinfo
import ui

GPU = 'NVIDIA GeForce RTX 2060 with Max-Q Design, 6144, 5240, 621.14, 57.30, 25'


class TestGpuStatus(unittest.TestCase):
    def test_parses_nvidia_smi(self):
        with patch.object(sysinfo.shutil, 'which', return_value='/usr/bin/nvidia-smi'), \
             patch.object(sysinfo, '_run', return_value=GPU):
            gpu = sysinfo.gpu_status()
        self.assertEqual(gpu['name'], 'NVIDIA GeForce RTX 2060 with Max-Q Design')
        self.assertEqual((gpu['memory.total'], gpu['temperature.gpu']), (6144.0, 57.3))

    def test_no_nvidia_smi(self):
        with patch.object(sysinfo.shutil, 'which', return_value=None):
            self.assertIsNone(sysinfo.gpu_status())


class TestSystemDetails(unittest.TestCase):
    def test_lines_on_this_computer(self):
        lines = sysinfo.system_details()
        self.assertTrue(lines[1].startswith('CPU: '))
        self.assertTrue(any(l.startswith('GPU: ') for l in lines))


class TestLoadMonitor(unittest.TestCase):
    def test_disabled_without_verbose(self):
        with patch.object(ui, 'verbose', False):
            with sysinfo.LoadMonitor() as load:
                pass
        self.assertEqual(load.lines(), [])

    def test_cpu_and_gpu_lines(self):
        samples = iter([{'utilization.gpu': 80.0, 'memory.used': 4000.0, 'memory.total': 6144.0,
                         'temperature.gpu': 70.0},
                        {'utilization.gpu': 100.0, 'memory.used': 4200.0, 'memory.total': 6144.0,
                         'temperature.gpu': 74.0}])
        with patch.object(ui, 'verbose', True), \
             patch.object(sysinfo.shutil, 'which', return_value='/usr/bin/nvidia-smi'), \
             patch.object(sysinfo, 'gpu_status', side_effect=lambda: next(samples, None)):
            with sysinfo.LoadMonitor(interval=0.01) as load:
                end = time.monotonic() + 0.1
                while time.monotonic() < end:  # keep a CPU thread busy
                    pass
        cpu, gpu = load.lines()
        self.assertRegex(cpu, r'^CPU: \d\.\d of \d+ threads busy on average')
        self.assertEqual(gpu, 'GPU: 90% busy on average (peak 100%), memory peak 4.1 of 6.0 GB, '
                              '74°C max (whole card)')


if __name__ == '__main__':
    unittest.main()
