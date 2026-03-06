#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
//prashntbhandari branch
// DHT11 Sensor configuration
#define DHTPIN 5          // Pin connected to DHT11 sensor
#define DHTTYPE DHT11     // DHT 11

#define mist 18
#define pump 19
//diplay 21 and 22 scl sda
//21 sda
//22 scl
// Soil Moisture Sensor configuration
#define SOIL_SENSOR_PIN 34 // Analog pin for soil moisture sensor (use appropriate pin for your board)

// BLE UUIDs
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define TEMP_CHAR_UUID      "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define HUMID_CHAR_UUID     "ceb5483e-36e1-4688-b7f5-ea07361b26a8"
#define SOIL_MOIST_UUID     "d2c5483e-36e1-4688-b7f5-ea07361b26a8"
//address = "F4:65:0B:49:8F:66" 
// OLED display width and height, in pixels
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

// Declaration for an SSD1306 display connected to I2C (SDA, SCL pins)
#define OLED_RESET -1 // Reset pin # (or -1 if sharing Arduino reset pin)
#define SCREEN_ADDRESS 0x3C // Common I2C address for 128x64 OLED

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
DHT dht(DHTPIN, DHTTYPE);

// BLE variables
BLEServer *pServer = NULL;
BLECharacteristic *pTempCharacteristic = NULL;
BLECharacteristic *pHumidCharacteristic = NULL;
BLECharacteristic *pSoilMoistCharacteristic = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// BLE Server Callbacks
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("BLE Client Connected");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("BLE Client Disconnected");
    }
};

void setup() {
  Serial.begin(115200);

  // Initialize DHT sensor
  dht.begin();

  // Initialize soil moisture sensor pin
  pinMode(SOIL_SENSOR_PIN, INPUT);

  // Initialize BLE
  // Serial.println("Starting BLE...");
  BLEDevice::init("Greenhouse Monitor");
  
  // Create BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create BLE Characteristics for Temperature
  pTempCharacteristic = pService->createCharacteristic(
                      TEMP_CHAR_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pTempCharacteristic->addDescriptor(new BLE2902());
  // Create BLE Characteristics for Humidity
  pHumidCharacteristic = pService->createCharacteristic(
                      HUMID_CHAR_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pHumidCharacteristic->addDescriptor(new BLE2902());
  pSoilMoistCharacteristic = pService->createCharacteristic(
                      SOIL_MOIST_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pSoilMoistCharacteristic->addDescriptor(new BLE2902());
  // Start the service
  pService->start();
  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
  Serial.println("BLE Advertising started. Device name: Greenhouse Monitor");

  // Initialize the OLED display
  if(!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }

  // Clear the buffer
  display.clearDisplay();

  // Display text
  display.setTextSize(1);      // Normal 1:1 pixel scale
  display.setTextColor(SSD1306_WHITE); // Draw white text
  display.setCursor(0, 0);     // Start at top-left corner
  display.println(F("Greenhouse"));
  display.println(F("Monitoring"));
  display.println(F("System"));
  display.println();
  display.println(F("BLE: Active"));
  display.setTextSize(2);      // Draw 2X-scale text
  display.println(F("Ready!"));
  // Display everything on the screen
  display.display();
  
  delay(2000);
}

void loop() {
  // Read temperature and humidity from DHT11 sensor
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();
  
  // Read soil moisture sensor
  int soilMoistureValue = analogRead(SOIL_SENSOR_PIN);
  
  // Check if readings failed
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  // Print to Serial Monitor
  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.print("%  Temperature: ");
  Serial.print(temperature);
  Serial.print("°C  ");
  Serial.print("Soil Moisture: ");
  Serial.print(soilMoistureValue);
  
  // Interpret soil moisture status
  // if (soilMoistureValue > 2800) {
  //   Serial.print(" (Dry)");
  // }
  // else if (soilMoistureValue > 1400) {
  //   Serial.print(" (Moist)");
  // }
  // else {
  //   Serial.print(" (Wet)");
  // }
  Serial.print("  BLE: ");
  Serial.println(deviceConnected ? "Connected" : "Disconnected");
  // Send data via BLE if device is connected
  if (deviceConnected) {
    // Convert float to string and send via BLE
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
    Serial.println("Data sent via BLE");
  }
  // Handle BLE disconnection/reconnection
  if (!deviceConnected && oldDeviceConnected) {
    delay(500); // Give the bluetooth stack time to get ready
    pServer->startAdvertising();
    Serial.println("Start advertising");
    oldDeviceConnected = deviceConnected;
  }
  // Handle BLE connection
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
  }
  // Update OLED display with sensor data
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print(F("BLE: "));
  display.println(deviceConnected ? F("Connected") : F("Waiting..."));
  display.println();

  display.setTextSize(1);
  display.print(F("Temp: "));
  display.print(temperature, 1);
  display.println(F("C"));
  
  display.print(F("Humidity: "));
  display.print(humidity, 1);
  display.println(F("%"));
  
  display.print(F("Soil: "));
  display.print(soilMoistureValue);
  // if (soilMoistureValue > 2800) {
  //   display.println(F(" Dry"));
  // }
  // else if (soilMoistureValue > 1400) {
  //   display.println(F(" Moist"));
  // }
  // else {
  //   display.println(F(" Wet"));
  // }
  display.display();
  // Wait 2 seconds between measurements
  delay(2000);
}
