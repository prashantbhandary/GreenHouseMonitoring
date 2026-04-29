# GreenHouse Monitoring System

An ESP32-based greenhouse monitoring system with sensor data collection, OLED display, and Bluetooth Low Energy (BLE) connectivity.

## Features

- **Temperature & Humidity Monitoring**: DHT11 sensor for ambient conditions
- **Soil Moisture Detection**: Analog soil moisture sensor
- **OLED Display**: Real-time data visualization on 128x64 SSD1306 display
- **BLE Connectivity**: Wireless data transmission to mobile apps or other BLE devices
- **Actuator Control**: Mist and pump control pins for automated irrigation

## Hardware

| Component | Pin | Description |
|-----------|-----|-------------|
| DHT11 Sensor | GPIO 5 | Temperature & humidity sensor |
| Soil Moisture | GPIO 34 | Analog soil moisture sensor |
| Mist Control | GPIO 18 | Mist system control |
| Pump Control | GPIO 19 | Water pump control |
| OLED SDA | GPIO 21 | I2C data line |
| OLED SCL | GPIO 22 | I2C clock line |

## BLE Service

- **Service UUID**: `4fafc201-1fb5-459e-8fcc-c5c9c331914b`
- **Temperature Characteristic**: `beb5483e-36e1-4688-b7f5-ea07361b26a8`
- **Humidity Characteristic**: `ceb5483e-36e1-4688-b7f5-ea07361b26a8`
- **Soil Moisture Characteristic**: `d2c5483e-36e1-4688-b7f5-ea07361b26a8`

## Building

This project uses PlatformIO. Build with:

```bash
pio run
```

Or use the Embedr IDE build system.

## Flashing

Connect your ESP32 via USB and flash with:

```bash
pio run --target upload
```

## Serial Monitor

Monitor serial output at 115200 baud:

```bash
pio device monitor -b 115200
```

## Libraries

- Adafruit BusIO
- Adafruit Unified Sensor
- DHT sensor library
- Adafruit SSD1306
- Adafruit GFX Library
- ESP32 BLE Arduino (built-in)

## License

MIT License
