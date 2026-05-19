import unittest

from app.main import line_indicates_slow_download, parse_transfer_rate_bytes


class DownloadMonitorTest(unittest.TestCase):
    def test_parse_transfer_rate_kib(self) -> None:
        rate = parse_transfer_rate_bytes("[download]  10.0% of 10.00MiB at 64.00KiB/s ETA 01:20")
        self.assertEqual(rate, 64 * 1024)

    def test_parse_transfer_rate_mb(self) -> None:
        rate = parse_transfer_rate_bytes("[download]  10.0% of 10.00MiB at 1.50MB/s ETA 00:10")
        self.assertEqual(rate, 1.5 * 1000 * 1000)

    def test_zero_speed_is_slow(self) -> None:
        self.assertTrue(line_indicates_slow_download("[download]   0.0% of 1.00MiB at 0.00B/s ETA Unknown", 32768))

    def test_unknown_speed_is_slow(self) -> None:
        self.assertTrue(line_indicates_slow_download("[download]   0.0% of 1.00MiB at Unknown speed ETA Unknown", 32768))

    def test_fast_speed_is_not_slow(self) -> None:
        self.assertFalse(line_indicates_slow_download("[download]  50.0% of 1.00MiB at 2.00MiB/s ETA 00:01", 32768))

    def test_non_download_line_is_not_slow(self) -> None:
        self.assertFalse(line_indicates_slow_download("[Merger] Merging formats into \"demo.mp4\"", 32768))


if __name__ == "__main__":
    unittest.main()
