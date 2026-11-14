import os
import tempfile
import unittest
from unittest.mock import patch

from modules import device_selector as ds


class TestDeviceSelector(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = os.path.join(self.tmp.name, "device.json")
        self.patches = [
            patch.object(ds, "CACHE_FILE", self.cache),
            patch.dict(os.environ, {}, clear=False),
        ]
        for p in self.patches:
            p.start()
        os.environ.pop("YT2POST_DEVICE", None)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_env_override_skips_detection(self):
        with patch.object(ds, "gpu_test") as probe:
            os.environ["YT2POST_DEVICE"] = "cpu"
            self.assertEqual(ds.select_device(), ds.CPU)
            os.environ["YT2POST_DEVICE"] = "cuda"
            self.assertEqual(ds.select_device(), ds.CUDA)
            probe.assert_not_called()

    def test_first_run_probes_and_caches(self):
        with patch.object(ds, "gpu_test", return_value=(True, "")) as probe:
            self.assertEqual(ds.select_device(), ds.CUDA)
            self.assertEqual(ds.select_device(), ds.CUDA)
            probe.assert_called_once()  # second call uses the cache

    def test_cache_from_other_environment_is_ignored(self):
        ds.save_result("cuda")
        with patch.object(ds, "_fingerprint", return_value={"host": "other", "python": "x", "ctranslate2": "0"}), \
             patch.object(ds, "gpu_test", return_value=(False, "no CUDA GPU found")) as probe:
            self.assertEqual(ds.select_device(), ds.CPU)
            probe.assert_called_once()

    def test_unwritable_cache_does_not_fail(self):
        with patch.object(ds, "CACHE_FILE", "/proc/nonexistent/device.json"), \
             patch.object(ds, "gpu_test", return_value=(False, "no CUDA GPU found")):
            self.assertEqual(ds.select_device(), ds.CPU)

    def test_timeout_is_not_cached(self):
        # e.g. the first load of freshly installed CUDA DLLs on Windows
        with patch.object(ds, "gpu_test", return_value=(False, "timeout")), patch("builtins.print"):
            self.assertEqual(ds.select_device(), ds.CPU)
        self.assertFalse(os.path.exists(self.cache))

    def test_gpu_failure_selects_cpu_and_shows_why(self):
        with patch.object(ds, "gpu_test", return_value=(False, "cublas64_12.dll not found")), \
             patch("builtins.print") as printed:
            self.assertEqual(ds.select_device(), ds.CPU)
        self.assertIn("cublas64_12.dll not found", printed.call_args.args[0])

    def test_installing_cuda_libraries_triggers_a_new_test(self):
        with patch.object(ds, "gpu_test", return_value=(False, "x")), patch("builtins.print"):
            ds.select_device()
        installed = dict(ds._fingerprint())
        installed["cuda_libraries"] = {"nvidia-cublas-cu12": "12.9", "nvidia-cudnn-cu12": "9.28"}
        with patch.object(ds, "_fingerprint", return_value=installed), \
             patch.object(ds, "gpu_test", return_value=(True, "")) as probe, patch("builtins.print"):
            self.assertEqual(ds.select_device(), ds.CUDA)
        probe.assert_called_once()


class TestLinuxCudaPreload(unittest.TestCase):
    def test_dependencies_loaded_in_any_order(self):
        with tempfile.TemporaryDirectory() as site:
            lib = os.path.join(site, 'nvidia', 'cublas', 'lib')
            os.makedirs(lib)
            names = ['libcublas.so.12', 'libcublasLt.so.12', 'libnvblas.so.12']
            for name in names:
                open(os.path.join(lib, name), 'w').close()
            loaded = []

            def cdll(path, mode=0):
                name = os.path.basename(path)
                # libcublas needs libcublasLt, sorted after it
                if name == 'libcublas.so.12' and 'libcublasLt.so.12' not in loaded:
                    raise OSError('libcublasLt.so.12: cannot open shared object file')
                loaded.append(name)

            with patch.object(ds, '_site_packages', return_value=[site]), patch('ctypes.CDLL', side_effect=cdll):
                self.assertEqual(ds._preload_linux_cuda_libraries(), 2)
            self.assertEqual(loaded, ['libcublasLt.so.12', 'libcublas.so.12'])  # not libnvblas

    def test_current_directory_is_not_searched(self):
        # sys.path may hold the current directory: a library planted there is not loaded
        with tempfile.TemporaryDirectory() as cwd:
            os.makedirs(os.path.join(cwd, 'nvidia', 'cublas', 'lib'))
            open(os.path.join(cwd, 'nvidia', 'cublas', 'lib', 'libcublas.so.12'), 'w').close()
            with patch.object(ds.sys, 'path', ['', cwd]), patch('os.getcwd', return_value=cwd):
                self.assertNotIn(cwd, ds._site_packages())

    def test_nothing_installed(self):
        with tempfile.TemporaryDirectory() as site, patch.object(ds, '_site_packages', return_value=[site]):
            self.assertEqual(ds._preload_linux_cuda_libraries(), 0)


if __name__ == '__main__':
    unittest.main()
