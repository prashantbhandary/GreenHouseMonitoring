#!/usr/bin/env python3
"""
Greenhouse Monitoring Data Analysis Script
============================================
Generates publication-quality figures for research paper.

Features:
- Outlier removal using IQR method
- Statistical summary tables
- Time series analysis
- Correlation analysis
- Control system validation figures

Author: Greenhouse Monitoring System
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from scipy.signal import savgol_filter
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Set publication-quality plot style
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
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
})

# ============================================================================
# DATA LOADING AND CLEANING
# ============================================================================

def load_and_clean_data(filepath='greenhouse_complete_log.csv'):
    """Load CSV and perform initial cleaning."""
    df = pd.read_csv(filepath)
    
    # Convert timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Convert numeric columns
    numeric_cols = ['temperature', 'humidity', 'soil_moisture', 'battery_voltage',
                    'temperature_threshold', 'humidity_threshold', 'soil_threshold']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Convert mode and status to int
    df['mode'] = pd.to_numeric(df['mode'], errors='coerce').astype('Int64')
    df['mist_status'] = pd.to_numeric(df['mist_status'], errors='coerce').astype('Int64')
    df['pump_status'] = pd.to_numeric(df['pump_status'], errors='coerce').astype('Int64')
    
    return df


def remove_outliers_iqr(df, columns, multiplier=1.5):
    """Remove outliers using Interquartile Range (IQR) method."""
    df_clean = df.copy()
    
    for col in columns:
        if col in df_clean.columns:
            Q1 = df_clean[col].quantile(0.25)
            Q3 = df_clean[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - multiplier * IQR
            upper_bound = Q3 + multiplier * IQR
            
            # Mark outliers
            outlier_mask = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
            n_outliers = outlier_mask.sum()
            
            if n_outliers > 0:
                print(f"  {col}: Removed {n_outliers} outliers (bounds: [{lower_bound:.2f}, {upper_bound:.2f}])")
                df_clean.loc[outlier_mask, col] = np.nan
    
    return df_clean


def remove_humidity_outliers(df, threshold=55):
    """Remove humidity spikes above threshold (DHT11 sensor errors)."""
    df_clean = df.copy()
    outlier_mask = df_clean['humidity'] > threshold
    n_outliers = outlier_mask.sum()
    
    if n_outliers > 0:
        print(f"  humidity: Removed {n_outliers} sensor error spikes (>{threshold}%)")
        df_clean.loc[outlier_mask, 'humidity'] = np.nan
    
    return df_clean


def process_data(df, battery_filter=7.25):
    """Full data processing pipeline."""
    print("=" * 60)
    print("DATA PROCESSING")
    print("=" * 60)
    
    print(f"\nOriginal data: {len(df)} rows")
    
    # Remove NaN values in sensor readings
    df_clean = df.dropna(subset=['temperature', 'humidity', 'soil_moisture'])
    print(f"After removing NaN: {len(df_clean)} rows")
    
    # Remove humidity sensor errors (spikes above 55%)
    df_clean = remove_humidity_outliers(df_clean, threshold=55)
    
    # Remove statistical outliers
    outlier_cols = ['temperature', 'soil_moisture', 'battery_voltage']
    df_clean = remove_outliers_iqr(df_clean, outlier_cols, multiplier=1.5)
    
    # Filter by battery voltage (test conducted at ~7.25V)
    if battery_filter:
        # Accept readings within ±0.5V of target
        df_clean = df_clean[
            (df_clean['battery_voltage'] >= battery_filter - 0.5) &
            (df_clean['battery_voltage'] <= battery_filter + 0.5)
        ]
        print(f"\nFiltered by battery voltage (~{battery_filter}V): {len(df_clean)} rows")
    
    # Drop remaining NaN values
    df_clean = df_clean.dropna(subset=['temperature', 'humidity', 'soil_moisture'])
    print(f"Final clean data: {len(df_clean)} rows")
    
    return df_clean


# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================

def generate_statistics(df):
    """Generate comprehensive statistical summary."""
    print("\n" + "=" * 60)
    print("STATISTICAL SUMMARY")
    print("=" * 60)
    
    stats_dict = {
        'temperature': {
            'mean': df['temperature'].mean(),
            'std': df['temperature'].std(),
            'min': df['temperature'].min(),
            'max': df['temperature'].max(),
            'median': df['temperature'].median(),
        },
        'humidity': {
            'mean': df['humidity'].mean(),
            'std': df['humidity'].std(),
            'min': df['humidity'].min(),
            'max': df['humidity'].max(),
            'median': df['humidity'].median(),
        },
        'soil_moisture': {
            'mean': df['soil_moisture'].mean(),
            'std': df['soil_moisture'].std(),
            'min': df['soil_moisture'].min(),
            'max': df['soil_moisture'].max(),
            'median': df['soil_moisture'].median(),
        },
        'battery_voltage': {
            'mean': df['battery_voltage'].mean(),
            'std': df['battery_voltage'].std(),
            'min': df['battery_voltage'].min(),
            'max': df['battery_voltage'].max(),
            'median': df['battery_voltage'].median(),
        }
    }
    
    # Print statistics
    for param, values in stats_dict.items():
        print(f"\n{param.replace('_', ' ').title()}:")
        for stat, value in values.items():
            if 'soil' in param:
                print(f"  {stat}: {value:.1f}")
            else:
                print(f"  {stat}: {value:.2f}")
    
    return stats_dict


def calculate_correlations(df):
    """Calculate correlation matrix."""
    cols = ['temperature', 'humidity', 'soil_moisture', 'battery_voltage']
    corr_matrix = df[cols].corr()
    
    print("\n" + "=" * 60)
    print("CORRELATION MATRIX")
    print("=" * 60)
    print(corr_matrix.round(3))
    
    return corr_matrix


# ============================================================================
# FIGURE GENERATION
# ============================================================================

def create_output_directory():
    """Create figures output directory."""
    import os
    os.makedirs('figures', exist_ok=True)
    print("\nFigures will be saved to: figures/")


def fig1_sensor_time_series(df):
    """
    Figure 1: Environmental Parameters Over Time
    Shows temperature, humidity, and soil moisture trends.
    """
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    
    # Temperature
    ax1 = axes[0]
    ax1.plot(df['timestamp'], df['temperature'], 'r-', alpha=0.7, linewidth=0.8, label='Temperature')
    ax1.axhline(y=21.0, color='r', linestyle='--', alpha=0.5, linewidth=1, label='Threshold (21°C)')
    ax1.fill_between(df['timestamp'], df['temperature'], 21.0, 
                     where=df['temperature'] > 21.0, alpha=0.2, color='red', label='Above Threshold')
    ax1.set_ylabel('Temperature (°C)')
    ax1.set_ylim([18, 28])
    ax1.legend(loc='upper right', ncol=3)
    ax1.set_title('Temperature Response to Mist Maker Activation')
    
    # Humidity
    ax2 = axes[1]
    ax2.plot(df['timestamp'], df['humidity'], 'b-', alpha=0.7, linewidth=0.8, label='Humidity')
    ax2.axhline(y=40.0, color='b', linestyle='--', alpha=0.5, linewidth=1, label='Threshold (40%)')
    ax2.fill_between(df['timestamp'], df['humidity'], 40.0,
                     where=df['humidity'] < 40.0, alpha=0.2, color='blue', label='Below Threshold')
    ax2.set_ylabel('Relative Humidity (%)')
    ax2.set_ylim([5, 50])
    ax2.legend(loc='upper right', ncol=3)
    ax2.set_title('Humidity Levels During Monitoring Period')
    
    # Soil Moisture
    ax3 = axes[2]
    ax3.plot(df['timestamp'], df['soil_moisture'], 'g-', alpha=0.7, linewidth=0.8, label='Soil Moisture')
    ax3.axhline(y=2416, color='g', linestyle='--', alpha=0.5, linewidth=1, label='Threshold (2416)')
    ax3.fill_between(df['timestamp'], df['soil_moisture'], 2416,
                     where=df['soil_moisture'] > 2416, alpha=0.2, color='green', label='Above Threshold (Drier)')
    ax3.set_ylabel('Soil Moisture (ADC)')
    ax3.set_ylim([400, 3200])
    ax3.legend(loc='upper right', ncol=3)
    ax3.set_title('Soil Moisture Levels (Higher = Drier Soil)')
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax3.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax3.set_xlabel('Time')
    
    plt.tight_layout()
    plt.savefig('figures/fig1_sensor_time_series.png')
    plt.savefig('figures/fig1_sensor_time_series.pdf')
    plt.close()
    print("  ✓ Figure 1: Sensor time series")


def fig2_control_system_validation(df):
    """
    Figure 2: Control System Validation
    Shows how actuators respond to threshold conditions.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    
    # Create time-relative column for x-axis
    time_rel = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / 60
    
    # 2a: Temperature vs Mist Status
    ax1 = axes[0, 0]
    mist_on = df[df['mist_status'] == 1]
    mist_off = df[df['mist_status'] == 0]
    
    ax1.scatter(mist_on['temperature'], mist_on['humidity'], c='red', alpha=0.5, s=20, label='Mist ON')
    ax1.scatter(mist_off['temperature'], mist_off['humidity'], c='blue', alpha=0.5, s=20, label='Mist OFF')
    ax1.axvline(x=21.0, color='gray', linestyle='--', alpha=0.7, label='Temp Threshold (21°C)')
    ax1.axhline(y=40.0, color='gray', linestyle=':', alpha=0.7, label='Humidity Threshold (40%)')
    ax1.set_xlabel('Temperature (°C)')
    ax1.set_ylabel('Relative Humidity (%)')
    ax1.set_title('(a) Mist Maker Activation Regions')
    ax1.legend(loc='upper right')
    ax1.set_xlim([20, 28])
    ax1.set_ylim([5, 45])
    
    # 2b: Soil Moisture Distribution vs Threshold
    ax2 = axes[0, 1]
    pump_on = df[df['pump_status'] == 1]
    pump_off = df[df['pump_status'] == 0]
    
    ax2.hist(pump_on['soil_moisture'], bins=30, alpha=0.6, color='green', label='Pump ON', density=True)
    ax2.hist(pump_off['soil_moisture'], bins=30, alpha=0.6, color='gray', label='Pump OFF', density=True)
    ax2.axvline(x=2416, color='black', linestyle='--', linewidth=2, label='Threshold (2416)')
    ax2.set_xlabel('Soil Moisture (ADC)')
    ax2.set_ylabel('Density')
    ax2.set_title('(b) Soil Moisture Distribution vs Pump Activation')
    ax2.legend()
    
    # 2c: Mode Distribution Over Time
    ax3 = axes[1, 0]
    auto_mode = df[df['mode'] == 0]
    manual_mode = df[df['mode'] == 1]
    
    ax3.scatter(time_rel[auto_mode.index], auto_mode['temperature'], c='blue', s=15, alpha=0.6, label='AUTO Mode')
    ax3.scatter(time_rel[manual_mode.index], manual_mode['temperature'], c='orange', s=15, alpha=0.6, label='MANUAL Mode')
    ax3.axhline(y=21.0, color='red', linestyle='--', alpha=0.7, label='Threshold')
    ax3.set_xlabel('Time (minutes from start)')
    ax3.set_ylabel('Temperature (°C)')
    ax3.set_title('(c) Control Mode Distribution')
    ax3.legend()
    
    # 2d: Battery Voltage Stability
    ax4 = axes[1, 1]
    ax4.plot(time_rel, df['battery_voltage'], 'purple', alpha=0.7, linewidth=0.8)
    ax4.axhline(y=df['battery_voltage'].mean(), color='red', linestyle='-', linewidth=2, 
                label=f"Mean: {df['battery_voltage'].mean():.2f}V")
    ax4.axhline(y=7.25, color='green', linestyle='--', linewidth=1.5, alpha=0.7, label='Expected: 7.25V')
    ax4.fill_between(time_rel, df['battery_voltage'].mean() - df['battery_voltage'].std(),
                     df['battery_voltage'].mean() + df['battery_voltage'].std(),
                     alpha=0.2, color='purple')
    ax4.set_xlabel('Time (minutes from start)')
    ax4.set_ylabel('Battery Voltage (V)')
    ax4.set_title('(d) Battery Voltage Stability')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('figures/fig2_control_validation.png')
    plt.savefig('figures/fig2_control_validation.pdf')
    plt.close()
    print("  ✓ Figure 2: Control system validation")


