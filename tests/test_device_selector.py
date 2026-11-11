import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))

import device_selector as ds


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
        with patch.object(ds, "gpu_works") as probe:
            os.environ["YT2POST_DEVICE"] = "cpu"
            self.assertEqual(ds.select_device(), ds.CPU)
            os.environ["YT2POST_DEVICE"] = "cuda"
            self.assertEqual(ds.select_device(), ds.CUDA)
            probe.assert_not_called()

    def test_first_run_probes_and_caches(self):
        with patch.object(ds, "gpu_works", return_value=True) as probe:
            self.assertEqual(ds.select_device(), ds.CUDA)
            self.assertEqual(ds.select_device(), ds.CUDA)
            probe.assert_called_once()  # second call uses the cache

    def test_gpu_failure_selects_cpu(self):
        with patch.object(ds, "gpu_works", return_value=False):
            self.assertEqual(ds.select_device(), ds.CPU)

    def test_cache_from_other_environment_is_ignored(self):
        ds.save_result("cuda")
        with patch.object(ds, "_fingerprint", return_value={"host": "other", "python": "x", "ctranslate2": "0"}), \
             patch.object(ds, "gpu_works", return_value=False) as probe:
            self.assertEqual(ds.select_device(), ds.CPU)
            probe.assert_called_once()

    def test_unwritable_cache_does_not_fail(self):
        with patch.object(ds, "CACHE_FILE", "/proc/nonexistent/device.json"), \
             patch.object(ds, "gpu_works", return_value=False):
            self.assertEqual(ds.select_device(), ds.CPU)


if __name__ == '__main__':
    unittest.main()
