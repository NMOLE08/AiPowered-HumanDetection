"""Mocked tests for Arduino LCD serial communication."""

from __future__ import annotations

import time
import unittest

from app.lcd_serial import CAMERA_OFFLINE, LCDSerial


def wait_for(predicate, timeout: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class RecordingSerial:
    def __init__(self, *args, fail_writes: bool = False, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.fail_writes = fail_writes
        self.writes: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> int:
        if self.fail_writes:
            raise OSError("USB cable disconnected")
        self.writes.append(data)
        return len(data)

    def close(self) -> None:
        self.closed = True


class SerialFactory:
    def __init__(self, devices: list[RecordingSerial]) -> None:
        self.devices = devices
        self.calls = []

    def __call__(self, *args, **kwargs) -> RecordingSerial:
        self.calls.append((args, kwargs))
        if not self.devices:
            raise OSError("Arduino not found")
        return self.devices.pop(0)


class LCDSerialTests(unittest.TestCase):
    def make_sender(self, factory: SerialFactory, **kwargs) -> LCDSerial:
        return LCDSerial(
            "COM7",
            startup_delay=0,
            reconnect_interval=0.01,
            worker_poll_interval=0.005,
            serial_factory=factory,
            **kwargs,
        )

    def test_count_protocol_has_required_newline(self) -> None:
        self.assertEqual(LCDSerial.format_count(0), "COUNT:0\n")
        self.assertEqual(LCDSerial.format_count(12), "COUNT:12\n")
        self.assertEqual(
            LCDSerial.format_status(CAMERA_OFFLINE), "STATUS:CAMERA_OFFLINE\n"
        )

    def test_invalid_counts_and_statuses_are_rejected(self) -> None:
        for value in (-1, 10000, True, 1.5):
            with self.assertRaises(ValueError):
                LCDSerial.format_count(value)
        with self.assertRaises(ValueError):
            LCDSerial.format_status("UNKNOWN")

    def test_change_heartbeat_and_status_messages_are_sent(self) -> None:
        device = RecordingSerial()
        sender = self.make_sender(SerialFactory([device]), heartbeat_interval=0.04)
        try:
            self.assertTrue(sender.publish_count(2))
            self.assertTrue(wait_for(lambda: device.writes == [b"COUNT:2\n"]))
            self.assertFalse(sender.publish_count(2))

            time.sleep(0.05)
            self.assertTrue(sender.publish_count(2))
            self.assertTrue(wait_for(lambda: len(device.writes) == 2))
            self.assertEqual(device.writes[-1], b"COUNT:2\n")

            self.assertTrue(sender.publish_status())
            self.assertTrue(wait_for(lambda: device.writes[-1:] == [b"STATUS:CAMERA_OFFLINE\n"]))
        finally:
            sender.close()
        self.assertTrue(device.closed)

    def test_disconnect_reconnects_and_resends_latest_message(self) -> None:
        failed_device = RecordingSerial(fail_writes=True)
        recovered_device = RecordingSerial()
        sender = self.make_sender(SerialFactory([failed_device, recovered_device]))
        try:
            sender.publish_count(3)
            self.assertTrue(
                wait_for(lambda: recovered_device.writes == [b"COUNT:3\n"])
            )
            self.assertTrue(failed_device.closed)
            self.assertTrue(sender.connected)
        finally:
            sender.close()
        self.assertTrue(recovered_device.closed)

    def test_unavailable_com_port_does_not_raise_or_block(self) -> None:
        factory = SerialFactory([])
        sender = self.make_sender(factory)
        try:
            self.assertTrue(sender.publish_count(1))
            self.assertTrue(wait_for(lambda: len(factory.calls) >= 1))
            self.assertFalse(sender.connected)
        finally:
            sender.close()

    def test_rapid_updates_keep_only_the_newest_pending_count(self) -> None:
        device = RecordingSerial()
        sender = LCDSerial(
            "COM7",
            startup_delay=0.05,
            reconnect_interval=0.01,
            worker_poll_interval=0.005,
            serial_factory=SerialFactory([device]),
        )
        try:
            sender.publish_count(1)
            sender.publish_count(2)
            sender.publish_count(3)
            self.assertTrue(wait_for(lambda: len(device.writes) >= 1))
            self.assertEqual(device.writes, [b"COUNT:3\n"])
        finally:
            sender.close()

    def test_no_port_keeps_detection_mode_optional(self) -> None:
        sender = LCDSerial(None)
        try:
            self.assertFalse(sender.enabled)
            self.assertFalse(sender.publish_count(1))
            self.assertIsNone(sender.pending_message)
        finally:
            sender.close()


if __name__ == "__main__":
    unittest.main()
