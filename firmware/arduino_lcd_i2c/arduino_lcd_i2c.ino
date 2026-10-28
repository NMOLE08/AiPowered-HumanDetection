// MCA Phase 5: Arduino Uno + 16x2 I2C LCD for live YOLO person counts.
// Wiring: VCC -> 5V, GND -> GND, SDA -> A4, SCL -> A5.
// Install "hd44780" by Bill Perry through Arduino IDE Library Manager.
// hd44780_I2Cexp detects common PCF8574 I2C backpack addresses automatically.

#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>
#include <string.h>

const byte LCD_COLUMNS = 16;
const byte LCD_ROWS = 2;
const byte RX_BUFFER_SIZE = 32;
const unsigned long NO_DATA_TIMEOUT_MS = 4000UL;
const unsigned int MAX_COUNT = 9999;

hd44780_I2Cexp lcd;
char receiveBuffer[RX_BUFFER_SIZE];
byte receiveLength = 0;
bool discardingLongMessage = false;
bool lcdReady = false;
unsigned long lastValidUpdate = 0;
char displayedLine1[LCD_COLUMNS + 1] = "";
char displayedLine2[LCD_COLUMNS + 1] = "";

void writeLine(byte row, const char *text, char *previousText) {
  char padded[LCD_COLUMNS + 1];
  byte index = 0;

  while (index < LCD_COLUMNS && text[index] != '\0') {
    padded[index] = text[index];
    index++;
  }
  while (index < LCD_COLUMNS) {
    padded[index++] = ' ';
  }
  padded[LCD_COLUMNS] = '\0';

  if (strcmp(padded, previousText) != 0) {
    lcd.setCursor(0, row);
    lcd.print(padded);
    strcpy(previousText, padded);
  }
}

void showScreen(const char *secondLine) {
  writeLine(0, "HUMAN DETECTOR", displayedLine1);
  writeLine(1, secondLine, displayedLine2);
}

void showCount(unsigned int count) {
  char line[LCD_COLUMNS + 1];
  if (count < 100) {
    snprintf(line, sizeof(line), "COUNT: %02u", count);
  } else {
    snprintf(line, sizeof(line), "COUNT: %u", count);
  }
  showScreen(line);
}

bool parseCount(const char *value, unsigned int *count) {
  if (value[0] == '\0') {
    return false;
  }

  unsigned long parsed = 0;
  for (byte index = 0; value[index] != '\0'; index++) {
    if (value[index] < '0' || value[index] > '9') {
      return false;
    }
    parsed = parsed * 10UL + (unsigned long)(value[index] - '0');
    if (parsed > MAX_COUNT) {
      return false;
    }
  }
  *count = (unsigned int)parsed;
  return true;
}

void processMessage(char *message) {
  const char countPrefix[] = "COUNT:";
  const char offlineMessage[] = "STATUS:CAMERA_OFFLINE";

  if (strncmp(message, countPrefix, strlen(countPrefix)) == 0) {
    unsigned int count = 0;
    if (parseCount(message + strlen(countPrefix), &count)) {
      showCount(count);
      lastValidUpdate = millis();
    }
    return;
  }

  if (strcmp(message, offlineMessage) == 0) {
    showScreen("CAMERA OFFLINE");
    lastValidUpdate = millis();
  }
}

void readSerialMessages() {
  while (Serial.available() > 0) {
    const char incoming = (char)Serial.read();

    if (incoming == '\n') {
      if (!discardingLongMessage && receiveLength > 0) {
        receiveBuffer[receiveLength] = '\0';
        processMessage(receiveBuffer);
      }
      receiveLength = 0;
      discardingLongMessage = false;
    } else if (incoming != '\r') {
      if (!discardingLongMessage) {
        if (receiveLength < RX_BUFFER_SIZE - 1) {
          receiveBuffer[receiveLength++] = incoming;
        } else {
          // Ignore every remaining byte of an oversized message until newline.
          receiveLength = 0;
          discardingLongMessage = true;
        }
      }
    }
  }
}

void setup() {
  Serial.begin(115200);

  const int lcdStatus = lcd.begin(LCD_COLUMNS, LCD_ROWS);
  if (lcdStatus != 0) {
    Serial.print("LCD INIT FAILED: ");
    Serial.println(lcdStatus);
    return;
  }

  lcdReady = true;
  lcd.backlight();
  showScreen("WAITING FOR PC");
  lastValidUpdate = millis();
  Serial.println("Arduino LCD ready");
}

void loop() {
  if (!lcdReady) {
    return;
  }
  readSerialMessages();

  if ((unsigned long)(millis() - lastValidUpdate) > NO_DATA_TIMEOUT_MS) {
    showScreen("NO DATA");
  }
}
