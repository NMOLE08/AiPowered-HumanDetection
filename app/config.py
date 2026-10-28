"""Command-line configuration for live detection and optional Arduino LCD output."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class AppConfig:
    """Validated runtime settings."""

    source: str | None
    image: Path | None
    model: str
    confidence: float
    image_size: int
    device: str
    frame_skip: int
    reconnect_attempts: int
    reconnect_delay: float
    read_timeout: float
    serial_port: str | None
    serial_baud: int
    ui: str
    web_host: str
    web_port: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect and count visible people with pretrained YOLO11n."
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--source",
        "--camera-url",
        dest="source",
        help="ESP32-CAM MJPEG URL, for example http://CAMERA_HOST:81/stream",
    )
    input_group.add_argument(
        "--image",
        type=Path,
        help="Local image used to verify detection without the camera.",
    )
    parser.add_argument("--model", default="yolo11n.pt", help="YOLO model weights path.")
    parser.add_argument(
        "--conf",
        "--confidence",
        dest="confidence",
        type=float,
        default=0.35,
        help="Minimum detection confidence (default: 0.35).",
    )
    parser.add_argument(
        "--imgsz",
        dest="image_size",
        type=int,
        default=640,
        help="YOLO inference image size (default: 640).",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Inference device accepted by Ultralytics, such as cpu, 0, or cuda:0.",
    )
    parser.add_argument(
        "--frame-skip",
        type=int,
        default=0,
        help="Camera frames to skip between inferences (default: 0).",
    )
    parser.add_argument(
        "--reconnect-attempts",
        type=int,
        default=5,
        help="Maximum retries after a stream failure (default: 5).",
    )
    parser.add_argument(
        "--reconnect-delay",
        type=float,
        default=1.0,
        help="Seconds between stream retries (default: 1.0).",
    )
    parser.add_argument(
        "--read-timeout",
        type=float,
        default=0.5,
        help="Seconds the UI waits for a new camera frame (default: 0.5).",
    )
    parser.add_argument(
        "--serial-port",
        default=None,
        help="Optional Arduino Uno port, for example COM7 on Windows.",
    )
    parser.add_argument(
        "--serial-baud",
        type=int,
        default=115200,
        help="Arduino serial baud rate (default: 115200).",
    )
    parser.add_argument(
        "--ui",
        choices=("opencv", "web"),
        default="opencv",
        help="Display mode: OpenCV popup or local web dashboard (default: opencv).",
    )
    parser.add_argument(
        "--web-host",
        default="localhost",
        help="Dashboard bind address in web mode (default: localhost).",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8000,
        help="Dashboard port in web mode (default: 8000).",
    )
    return parser


def parse_config(argv: Sequence[str] | None = None) -> AppConfig:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not 0.0 < args.confidence <= 1.0:
        parser.error("--conf must be greater than 0 and at most 1")
    if args.image_size <= 0:
        parser.error("--imgsz must be a positive integer")
    if args.frame_skip < 0:
        parser.error("--frame-skip cannot be negative")
    if args.reconnect_attempts < 0:
        parser.error("--reconnect-attempts cannot be negative")
    if args.reconnect_delay < 0:
        parser.error("--reconnect-delay cannot be negative")
    if args.read_timeout <= 0:
        parser.error("--read-timeout must be greater than 0")
    if args.serial_baud <= 0:
        parser.error("--serial-baud must be a positive integer")
    if not 1 <= args.web_port <= 65535:
        parser.error("--web-port must be between 1 and 65535")
    if args.source is not None and not args.source.strip():
        parser.error("--source cannot be empty")
    if args.image is not None and args.serial_port is not None:
        parser.error("--serial-port can only be used with --source")
    if args.image is not None and args.ui == "web":
        parser.error("--ui web requires --source")

    return AppConfig(
        source=args.source,
        image=args.image,
        model=args.model,
        confidence=args.confidence,
        image_size=args.image_size,
        device=args.device,
        frame_skip=args.frame_skip,
        reconnect_attempts=args.reconnect_attempts,
        reconnect_delay=args.reconnect_delay,
        read_timeout=args.read_timeout,
        serial_port=args.serial_port,
        serial_baud=args.serial_baud,
        ui=args.ui,
        web_host=args.web_host,
        web_port=args.web_port,
    )
