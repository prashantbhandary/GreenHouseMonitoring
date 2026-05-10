#!/usr/bin/env python3
"""
Greenhouse Monitoring System - Research Findings Analysis
===========================================================
Generates publication-quality figures for research paper.

Datasets:
- greenhouse_auto_log.csv: AUTO mode data (threshold-based control)
- greenhouse_manual_log.csv: MANUAL mode data (manual control)

Thresholds Used:
- Temperature: 21-27°C range (Mist ON if temp > 27°C, OFF if <= 27°C)
- Humidity: 50-70% range (Mist ON if humidity < 50%, OFF if > 70%)
- Soil Moisture: 2416 threshold (Pump ON if soil > 2416)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Publication-quality settings
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'legend.fontsize': 9,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

# Thresholds from firmware
TEMP_HIGH_THRESHOLD = 27.0  # °C - Mist ON if temp > this
TEMP_LOW_THRESHOLD = 21.0   # °C - Target range
HUMIDITY_LOW_THRESHOLD = 50.0   # % - Mist ON if humidity < this
HUMIDITY_HIGH_THRESHOLD = 70.0  # % - Mist OFF if humidity > this
SOIL_THRESHOLD = 2416  # Pump ON if soil > this

# Create output directory
import os
os.makedirs('figures', exist_ok=True)


def load_and_clean_data(filepath):
    """Load CSV and clean data."""
    df = pd.read_csv(filepath)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Convert numeric columns
    numeric_cols = ['temperature', 'humidity', 'soil_moisture', 'battery_voltage']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with missing critical data
    df = df.dropna(subset=['temperature', 'humidity'])
    
    return df


def calculate_statistics(df, name):
    """Calculate key statistics for the dataset."""
    stats_dict = {
        'name': name,
        'n_samples': len(df),
        'duration_minutes': (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60,
        'temp_mean': df['temperature'].mean(),
        'temp_std': df['temperature'].std(),
        'temp_min': df['temperature'].min(),
        'temp_max': df['temperature'].max(),
        'humidity_mean': df['humidity'].mean(),
        'humidity_std': df['humidity'].std(),
        'humidity_min': df['humidity'].min(),
        'humidity_max': df['humidity'].max(),
        'soil_mean': df['soil_moisture'].mean(),
        'soil_std': df['soil_moisture'].std(),
        'battery_mean': df['battery_voltage'].mean(),
        'battery_std': df['battery_voltage'].std(),
        'mist_on_pct': (df['mist_status'].sum() / len(df)) * 100 if 'mist_status' in df else 0,
        'pump_on_pct': (df['pump_status'].sum() / len(df)) * 100 if 'pump_status' in df else 0,
    }
    return stats_dict


def fig1_environmental_time_series(auto_df, manual_df):
    """Figure 1: Environmental parameters over time for both modes."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot AUTO mode data
    ax1 = axes[0, 0]
    ax1.plot(auto_df['timestamp'], auto_df['temperature'], 'r-', alpha=0.7, linewidth=0.8, label='Temperature')
    ax1.axhline(y=TEMP_HIGH_THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'Temp Threshold ({TEMP_HIGH_THRESHOLD}°C)')
    ax1.axhline(y=TEMP_LOW_THRESHOLD, color='red', linestyle=':', linewidth=1.5, alpha=0.7, label=f'Temp Low ({TEMP_LOW_THRESHOLD}°C)')
    ax1.fill_between(auto_df['timestamp'], auto_df['temperature'], TEMP_HIGH_THRESHOLD, 
                      where=auto_df['temperature'] > TEMP_HIGH_THRESHOLD, alpha=0.2, color='red')
    ax1.set_ylabel('Temperature (°C)')
    ax1.set_title('(a) Temperature - AUTO Mode')
    ax1.legend(loc='upper right', fontsize=8)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    ax2 = axes[0, 1]
    ax2.plot(auto_df['timestamp'], auto_df['humidity'], 'b-', alpha=0.7, linewidth=0.8, label='Humidity')
    ax2.axhline(y=HUMIDITY_LOW_THRESHOLD, color='blue', linestyle='--', linewidth=2, label=f'Low Threshold ({HUMIDITY_LOW_THRESHOLD}%)')
    ax2.axhline(y=HUMIDITY_HIGH_THRESHOLD, color='blue', linestyle=':', linewidth=2, label=f'High Threshold ({HUMIDITY_HIGH_THRESHOLD}%)')
    ax2.fill_between(auto_df['timestamp'], auto_df['humidity'], HUMIDITY_LOW_THRESHOLD,
                      where=auto_df['humidity'] < HUMIDITY_LOW_THRESHOLD, alpha=0.2, color='blue')
    ax2.fill_between(auto_df['timestamp'], auto_df['humidity'], HUMIDITY_HIGH_THRESHOLD,
                      where=auto_df['humidity'] > HUMIDITY_HIGH_THRESHOLD, alpha=0.2, color='orange')
    ax2.set_ylabel('Relative Humidity (%)')
    ax2.set_title('(b) Humidity - AUTO Mode')
    ax2.legend(loc='upper right', fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    # Plot MANUAL mode data
    ax3 = axes[1, 0]
    ax3.plot(manual_df['timestamp'], manual_df['temperature'], 'darkred', alpha=0.7, linewidth=0.8, label='Temperature')
    ax3.axhline(y=TEMP_HIGH_THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'Temp Threshold ({TEMP_HIGH_THRESHOLD}°C)')
    ax3.set_ylabel('Temperature (°C)')
    ax3.set_xlabel('Time')
    ax3.set_title('(c) Temperature - MANUAL Mode')
    ax3.legend(loc='upper right', fontsize=8)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    ax4 = axes[1, 1]
    ax4.plot(manual_df['timestamp'], manual_df['humidity'], 'darkblue', alpha=0.7, linewidth=0.8, label='Humidity')
    ax4.axhline(y=HUMIDITY_LOW_THRESHOLD, color='blue', linestyle='--', linewidth=2, label=f'Low Threshold ({HUMIDITY_LOW_THRESHOLD}%)')
    ax4.axhline(y=HUMIDITY_HIGH_THRESHOLD, color='blue', linestyle=':', linewidth=2, label=f'High Threshold ({HUMIDITY_HIGH_THRESHOLD}%)')
    ax4.set_ylabel('Relative Humidity (%)')
    ax4.set_xlabel('Time')
    ax4.set_title('(d) Humidity - MANUAL Mode')
    ax4.legend(loc='upper right', fontsize=8)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    
    plt.tight_layout()
    plt.savefig('figures/fig1_environmental_time_series.png')
    plt.savefig('figures/fig1_environmental_time_series.pdf')
    plt.close()
    print("  ✓ Figure 1: Environmental time series")


def fig2_control_effectiveness(auto_df):
    """Figure 2: Control system effectiveness in AUTO mode."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Temperature control effectiveness
    ax1 = axes[0, 0]
    temp_in_range = ((auto_df['temperature'] >= TEMP_LOW_THRESHOLD) & 
                      (auto_df['temperature'] <= TEMP_HIGH_THRESHOLD)).sum()
    temp_above = (auto_df['temperature'] > TEMP_HIGH_THRESHOLD).sum()
    temp_below = (auto_df['temperature'] < TEMP_LOW_THRESHOLD).sum()
    
    colors_temp = ['#2ecc71', '#e74c3c', '#f39c12']
    wedges1, texts1, autotexts1 = ax1.pie([temp_in_range, temp_above, temp_below], 
                                           labels=['In Range (21-27°C)', f'Above {TEMP_HIGH_THRESHOLD}°C', f'Below {TEMP_LOW_THRESHOLD}°C'],
                                           colors=colors_temp, autopct='%1.1f%%', startangle=90,
                                           explode=(0.02, 0.05, 0.02))
    ax1.set_title(f'(a) Temperature Control\n({len(auto_df)} samples)')
    
    # Humidity control effectiveness
    ax2 = axes[0, 1]
    humid_in_range = ((auto_df['humidity'] >= HUMIDITY_LOW_THRESHOLD) & 
                       (auto_df['humidity'] <= HUMIDITY_HIGH_THRESHOLD)).sum()
    humid_below = (auto_df['humidity'] < HUMIDITY_LOW_THRESHOLD).sum()
    humid_above = (auto_df['humidity'] > HUMIDITY_HIGH_THRESHOLD).sum()
    
    colors_humid = ['#2ecc71', '#3498db', '#e74c3c']
    wedges2, texts2, autotexts2 = ax2.pie([humid_in_range, humid_below, humid_above],
                                            labels=['In Range (50-70%)', f'Below {HUMIDITY_LOW_THRESHOLD}%', f'Above {HUMIDITY_HIGH_THRESHOLD}%'],
                                            colors=colors_humid, autopct='%1.1f%%', startangle=90,
                                            explode=(0.02, 0.05, 0.05))
    ax2.set_title(f'(b) Humidity Control\n({len(auto_df)} samples)')
    
    # Mist activation distribution
    ax3 = axes[1, 0]
    mist_on = auto_df['mist_status'].sum()
    mist_off = len(auto_df) - mist_on
    
    colors_mist = ['#e74c3c', '#2ecc71']
    wedges3, texts3, autotexts3 = ax3.pie([mist_on, mist_off],
                                           labels=['Mist ON', 'Mist OFF'],
                                           colors=colors_mist, autopct='%1.1f%%', startangle=90,
                                           explode=(0.05, 0))
    ax3.set_title(f'(c) Mist Maker Activation\n({mist_on} ON / {mist_off} OFF)')
    
    # Battery voltage stability
    ax4 = axes[1, 1]
    ax4.hist(auto_df['battery_voltage'], bins=20, color='purple', alpha=0.7, edgecolor='black')
    ax4.axvline(x=auto_df['battery_voltage'].mean(), color='red', linestyle='-', linewidth=2,
                label=f"Mean: {auto_df['battery_voltage'].mean():.2f}V")
    ax4.axvline(x=auto_df['battery_voltage'].mean() - auto_df['battery_voltage'].std(), 
                color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    ax4.axvline(x=auto_df['battery_voltage'].mean() + auto_df['battery_voltage'].std(),
                color='red', linestyle='--', linewidth=1.5, alpha=0.7)
    ax4.set_xlabel('Battery Voltage (V)')
    ax4.set_ylabel('Frequency')
    ax4.set_title(f'(d) Battery Voltage Distribution\n(μ={auto_df["battery_voltage"].mean():.2f}V, σ={auto_df["battery_voltage"].std():.2f}V)')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('figures/fig2_control_effectiveness.png')
    plt.savefig('figures/fig2_control_effectiveness.pdf')
    plt.close()
    print("  ✓ Figure 2: Control effectiveness")


def fig3_mode_comparison(auto_df, manual_df):
    """Figure 3: Comparison between AUTO and MANUAL modes."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Temperature distribution comparison
    ax1 = axes[0, 0]
    ax1.hist(auto_df['temperature'], bins=25, alpha=0.6, color='blue', label='AUTO Mode', edgecolor='black')
    ax1.hist(manual_df['temperature'], bins=25, alpha=0.6, color='orange', label='MANUAL Mode', edgecolor='black')
    ax1.axvline(x=TEMP_HIGH_THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'Temp Threshold ({TEMP_HIGH_THRESHOLD}°C)')
    ax1.set_xlabel('Temperature (°C)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('(a) Temperature Distribution: AUTO vs MANUAL')
    ax1.legend()
    
    # Humidity distribution comparison
    ax2 = axes[0, 1]
    ax2.hist(auto_df['humidity'], bins=25, alpha=0.6, color='blue', label='AUTO Mode', edgecolor='black')
    ax2.hist(manual_df['humidity'], bins=25, alpha=0.6, color='orange', label='MANUAL Mode', edgecolor='black')
    ax2.axvline(x=HUMIDITY_LOW_THRESHOLD, color='blue', linestyle='--', linewidth=2, label=f'Low ({HUMIDITY_LOW_THRESHOLD}%)')
    ax2.axvline(x=HUMIDITY_HIGH_THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'High ({HUMIDITY_HIGH_THRESHOLD}%)')
    ax2.set_xlabel('Relative Humidity (%)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('(b) Humidity Distribution: AUTO vs MANUAL')
    ax2.legend()
    
    # Soil moisture comparison
    ax3 = axes[1, 0]
    ax3.hist(auto_df['soil_moisture'], bins=25, alpha=0.6, color='green', label='AUTO Mode', edgecolor='black')
    ax3.hist(manual_df['soil_moisture'], bins=25, alpha=0.6, color='brown', label='MANUAL Mode', edgecolor='black')
    ax3.axvline(x=SOIL_THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'Soil Threshold ({SOIL_THRESHOLD})')
    ax3.set_xlabel('Soil Moisture (ADC)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('(c) Soil Moisture Distribution: AUTO vs MANUAL')
    ax3.legend()
    
    # Battery voltage comparison
    ax4 = axes[1, 1]
    ax4.hist(auto_df['battery_voltage'], bins=20, alpha=0.6, color='purple', label='AUTO Mode', edgecolor='black')
    ax4.hist(manual_df['battery_voltage'], bins=20, alpha=0.6, color='gray', label='MANUAL Mode', edgecolor='black')
    ax4.set_xlabel('Battery Voltage (V)')
    ax4.set_ylabel('Frequency')
    ax4.set_title('(d) Battery Voltage: AUTO vs MANUAL')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('figures/fig3_mode_comparison.png')
    plt.savefig('figures/fig3_mode_comparison.pdf')
    plt.close()
    print("  ✓ Figure 3: Mode comparison")


def fig4_threshold_analysis(auto_df):
    """Figure 4: Detailed threshold crossing analysis."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Temperature vs Mist Status
    ax1 = axes[0, 0]
    mist_on = auto_df[auto_df['mist_status'] == 1]
    mist_off = auto_df[auto_df['mist_status'] == 0]
    
    ax1.scatter(mist_on['temperature'], mist_on['humidity'], c='red', alpha=0.5, s=15, label='Mist ON')
    ax1.scatter(mist_off['temperature'], mist_off['humidity'], c='blue', alpha=0.5, s=15, label='Mist OFF')
    ax1.axvline(x=TEMP_HIGH_THRESHOLD, color='gray', linestyle='--', alpha=0.7, label=f'Temp > {TEMP_HIGH_THRESHOLD}°C')
    ax1.axhline(y=HUMIDITY_LOW_THRESHOLD, color='gray', linestyle=':', alpha=0.7, label=f'Humidity < {HUMIDITY_LOW_THRESHOLD}%')
    ax1.axhline(y=HUMIDITY_HIGH_THRESHOLD, color='gray', linestyle='-.', alpha=0.7, label=f'Humidity > {HUMIDITY_HIGH_THRESHOLD}%')
    ax1.set_xlabel('Temperature (°C)')
    ax1.set_ylabel('Relative Humidity (%)')
    ax1.set_title('(a) Mist Activation Regions')
    ax1.legend(loc='upper right', fontsize=8)
    
    # Time spent in each zone
    ax2 = axes[0, 1]
    temp_below_21 = (auto_df['temperature'] < TEMP_LOW_THRESHOLD).sum()
    temp_in_range = ((auto_df['temperature'] >= TEMP_LOW_THRESHOLD) & 
                     (auto_df['temperature'] <= TEMP_HIGH_THRESHOLD)).sum()
    temp_above_27 = (auto_df['temperature'] > TEMP_HIGH_THRESHOLD).sum()
    
    zones = [f'< {TEMP_LOW_THRESHOLD}°C', f'{TEMP_LOW_THRESHOLD}-{TEMP_HIGH_THRESHOLD}°C', f'> {TEMP_HIGH_THRESHOLD}°C']
    counts = [temp_below_21, temp_in_range, temp_above_27]
    colors = ['#3498db', '#2ecc71', '#e74c3c']
    
    bars = ax2.bar(zones, counts, color=colors, edgecolor='black')
    ax2.set_ylabel('Number of Samples')
    ax2.set_title('(b) Temperature Zone Distribution')
    for bar, count in zip(bars, counts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                 f'{count}\n({count/len(auto_df)*100:.1f}%)', ha='center', fontsize=9)
    
    # Humidity zone distribution
    ax3 = axes[1, 0]
    humid_below_50 = (auto_df['humidity'] < HUMIDITY_LOW_THRESHOLD).sum()
    humid_in_range = ((auto_df['humidity'] >= HUMIDITY_LOW_THRESHOLD) & 
                       (auto_df['humidity'] <= HUMIDITY_HIGH_THRESHOLD)).sum()
    humid_above_70 = (auto_df['humidity'] > HUMIDITY_HIGH_THRESHOLD).sum()
    
    zones_h = [f'< {HUMIDITY_LOW_THRESHOLD}%', f'{HUMIDITY_LOW_THRESHOLD}-{HUMIDITY_HIGH_THRESHOLD}%', f'> {HUMIDITY_HIGH_THRESHOLD}%']
    counts_h = [humid_below_50, humid_in_range, humid_above_70]
    colors_h = ['#3498db', '#2ecc71', '#e74c3c']
    
    bars_h = ax3.bar(zones_h, counts_h, color=colors_h, edgecolor='black')
    ax3.set_ylabel('Number of Samples')
    ax3.set_title('(c) Humidity Zone Distribution')
    for bar, count in zip(bars_h, counts_h):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                 f'{count}\n({count/len(auto_df)*100:.1f}%)', ha='center', fontsize=9)
    
    # Control response time
    ax4 = axes[1, 1]
    # Calculate mist state changes
    mist_changes = auto_df['mist_status'].diff().fillna(0)
    mist_on_events = (mist_changes == 1).sum()
    mist_off_events = (mist_changes == -1).sum()
    
    events = ['Mist ON Events', 'Mist OFF Events']
    event_counts = [mist_on_events, mist_off_events]
    colors_e = ['#27ae60', '#c0392b']
    
    bars_e = ax4.bar(events, event_counts, color=colors_e, edgecolor='black')
    ax4.set_ylabel('Number of Events')
    ax4.set_title(f'(d) Control Response Events\n(Total: {len(auto_df)} samples, {auto_df["mist_status"].sum()} mist ON samples)')
    for bar, count in zip(bars_e, event_counts):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 str(count), ha='center', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('figures/fig4_threshold_analysis.png')
    plt.savefig('figures/fig4_threshold_analysis.pdf')
    plt.close()
    print("  ✓ Figure 4: Threshold analysis")


def fig5_summary_table(auto_stats, manual_stats):
    """Figure 5: Summary statistics table."""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('off')
    
    # Create comparison table
    table_data = [
        ['Parameter', 'AUTO Mode', 'MANUAL Mode', 'Difference'],
        ['Samples', f"{auto_stats['n_samples']}", f"{manual_stats['n_samples']}", '-'],
        ['Duration (min)', f"{auto_stats['duration_minutes']:.1f}", f"{manual_stats['duration_minutes']:.1f}", '-'],
        ['Temperature Mean (°C)', f"{auto_stats['temp_mean']:.2f}", f"{manual_stats['temp_mean']:.2f}", 
         f"{auto_stats['temp_mean'] - manual_stats['temp_mean']:.2f}"],
        ['Temperature Std (°C)', f"{auto_stats['temp_std']:.2f}", f"{manual_stats['temp_std']:.2f}", '-'],
        ['Temperature Range (°C)', f"{auto_stats['temp_min']:.1f}-{auto_stats['temp_max']:.1f}", 
         f"{manual_stats['temp_min']:.1f}-{manual_stats['temp_max']:.1f}", '-'],
        ['Humidity Mean (%)', f"{auto_stats['humidity_mean']:.1f}", f"{manual_stats['humidity_mean']:.1f}",
         f"{auto_stats['humidity_mean'] - manual_stats['humidity_mean']:.1f}"],
        ['Humidity Std (%)', f"{auto_stats['humidity_std']:.1f}", f"{manual_stats['humidity_std']:.1f}", '-'],
        ['Humidity Range (%)', f"{auto_stats['humidity_min']:.1f}-{auto_stats['humidity_max']:.1f}",
         f"{manual_stats['humidity_min']:.1f}-{manual_stats['humidity_max']:.1f}", '-'],
        ['Soil Moisture Mean', f"{auto_stats['soil_mean']:.0f}", f"{manual_stats['soil_mean']:.0f}", '-'],
        ['Battery Voltage (V)', f"{auto_stats['battery_mean']:.2f} ± {auto_stats['battery_std']:.2f}", 
         f"{manual_stats['battery_mean']:.2f} ± {manual_stats['battery_std']:.2f}", '-'],
        ['Mist ON (%)', f"{auto_stats['mist_on_pct']:.1f}%", f"{manual_stats['mist_on_pct']:.1f}%", '-'],
    ]
    
    table = ax.table(cellText=table_data, loc='center', cellLoc='center',
                     colWidths=[0.30, 0.22, 0.22, 0.18])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    # Style header
    for j in range(4):
        table[(0, j)].set_facecolor('#2c3e50')
        table[(0, j)].set_text_props(color='white', fontweight='bold')
    
    # Style alternating rows
    for i in range(1, len(table_data)):
        for j in range(4):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#ecf0f1')
    
    ax.set_title('Table 1: Comparison of AUTO vs MANUAL Mode Operation\n', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('figures/fig5_summary_table.png', bbox_inches='tight', dpi=300)
    plt.savefig('figures/fig5_summary_table.pdf', bbox_inches='tight')
    plt.close()
    print("  ✓ Figure 5: Summary table")


def generate_latex_table(auto_stats, manual_stats):
    """Generate LaTeX table for paper."""
    latex = r"""
\begin{table}[h]
\centering
\caption{Greenhouse Monitoring System: AUTO vs MANUAL Mode Comparison}
\label{tab:mode_comparison}
\begin{tabular}{lccc}
\hline
\textbf{Parameter} & \textbf{AUTO Mode} & \textbf{MANUAL Mode} & \textbf{Threshold} \\
\hline
""" + f"""Samples & {auto_stats['n_samples']} & {manual_stats['n_samples']} & - \\
Temperature (°C) & ${auto_stats['temp_mean']:.2f} \\pm {auto_stats['temp_std']:.2f}$ & ${manual_stats['temp_mean']:.2f} \\pm {manual_stats['temp_std']:.2f}$ & 21-27 \\
Humidity (\%) & ${auto_stats['humidity_mean']:.1f} \\pm {auto_stats['humidity_std']:.1f}$ & ${manual_stats['humidity_mean']:.1f} \\pm {manual_stats['humidity_std']:.1f}$ & 50-70 \\
Soil Moisture & ${auto_stats['soil_mean']:.0f} \\pm {auto_stats['soil_std']:.0f}$ & ${manual_stats['soil_mean']:.0f} \\pm {manual_stats['soil_std']:.0f}$ & <2416 \\
Battery (V) & ${auto_stats['battery_mean']:.2f} \\pm {auto_stats['battery_std']:.2f}$ & ${manual_stats['battery_mean']:.2f} \\pm {manual_stats['battery_std']:.2f}$ & - \\
Mist ON (\%) & {auto_stats['mist_on_pct']:.1f}\% & {manual_stats['mist_on_pct']:.1f}\% & - \\
""" + r"""\hline
\end{tabular}
\end{table}
"""
    
    with open('figures/table_mode_comparison.tex', 'w') as f:
        f.write(latex)
    
    print("  ✓ LaTeX table saved")


def main():
    """Main analysis pipeline."""
    print("\n" + "=" * 60)
    print("GREENHOUSE MONITORING - RESEARCH FINDINGS ANALYSIS")
    print("=" * 60)
    
    # Load data
    print("\nLoading data...")
    auto_df = load_and_clean_data('greenhouse_auto_log.csv')
    manual_df = load_and_clean_data('greenhouse_manual_log.csv')
    
    print(f"  AUTO Mode: {len(auto_df)} samples")
    print(f"  MANUAL Mode: {len(manual_df)} samples")
    
    # Calculate statistics
    auto_stats = calculate_statistics(auto_df, 'AUTO')
    manual_stats = calculate_statistics(manual_df, 'MANUAL')
    
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)
    
    print(f"\n--- AUTO Mode ---")
    print(f"  Temperature: {auto_stats['temp_mean']:.2f}°C ± {auto_stats['temp_std']:.2f}°C")
    print(f"  Humidity: {auto_stats['humidity_mean']:.1f}% ± {auto_stats['humidity_std']:.1f}%")
    print(f"  Mist ON: {auto_stats['mist_on_pct']:.1f}% of time")
    
    print(f"\n--- MANUAL Mode ---")
    print(f"  Temperature: {manual_stats['temp_mean']:.2f}°C ± {manual_stats['temp_std']:.2f}°C")
    print(f"  Humidity: {manual_stats['humidity_mean']:.1f}% ± {manual_stats['humidity_std']:.1f}%")
    print(f"  Mist ON: {manual_stats['mist_on_pct']:.1f}% of time")
    
    # Generate figures
    print("\n" + "=" * 60)
    print("GENERATING FIGURES")
    print("=" * 60)
    
    fig1_environmental_time_series(auto_df, manual_df)
    fig2_control_effectiveness(auto_df)
    fig3_mode_comparison(auto_df, manual_df)
    fig4_threshold_analysis(auto_df)
    fig5_summary_table(auto_stats, manual_stats)
    generate_latex_table(auto_stats, manual_stats)
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nGenerated 5 publication-quality figures in 'figures/' directory:")
    print("  - fig1_environmental_time_series.png/pdf")
    print("  - fig2_control_effectiveness.png/pdf")
    print("  - fig3_mode_comparison.png/pdf")
    print("  - fig4_threshold_analysis.png/pdf")
    print("  - fig5_summary_table.png/pdf")
    print("  - table_mode_comparison.tex (LaTeX)")
    
    return auto_df, manual_df, auto_stats, manual_stats


if __name__ == "__main__":
    auto_df, manual_df, auto_stats, manual_stats = main()
