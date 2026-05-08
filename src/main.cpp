#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <math.h>
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

// Battery monitoring configuration
#define BATTERY_ADC_PIN 34
#define NUM_SAMPLES 2500
#define DHT_AVG_SAMPLES 5
#define VOLTAGE_STEP 0.0024898648648649

// BLE UUIDs
#define SERVICE_UUID "FFF0"
#define SENSOR_CHAR_UUID "FFF1" // "temp,humid,soil,batteryV" e.g. "24.5,60.0,2100,7.8"
#define CTRL_CHAR_UUID "FFF4"   // "mode,mist,pump" e.g. "0,1,0"
#define THRESH_CHAR_UUID "FFF7" // "tempThresh,humidThresh,soilThresh" e.g. "21.0,40.0,2416"

// OLED display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define SCREEN_ADDRESS 0x3C

// BLE notification interval (1 minute)
#define BLE_NOTIFY_INTERVAL_MS 5000

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
DHT dht(DHTPIN, DHTTYPE);

// BLE variables
BLEServer *pServer = NULL;
BLECharacteristic *pSensorCharacteristic = NULL;
BLECharacteristic *pControlCharacteristic = NULL;
BLECharacteristic *pThreshCharacteristic = NULL;

bool deviceConnected = false;
bool oldDeviceConnected = false;

// Timing variables
unsigned long lastBleNotifyTime = 0;

// ============================================
// CONTROL VARIABLES
// ============================================
bool autoMode = true;                // true = automatic, false = manual
bool mistManualOn = false;           // Manual mist state
bool pumpManualOn = false;           // Manual pump state
float temperature_threshold = 21.0;  // Turn on mist if temp > threshold
float humidity_threshold = 40.0;     // Turn on mist if humidity < threshold
int soil_threshold = 2416;           // Turn on pump if soil > threshold (dry)

// Battery variables
float batteryVoltage = 0.0;
float temperatureAverage = 0.0;
float humidityAverage = 0.0;

float dhtTempSamples[DHT_AVG_SAMPLES] = {0.0};
float dhtHumiditySamples[DHT_AVG_SAMPLES] = {0.0};
int dhtSampleIndex = 0;
int dhtSampleCount = 0;
float dhtTempSum = 0.0;
float dhtHumiditySum = 0.0;

// ============================================
// BATTERY FUNCTION
// ============================================
float readBatteryVoltage()
{
    unsigned long sum = 0;
    for (int i = 0; i < NUM_SAMPLES; ++i)
    {
        sum += analogRead(BATTERY_ADC_PIN);
    }
    float avg_adc = (float)sum / (float)NUM_SAMPLES;
    return avg_adc * VOLTAGE_STEP;
}

int readSoilMoistureAverage()
{
    unsigned long sum = 0;
    for (int i = 0; i < NUM_SAMPLES; ++i)
    {
        sum += analogRead(SOIL_SENSOR_PIN);
    }
    return (int)((float)sum / (float)NUM_SAMPLES);
}

bool updateDhtAverages(float temperature, float humidity, float &avgTemperature, float &avgHumidity)
{
    if (isnan(temperature) || isnan(humidity))
    {
        return false;
    }

    if (dhtSampleCount < DHT_AVG_SAMPLES)
    {
        dhtTempSamples[dhtSampleIndex] = temperature;
        dhtHumiditySamples[dhtSampleIndex] = humidity;
        dhtTempSum += temperature;
        dhtHumiditySum += humidity;
        dhtSampleCount++;
    }
    else
    {
        dhtTempSum -= dhtTempSamples[dhtSampleIndex];
        dhtHumiditySum -= dhtHumiditySamples[dhtSampleIndex];
        dhtTempSamples[dhtSampleIndex] = temperature;
        dhtHumiditySamples[dhtSampleIndex] = humidity;
        dhtTempSum += temperature;
        dhtHumiditySum += humidity;
    }

    dhtSampleIndex = (dhtSampleIndex + 1) % DHT_AVG_SAMPLES;
    avgTemperature = dhtTempSum / (float)dhtSampleCount;
    avgHumidity = dhtHumiditySum / (float)dhtSampleCount;
    return true;
}

void startBleAdvertising()
{
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    BLEDevice::startAdvertising();
}

