# Hardware wiring

## Running circuit

ESP32-CAM: 5V -> regulated 5V; GND -> power GND. Leave GPIO0 open, no ESP32-CAM-to-Arduino direct wiring. Video is transferred over local 2.4GHz Wi-Fi.

Arduino Uno: USB cable to laptop both for power and serial data.

### 4-pin I2C LCD (PCF8574 backpack or compatible)

| LCD | Arduino Uno |
|---|---|
| VCC | 5V |
| GND | GND |
| SDA | A4 |
| SCL | A5 |

Upload `firmware/arduino_lcd_i2c/arduino_lcd_i2c.ino`. Install **hd44780 by Bill Perry** using Arduino IDE Library Manager.

### Bare 16-pin HD44780 LCD, 4-bit mode

| LCD pin | Arduino Uno connection |
|---|---|
| 1 VSS | GND |
| 2 VDD | 5V |
| 3 VO | center terminal of 10k contrast potentiometer |
| 4 RS | D12 |
| 5 RW | GND |
| 6 E | D11 |
| 7-10 D0-D3 | disconnected |
| 11 D4 | D5 |
| 12 D5 | D4 |
| 13 D6 | D3 |
| 14 D7 | D2 |
| 15 LED+/A | 5V via current limiting resistor unless LCD has built-in resistor |
| 16 LED-/K | GND |

Contrast potentiometer outside terminals: 5V and GND. Upload `firmware/arduino_lcd_parallel/arduino_lcd_parallel.ino`. `LiquidCrystal` is included with Arduino IDE.

## Camera flashing with USB-to-serial adapter

| USB-UART | ESP32-CAM |
|---|---|
| UART TX (3.3V logic) | U0R (GPIO3) |
| UART RX (3.3V logic) | U0T (GPIO1) |
| GND | GND |
| Stable power 5V | 5V |
| temporary jumper | GPIO0 -> GND while flashing |

Do not apply 5V *logic* to CAM input pins. Avoid using unstable 3.3V adapter regulator to power Wi-Fi camera; use its 5V input with adequate power supply. Power down before changing wiring.

If using ESP32 DevKit as an adapter, see `firmware/esp32_cam/README.md` for conditional setup.
