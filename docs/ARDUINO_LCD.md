# Arduino LCD Integration

## Firmware

Upload `firmware/arduino_lcd_i2c/arduino_lcd_i2c.ino` to an Arduino Uno after
installing **hd44780 by Bill Perry** through Arduino IDE Library Manager.

The firmware:

- initializes a 16×2 I²C LCD with automatic address detection;
- reads serial input at 115200 baud without blocking;
- accepts complete newline-terminated `COUNT:` and `STATUS:` messages;
- validates counts from `0` to `9999`;
- rejects malformed or oversized input safely;
- avoids full-screen LCD clearing to reduce flicker;
- shows `NO DATA` after four seconds without a valid update.

See [HARDWARE.md](HARDWARE.md) for the circuit table.

## Protocol

```text
COUNT:0
COUNT:12
STATUS:CAMERA_OFFLINE
```

Each message ends with `\n`. The Python serial worker sends a changed count
immediately and resends the latest state at least once a second. It stores only
one pending message, so a slow or disconnected Arduino never creates a backlog.

| Input | LCD second row |
|---|---|
| `COUNT:0` | `COUNT: 00` |
| `COUNT:1` | `COUNT: 01` |
| `COUNT:12` | `COUNT: 12` |
| `STATUS:CAMERA_OFFLINE` | `CAMERA OFFLINE` |
| No valid message for over four seconds | `NO DATA` |

## Independent test

```powershell
.\.venv\Scripts\python.exe tools\test_lcd_serial.py --port COM_PORT
```

This runs a visible count sequence without camera or YOLO dependencies. Close
Arduino IDE Serial Monitor before running it.
