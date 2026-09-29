import unittest
from detector import BurstDetector


class BurstDetectorTests(unittest.TestCase):
    def test_fast_burst_alerts_once(self):
        detector = BurstDetector()
        alerts = [detector.observe(i * 0.03) for i in range(20)]
        self.assertEqual(sum(a is not None for a in alerts), 1)
        self.assertGreater(alerts[11].keys_per_second, 18)

    def test_slow_typing_does_not_alert(self):
        detector = BurstDetector()
        self.assertTrue(all(detector.observe(i * 0.2) is None for i in range(30)))

    def test_new_burst_after_cooldown(self):
        detector = BurstDetector()
        alerts = [detector.observe(i * 0.03) for i in range(15)]
        alerts += [detector.observe(4 + i * 0.03) for i in range(15)]
        self.assertEqual(sum(a is not None for a in alerts), 2)

    def test_same_timestamp_no_rate_claim(self):
        detector = BurstDetector()
        self.assertTrue(all(detector.observe(0.0) is None for _ in range(15)))

    def test_non_monotonic_rejected(self):
        detector = BurstDetector()
        detector.observe(2.0)
        with self.assertRaises(ValueError):
            detector.observe(1.0)


if __name__ == "__main__":
    unittest.main()
