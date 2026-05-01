#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <stdio.h>

// DHT11 Sensor configuration
#define DHTPIN 5      // Pin connected to DHT11 sensor
#define DHTTYPE DHT11 // DHT 11

// Actuator pins
#define MIST_PIN 26 // Mist maker/humidifier relay
#define PUMP_PIN 32 // Water pump relay

// SDA = 21, SCL = 22
// Soil Moisture Sensor configuration
#define SOIL_SENSOR_PIN 33 // Analog pin for soil moisture sensor

#define SERVICE_UUID "FFF0"
// Sensor characteristics (READ + NOTIFY)
#define SENSOR_CHAR_UUID "FFF1" // "temp,humid,soil" e.g. "24.5,60.0,2100"
// Control characteristics (READ + WRITE)
#define CTRL_CHAR_UUID "FFF4"   // "mode,mist,pump" e.g. "0,1,0"
#define THRESH_CHAR_UUID "FFF7" // "tempThresh,soilThresh" e.g. "25.0,2500"

// OLED display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
DHT dht(DHTPIN, DHTTYPE);

// BLE variables
BLEServer *pServer = NULL;
BLECharacteristic *pSensorCharacteristic = NULL;
BLECharacteristic *pControlCharacteristic = NULL;
BLECharacteristic *pThreshCharacteristic = NULL;

bool deviceConnected = false;
bool oldDeviceConnected = false;

// ============================================
// CONTROL VARIABLES
// ============================================
bool autoMode = true;               // true = automatic, false = manual
bool mistManualOn = false;          // Manual mist state
bool pumpManualOn = false;          // Manual pump state
float temperature_threshold = 25.0; // Turn on mist if temp > threshold
int soil_threshold = 2500;          // Turn on pump if soil > threshold (dry)

void startBleAdvertising()
{
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    // pAdvertising->setScanResponse(true);
    // pAdvertising->setMinPreferred(0x06);
    // pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();
}

