#!/usr/bin/env python3
"""
Generate Realistic Soil Moisture + Pump Control Dataset
=========================================================
Creates a 2-hour dataset showing:
1. Soil getting dry over time (moisture value increasing)
2. Pump turning ON when soil > threshold (2416)
3. Soil moisture decreasing after watering
4. Multiple realistic watering cycles
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

SOIL_THRESHOLD = 2200  # Pump ON if soil > this (lowered for more activations)
DATA_INTERVAL_SEC = 5  # Data every 5 seconds
DURATION_HOURS = 2
TOTAL_SAMPLES = int(DURATION_HOURS * 3600 / DATA_INTERVAL_SEC)

def generate_realistic_soil_data():
    """Generate realistic soil moisture data with pump cycles."""
    
    data = []
    start_time = datetime(2026, 5, 10, 10, 0, 0)  # Start at 10:00 AM
    
    # Initial soil moisture (wet soil, low value)
    soil_moisture = 1800  # Wet soil
    temp_base = 28.0
    humidity_base = 65.0
    
    pump_on = False
    pump_on_time = 0
    
    for i in range(TOTAL_SAMPLES):
        current_time = start_time + timedelta(seconds=i * DATA_INTERVAL_SEC)
        
        # Time-based environmental changes
        hour = current_time.hour + current_time.minute / 60
        
        # Temperature: rises in afternoon, cooler in morning/evening
        temp_variation = 2.0 * np.sin((hour - 6) * np.pi / 12)
        temperature = temp_base + temp_variation + random.gauss(0, 0.3)
        
        # Humidity: inversely related to temperature
        humidity = humidity_base - temp_variation * 5 + random.gauss(0, 2)
        humidity = max(40, min(85, humidity))
        
        # Battery voltage (slowly decreasing)
        battery = 7.4 - (i / TOTAL_SAMPLES) * 1.5 + random.gauss(0, 0.1)
        battery = max(5.5, min(8.0, battery))
        
        # ============================================
        # SOIL MOISTURE DYNAMICS
        # ============================================
        
        # Natural drying rate (depends on temperature)
        drying_rate = 0.8 + (temperature - 25) * 0.1  # Faster drying when hot
        soil_moisture += drying_rate + random.gauss(0, 0.5)
        
        # Pump control logic
        if soil_moisture > SOIL_THRESHOLD and not pump_on:
            # Soil too dry - turn pump ON
            pump_on = True
            pump_on_time = 0
        elif pump_on:
            pump_on_time += 1
            
            # Watering effect (reduces soil moisture)
            if pump_on_time < 12:  # Pump runs for ~1 minute (12 samples)
                soil_moisture -= 40 + random.gauss(0, 5)  # Strong watering effect
            else:
                # Turn pump OFF after watering
                pump_on = False
                pump_on_time = 0
        
        # Ensure soil moisture stays realistic
        soil_moisture = max(1600, min(2800, soil_moisture))
        
        # Mist control (based on temperature and humidity)
        mist_on = 0
        if temperature > 27.0 or humidity < 50.0:
            if humidity < 70.0:  # Don't mist if too humid
                mist_on = 1
        
        # Mode: AUTO (0)
        mode = 0
        
        data.append({
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'temperature': round(temperature, 1),
            'humidity': round(humidity, 1),
            'soil_moisture': int(soil_moisture),
            'battery_voltage': round(battery, 1),
            'mode': mode,
            'mist_status': mist_on,
            'pump_status': 1 if pump_on else 0
        })
    
    return pd.DataFrame(data)

def main():
    print("=" * 60)
    print("GENERATING REALISTIC SOIL MOISTURE + PUMP CONTROL DATA")
    print("=" * 60)
    print(f"\nDuration: {DURATION_HOURS} hours")
    print(f"Threshold: Soil > {SOIL_THRESHOLD} → Pump ON")
    print(f"Interval: {DATA_INTERVAL_SEC} seconds")
    
    # Generate data
    df = generate_realistic_soil_data()
    
    # Save to CSV
    output_file = 'greenhouse_pump_control_log.csv'
    df.to_csv(output_file, index=False)
    
    # Statistics
    pump_events = df['pump_status'].sum()
    pump_cycles = (df['pump_status'].diff().fillna(0) == 1).sum()
    
    print(f"\n" + "=" * 60)
    print("DATASET GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nFile: {output_file}")
    print(f"Total samples: {len(df)}")
    print(f"Duration: {DURATION_HOURS} hours")
    print(f"\nSoil Moisture Statistics:")
    print(f"  Min: {df['soil_moisture'].min()}")
    print(f"  Max: {df['soil_moisture'].max()}")
    print(f"  Mean: {df['soil_moisture'].mean():.0f}")
    print(f"\nPump Statistics:")
    print(f"  Total pump ON samples: {pump_events}")
    print(f"  Number of watering cycles: {pump_cycles}")
    print(f"  Pump ON percentage: {(pump_events / len(df)) * 100:.1f}%")
    
    print(f"\nSoil Threshold: {SOIL_THRESHOLD}")
    print(f"Samples with soil > threshold: {(df['soil_moisture'] > SOIL_THRESHOLD).sum()}")
    
    print("\n" + "=" * 60)
    print("SAMPLE DATA (First 20 rows)")
    print("=" * 60)
    print(df.head(20).to_string(index=False))
    
    print("\n" + "=" * 60)
    print("PUMP ACTIVATION EVENTS")
    print("=" * 60)
    
    # Find pump activation events
    pump_starts = df[df['pump_status'].diff().fillna(0) == 1]
    pump_ends = df[df['pump_status'].diff().fillna(0) == -1]
    
    for i, (start_row, end_row) in enumerate(zip(pump_starts.iterrows(), pump_ends.iterrows())):
        start_time = start_row[1]['timestamp']
        end_time = end_row[1]['timestamp']
        start_soil = start_row[1]['soil_moisture']
        end_soil = end_row[1]['soil_moisture']
        duration = (pd.to_datetime(end_time) - pd.to_datetime(start_time)).seconds
        
        print(f"\nCycle {i+1}:")
        print(f"  Started: {start_time} (soil: {start_soil})")
        print(f"  Ended: {end_time} (soil: {end_soil})")
        print(f"  Duration: {duration}s")
        print(f"  Soil reduction: {start_soil - end_soil}")
    
    return df

if __name__ == "__main__":
    df = main()
