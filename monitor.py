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


def build_detector(args):
    """Create a BurstDetector from parsed CLI arguments."""
    return BurstDetector(
        window_seconds=args.window,
        min_keys=args.min_keys,
        min_rate=args.min_rate,
        cooldown_seconds=args.cooldown,
    )


def describe_rule(args):
    """Human-readable summary of the active detection rule."""
    return (f"Rule: {args.min_keys}+ presses within {args.window}s at "
            f"{args.min_rate}+ keys/sec, {args.cooldown}s cooldown.")


def write_alert(alert, destination, output_format="json"):
    """Print timing metadata; keep file logs as JSON Lines in either format."""
    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "window_seconds": round(alert.elapsed_seconds, 3),
        "key_count": alert.key_count,
        "keys_per_second": round(alert.keys_per_second, 1),
        "classification": "fast_typing_burst_not_attribution",
    }
    if destination is not None:
        fd = os.open(destination, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as out:
            out.write(json.dumps(record) + "\n")
    if output_format == "text":
        print(f"[{record['timestamp_utc']}] Fast typing burst: "
              f"{alert.key_count} presses in {alert.elapsed_seconds:.3f}s "
              f"({alert.keys_per_second:.1f} keys/sec). "
              "Timing heuristic only; not proof of malicious input.", flush=True)
    else:
        print(json.dumps(record), flush=True)


def write_summary(presses, alerts, elapsed, status):
    """Use stderr so JSON stdout remains a parseable event stream."""
    print(f"Session {status}: {presses} presses processed, {alerts} alerts emitted, "
          f"{elapsed:.2f}s elapsed. No key content recorded.",
          file=sys.stderr, flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Opt-in timing-only typing burst monitor")
    parser.add_argument("--log", type=Path, help="write alert metadata as JSON Lines; no keystrokes")
    parser.add_argument("--format", choices=("json", "text"), default="json",
                        help="alert output: json (default) or readable text; logs stay JSON Lines")
    parser.add_argument("--demo", action="store_true", help="run synthetic timestamps without a keyboard listener")
    parser.add_argument("--window", type=float, default=0.75,
                        help="sliding window length in seconds (default: 0.75)")
    parser.add_argument("--min-keys", type=int, default=12,
                        help="presses required inside the window (default: 12)")
    parser.add_argument("--min-rate", type=float, default=18.0,
                        help="minimum presses per second to alert (default: 18.0)")
    parser.add_argument("--cooldown", type=float, default=3.0,
                        help="seconds to suppress repeats after an alert (default: 3.0)")
    args = parser.parse_args(argv)
    try:
        detector = build_detector(args)
    except ValueError as exc:
        parser.error(f"invalid rule settings: {exc}")
    print(describe_rule(args), file=sys.stderr, flush=True)
    started = time.monotonic()
    presses = alerts = 0
    status = "completed"

    def process(stamp):
        nonlocal presses, alerts
        presses += 1
        alert = detector.observe(stamp)
        if alert:
            write_alert(alert, args.log, args.format)
            alerts += 1

    try:
        if args.demo:
            for i in range(15):
                process(i * 0.03)
            return 0

        try:
            from pynput import keyboard
        except ImportError:
            print("Install pynput: python -m pip install -r requirements.txt", file=sys.stderr)
            status = "failed"
            return 2
        except Exception as exc:
            print(f"Keyboard listener unavailable: {exc}", file=sys.stderr)
            status = "failed"
            return 2

        # The callback is deliberately short; the main thread handles output/I/O.
        events = queue.Queue()
        def on_press(_key):
            events.put(time.monotonic())

        print("Monitoring key timing only. Press Ctrl+C to stop. No key content is recorded.",
              file=sys.stderr, flush=True)
        with keyboard.Listener(on_press=on_press, suppress=False) as listener:
            while listener.is_alive():
                try:
                    stamp = events.get(timeout=0.2)
                except queue.Empty:
                    continue
                process(stamp)
            listener.join()
    except KeyboardInterrupt:
        status = "interrupted"
        return 0
    except OSError as exc:
        print(f"Output or log write failed: {exc}", file=sys.stderr)
        status = "failed"
        return 2
    except Exception as exc:
        print(f"Keyboard listener stopped: {exc}", file=sys.stderr)
        status = "failed"
        return 2
    finally:
        write_summary(presses, alerts, time.monotonic() - started, status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
