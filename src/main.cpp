#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// DHT11 Sensor configuration
#define DHTPIN 5      // Pin connected to DHT11 sensor
#define DHTTYPE DHT11 // DHT 11

//mist 26
//motor 32
#define MIST_PIN 18
#define PUMP_PIN 19

// OLED Display I2C pins (ESP32 default)
// SDA = 21, SCL = 22

// Soil Moisture Sensor configuration
#define SOIL_SENSOR_PIN 33 // Analog pin for soil moisture sensor

// ============================================
// BLE UUIDs
// ============================================
#define SERVICE_UUID "4fafc201-1fb5-459e-8fcc-c5c9c331914b"

// Sensor characteristics (READ + NOTIFY)
#define TEMP_CHAR_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define HUMID_CHAR_UUID "ceb5483e-36e1-4688-b7f5-ea07361b26a8"
#define SOIL_MOIST_UUID "d2c5483e-36e1-4688-b7f5-ea07361b26a8"

// Control characteristics (READ + WRITE)
#define MODE_CHAR_UUID "a1b5483e-36e1-4688-b7f5-ea07361b26a8"      // 0=auto, 1=manual
#define MIST_CTRL_UUID "a2b5483e-36e1-4688-b7f5-ea07361b26a8"      // 0=off, 1=on (manual mode)
#define PUMP_CTRL_UUID "a3b5483e-36e1-4688-b7f5-ea07361b26a8"      // 0=off, 1=on (manual mode)
#define TEMP_THRESH_UUID "a4b5483e-36e1-4688-b7f5-ea07361b26a8"    // Temperature threshold
#define SOIL_THRESH_UUID "a5b5483e-36e1-4688-b7f5-ea07361b26a8"    // Soil moisture threshold

// OLED display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
DHT dht(DHTPIN, DHTTYPE);

// BLE variables
BLEServer *pServer = NULL;
BLECharacteristic *pTempCharacteristic = NULL;
BLECharacteristic *pHumidCharacteristic = NULL;
BLECharacteristic *pSoilMoistCharacteristic = NULL;
BLECharacteristic *pModeCharacteristic = NULL;
BLECharacteristic *pMistCtrlCharacteristic = NULL;
BLECharacteristic *pPumpCtrlCharacteristic = NULL;
BLECharacteristic *pTempThreshCharacteristic = NULL;
BLECharacteristic *pSoilThreshCharacteristic = NULL;

bool deviceConnected = false;
bool oldDeviceConnected = false;

// ============================================
// CONTROL VARIABLES
// ============================================
bool autoMode = true;               // true = automatic, false = manual
bool mistManualOn = false;          // Manual mist state
bool pumpManualOn = false;          // Manual pump state
float temperature_threshold = 30.0; // Turn on mist if temp > threshold
int soil_threshold = 2500;          // Turn on pump if soil > threshold (dry)

// ============================================
// BLE CALLBACKS FOR WRITEABLE CHARACTERISTICS
// ============================================
class ModeCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        String value = pCharacteristic->getValue().c_str();
        if (value.length() > 0)
        {
            int mode = value.toInt();
            autoMode = (mode == 0); // 0 = auto, 1 = manual
            Serial.print("Mode changed to: ");
            Serial.println(autoMode ? "AUTO" : "MANUAL");
        }
    }
};

class MistCtrlCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        String value = pCharacteristic->getValue().c_str();
        if (value.length() > 0)
        {
            mistManualOn = (value.toInt() == 1);
            Serial.print("Mist manual control: ");
            Serial.println(mistManualOn ? "ON" : "OFF");
        }
    }
};

class PumpCtrlCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        String value = pCharacteristic->getValue().c_str();
        if (value.length() > 0)
        {
            pumpManualOn = (value.toInt() == 1);
            Serial.print("Pump manual control: ");
            Serial.println(pumpManualOn ? "ON" : "OFF");
        }
    }
};

class TempThreshCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        String value = pCharacteristic->getValue().c_str();
        if (value.length() > 0)
        {
            temperature_threshold = value.toFloat();
            Serial.print("Temperature threshold set to: ");
            Serial.print(temperature_threshold);
            Serial.println(" C");
        }
    }
};

class SoilThreshCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        String value = pCharacteristic->getValue().c_str();
        if (value.length() > 0)
        {
            soil_threshold = value.toInt();
            Serial.print("Soil threshold set to: ");
            Serial.println(soil_threshold);
        }
    }
};

