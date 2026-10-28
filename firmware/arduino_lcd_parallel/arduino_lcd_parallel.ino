// MCA Human Counter - bare 16-pin HD44780 LCD and Arduino Uno
// Wire: RS=D12, E=D11, D4=D5, D5=D4, D6=D3, D7=D2, RW=GND
// Contrast: LCD VO -> wiper of a 10k pot between +5V and GND.
#include <LiquidCrystal.h>
#include <stdlib.h>

LiquidCrystal lcd(12, 11, 5, 4, 3, 2);
char numberBuffer[8];
byte pos = 0;
unsigned long lastMessage = 0;
bool showingOffline = false;

void showCount(int count) {
  lcd.setCursor(0, 0);
  lcd.print("HUMAN DETECTOR  ");
  lcd.setCursor(0, 1);
  lcd.print("Humans:         ");
  lcd.setCursor(8, 1);
  lcd.print(count);
  showingOffline = false;
}

void setup() {
  Serial.begin(9600);
  lcd.begin(16, 2);
  lcd.setCursor(0, 0);
  lcd.print("HUMAN DETECTOR");
  lcd.setCursor(0, 1);
  lcd.print("Waiting for PC");
  lastMessage = millis();
}

void loop() {
  while (Serial.available() > 0) {
    char ch = (char)Serial.read();
    if (ch == '\n') {
      numberBuffer[pos] = '\0';
      if (pos > 0) {
        int count = atoi(numberBuffer);
        showCount(count);
        lastMessage = millis();
      }
      pos = 0;
    } else if (ch >= '0' && ch <= '9') {
      if (pos < sizeof(numberBuffer) - 1) {
        numberBuffer[pos++] = ch;
      } else {
        pos = 0;
      }
    } else if (ch != '\r') {
      pos = 0;
    }
  }
  if (!showingOffline && millis() - lastMessage > 5000UL) {
    lcd.setCursor(0, 1);
    lcd.print("Signal lost     ");
    showingOffline = true;
  }
}
