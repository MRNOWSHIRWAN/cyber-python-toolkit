import io
import json
import unittest
from contextlib import redirect_stdout

import monitor


def run_demo(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = monitor.main(["--demo", *argv])
    lines = buf.getvalue().splitlines()
    alerts = [json.loads(line) for line in lines if line.startswith("{")]
    return code, lines, alerts


class MonitorCliTests(unittest.TestCase):
    def test_demo_default_rule_alerts_once(self):
        code, lines, alerts = run_demo([])
        self.assertEqual(code, 0)
        self.assertEqual(len(alerts), 1)

    def test_rule_line_printed(self):
        code, lines, alerts = run_demo([])
        self.assertTrue(any(line.startswith("Rule: 12+ presses") for line in lines))

    def test_looser_rule_alerts_earlier(self):
        code, lines, alerts = run_demo(["--min-keys", "5"])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["key_count"], 5)

    def test_impossible_rate_suppresses_alert(self):
        code, lines, alerts = run_demo(["--min-rate", "100"])
        self.assertEqual(alerts, [])

    def test_zero_cooldown_allows_repeated_alerts(self):
        code, lines, alerts = run_demo(["--cooldown", "0"])
        self.assertGreater(len(alerts), 1)

    def test_invalid_values_rejected(self):
        for bad in (["--window", "0"], ["--min-keys", "1"],
                    ["--min-rate", "-3"], ["--cooldown", "-1"]):
            with self.assertRaises(SystemExit) as ctx:
                with redirect_stdout(io.StringIO()):
                    monitor.main(["--demo", *bad])
            self.assertEqual(ctx.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
