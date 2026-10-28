"""Nonblocking USB serial output for the Arduino I²C LCD."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

try:
    import serial
except ImportError:  # Allows mocked tests to run before dependencies are installed.
    serial = None


CAMERA_OFFLINE = "CAMERA_OFFLINE"
MAX_LCD_COUNT = 9999


class LCDSerial:
    """Publish the latest count or status without blocking the detection loop.

    Calls to :meth:`publish_count` and :meth:`publish_status` only replace one
    pending message. A worker thread owns the serial port, handles Uno reset
    delay, and reconnects after a serial failure. Old messages are never queued.
    """

    def __init__(
        self,
        port: str | None = None,
        baud_rate: int = 115200,
        *,
        heartbeat_interval: float = 1.0,
        reconnect_interval: float = 2.0,
        startup_delay: float = 2.0,
        serial_factory: Callable[..., Any] | None = None,
        worker_poll_interval: float = 0.1,
    ) -> None:
        if baud_rate <= 0:
            raise ValueError("baud_rate must be positive.")
        if heartbeat_interval <= 0:
            raise ValueError("heartbeat_interval must be positive.")
        if reconnect_interval <= 0:
            raise ValueError("reconnect_interval must be positive.")
        if startup_delay < 0:
            raise ValueError("startup_delay cannot be negative.")

        self.port = port
        self.baud_rate = baud_rate
        self.heartbeat_interval = heartbeat_interval
        self.reconnect_interval = reconnect_interval
        self.startup_delay = startup_delay
        self.worker_poll_interval = worker_poll_interval
        self._serial_factory = serial_factory or self._default_serial_factory
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._device: Any | None = None
        self._desired_message: str | None = None
        self._desired_version = 0
        self._sent_version = 0
        self._last_queued_at = 0.0
        self._thread: threading.Thread | None = None

        if port:
            self._thread = threading.Thread(
                target=self._worker,
                name="arduino-lcd-serial",
                daemon=True,
            )
            self._thread.start()
        else:
            print("LCD serial disabled; running video-only mode.")

    @staticmethod
    def _default_serial_factory(*args: Any, **kwargs: Any) -> Any:
        if serial is None:
            raise RuntimeError("PySerial is not installed. Run pip install -r requirements.txt.")
        return serial.Serial(*args, **kwargs)

    @property
    def enabled(self) -> bool:
        return self.port is not None

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._device is not None

    @property
    def pending_message(self) -> str | None:
        """Expose the newest protocol message for diagnostics and unit tests."""
        with self._lock:
            return self._desired_message

    @staticmethod
    def format_count(count: int) -> str:
        """Validate and encode a count as one newline-terminated protocol message."""
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError("count must be an integer.")
        if not 0 <= count <= MAX_LCD_COUNT:
            raise ValueError(f"count must be between 0 and {MAX_LCD_COUNT}.")
        return f"COUNT:{count}\n"

    @staticmethod
    def format_status(status: str = CAMERA_OFFLINE) -> str:
        """Validate and encode an LCD status message."""
        if status != CAMERA_OFFLINE:
            raise ValueError(f"Unsupported LCD status: {status!r}")
        return f"STATUS:{status}\n"

    def _publish(self, message: str, now: float | None = None) -> bool:
        """Store only the latest message, with change and heartbeat throttling."""
        if not self.enabled:
            return False
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            changed = message != self._desired_message
            heartbeat_due = timestamp - self._last_queued_at >= self.heartbeat_interval
            if not changed and not heartbeat_due:
                return False
            self._desired_message = message
            self._desired_version += 1
            self._last_queued_at = timestamp
        self._wake.set()
        return True

    def publish_count(self, count: int, *, now: float | None = None) -> bool:
        """Publish an accepted visible-person count when changed or due as heartbeat."""
        return self._publish(self.format_count(count), now)

    def publish_status(self, status: str = CAMERA_OFFLINE, *, now: float | None = None) -> bool:
        """Publish camera/inference unavailability without sending a false zero count."""
        return self._publish(self.format_status(status), now)

    def send(self, count: int) -> bool:
        """Compatibility alias for the previous count-only serial helper."""
        return self.publish_count(count)

    def _connect(self) -> Any | None:
        assert self.port is not None
        try:
            device = self._serial_factory(
                self.port,
                self.baud_rate,
                timeout=0,
                write_timeout=0.2,
            )
        except (OSError, RuntimeError) as exc:
            print(f"WARNING: Arduino serial unavailable on {self.port} ({exc}). Retrying.")
            return None
        except Exception as exc:  # PySerial exposes platform-specific exception classes.
            print(f"WARNING: Arduino serial unavailable on {self.port} ({exc}). Retrying.")
            return None

        with self._lock:
            self._device = device
            # An Uno reset loses its previous display state. Force the newest
            # desired value to be sent again after every successful reconnect.
            self._sent_version = 0
        print(f"Arduino LCD connected on {self.port} at {self.baud_rate} baud.")
        return device

    def _disconnect(self, device: Any, reason: Exception | None = None) -> None:
        with self._lock:
            if self._device is device:
                self._device = None
        try:
            device.close()
        except Exception:
            pass
        if reason is not None:
            print(f"WARNING: Arduino LCD connection lost ({reason}). Retrying.")

    def _worker(self) -> None:
        while not self._stop.is_set():
            device = self._connect()
            if device is None:
                self._stop.wait(self.reconnect_interval)
                continue

            # Opening an Uno serial port normally resets the board. This wait is
            # isolated in the worker, so it never pauses camera or YOLO processing.
            if self._stop.wait(self.startup_delay):
                self._disconnect(device)
                return

            while not self._stop.is_set():
                with self._lock:
                    message = self._desired_message
                    version = self._desired_version
                if message is not None and version > self._sent_version:
                    try:
                        written = device.write(message.encode("ascii"))
                        if written != len(message):
                            raise OSError("Incomplete serial write")
                    except Exception as exc:
                        self._disconnect(device, exc)
                        break
                    self._sent_version = version
                    continue

                self._wake.wait(self.worker_poll_interval)
                self._wake.clear()

    def close(self) -> None:
        """Stop the worker and release the COM port without blocking indefinitely."""
        self._stop.set()
        self._wake.set()
        with self._lock:
            device = self._device
            self._device = None
        if device is not None:
            try:
                device.close()
            except Exception:
                pass
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, self.worker_poll_interval * 4))
        self._thread = None
