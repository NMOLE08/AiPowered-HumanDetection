"""Send a visible protocol test sequence to the Arduino LCD without YOLO."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Running this file directly makes tools/ the first import location. Add the
# project root so the application package is found without installation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.lcd_serial import CAMERA_OFFLINE, LCDSerial


TEST_SEQUENCE: tuple[int | str, ...] = (
    0,
    1,
    2,
    3,
    2,
    1,
    0,
    CAMERA_OFFLINE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test the Arduino I2C LCD serial protocol without camera or YOLO."
    )
    parser.add_argument("--port", required=True, help="Arduino COM port, for example COM7.")
    parser.add_argument("--baud", type=int, default=115200, help="Default: 115200.")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds each test value remains visible (default: 1.0).",
    )
    args = parser.parse_args()
    if args.baud <= 0:
        parser.error("--baud must be positive")
    if args.delay <= 0:
        parser.error("--delay must be positive")
    return args


def main() -> int:
    args = parse_args()
    sender = LCDSerial(args.port, args.baud)
    try:
        # Opening Uno serial commonly resets it. Let its startup screen become
        # visible before beginning the requested count sequence.
        print("Waiting for the Arduino to restart...")
        time.sleep(2.2)
        for value in TEST_SEQUENCE:
            if isinstance(value, int):
                message = sender.format_count(value).strip()
                sender.publish_count(value)
            else:
                message = sender.format_status(value).strip()
                sender.publish_status(value)
            print(f"Sent {message}")
            time.sleep(args.delay)
        print("LCD serial test completed.")
        return 0
    except KeyboardInterrupt:
        print("LCD serial test stopped by user.")
        return 0
    finally:
        sender.close()


if __name__ == "__main__":
    raise SystemExit(main())
