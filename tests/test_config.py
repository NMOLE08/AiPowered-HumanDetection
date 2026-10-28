"""Tests for optional Arduino command-line configuration."""

import unittest

from app.config import parse_config


class ConfigTests(unittest.TestCase):
    def test_serial_options_are_available_for_live_source(self) -> None:
        config = parse_config(
            ["--source", "http://camera:81/stream", "--serial-port", "COM7"]
        )
        self.assertEqual(config.serial_port, "COM7")
        self.assertEqual(config.serial_baud, 115200)

    def test_web_mode_uses_localhost_defaults(self) -> None:
        config = parse_config(["--source", "http://camera:81/stream", "--ui", "web"])
        self.assertEqual(config.ui, "web")
        self.assertEqual(config.web_host, "localhost")
        self.assertEqual(config.web_port, 8000)

    def test_serial_port_is_rejected_for_local_image_mode(self) -> None:
        with self.assertRaises(SystemExit):
            parse_config(["--image", "person.jpg", "--serial-port", "COM7"])


if __name__ == "__main__":
    unittest.main()
