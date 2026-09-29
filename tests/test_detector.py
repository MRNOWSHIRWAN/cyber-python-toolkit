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

    def test_custom_thresholds_change_alerting(self):
        # Six presses at 20 keys/sec: defaults stay silent, a looser rule flags it.
        default = BurstDetector()
        loose = BurstDetector(min_keys=6, min_rate=10.0)
        stamps = [i * 0.05 for i in range(6)]
        self.assertTrue(all(default.observe(t) is None for t in stamps))
        self.assertIsNotNone([loose.observe(t) for t in stamps][-1])

    def test_invalid_config_rejected(self):
        with self.assertRaises(ValueError):
            BurstDetector(window_seconds=0)
        with self.assertRaises(ValueError):
            BurstDetector(min_keys=1)
        with self.assertRaises(ValueError):
            BurstDetector(min_rate=0)
        with self.assertRaises(ValueError):
            BurstDetector(cooldown_seconds=-0.5)


if __name__ == "__main__":
    unittest.main()
