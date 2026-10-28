"""OpenCV annotations and display helpers."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

import cv2

from app.detector import Detection


class FPSMeter:
    """Measure effective inference FPS using a smoothed moving estimate."""

    def __init__(self, smoothing: float = 0.85) -> None:
        self.smoothing = smoothing
        self._previous: float | None = None
        self.value = 0.0

    def update(self) -> float:
        now = time.perf_counter()
        if self._previous is not None:
            elapsed = now - self._previous
            if elapsed > 0:
                instantaneous = 1.0 / elapsed
                self.value = (
                    instantaneous
                    if self.value == 0.0
                    else self.smoothing * self.value
                    + (1.0 - self.smoothing) * instantaneous
                )
        self._previous = now
        return self.value


class Visualizer:
    """Draw person boxes, current count, FPS, and camera status."""

    def __init__(self, window_name: str = "ESP32-CAM AI Human Detection") -> None:
        self.window_name = window_name

    def annotate(
        self,
        frame: Any,
        detections: Iterable[Detection],
        count: int,
        fps: float,
        status: str,
    ):
        canvas = frame.copy()
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            cv2.rectangle(canvas, (x1, y1), (x2, y2), (0, 210, 0), 2)
            label = f"Person {detection['confidence']:.2f}"
            text_y = max(18, y1 - 7)
            cv2.putText(
                canvas,
                label,
                (x1, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        overlay_height = min(66, canvas.shape[0])
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (canvas.shape[1], overlay_height), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.58, canvas, 0.42, 0, canvas)
        status_color = (0, 255, 0) if status == "CONNECTED" else (0, 165, 255)
        cv2.putText(
            canvas,
            f"Humans Detected: {count}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            f"Inference FPS: {fps:.1f}",
            (10, 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            canvas,
            f"Status: {status}",
            (max(10, canvas.shape[1] - 150), 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            status_color,
            1,
            cv2.LINE_AA,
        )
        return canvas

    @staticmethod
    def annotate_for_web(
        frame: Any,
        detections: Iterable[Detection],
        *,
        show_boxes: bool = True,
        show_labels: bool = True,
    ):
        """Draw only detection overlays for the dashboard's annotated video feed."""
        canvas = frame.copy()
        accent_bgr = (160, 167, 25)  # Sentinel Vision accent #19A7A0 in BGR.
        text_color = (255, 255, 255)
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox"]
            if show_boxes:
                cv2.rectangle(canvas, (x1, y1), (x2, y2), accent_bgr, 2)
            if show_labels:
                label = f"Person {detection['confidence']:.2f}"
                (label_width, label_height), baseline = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
                )
                label_y = max(label_height + baseline + 6, y1)
                cv2.rectangle(
                    canvas,
                    (x1, label_y - label_height - baseline - 6),
                    (x1 + label_width + 8, label_y),
                    accent_bgr,
                    -1,
                )
                cv2.putText(
                    canvas,
                    label,
                    (x1 + 4, label_y - baseline - 3),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    text_color,
                    1,
                    cv2.LINE_AA,
                )
        return canvas

    def show(self, frame: Any) -> bool:
        """Display a frame and return True when Q or Escape is pressed."""
        cv2.imshow(self.window_name, frame)
        return cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q"), 27)

    @staticmethod
    def close() -> None:
        cv2.destroyAllWindows()
