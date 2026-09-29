# Typing-burst monitor

A small, opt-in Python experiment that flags unusually fast runs of keypresses. It is a timing heuristic for studying keyboard-injection-style behavior, not a USB Rubber Ducky detector or proof that a device is malicious.

## Try it safely

python monitor.py --demo
python -m unittest discover -s tests -v

To monitor keyboard timing on a supported local desktop:
python -m pip install -r requirements.txt
python monitor.py

--log alerts.jsonl saves alert metadata only (UTC time, burst duration, press count, keys/sec). No characters, key names, passwords or screenshots are saved. Log files get owner-only permissions.

## Configuring the rule

The detection thresholds are CLI flags, so the rule can be tuned without editing source:

python monitor.py --demo --min-keys 8 --min-rate 25

--window sets the sliding window length in seconds (default 0.75), --min-keys the presses required inside it (default 12), --min-rate the alerting speed in presses per second (default 18.0), and --cooldown the seconds repeat alerts are suppressed (default 3.0). The active rule prints at startup.

## How it works

Each key press is timestamped with a monotonic clock; a sliding-window detector flags 12+ presses within 0.75s at 18+ presses/sec, with a 3s cooldown (all four values configurable, see above). Key identity is discarded immediately. --demo runs synthetic timestamps without keyboard access.

## Limits

Fast bursts can be legitimate macros or automation; slow staged injection can evade it. Cannot identify USB devices, block input, or lock screens. Not tested against a physical injection device. On Linux Wayland/Xwayland some events may be missed. Use only on machines you own or are authorized to monitor.

## Next steps

Test on real systems, measure false positives, improve alert presentation. A detection is not forensic proof.
