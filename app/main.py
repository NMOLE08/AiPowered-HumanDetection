"""Phase 3 entry point for live or local-image human detection."""

from __future__ import annotations

import sys
from typing import Any

import cv2

from app.camera import CameraReadTimeout, CameraStream
from app.config import AppConfig, parse_config
from app.counter import PersonCounter
from app.detector import Detection, PersonDetector
from app.lcd_serial import CAMERA_OFFLINE, LCDSerial
from app.visualizer import FPSMeter, Visualizer


def _build_detector(config: AppConfig) -> PersonDetector:
    print(f"Loading pretrained model: {config.model}")
    return PersonDetector(
        model_path=config.model,
        confidence=config.confidence,
        image_size=config.image_size,
        device=config.device,
    )


def run_image(config: AppConfig, detector: PersonDetector) -> int:
    """Verify the model independently on one local image."""
    assert config.image is not None
    frame = cv2.imread(str(config.image))
    if frame is None:
        print(f"ERROR: Cannot read image: {config.image}", file=sys.stderr)
        return 2

    counter = PersonCounter()
    visualizer = Visualizer("YOLO11n Local Image Test")
    detections = detector.detect(frame)
    count = counter.update(detections)
    annotated = visualizer.annotate(frame, detections, count, 0.0, "LOCAL IMAGE")
    print(f"Detected {count} visible person(s) in {config.image}.")
    print("Press Q or Escape in the image window to close it.")
    try:
        while not visualizer.show(annotated):
            pass
    finally:
        visualizer.close()
    return 0


def run_camera(config: AppConfig, detector: PersonDetector) -> int:
    """Run person detection against the configured ESP32-CAM stream."""
    assert config.source is not None
    camera = CameraStream(
        config.source,
        max_reconnect_attempts=config.reconnect_attempts,
        reconnect_delay=config.reconnect_delay,
    )
    counter = PersonCounter()
    lcd = LCDSerial(config.serial_port, config.serial_baud)
    visualizer = Visualizer()
    fps_meter = FPSMeter()
    detections: list[Detection] = []
    last_frame: Any | None = None
    frame_number = 0
    dimensions_reported = False
    needs_inference = True

    try:
        camera.open()
        print("Camera stream opened. Press Q or Escape in the video window to exit.")
        while True:
            try:
                frame = camera.read(timeout=config.read_timeout)
                last_frame = frame
                if not dimensions_reported:
                    height, width = frame.shape[:2]
                    print(f"Receiving camera frames at {width} x {height} pixels.")
                    dimensions_reported = True
            except CameraReadTimeout:
                counter.clear()
                detections = []
                lcd.publish_status(CAMERA_OFFLINE)
                needs_inference = True
                if last_frame is not None:
                    waiting = visualizer.annotate(
                        last_frame, detections, 0, fps_meter.value, camera.status
                    )
                    if visualizer.show(waiting):
                        break
                continue

            should_infer = needs_inference or frame_number % (config.frame_skip + 1) == 0
            if should_infer:
                detections = detector.detect(frame)
                counter.update(detections)
                fps_meter.update()
                needs_inference = False
            frame_number += 1

            # This is the exact accepted count already used by the visualizer;
            # serial output never performs a second YOLO inference or recount.
            lcd.publish_count(counter.current_count)

            annotated = visualizer.annotate(
                frame,
                detections,
                counter.current_count,
                fps_meter.value,
                camera.status,
            )
            if visualizer.show(annotated):
                break
        return 0
    except ConnectionError as exc:
        counter.clear()
        lcd.publish_status(CAMERA_OFFLINE)
        print(f"CAMERA ERROR: {exc}", file=sys.stderr)
        return 3
    except RuntimeError as exc:
        counter.clear()
        lcd.publish_status(CAMERA_OFFLINE)
        print(f"INFERENCE ERROR: {exc}", file=sys.stderr)
        return 4
    except KeyboardInterrupt:
        print("Stopped by user.")
        return 0
    finally:
        camera.close()
        lcd.close()
        visualizer.close()


def run_web(config: AppConfig, detector: PersonDetector) -> int:
    """Run the browser dashboard with one shared camera/detection worker."""
    from app.web_server import run_dashboard

    return run_dashboard(config, detector)


def main(argv: list[str] | None = None) -> int:
    config = parse_config(argv)
    try:
        detector = _build_detector(config)
    except RuntimeError as exc:
        print(f"MODEL ERROR: {exc}", file=sys.stderr)
        return 5

    if config.image is not None:
        try:
            return run_image(config, detector)
        except RuntimeError as exc:
            print(f"INFERENCE ERROR: {exc}", file=sys.stderr)
            return 4
    if config.ui == "web":
        return run_web(config, detector)
    return run_camera(config, detector)


if __name__ == "__main__":
    raise SystemExit(main())