void renderDisplay(float temperature, float humidity, int soilMoistureValue, bool mistOn, bool pumpOn)
{
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);

    display.print(F("BLE:"));
    display.print(deviceConnected ? F("OK") : F("--"));
    display.print(F(" "));
    display.println(autoMode ? F("AUTO") : F("MAN"));

    display.print(F("T:"));
    display.print(temperature, 1);
    display.print(F("C  H:"));
    display.print(humidity, 0);
    display.println(F("%"));

    display.print(F("S:"));
    display.print(soilMoistureValue);
    display.print(F("  M:"));
    display.print(mistOn ? F("ON") : F("OFF"));
    display.print(F(" P:"));
    display.println(pumpOn ? F("ON") : F("OFF"));

    display.print(F("Th T:"));
    display.print((int)temperature_threshold);
    display.print(F(" S:"));
    display.print(soil_threshold);

    display.display();
}
// BLE CALLBACKS FOR WRITEABLE CHARACTERISTICS
class ControlCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        String value = pCharacteristic->getValue().c_str();
        if (value.length() == 0)
            return;
        int mode = -1;
        int mist = -1;
        int pump = -1;
        if (sscanf(value.c_str(), "%d,%d,%d", &mode, &mist, &pump) == 3)
        {
            autoMode = (mode == 0);
            mistManualOn = (mist == 1);
            pumpManualOn = (pump == 1);
            Serial.print("Control updated: mode=");
            Serial.print(autoMode ? "AUTO" : "MANUAL");
            Serial.print(" mist=");
            Serial.print(mistManualOn ? "ON" : "OFF");
            Serial.print(" pump=");
            Serial.println(pumpManualOn ? "ON" : "OFF");
        }
    }
};
class ThreshCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic *pCharacteristic)
    {
        String value = pCharacteristic->getValue().c_str();
        if (value.length() == 0)
            return;

        float tempThresh = temperature_threshold;
        int soilThresh = soil_threshold;
        if (sscanf(value.c_str(), "%f,%d", &tempThresh, &soilThresh) == 2)
        {
            temperature_threshold = tempThresh;
            soil_threshold = soilThresh;
            Serial.print("Thresholds updated: T=");
            Serial.print(temperature_threshold);
            Serial.print(" C, S=");
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
    delay(300);
    Serial.println("\nGreenhouse Monitor booting...");
    dht.begin();
    pinMode(SOIL_SENSOR_PIN, INPUT);
    pinMode(MIST_PIN, OUTPUT);
    pinMode(PUMP_PIN, OUTPUT);
    digitalWrite(MIST_PIN, LOW);
    digitalWrite(PUMP_PIN, LOW);

    BLEDevice::init("Greenhouse Monitor system");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    BLEService *pService = pServer->createService(SERVICE_UUID);
    // Serial.println("BLE service FFF0 created");

    pSensorCharacteristic = pService->createCharacteristic(
        SENSOR_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    pSensorCharacteristic->addDescriptor(new BLE2902());
    pSensorCharacteristic->setValue("0.0,0.0,0");
    // Serial.println("Char FFF1 (sensor) created");

    pControlCharacteristic = pService->createCharacteristic(
        CTRL_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    pControlCharacteristic->setCallbacks(new ControlCallbacks());
    pControlCharacteristic->setValue("0,0,0");
    // Serial.println("Char FFF4 (control) created");
    pThreshCharacteristic = pService->createCharacteristic(
        THRESH_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
    pThreshCharacteristic->setCallbacks(new ThreshCallbacks());
    pThreshCharacteristic->setValue("30.0,2500");
    // Serial.println("Char FFF7 (thresholds) created");
    pService->start();
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS))
    {
        Serial.println("OLED init failed");
        for (;;)
            ;
    }
    startBleAdvertising();
    renderDisplay(0, 0, 0, false, false);
    // Serial.println("Advertising Greenhouse Monitor...");
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
    if (deviceConnected)
    {
        char sensorString[24];
        snprintf(sensorString, sizeof(sensorString), "%.1f,%.1f,%d",
                 temperature,
                 humidity,
                 soilMoistureValue);
        pSensorCharacteristic->setValue(sensorString);
        pSensorCharacteristic->notify();

        // Send current control values
        char controlString[10];
        char threshString[16];

        snprintf(controlString, sizeof(controlString), "%d,%d,%d",
                 autoMode ? 0 : 1,
                 mistManualOn ? 1 : 0,
                 pumpManualOn ? 1 : 0);
        pControlCharacteristic->setValue(controlString);

        snprintf(threshString, sizeof(threshString), "%.1f,%d",
                 temperature_threshold,
                 soil_threshold);
        pThreshCharacteristic->setValue(threshString);
    }

    // Handle BLE disconnection/reconnection
    if (!deviceConnected && oldDeviceConnected)
    {
        delay(300);
        startBleAdvertising();
        Serial.println("BLE advertising restarted");
        oldDeviceConnected = deviceConnected;
    }

    if (deviceConnected && !oldDeviceConnected)
    {
        oldDeviceConnected = deviceConnected;
        Serial.println("BLE connected");
    }

    bool mistOn = false;
    bool pumpOn = false;
    if (autoMode)
    {
        // AUTOMATIC MODE - Control based on thresholds
        if (temperature > temperature_threshold)
        {
            digitalWrite(MIST_PIN, HIGH);
            mistOn = true;
        }
        else
        {
            digitalWrite(MIST_PIN, LOW);
            mistOn = false;
        }

        if (soilMoistureValue > soil_threshold)
        {
            digitalWrite(PUMP_PIN, HIGH);
            pumpOn = true;
        }
        else
        {
            digitalWrite(PUMP_PIN, LOW);
            pumpOn = false;
        }
    }
    else
    {
        // MANUAL MODE - Control from dashboard
        if (mistManualOn)
        {
            digitalWrite(MIST_PIN, HIGH);
            mistOn = true;
        }
        else
        {
            digitalWrite(MIST_PIN, LOW);
            mistOn = false;
        }

        if (pumpManualOn)
        {
            digitalWrite(PUMP_PIN, HIGH);
            pumpOn = true;
        }
        else
        {
            digitalWrite(PUMP_PIN, LOW);
            pumpOn = false;
        }
    }
    renderDisplay(temperature, humidity, soilMoistureValue, mistOn, pumpOn);
    delay(10000);
}