def fig3_correlation_analysis(df):
    """
    Figure 3: Correlation Analysis
    Shows relationships between parameters.
    """
    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    
    # 3a: Temperature vs Humidity
    ax1 = axes[0, 0]
    ax1.scatter(df['temperature'], df['humidity'], alpha=0.5, s=20, c='steelblue')
    
    # Add regression line
    mask = ~np.isnan(df['temperature']) & ~np.isnan(df['humidity'])
    if mask.sum() > 2:
        z = np.polyfit(df['temperature'][mask], df['humidity'][mask], 1)
        p = np.poly1d(z)
        x_line = np.linspace(df['temperature'].min(), df['temperature'].max(), 100)
        ax1.plot(x_line, p(x_line), 'r-', linewidth=2, label=f'Trend: y={z[0]:.2f}x+{z[1]:.1f}')
    
    ax1.set_xlabel('Temperature (°C)')
    ax1.set_ylabel('Relative Humidity (%)')
    ax1.set_title('(a) Temperature vs Humidity')
    ax1.legend()
    
    # 3b: Temperature vs Soil Moisture
    ax2 = axes[0, 1]
    ax2.scatter(df['temperature'], df['soil_moisture'], alpha=0.5, s=20, c='forestgreen')
    ax2.set_xlabel('Temperature (°C)')
    ax2.set_ylabel('Soil Moisture (ADC)')
    ax2.set_title('(b) Temperature vs Soil Moisture')
    
    # 3c: Humidity vs Soil Moisture
    ax3 = axes[1, 0]
    ax3.scatter(df['humidity'], df['soil_moisture'], alpha=0.5, s=20, c='coral')
    ax3.set_xlabel('Relative Humidity (%)')
    ax3.set_ylabel('Soil Moisture (ADC)')
    ax3.set_title('(c) Humidity vs Soil Moisture')
    
    # 3d: Correlation Heatmap
    ax4 = axes[1, 1]
    cols = ['temperature', 'humidity', 'soil_moisture', 'battery_voltage']
    corr = df[cols].corr()
    
    im = ax4.imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1)
    ax4.set_xticks(range(len(cols)))
    ax4.set_yticks(range(len(cols)))
    ax4.set_xticklabels(['Temp', 'Hum', 'Soil', 'Batt'], rotation=45)
    ax4.set_yticklabels(['Temp', 'Hum', 'Soil', 'Batt'])
    
    # Add correlation values
    for i in range(len(cols)):
        for j in range(len(cols)):
            text = ax4.text(j, i, f'{corr.iloc[i, j]:.2f}',
                           ha='center', va='center', color='black', fontsize=10)
    
    ax4.set_title('(d) Correlation Matrix')
    plt.colorbar(im, ax=ax4, label='Correlation Coefficient')
    
    plt.tight_layout()
    plt.savefig('figures/fig3_correlation_analysis.png')
    plt.savefig('figures/fig3_correlation_analysis.pdf')
    plt.close()
    print("  ✓ Figure 3: Correlation analysis")


