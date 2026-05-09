# Firmware Changes - v2.0

## Summary of Changes

### 1. Fixed Boot Issue (Mist Turning ON During Startup)

**Problem:** Relay was briefly turning ON during ESP32 boot/reboot.

**Solution:**
- Changed GPIO initialization order in `setup()`
- Set pin HIGH **before** setting as OUTPUT (for active-LOW relays)
- Added 100ms settling delay after relay initialization

```cpp
// OLD (problematic):
pinMode(MIST_PIN, OUTPUT);
digitalWrite(MIST_PIN, LOW);  // Brief LOW pulse during pinMode!

// NEW (fixed):
digitalWrite(MIST_PIN, HIGH);  // Set HIGH first (OFF for active-LOW relay)
pinMode(MIST_PIN, OUTPUT);     // Then configure as output
delay(100);                    // Let relay settle
```

### 2. Updated Threshold Logic

**Old Logic:**
- Mist ON when `temp > threshold` OR `humidity < threshold`

**New Logic:**
- Mist ON when `temp < 25°C` (cooling mode)
- Mist ON when `humidity < 40%` (humidification)
- Mist OFF when `humidity > 80%` (prevent over-humidification)

```cpp
bool mistShouldBeOn = (temperature < temperature_threshold) || 
                       (humidity < humidity_low_threshold);
if (humidity > humidity_high_threshold) {
    mistShouldBeOn = false;  // Stop at 80% humidity
}
```

### 3. Added Dual Humidity Thresholds

| Parameter | Old Value | New Value | Purpose |
|-----------|-----------|-----------|---------|
| Temperature Threshold | 21°C (ON if >) | 25°C (ON if <) | Cooling mode |
| Humidity Low Threshold | 40% | 40% | Turn ON mist |
| Humidity High Threshold | N/A | 80% | Turn OFF mist |
| Soil Threshold | 2416 | 2416 | Pump ON if > |

### 4. Updated BLE Threshold Format

**Old Format:** `tempThresh,humidThresh,soilThresh`
**New Format:** `tempThresh,humidLowThresh,humidHighThresh,soilThresh`

Example: `25.0,40.0,80.0,2416`

### 5. Fixed Active-LOW Relay Logic

Assuming your relay module is active-LOW (most common):

| GPIO State | Relay State | Actuator |
|------------|-------------|----------|
| HIGH | OFF | Mist/Pump OFF |
| LOW | ON | Mist/Pump ON |

## Control Logic Summary

### AUTO Mode

```
MIST ON if:
  (temperature < 25°C) OR (humidity < 40%)
  AND humidity < 80%

MIST OFF if:
  humidity > 80%
  OR (temperature >= 25°C AND humidity >= 40%)

PUMP ON if:
  soil_moisture > 2416 (dry soil)
```

### MANUAL Mode

Direct control via BLE commands:
- `mode,mist,pump` format
- `1,1,0` = MANUAL mode, Mist ON, Pump OFF

## Hardware Notes

### Active-LOW vs Active-HIGH Relay

Most relay modules are **active-LOW**:
- LOW signal = Relay ON
- HIGH signal = Relay OFF

If your relay is **active-HIGH**, change:
```cpp
// In setup():
digitalWrite(MIST_PIN, LOW);   // Change HIGH to LOW
digitalWrite(PUMP_PIN, LOW);   // Change HIGH to LOW

// In control logic:
digitalWrite(MIST_PIN, HIGH);  // Change LOW to HIGH (for ON)
digitalWrite(MIST_PIN, LOW);   // Change HIGH to LOW (for OFF)
```

## Testing Checklist

- [ ] Mist stays OFF during boot
- [ ] Mist turns ON when temp drops below 25°C
- [ ] Mist turns ON when humidity drops below 40%
- [ ] Mist turns OFF when humidity exceeds 80%
- [ ] Pump activates when soil is dry (>2416)
- [ ] BLE commands work correctly
- [ ] Manual mode works

## Flash the Updated Firmware

```bash
# Build and flash
pio run -t upload

# Or using Embedr IDE
# Click "Upload" button
```
