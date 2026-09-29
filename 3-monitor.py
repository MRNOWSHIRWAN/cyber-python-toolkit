"""Opt-in keyboard timing monitor; records no characters or key identities."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import sys
import time

from detector import BurstDetector


def write_alert(alert, destination):
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "window_seconds": round(alert.elapsed_seconds, 3),
        "key_count": alert.key_count,
        "keys_per_second": round(alert.keys_per_second, 1),
        "classification": "fast_typing_burst_not_attribution",
    }
    print(json.dumps(record), flush=True)
    if destination is not None:
        fd = os.open(destination, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as out:
            out.write(json.dumps(record) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Opt-in timing-only typing burst monitor")
    parser.add_argument("--log", type=Path, help="write alert metadata as JSON Lines; no keystrokes")
    parser.add_argument("--demo", action="store_true", help="run synthetic timestamps without a keyboard listener")
    args = parser.parse_args(argv)
    detector = BurstDetector()
    if args.demo:
        for i in range(15):
            alert = detector.observe(i * 0.03)
            if alert:
                write_alert(alert, args.log)
        return 0

    try:
        from pynput import keyboard
    except ImportError:
        print("Install pynput: python -m pip install -r requirements.txt", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Keyboard listener unavailable: {exc}", file=sys.stderr)
        return 2

    # The callback is deliberately short; the main thread handles output/I/O.
    events = queue.Queue()
    def on_press(_key):
        events.put(time.monotonic())

    print("Monitoring key timing only. Press Ctrl+C to stop. No key content is recorded.")
    try:
        with keyboard.Listener(on_press=on_press, suppress=False) as listener:
            while listener.is_alive():
                try:
                    stamp = events.get(timeout=0.2)
                except queue.Empty:
                    continue
                alert = detector.observe(stamp)
                if alert:
                    write_alert(alert, args.log)
            listener.join()
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Keyboard listener stopped: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