def fig4_distribution_analysis(df):
    """
    Figure 4: Parameter Distributions
    Shows distribution of each measured parameter.
    """
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    
    # 4a: Temperature Distribution
    ax1 = axes[0, 0]
    ax1.hist(df['temperature'], bins=25, color='indianred', alpha=0.7, edgecolor='black')
    ax1.axvline(x=df['temperature'].mean(), color='red', linestyle='-', linewidth=2, 
                label=f"Mean: {df['temperature'].mean():.1f}°C")
    ax1.axvline(x=21.0, color='blue', linestyle='--', linewidth=2, label='Threshold: 21°C')
    ax1.set_xlabel('Temperature (°C)')
    ax1.set_ylabel('Frequency')
    ax1.set_title('(a) Temperature Distribution')
    ax1.legend()
    
    # 4b: Humidity Distribution
    ax2 = axes[0, 1]
    ax2.hist(df['humidity'], bins=25, color='steelblue', alpha=0.7, edgecolor='black')
    ax2.axvline(x=df['humidity'].mean(), color='red', linestyle='-', linewidth=2,
                label=f"Mean: {df['humidity'].mean():.1f}%")
    ax2.axvline(x=40.0, color='blue', linestyle='--', linewidth=2, label='Threshold: 40%')
    ax2.set_xlabel('Relative Humidity (%)')
    ax2.set_ylabel('Frequency')
    ax2.set_title('(b) Humidity Distribution')
    ax2.legend()
    
    # 4c: Soil Moisture Distribution
    ax3 = axes[1, 0]
    ax3.hist(df['soil_moisture'], bins=30, color='forestgreen', alpha=0.7, edgecolor='black')
    ax3.axvline(x=df['soil_moisture'].mean(), color='red', linestyle='-', linewidth=2,
                label=f"Mean: {df['soil_moisture'].mean():.0f}")
    ax3.axvline(x=2416, color='blue', linestyle='--', linewidth=2, label='Threshold: 2416')
    ax3.set_xlabel('Soil Moisture (ADC)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('(c) Soil Moisture Distribution')
    ax3.legend()
    
    # 4d: Battery Voltage Distribution
    ax4 = axes[1, 1]
    ax4.hist(df['battery_voltage'], bins=20, color='purple', alpha=0.7, edgecolor='black')
    ax4.axvline(x=df['battery_voltage'].mean(), color='red', linestyle='-', linewidth=2,
                label=f"Mean: {df['battery_voltage'].mean():.2f}V")
    ax4.axvline(x=7.25, color='green', linestyle='--', linewidth=2, label='Expected: 7.25V')
    ax4.set_xlabel('Battery Voltage (V)')
    ax4.set_ylabel('Frequency')
    ax4.set_title('(d) Battery Voltage Distribution')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('figures/fig4_distribution_analysis.png')
    plt.savefig('figures/fig4_distribution_analysis.pdf')
    plt.close()
    print("  ✓ Figure 4: Distribution analysis")


def fig5_system_performance_summary(df, stats_dict):
    """
    Figure 5: System Performance Summary Table
    Creates a publication-ready summary table.
    """
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('off')
    
    # Create summary table
    table_data = [
        ['Parameter', 'Mean', 'Std Dev', 'Min', 'Max', 'Threshold', 'Threshold Status'],
        ['Temperature (°C)', f"{stats_dict['temperature']['mean']:.1f}", 
         f"{stats_dict['temperature']['std']:.1f}",
         f"{stats_dict['temperature']['min']:.1f}", f"{stats_dict['temperature']['max']:.1f}",
         '21.0', 'Activated (>21°C)'],
        ['Humidity (%)', f"{stats_dict['humidity']['mean']:.1f}",
         f"{stats_dict['humidity']['std']:.1f}",
         f"{stats_dict['humidity']['min']:.1f}", f"{stats_dict['humidity']['max']:.1f}",
         '40.0', 'Activated (<40%)'],
        ['Soil Moisture (ADC)', f"{stats_dict['soil_moisture']['mean']:.0f}",
         f"{stats_dict['soil_moisture']['std']:.0f}",
         f"{stats_dict['soil_moisture']['min']:.0f}", f"{stats_dict['soil_moisture']['max']:.0f}",
         '2416', 'Activated (>2416)'],
        ['Battery Voltage (V)', f"{stats_dict['battery_voltage']['mean']:.2f}",
         f"{stats_dict['battery_voltage']['std']:.2f}",
         f"{stats_dict['battery_voltage']['min']:.2f}", f"{stats_dict['battery_voltage']['max']:.2f}",
         '-', 'Stable'],
    ]
    
    table = ax.table(cellText=table_data, loc='center', cellLoc='center',
                     colWidths=[0.18, 0.12, 0.12, 0.10, 0.10, 0.12, 0.18])
    
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)
    
    # Style header row
    for j in range(7):
        table[(0, j)].set_facecolor('#4472C4')
        table[(0, j)].set_text_props(color='white', fontweight='bold')
    
    # Style data rows
    for i in range(1, 5):
        for j in range(7):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#D9E2F3')
    
    ax.set_title('Table 1: Greenhouse Monitoring System Performance Summary\n', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('figures/fig5_performance_summary.png', bbox_inches='tight', dpi=300)
    plt.savefig('figures/fig5_performance_summary.pdf', bbox_inches='tight')
    plt.close()
    print("  ✓ Figure 5: Performance summary table")


def fig6_control_effectiveness(df):
    """
    Figure 6: Control System Effectiveness
    Shows how well the system maintains conditions.
    """
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    
    # Calculate percentages
    total_points = len(df)
    
    # Temperature control effectiveness
    temp_above = (df['temperature'] > 21.0).sum()
    temp_pct = (temp_above / total_points) * 100
    
    ax1 = axes[0]
    sizes1 = [100 - temp_pct, temp_pct]
    labels1 = ['Within Range', 'Above Threshold']
    colors1 = ['#4CAF50', '#FF5722']
    wedges1, texts1, autotexts1 = ax1.pie(sizes1, labels=labels1, colors=colors1,
                                          autopct='%1.1f%%', startangle=90,
                                          explode=(0, 0.05))
    ax1.set_title(f'(a) Temperature\n(Mist Active: {temp_pct:.1f}%)')
    
    # Humidity control effectiveness
    humid_below = (df['humidity'] < 40.0).sum()
    humid_pct = (humid_below / total_points) * 100
    
    ax2 = axes[1]
    sizes2 = [100 - humid_pct, humid_pct]
    labels2 = ['Above Threshold', 'Below Threshold']
    colors2 = ['#4CAF50', '#2196F3']
    wedges2, texts2, autotexts2 = ax2.pie(sizes2, labels=labels2, colors=colors2,
                                          autopct='%1.1f%%', startangle=90,
                                          explode=(0, 0.05))
    ax2.set_title(f'(b) Humidity\n(Mist Active: {humid_pct:.1f}%)')
    
    # Soil moisture effectiveness
    soil_above = (df['soil_moisture'] > 2416).sum()
    soil_pct = (soil_above / total_points) * 100
    
    ax3 = axes[2]
    sizes3 = [100 - soil_pct, soil_pct]
    labels3 = ['Moist (OK)', 'Dry (Pump Active)']
    colors3 = ['#4CAF50', '#FF9800']
    wedges3, texts3, autotexts3 = ax3.pie(sizes3, labels=labels3, colors=colors3,
                                          autopct='%1.1f%%', startangle=90,
                                          explode=(0, 0.05))
    ax3.set_title(f'(c) Soil Moisture\n(Pump Active: {soil_pct:.1f}%)')
    
    plt.tight_layout()
    plt.savefig('figures/fig6_control_effectiveness.png')
    plt.savefig('figures/fig6_control_effectiveness.pdf')
    plt.close()
    print("  ✓ Figure 6: Control system effectiveness")


def generate_latex_table(stats_dict):
    """Generate LaTeX formatted table for paper."""
    latex_code = r"""
\begin{table}[h]
\centering
\caption{Greenhouse Monitoring System Performance Summary}
\label{tab:performance}
\begin{tabular}{lcccccl}
\hline
\textbf{Parameter} & \textbf{Mean} & \textbf{Std Dev} & \textbf{Min} & \textbf{Max} & \textbf{Threshold} & \textbf{Status} \\
\hline
Temperature (°C) & """ + f"{stats_dict['temperature']['mean']:.1f}" + r""" & """ + f"{stats_dict['temperature']['std']:.1f}" + r""" & """ + f"{stats_dict['temperature']['min']:.1f}" + r""" & """ + f"{stats_dict['temperature']['max']:.1f}" + r""" & 21.0 & Activated \\
Humidity (\%) & """ + f"{stats_dict['humidity']['mean']:.1f}" + r""" & """ + f"{stats_dict['humidity']['std']:.1f}" + r""" & """ + f"{stats_dict['humidity']['min']:.1f}" + r""" & """ + f"{stats_dict['humidity']['max']:.1f}" + r""" & 40.0 & Activated \\
Soil Moisture (ADC) & """ + f"{stats_dict['soil_moisture']['mean']:.0f}" + r""" & """ + f"{stats_dict['soil_moisture']['std']:.0f}" + r""" & """ + f"{stats_dict['soil_moisture']['min']:.0f}" + r""" & """ + f"{stats_dict['soil_moisture']['max']:.0f}" + r""" & 2416 & Activated \\
Battery Voltage (V) & """ + f"{stats_dict['battery_voltage']['mean']:.2f}" + r""" & """ + f"{stats_dict['battery_voltage']['std']:.2f}" + r""" & """ + f"{stats_dict['battery_voltage']['min']:.2f}" + r""" & """ + f"{stats_dict['battery_voltage']['max']:.2f}" + r""" & -- & Stable \\
\hline
\end{tabular}
\end{table}
"""
    
    with open('figures/table_performance.tex', 'w') as f:
        f.write(latex_code)
    
    print("  ✓ LaTeX table saved to: figures/table_performance.tex")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main analysis pipeline."""
    print("\n" + "=" * 60)
    print("GREENHOUSE MONITORING DATA ANALYSIS")
    print("=" * 60)
    
    # Load and process data
    df_raw = load_and_clean_data('greenhouse_complete_log.csv')
    df_clean = process_data(df_raw, battery_filter=7.25)
    
    # Generate statistics
    stats_dict = generate_statistics(df_clean)
    corr_matrix = calculate_correlations(df_clean)
    
    # Create output directory
    create_output_directory()
    
    print("\n" + "=" * 60)
    print("GENERATING FIGURES")
    print("=" * 60)
    
    # Generate all figures
    fig1_sensor_time_series(df_clean)
    fig2_control_system_validation(df_clean)
    fig3_correlation_analysis(df_clean)
    fig4_distribution_analysis(df_clean)
    fig5_system_performance_summary(df_clean, stats_dict)
    fig6_control_effectiveness(df_clean)
    
    # Generate LaTeX table
    generate_latex_table(stats_dict)
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nGenerated 6 publication-quality figures in 'figures/' directory")
    print("  - fig1_sensor_time_series.png/pdf")
    print("  - fig2_control_validation.png/pdf")
    print("  - fig3_correlation_analysis.png/pdf")
    print("  - fig4_distribution_analysis.png/pdf")
    print("  - fig5_performance_summary.png/pdf")
    print("  - fig6_control_effectiveness.png/pdf")
    print("  - table_performance.tex (LaTeX table)")
    
    return df_clean, stats_dict


if __name__ == "__main__":
    df, stats = main()
