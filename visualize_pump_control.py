#!/usr/bin/env python3
"""
Visualize Soil Moisture + Pump Control Data
============================================
Creates clear visualizations showing:
1. Soil moisture over time with threshold line
2. Pump ON/OFF states
3. Watering cycles clearly marked
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np
import os
os.makedirs('figures', exist_ok=True)

# Settings
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'legend.fontsize': 10,
    'figure.dpi': 150,
})

SOIL_THRESHOLD = 2200

def load_data():
    """Load the pump control dataset."""
    df = pd.read_csv('greenhouse_pump_control_log.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

def plot_soil_pump_control(df):
    """Create comprehensive visualization of soil moisture and pump control."""
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # ============================================
    # Plot 1: Soil Moisture with Threshold
    # ============================================
    ax1 = axes[0]
    
    # Plot soil moisture
    ax1.plot(df['timestamp'], df['soil_moisture'], 'b-', linewidth=1.5, 
             label='Soil Moisture', alpha=0.8)
    
    # Plot threshold line
    ax1.axhline(y=SOIL_THRESHOLD, color='red', linestyle='--', linewidth=2,
                label=f'Threshold ({SOIL_THRESHOLD})')
    
    # Fill regions above threshold (dry soil)
    ax1.fill_between(df['timestamp'], df['soil_moisture'], SOIL_THRESHOLD,
                      where=df['soil_moisture'] >= SOIL_THRESHOLD,
                      color='red', alpha=0.3, label='Dry Soil (Pump ON)')
    
    # Fill regions below threshold (wet soil)
    ax1.fill_between(df['timestamp'], df['soil_moisture'], SOIL_THRESHOLD,
                      where=df['soil_moisture'] < SOIL_THRESHOLD,
                      color='blue', alpha=0.2, label='Wet Soil')
    
    ax1.set_ylabel('Soil Moisture (ADC)')
    ax1.set_title('(a) Soil Moisture Level Over Time')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # ============================================
    # Plot 2: Pump Status
    # ============================================
    ax2 = axes[1]
    
    # Plot pump status as shaded regions
    pump_on_mask = df['pump_status'] == 1
    
    ax2.fill_between(df['timestamp'], 0, 1,
                      where=pump_on_mask,
                      color='green', alpha=0.6, label='Pump ON')
    ax2.fill_between(df['timestamp'], 0, 1,
                      where=~pump_on_mask,
                      color='gray', alpha=0.2, label='Pump OFF')
    
    ax2.set_ylabel('Pump Status')
    ax2.set_ylim(0, 1)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(['OFF', 'ON'])
    ax2.set_title('(b) Water Pump Control Status')
    ax2.legend(loc='upper right', fontsize=9)
    ax2.grid(True, alpha=0.3, axis='x')
    
    # ============================================
    # Plot 3: Combined View
    # ============================================
    ax3 = axes[2]
    
    # Plot soil moisture
    ax3.plot(df['timestamp'], df['soil_moisture'], 'b-', linewidth=1.5, 
             label='Soil Moisture', alpha=0.7)
    
    # Highlight pump ON periods
    pump_starts = df[df['pump_status'].diff().fillna(0) == 1]
    pump_ends = df[df['pump_status'].diff().fillna(0) == -1]
    
    for i, (start_row, end_row) in enumerate(zip(pump_starts.iterrows(), pump_ends.iterrows())):
        start_time = start_row[1]['timestamp']
        end_time = end_row[1]['timestamp']
        
        # Shade the watering period
        ax3.axvspan(start_time, end_time, color='green', alpha=0.3, 
                    label='Watering' if i == 0 else '')
        
        # Add annotation
        mid_time = start_time + (end_time - start_time) / 2
        ax3.annotate(f'Cycle {i+1}', xy=(mid_time, df['soil_moisture'].max() - 50),
                     ha='center', fontsize=9, color='darkgreen', fontweight='bold')
    
    # Plot threshold
    ax3.axhline(y=SOIL_THRESHOLD, color='red', linestyle='--', linewidth=2,
                label=f'Threshold ({SOIL_THRESHOLD})')
    
    ax3.set_ylabel('Soil Moisture (ADC)')
    ax3.set_xlabel('Time')
    ax3.set_title('(c) Soil Moisture with Watering Cycles Highlighted')
    ax3.legend(loc='upper left', fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax3.xaxis.set_major_locator(mdates.MinuteLocator(interval=15))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # Save figures
    plt.savefig('figures/soil_pump_control_visualization.png', dpi=300, bbox_inches='tight')
    plt.savefig('figures/soil_pump_control_visualization.pdf', bbox_inches='tight')
    
    print("✓ Visualization saved to figures/")
    
    return fig

def print_pump_cycles(df):
    """Print detailed pump cycle information."""
    
    print("\n" + "=" * 70)
    print("PUMP ACTIVATION CYCLES")
    print("=" * 70)
    
    pump_starts = df[df['pump_status'].diff().fillna(0) == 1]
    pump_ends = df[df['pump_status'].diff().fillna(0) == -1]
    
    for i, (start_row, end_row) in enumerate(zip(pump_starts.iterrows(), pump_ends.iterrows())):
        start_time = start_row[1]['timestamp']
        end_time = end_row[1]['timestamp']
        start_soil = start_row[1]['soil_moisture']
        end_soil = end_row[1]['soil_moisture']
        duration = (end_time - start_time).seconds
        
        print(f"\nCycle {i+1}:")
        print(f"  Started: {start_time.strftime('%H:%M:%S')} (soil: {start_soil})")
        print(f"  Ended:   {end_time.strftime('%H:%M:%S')} (soil: {end_soil})")
        print(f"  Duration: {duration}s")
        print(f"  Soil reduction: {start_soil - end_soil} units")
        print(f"  Status: {'✓ Crossed threshold' if start_soil >= SOIL_THRESHOLD else '✗ Below threshold'}")

def main():
    print("=" * 70)
    print("SOIL MOISTURE + PUMP CONTROL VISUALIZATION")
    print("=" * 70)
    
    # Load data
    df = load_data()
    print(f"\nLoaded {len(df)} samples")
    print(f"Duration: {df['timestamp'].max() - df['timestamp'].min()}")
    
    # Print cycle details
    print_pump_cycles(df)
    
    # Create visualization
    print("\n" + "=" * 70)
    print("GENERATING VISUALIZATION")
    print("=" * 70)
    
    fig = plot_soil_pump_control(df)
    
    print("\n✓ Files created:")
    print("  - figures/soil_pump_control_visualization.png")
    print("  - figures/soil_pump_control_visualization.pdf")
    
    plt.show()
    
    return df

if __name__ == "__main__":
    df = main()
