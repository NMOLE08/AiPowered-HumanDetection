"""Thread-safe live state shared by the detection worker and web dashboard."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import Condition
from time import time
from typing import Any

from app.detector import Detection


class LiveState:
    """Keep the newest frame and a bounded, truthful dashboard data snapshot."""

    def __init__(
        self,
        source: str,
        *,
        event_limit: int = 12,
        stale_after_seconds: float = 2.5,
    ) -> None:
        self.source = source
        self.stale_after_seconds = stale_after_seconds
        self._condition = Condition()
        self._frame: Any | None = None
        self._detections: list[Detection] = []
        self._frame_version = 0
        self._camera = "connecting"
        self._model = "initializing"
        self._arduino = "not_configured"
        self._human_count: int | None = None
        self._count_valid = False
        self._fps = 0.0
        self._inference_ms: float | None = None
        self._last_detection_at: float | None = None
        self._last_frame_at: float | None = None
        self._resolution: tuple[int, int] | None = None
        self._last_error: str | None = None
        self._events: deque[dict[str, str]] = deque(maxlen=event_limit)

    @staticmethod
    def _timestamp(value: float | None = None) -> str:
        return datetime.fromtimestamp(value or time(), UTC).isoformat()

    def _add_event_locked(self, message: str, level: str = "info") -> None:
        self._events.appendleft(
            {"message": message, "level": level, "timestamp": self._timestamp()}
        )

    def add_event(self, message: str, level: str = "info") -> None:
        """Add an observed system event to the bounded current-session feed."""
        with self._condition:
            self._add_event_locked(message, level)
            self._condition.notify_all()

    def set_model_status(self, status: str, error: str | None = None) -> None:
        with self._condition:
            if status != self._model:
                level = "success" if status == "ready" else "error" if status == "error" else "warning"
                self._add_event_locked(f"YOLO model {status.replace('_', ' ')}", level)
            self._model = status
            self._last_error = error
            self._condition.notify_all()

    def set_camera_status(self, status: str, error: str | None = None) -> None:
        with self._condition:
            if status != self._camera:
                labels = {
                    "connected": "Camera connected",
                    "reconnecting": "Camera reconnecting",
                    "disconnected": "Camera disconnected",
                    "connecting": "Camera connecting",
                }
                level = "success" if status == "connected" else "error" if status == "disconnected" else "warning"
                self._add_event_locked(labels.get(status, f"Camera {status}"), level)
            self._camera = status
            self._last_error = error
            self._condition.notify_all()

    def set_arduino_status(self, status: str) -> None:
        with self._condition:
            if status != self._arduino:
                labels = {
                    "connected": "Arduino serial connection established",
                    "reconnecting": "Arduino serial reconnecting",
                    "not_configured": "Arduino LCD not configured",
                    "error": "Arduino serial connection unavailable",
                }
                level = "success" if status == "connected" else "error" if status == "error" else "warning"
                self._add_event_locked(labels.get(status, f"Arduino {status}"), level)
            self._arduino = status
            self._condition.notify_all()

    def mark_detection_unavailable(self, camera_status: str, error: str | None = None) -> None:
        """Invalidate the count rather than presenting a stale zero or old value."""
        with self._condition:
            self._human_count = None
            self._count_valid = False
            self._camera = camera_status
            self._last_error = error
            self._condition.notify_all()

    def record_detection(
        self,
        frame: Any,
        detections: list[Detection],
        count: int,
        fps: float,
        inference_ms: float,
    ) -> None:
        """Publish one real detection result and its corresponding camera frame."""
        now = time()
        height, width = frame.shape[:2]
        with self._condition:
            previous_count = self._human_count if self._count_valid else None
            self._frame = frame.copy()
            self._detections = [detection.copy() for detection in detections]
            self._frame_version += 1
            self._human_count = count
            self._count_valid = True
            self._fps = fps
            self._inference_ms = inference_ms
            self._last_detection_at = now
            self._last_frame_at = now
            self._resolution = (width, height)
            self._camera = "connected"
            self._model = "ready"
            self._last_error = None
            if previous_count is not None and previous_count != count:
                self._add_event_locked(
                    f"Human count changed from {previous_count} to {count}", "info"
                )
            elif previous_count is None:
                self._add_event_locked(f"Detection active: {count} human(s) visible", "success")
            self._condition.notify_all()

    def record_display_frame(self, frame: Any, detections: list[Detection]) -> None:
        """Refresh the browser frame without changing the last valid detection timestamp."""
        now = time()
        with self._condition:
            self._frame = frame.copy()
            self._detections = [detection.copy() for detection in detections]
            self._frame_version += 1
            self._last_frame_at = now
            self._condition.notify_all()

    def get_frame_after(
        self, version: int, timeout: float = 1.0
    ) -> tuple[int, Any, list[Detection]] | None:
        """Return one newer latest frame for an MJPEG client, without a frame queue."""
        with self._condition:
            if self._frame_version <= version:
                self._condition.wait(timeout)
            if self._frame is None or self._frame_version <= version:
                return None
            return (
                self._frame_version,
                self._frame.copy(),
                [detection.copy() for detection in self._detections],
            )

    def status_snapshot(self) -> dict[str, Any]:
        """Return small JSON-safe dashboard data derived only from observed state."""
        now = time()
        with self._condition:
            stale = (
                self._last_detection_at is None
                or now - self._last_detection_at > self.stale_after_seconds
            )
            count_valid = self._count_valid and not stale
            resolution = (
                {"width": self._resolution[0], "height": self._resolution[1]}
                if self._resolution is not None
                else None
            )
            return {
                "camera": self._camera,
                "model": self._model,
                "arduino": self._arduino,
                "human_count": self._human_count if count_valid else None,
                "count_valid": count_valid,
                "count_stale": self._count_valid and stale,
                "fps": round(self._fps, 2) if self._fps else 0.0,
                "inference_ms": round(self._inference_ms, 2)
                if self._inference_ms is not None
                else None,
                "last_detection_at": self._timestamp(self._last_detection_at)
                if self._last_detection_at is not None
                else None,
                "last_frame_at": self._timestamp(self._last_frame_at)
                if self._last_frame_at is not None
                else None,
                "model_name": "YOLO11n",
                "source": self.source,
                "resolution": resolution,
                "last_error": self._last_error,
                "events": list(self._events),
            }
