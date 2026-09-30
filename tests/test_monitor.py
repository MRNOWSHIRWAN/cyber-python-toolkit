import io
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

import monitor


def run_demo(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = monitor.main(["--demo", *argv])
    lines = out.getvalue().splitlines()
    alerts = [json.loads(line) for line in lines if line.startswith("{")]
    return code, lines, alerts, err.getvalue()


class MonitorCliTests(unittest.TestCase):
    def test_demo_default_rule_alerts_once(self):
        code, lines, alerts, err = run_demo([])
        self.assertEqual(code, 0)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(lines), 1)
        self.assertIn("15 presses processed, 1 alerts emitted", err)

    def test_rule_line_printed_on_stderr(self):
        code, lines, alerts, err = run_demo([])
        self.assertIn("Rule: 12+ presses", err)
        self.assertTrue(all(line.startswith("{") for line in lines))

    def test_looser_rule_alerts_earlier(self):
        code, lines, alerts, err = run_demo(["--min-keys", "5"])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["key_count"], 5)

    def test_impossible_rate_suppresses_alert(self):
        code, lines, alerts, err = run_demo(["--min-rate", "100"])
        self.assertEqual(alerts, [])
        self.assertIn("0 alerts emitted", err)

    def test_zero_cooldown_allows_repeated_alerts(self):
        code, lines, alerts, err = run_demo(["--cooldown", "0"])
        self.assertEqual(len(alerts), 4)
        self.assertIn("4 alerts emitted", err)

    def test_invalid_values_rejected(self):
        for bad in (["--window", "0"], ["--min-keys", "1"],
                    ["--min-rate", "-3"], ["--cooldown", "-1"],
                    ["--format", "xml"]):
            with self.assertRaises(SystemExit) as ctx:
                run_demo(bad)
            self.assertEqual(ctx.exception.code, 2)

    def test_text_alert_explains_burst_without_attribution(self):
        code, lines, alerts, err = run_demo(["--format", "text"])
        self.assertEqual(code, 0)
        self.assertEqual(alerts, [])
        self.assertEqual(len(lines), 1)
        self.assertIn("12 presses in 0.330s (33.3 keys/sec)", lines[0])
        self.assertIn("not proof of malicious input", lines[0])
        self.assertIn("Session completed:", err)

    def test_text_mode_keeps_log_as_json_and_appends(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alerts.jsonl"
            run_demo(["--format", "text", "--log", str(path)])
            run_demo(["--format", "text", "--log", str(path)])
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(records), 2)
            self.assertEqual(set(records[0]), {"timestamp_utc", "window_seconds",
                             "key_count", "keys_per_second", "classification"})
            self.assertEqual(records[0]["key_count"], 12)
            if os.name == "posix":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_log_failure_returns_nonzero_and_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            code, lines, alerts, err = run_demo(["--log", directory])
        self.assertEqual(code, 2)
        self.assertIn("Output or log write failed:", err)
        self.assertIn("Session failed:", err)

    def test_summary_uses_elapsed_time_and_stderr(self):
        with patch.object(monitor.time, "monotonic", side_effect=[100.0, 102.5]):
            code, lines, alerts, err = run_demo([])
        self.assertIn("2.50s elapsed", err)

    def test_keyboard_interrupt_reports_processed_count(self):
        with patch.object(monitor.BurstDetector, "observe", side_effect=KeyboardInterrupt):
            code, lines, alerts, err = run_demo([])
        self.assertEqual(code, 0)
        self.assertIn("Session interrupted: 1 presses processed, 0 alerts emitted", err)

    def test_missing_listener_reports_failure(self):
        out, err = io.StringIO(), io.StringIO()
        with patch.dict("sys.modules", {"pynput": None}):
            with redirect_stdout(out), redirect_stderr(err):
                code = monitor.main([])
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Install pynput:", err.getvalue())
        self.assertIn("Session failed: 0 presses processed", err.getvalue())

    def test_listener_events_use_the_same_output_and_summary(self):
        class FakeListener:
            def __init__(self, on_press, suppress):
                self.on_press = on_press
                self.remaining = 15
                self.suppress = suppress
            def __enter__(self):
                for _ in range(15):
                    self.on_press(object())
                return self
            def __exit__(self, *args):
                return False
            def is_alive(self):
                self.remaining -= 1
                return self.remaining >= 0
            def join(self):
                pass
        module = types.SimpleNamespace(keyboard=types.SimpleNamespace(Listener=FakeListener))
        out, err = io.StringIO(), io.StringIO()
        with patch.dict("sys.modules", {"pynput": module}):
            with patch.object(monitor.time, "monotonic", side_effect=[0.0] +
                              [i * 0.03 for i in range(15)] + [0.5]):
                with redirect_stdout(out), redirect_stderr(err):
                    code = monitor.main(["--format", "text"])
        self.assertEqual(code, 0)
        self.assertIn("Fast typing burst:", out.getvalue())
        self.assertIn("15 presses processed, 1 alerts emitted, 0.50s elapsed", err.getvalue())


if __name__ == "__main__":
    unittest.main()