// BLE Server Callbacks
class MyServerCallbacks : public BLEServerCallbacks
{
    void onConnect(BLEServer *pServer)
    {
        deviceConnected = true;
        Serial.println("BLE Client Connected");
    }

    void onDisconnect(BLEServer *pServer)
    {
        deviceConnected = false;
        Serial.println("BLE Client Disconnected");
    }
};

void setup()
{
    Serial.begin(115200);

    // Initialize DHT sensor
    dht.begin();

    // Initialize soil moisture sensor pin
    pinMode(SOIL_SENSOR_PIN, INPUT);

    // Initialize mist and pump pins
    pinMode(MIST_PIN, OUTPUT);
    pinMode(PUMP_PIN, OUTPUT);
    digitalWrite(MIST_PIN, LOW);
    digitalWrite(PUMP_PIN, LOW);

    // Initialize BLE
    BLEDevice::init("Greenhouse Monitor");

    // Create BLE Server
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    // Create BLE Service
    BLEService *pService = pServer->createService(SERVICE_UUID);

    // ============================================
    // SENSOR CHARACTERISTICS (READ + NOTIFY)
    // ============================================
    pTempCharacteristic = pService->createCharacteristic(
        TEMP_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    pTempCharacteristic->addDescriptor(new BLE2902());

    pHumidCharacteristic = pService->createCharacteristic(
        HUMID_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    pHumidCharacteristic->addDescriptor(new BLE2902());

    pSoilMoistCharacteristic = pService->createCharacteristic(
        SOIL_MOIST_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    pSoilMoistCharacteristic->addDescriptor(new BLE2902());

    // ============================================
    // CONTROL CHARACTERISTICS (READ + WRITE)
    // ============================================
    pModeCharacteristic = pService->createCharacteristic(
        MODE_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    pModeCharacteristic->setCallbacks(new ModeCallbacks());

    pMistCtrlCharacteristic = pService->createCharacteristic(
        MIST_CTRL_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    pMistCtrlCharacteristic->setCallbacks(new MistCtrlCallbacks());

    pPumpCtrlCharacteristic = pService->createCharacteristic(
        PUMP_CTRL_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    pPumpCtrlCharacteristic->setCallbacks(new PumpCtrlCallbacks());

    pTempThreshCharacteristic = pService->createCharacteristic(
        TEMP_THRESH_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    pTempThreshCharacteristic->setCallbacks(new TempThreshCallbacks());

    pSoilThreshCharacteristic = pService->createCharacteristic(
        SOIL_THRESH_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    pSoilThreshCharacteristic->setCallbacks(new SoilThreshCallbacks());

    // Start the service
    pService->start();

    // Start advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    BLEDevice::startAdvertising();
    Serial.println("BLE Advertising started. Device name: Greenhouse Monitor");

    // Initialize the OLED display
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS))
    {
        Serial.println(F("SSD1306 allocation failed"));
        for (;;);
    }

    // Display startup message
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println(F("Greenhouse"));
    display.println(F("Monitoring"));
    display.println(F("System"));
    display.println();
    display.println(F("BLE: Active"));
    display.setTextSize(2);
    display.println(F("Ready!"));
    display.display();

    delay(2000);
}

void loop()
{
    // Read temperature and humidity from DHT11 sensor
    float humidity = dht.readHumidity();
    float temperature = dht.readTemperature();

    // Read soil moisture sensor
    int soilMoistureValue = analogRead(SOIL_SENSOR_PIN);

    // Check if readings failed
    if (isnan(humidity) || isnan(temperature))
    {
        Serial.println("Failed to read from DHT sensor!");
    }
    else
    {
        // Print to Serial Monitor
        Serial.print("Humidity: ");
        Serial.print(humidity);
        Serial.print("%  Temperature: ");
        Serial.print(temperature);
        Serial.print(" C  Soil: ");
        Serial.print(soilMoistureValue);
        Serial.print("  Mode: ");
        Serial.print(autoMode ? "AUTO" : "MANUAL");
        Serial.print("  BLE: ");
        Serial.println(deviceConnected ? "Connected" : "Disconnected");

        // Send sensor data via BLE
        if (deviceConnected)
        {
            char tempString[8];
            char humidString[8];
            char soilMoistString[8];
            dtostrf(temperature, 4, 1, tempString);
            dtostrf(humidity, 4, 1, humidString);
            dtostrf(soilMoistureValue, 4, 0, soilMoistString);

            pTempCharacteristic->setValue(tempString);
            pTempCharacteristic->notify();

            pHumidCharacteristic->setValue(humidString);
            pHumidCharacteristic->notify();

            pSoilMoistCharacteristic->setValue(soilMoistString);
            pSoilMoistCharacteristic->notify();

            // Send current control values
            char modeString[2];
            char threshString[8];
            
            modeString[0] = autoMode ? '0' : '1';
            modeString[1] = '\0';
            pModeCharacteristic->setValue(modeString);

            modeString[0] = mistManualOn ? '1' : '0';
            pMistCtrlCharacteristic->setValue(modeString);

            modeString[0] = pumpManualOn ? '1' : '0';
            pPumpCtrlCharacteristic->setValue(modeString);

            dtostrf(temperature_threshold, 4, 1, threshString);
            pTempThreshCharacteristic->setValue(threshString);

            dtostrf(soil_threshold, 4, 0, threshString);
            pSoilThreshCharacteristic->setValue(threshString);
        }
    }

    // Handle BLE disconnection/reconnection
    if (!deviceConnected && oldDeviceConnected)
    {
        delay(500);
        pServer->startAdvertising();
        Serial.println("Start advertising");
        oldDeviceConnected = deviceConnected;
    }

    if (deviceConnected && !oldDeviceConnected)
    {
        oldDeviceConnected = deviceConnected;
    }

    // ============================================
    // ACTUATOR CONTROL LOGIC
    // ============================================
    bool mistOn = false;
    bool pumpOn = false;

    if (autoMode)
    {
        // AUTOMATIC MODE - Control based on thresholds
        if (temperature > temperature_threshold)
        {
            digitalWrite(MIST_PIN, HIGH);
            mistOn = true;
            Serial.println("Mist ON (Auto) - Temperature high");
        }
        else
        {
            digitalWrite(MIST_PIN, LOW);
            mistOn = false;
            Serial.println("Mist OFF (Auto) - Temperature normal");
        }

        if (soilMoistureValue > soil_threshold)
        {
            digitalWrite(PUMP_PIN, HIGH);
            pumpOn = true;
            Serial.println("Pump ON (Auto) - Soil dry");
        }
        else
        {
            digitalWrite(PUMP_PIN, LOW);
            pumpOn = false;
            Serial.println("Pump OFF (Auto) - Soil moist");
        }
    }
    else
    {
        // MANUAL MODE - Control from dashboard
        if (mistManualOn)
        {
            digitalWrite(MIST_PIN, HIGH);
            mistOn = true;
            Serial.println("Mist ON (Manual)");
        }
        else
        {
            digitalWrite(MIST_PIN, LOW);
            mistOn = false;
            Serial.println("Mist OFF (Manual)");
        }

        if (pumpManualOn)
        {
            digitalWrite(PUMP_PIN, HIGH);
            pumpOn = true;
            Serial.println("Pump ON (Manual)");
        }
        else
        {
            digitalWrite(PUMP_PIN, LOW);
            pumpOn = false;
            Serial.println("Pump OFF (Manual)");
        }
    }

    // ============================================
    // UPDATE OLED DISPLAY
    // ============================================
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);

    // Line 1: BLE and Mode status
    display.print(F("BLE:"));
    display.print(deviceConnected ? F("OK") : F("--"));
    display.print(F(" Mode:"));
    display.println(autoMode ? F("AUTO") : F("MAN"));

    // Sensor readings
    display.print(F("Temp:"));
    display.print(temperature, 1);
    display.print(F("C"));
    display.println(mistOn ? F(" [M]") : F(""));

    display.print(F("Hum:"));
    display.print(humidity, 0);
    display.print(F("% Soil:"));
    display.println(pumpOn ? F("[P]") : F(""));

    display.print(F("Soil:"));
    display.print(soilMoistureValue);

    // Thresholds
    display.println();
    display.print(F("T>"));
    display.print((int)temperature_threshold);
    display.print(F("C S>"));
    display.print(soil_threshold);

    display.display();

    // Wait 2 seconds between measurements
    delay(2000);
}
