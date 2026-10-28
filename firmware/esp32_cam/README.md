# ESP32-CAM firmware — use the official CameraWebServer example

Official Arduino-ESP32 example: https://github.com/espressif/arduino-esp32/tree/master/libraries/ESP32/examples/Camera/CameraWebServer

No custom camera sketch is required.

1. Arduino IDE -> Boards Manager -> install `esp32` by Espressif Systems.
2. File -> Examples -> ESP32 -> Camera -> CameraWebServer.
3. In the `board_config.h` tab, **comment out** `#define CAMERA_MODEL_ESP_EYE` and **uncomment** `#define CAMERA_MODEL_AI_THINKER`. If your module is not AI-Thinker, pick its matching definition.
4. In `CameraWebServer.ino`, set `ssid` and `password` to the same **2.4 GHz** Wi-Fi used by the laptop.
5. Select **AI Thinker ESP32-CAM** in the Arduino-ESP32 board menu and a partition scheme allowing **>= 3 MB app space**; 115200 upload speed is a conservative setting.
6. Flash using a **3.3 V logic** USB-to-UART interface. Cross TX to CAM U0R, RX to CAM U0T, connect GND; power the CAM at its 5V pin with a stable 5V source. Keep CAM GPIO0 to GND at reset for flashing.
7. After success, remove CAM GPIO0-GND jumper, reset CAM. Serial monitor at 115200 prints its local network host.
8. Check `http://CAMERA_HOST/` from laptop browser, select QVGA (320x240) or VGA (640x480), and press Start Stream.
9. For Python, use `http://CAMERA_HOST:81/stream` (default Espressif firmware stream endpoint).

## Optional: use your existing ESP32 DevKit as USB-to-serial bridge
Only when the ESP32 DevKit exposes USB-UART TX0/RX0 and its USB-UART bridge remains active with EN grounded:
- DevKit EN -> GND (holds DevKit ESP32 CPU in reset)
- DevKit TX0/GPIO1 -> CAM U0R/GPIO3
- DevKit RX0/GPIO3 -> CAM U0T/GPIO1
- DevKit GND -> CAM GND
- CAM GPIO0 -> CAM GND for flashing only
- Separate stable 5 V source -> CAM 5V; power source GND -> common GND
- DevKit USB -> laptop

USB-UART circuit wiring and camera supply capability vary between ESP32 boards. A dedicated USB-UART or ESP32-CAM-MB adapter is safer if uncertain. Do not use Arduino Uno 5V UART TX directly into the CAM 3.3V input.