void renderDisplay(float temperature, float humidity, int soilMoistureValue, bool mistOn, bool pumpOn)
{
    display.clearDisplay();
    display.setTextSize(1); // Large font for better visibility
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);

    // Line 1: BLE status, Mode, Battery voltage
    display.print(F("BLE:"));
    display.print(deviceConnected ? F("OK") : F("--"));
    display.print(F("  "));
    display.print(autoMode ? F("AUTO") : F("MAN"));
    display.print(F("  "));
    display.print(batteryVoltage, 1);
    display.println(F("V"));

    // Line 2: Temperature and Humidity
    display.print(F("T:"));
    display.print(temperature, 1);
    display.print(F("C  "));
    display.print(F("H:"));
    display.print(humidity, 0);
    display.println(F("%"));

    // Line 3: Soil and Actuators
    display.print(F("S:"));
    display.print(soilMoistureValue);
    display.print(F("  "));
    display.print(F("M:"));
    display.print(mistOn ? F("ON") : F("OFF"));
    display.print(F("  "));
    display.print(F("P:"));
    display.println(pumpOn ? F("ON") : F("OFF"));

    // Line 4: Thresholds
    display.print(F("Th T:"));
    display.print((int)temperature_threshold);
    display.print(F("  "));
    display.print(F("H:"));
    display.print((int)humidity_threshold);
    display.print(F("  "));
    display.print(F("S:"));
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
        float humidThresh = humidity_threshold;
        int soilThresh = soil_threshold;
        if (sscanf(value.c_str(), "%f,%f,%d", &tempThresh, &humidThresh, &soilThresh) == 3)
        {
            temperature_threshold = tempThresh;
            humidity_threshold = humidThresh;
            soil_threshold = soilThresh;
            Serial.print("Thresholds updated: T=");
            Serial.print(temperature_threshold);
            Serial.print(" C, H=");
            Serial.print(humidity_threshold);
            Serial.print(" %, S=");
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
    pinMode(BATTERY_ADC_PIN, INPUT);
    pinMode(MIST_PIN, OUTPUT);
    pinMode(PUMP_PIN, OUTPUT);
    digitalWrite(MIST_PIN, LOW);
    digitalWrite(PUMP_PIN, LOW);

    BLEDevice::init("Greenhouse Monitor system");
    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());

    BLEService *pService = pServer->createService(SERVICE_UUID);

    pSensorCharacteristic = pService->createCharacteristic(
        SENSOR_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    pSensorCharacteristic->addDescriptor(new BLE2902());
    pSensorCharacteristic->setValue("0.0,0.0,0,0.0");

    pControlCharacteristic = pService->createCharacteristic(
        CTRL_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY);
    pControlCharacteristic->addDescriptor(new BLE2902());
    pControlCharacteristic->setCallbacks(new ControlCallbacks());
    pControlCharacteristic->setValue("0,0,0");

    pThreshCharacteristic = pService->createCharacteristic(
        THRESH_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_NOTIFY);
    pThreshCharacteristic->addDescriptor(new BLE2902());
    pThreshCharacteristic->setCallbacks(new ThreshCallbacks());
    pThreshCharacteristic->setValue("21.0,40.0,2416");

    pService->start();
    
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS))
    {
        Serial.println("OLED init failed");
        for (;;)
            ;
    }
    
    startBleAdvertising();
    
    // Initial battery reading
    batteryVoltage = readBatteryVoltage();
    
    renderDisplay(0, 0, 0, false, false);
    Serial.println("Greenhouse Monitor ready!");
    delay(2000);
}

void loop()
{
    unsigned long currentMillis = millis();
    
    // Read temperature and humidity from DHT11 sensor
    float humidityRaw = dht.readHumidity();
    float temperatureRaw = dht.readTemperature();
    updateDhtAverages(temperatureRaw, humidityRaw, temperatureAverage, humidityAverage);
    float humidity = humidityAverage;
    float temperature = temperatureAverage;

    // Read soil moisture sensor
    int soilMoistureValue = readSoilMoistureAverage();
    
    // Read battery voltage
    batteryVoltage = readBatteryVoltage();

    // BLE notification every 1 minute
    if (deviceConnected && (currentMillis - lastBleNotifyTime >= BLE_NOTIFY_INTERVAL_MS))
    {
        lastBleNotifyTime = currentMillis;
        
        // Send sensor data: "temp,humid,soil,batteryV"
        char sensorString[32];
        snprintf(sensorString, sizeof(sensorString), "%.1f,%.1f,%d,%.1f",
                 temperature,
                 humidity,
                 soilMoistureValue,
                 batteryVoltage);
        pSensorCharacteristic->setValue(sensorString);
        pSensorCharacteristic->notify();
        
        // Send current control values: "mode,mist_actual,pump_actual"
        // This sends the ACTUAL state of the actuators, not just manual commands
        bool mistActual = false;
        bool pumpActual = false;
        
        if (autoMode) {
            // In AUTO mode, actuators are controlled by thresholds
            // Mist turns ON if temp > threshold OR humidity < threshold
            mistActual = (temperature > temperature_threshold || humidity < humidity_threshold);
            pumpActual = (soilMoistureValue > soil_threshold);
        } else {
            // In MANUAL mode, actuators are controlled by dashboard
            mistActual = mistManualOn;
            pumpActual = pumpManualOn;
        }
        
        char controlString[10];
        snprintf(controlString, sizeof(controlString), "%d,%d,%d",
                 autoMode ? 0 : 1,
                 mistActual ? 1 : 0,
                 pumpActual ? 1 : 0);
        pControlCharacteristic->setValue(controlString);
        pControlCharacteristic->notify();  // Notify the control values

        // Send threshold values
        char threshString[24];
        snprintf(threshString, sizeof(threshString), "%.1f,%.1f,%d",
             temperature_threshold,
             humidity_threshold,
             soil_threshold);
        pThreshCharacteristic->setValue(threshString);
        pThreshCharacteristic->notify();  // Notify the threshold values
        
        Serial.print("BLE notify: ");
        Serial.print(sensorString);
        Serial.print(" | Control: ");
        Serial.print(controlString);
        Serial.print(" | Battery: ");
        Serial.print(batteryVoltage, 2);
        Serial.println("V");
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
        lastBleNotifyTime = currentMillis; // Reset timer on new connection
        Serial.println("BLE connected");
    }

    // Actuator control logic
    bool mistOn = false;
    bool pumpOn = false;
    
    if (autoMode)
    {
        // AUTOMATIC MODE - Control based on thresholds
        if (temperature > temperature_threshold || humidity < humidity_threshold)
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
    
    // Short delay for display update (not for BLE timing)
    delay(5000);
}
