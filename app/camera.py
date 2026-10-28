"""Latest-frame reader for an ESP32-CAM MJPEG stream."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

import cv2


class CameraReadTimeout(TimeoutError):
    """Raised when no new frame arrives before the UI wait expires."""


class CameraStream:
    """Read an MJPEG stream while retaining at most one decoded frame.

    A background thread continuously consumes the OpenCV stream. Replacing the
    stored frame instead of queuing frames prevents latency from growing when
    YOLO inference is slower than camera capture.
    """

    def __init__(
        self,
        url: str,
        max_reconnect_attempts: int = 5,
        reconnect_delay: float = 1.0,
        capture_factory: Callable[[str], Any] | None = None,
    ) -> None:
        if not url or not url.strip():
            raise ValueError("Camera stream URL cannot be empty.")
        if max_reconnect_attempts < 0:
            raise ValueError("max_reconnect_attempts cannot be negative.")
        if reconnect_delay < 0:
            raise ValueError("reconnect_delay cannot be negative.")

        self.url = url
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self._capture_factory = capture_factory or cv2.VideoCapture
        self._capture: Any | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._condition = threading.Condition()
        self._latest_frame: Any | None = None
        self._sequence = 0
        self._last_delivered_sequence = 0
        self._connected = False
        self._terminal_error: str | None = None
        self._frame_size: tuple[int, int] | None = None

    @property
    def connected(self) -> bool:
        with self._condition:
            return self._connected

    @property
    def status(self) -> str:
        with self._condition:
            if self._connected:
                return "CONNECTED"
            if self._terminal_error:
                return "DISCONNECTED"
            return "RECONNECTING"

    @property
    def frame_size(self) -> tuple[int, int] | None:
        with self._condition:
            return self._frame_size

    def _new_capture(self) -> Any:
        capture = self._capture_factory(self.url)
        try:
            capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except (AttributeError, TypeError):
            pass
        if not capture.isOpened():
            capture.release()
            raise ConnectionError(f"Cannot open ESP32-CAM stream: {self.url}")
        return capture

    def open(self) -> None:
        """Open the stream and start the latest-frame reader."""
        self.close()
        try:
            capture = self._new_capture()
        except (OSError, cv2.error, ConnectionError) as exc:
            raise ConnectionError(
                f"Unable to open camera stream '{self.url}'. "
                "Check the URL, camera power, and Wi-Fi connection."
            ) from exc

        with self._condition:
            self._capture = capture
            self._connected = True
            self._terminal_error = None
            self._latest_frame = None
            self._sequence = 0
            self._last_delivered_sequence = 0
            self._frame_size = None
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._reader_loop,
            name="esp32-camera-reader",
            daemon=True,
        )
        self._thread.start()

    def _reader_loop(self) -> None:
        while not self._stop.is_set():
            with self._condition:
                capture = self._capture
            if capture is None:
                return

            try:
                success, frame = capture.read()
            except (OSError, cv2.error):
                success, frame = False, None

            if success and frame is not None:
                height, width = frame.shape[:2]
                with self._condition:
                    self._latest_frame = frame
                    self._sequence += 1
                    self._connected = True
                    self._frame_size = (width, height)
                    self._condition.notify_all()
                continue

            if not self._reconnect():
                return

    def _reconnect(self) -> bool:
        with self._condition:
            self._connected = False
            old_capture = self._capture
            self._capture = None
            self._condition.notify_all()
        if old_capture is not None:
            old_capture.release()

        for attempt in range(1, self.max_reconnect_attempts + 1):
            if self._stop.wait(self.reconnect_delay):
                return False
            print(
                f"Camera stream unavailable. Reconnecting "
                f"({attempt}/{self.max_reconnect_attempts})..."
            )
            try:
                capture = self._new_capture()
            except (OSError, cv2.error, ConnectionError):
                continue
            if self._stop.is_set():
                capture.release()
                return False
            with self._condition:
                self._capture = capture
                self._connected = True
                self._condition.notify_all()
            print("Camera stream reconnected.")
            return True

        with self._condition:
            self._terminal_error = (
                f"Camera disconnected after {self.max_reconnect_attempts} "
                "reconnection attempts."
            )
            self._condition.notify_all()
        return False

    def read(self, timeout: float = 0.5):
        """Return the newest frame, waiting briefly for a new one."""
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0.")
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._sequence <= self._last_delivered_sequence:
                if self._terminal_error:
                    raise ConnectionError(self._terminal_error)
                if self._thread is None:
                    raise ConnectionError("Camera stream is not open.")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CameraReadTimeout(
                        f"No new camera frame received within {timeout:.1f} seconds."
                    )
                self._condition.wait(remaining)

            self._last_delivered_sequence = self._sequence
            return self._latest_frame.copy()

    def close(self) -> None:
        """Stop the reader and release the OpenCV capture."""
        self._stop.set()
        with self._condition:
            capture = self._capture
            self._capture = None
            self._connected = False
            self._condition.notify_all()
        if capture is not None:
            capture.release()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._thread = None
