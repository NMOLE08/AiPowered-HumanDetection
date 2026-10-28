"""Camera lifecycle tests that do not require OpenCV or live hardware."""

from __future__ import annotations

import sys
import threading
import time
import types
import unittest

try:
    import cv2  # noqa: F401
except ModuleNotFoundError:
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.CAP_PROP_BUFFERSIZE = 38
    cv2_stub.error = RuntimeError
    cv2_stub.VideoCapture = lambda url: None
    sys.modules["cv2"] = cv2_stub

from app.camera import CameraReadTimeout, CameraStream


class FakeFrame:
    def __init__(self, name: str, width: int = 320, height: int = 240) -> None:
        self.name = name
        self.shape = (height, width, 3)

    def copy(self):
        return FakeFrame(self.name, self.shape[1], self.shape[0])


class ControlledCapture:
    def __init__(
        self,
        frames: list[FakeFrame] | None = None,
        *,
        opened: bool = True,
        fail_signal: threading.Event | None = None,
    ) -> None:
        self.frames = list(frames or [])
        self.opened = opened
        self.fail_signal = fail_signal
        self.released = False

    def set(self, *args) -> bool:
        return True

    def isOpened(self) -> bool:
        return self.opened and not self.released

    def read(self):
        if self.frames:
            return True, self.frames.pop(0)
        while not self.released:
            if self.fail_signal is not None and self.fail_signal.wait(0.01):
                return False, None
            time.sleep(0.005)
        return False, None

    def release(self) -> None:
        self.released = True


class CameraStreamTests(unittest.TestCase):
    def test_invalid_stream_reports_clear_open_error(self) -> None:
        closed_capture = ControlledCapture(opened=False)
        camera = CameraStream("invalid", capture_factory=lambda url: closed_capture)

        with self.assertRaisesRegex(ConnectionError, "Unable to open camera stream"):
            camera.open()
        self.assertTrue(closed_capture.released)

    def test_read_timeout_does_not_return_a_stale_frame(self) -> None:
        capture = ControlledCapture()
        camera = CameraStream("mock://stream", capture_factory=lambda url: capture)
        camera.open()
        try:
            with self.assertRaises(CameraReadTimeout):
                camera.read(timeout=0.02)
        finally:
            camera.close()

    def test_stream_recovers_after_temporary_disconnect(self) -> None:
        disconnect = threading.Event()
        first = ControlledCapture([FakeFrame("first")], fail_signal=disconnect)
        second = ControlledCapture([FakeFrame("second")])
        captures = iter([first, second])
        camera = CameraStream(
            "mock://stream",
            max_reconnect_attempts=2,
            reconnect_delay=0.01,
            capture_factory=lambda url: next(captures),
        )

        camera.open()
        try:
            self.assertEqual(camera.read(timeout=1.0).name, "first")
            self.assertEqual(camera.frame_size, (320, 240))
            disconnect.set()
            self.assertEqual(camera.read(timeout=1.0).name, "second")
            self.assertTrue(camera.connected)
        finally:
            camera.close()

        self.assertTrue(first.released)
        self.assertTrue(second.released)


if __name__ == "__main__":
    unittest.main()
