#include <Arduino.h>

const int MIST_PIN = 26;

// Change these 2 values as you want.
const int ON_TIME_MS = 5000;
const int OFF_TIME_MS = 5000;

void setup() {
	Serial.begin(115200);
	pinMode(MIST_PIN, OUTPUT);
	digitalWrite(MIST_PIN, LOW); // Start OFF
}

void loop() {
	digitalWrite(MIST_PIN, HIGH); // Mist ON
	Serial.println("Mist ON");
	delay(ON_TIME_MS);

	digitalWrite(MIST_PIN, LOW); // Mist OFF
	Serial.println("Mist OFF");
	delay(OFF_TIME_MS);
}
