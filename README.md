# Time-Series-Align

Demonstrate time series alignment algorithms for robotics applications. 
It aligns two time series with different sampling frequencies:

1. **low-frequency** command (e.g., 30 Hz from AI Action Model, or Human Teleoperation)

2. **high-frequency** data (e.g., 1000 Hz from CSP motor command or actual motor feedback)

Implemented 4 alignment methods like
1) Dynamic Time Warping (**DTW**) from scratch
2) Dynamic Time Warping (**DTW**) using **fastdtw** lib
3) **Naive Cross-Correlation** from scratch
4) **FFT** based Cross-Correlation lib

The project simulates realistic data generation: applies **network effects** and **physical disturbances**

The main.py will **1) generate** sim data,  **2) aligns** the series, and **3) visualizes** the results.

## Experiments and Results
[Experiments and Results](experiments_results.md)


## Features

### 1. Data Generation
The project generates synthetic time series data to simulate a robotic control scenario:
- **Low-Frequency Command Data**:
  - Generated at ~30 Hz (configurable) to mimic VLA position control data or Teleoperation data.
  - Features **irregular timestamps** and **skipped frames** to simulate real-world imperfections.
  - Uses a decaying sine wave (amplitude decreases over time) to create dynamic motion patterns.
- **High-Frequency Motor Data**:
  - Generated at ~1000 Hz (configurable) to simulate a motor control loop.
  - Incorporates a **PD (Proportional-Derivative) controller** to track command angles.
  - Simulates **network effects**:
    - Configurable **mean delay** (e.g., 50ms).
    - **Jitter (random delay variation)** applied within a specified time window.
    - **Extra delay** during a specified period to simulate network congestion.
    - Out-of-order packet handling: Ignores packets delayed so much that they arrive after a later-sent packet.
  - Applies physical disturbances during the control loop:
    - **Heavy Object**: Reduces motor responsiveness (slower tracking).
    - **Overheating**: Decreases motor torque output and adds random noise.
    - **Hitting a Wall**: Caps the motor angle at a maximum value.
- **Crazy Data Changes**: Optional negation and flipping of motor angles to generate negative data for testing alignment algorithms (controlled by a config flag).

### 2. Time Series Alignment
Implemented 4 alignment methods:
- **DTW (Dynamic Time Warping) methods**:
  - `dtw_custom`: A custom DTW implementation with detailed comments for demonstration and verification purposes.
  - `dtw_library`: Uses the `fastdtw` library for efficiency.
  - Cleans the DTW path to remove redundant one-to-many mappings at the start and end.
- **Cross-Correlation methods**:
  - `cc_naive`: **Brute-force cross-correlation** to find the best global shift.
  - `cc_fft`: **FFT-based cross-correlation** for faster computation.
- **Features**:
  - Resamples both series to a common frequency (e.g., 200 Hz) using linear interpolation (configurable).
  - Computes alignment metrics: **global latency**, **jitter** (local latency, only available with DTW methods), and **matching score** (correlation coefficient between aligned series).
  - Saves alignment results (path, global shift, jitter, score, **runtime**) to JSON files for later visualization.

### 3. Visualization
The project provides visualization tools to analyze the generated data and alignment results:
- **Raw Data Plot**:
  - Plots low-frequency commands (step-wise) and high-frequency motor angles (continuous).
- **Alignment Result Plot**:
  - Visualizes the aligned time series:
    - Shows the mapping path (lines connecting matched points).
  - Displays **local jitter intensity** (time difference minus global shift).
  - Shows **local angle errors after alignment**.

### 4. Configurable Pipeline
- **config_data_gen_.yaml**: controls simulation data generation parameters.
  - Frequencies, network delays, physical disturbances, etc.
- **config_alignment_.yaml**: controls alignment parameters.
  - Resampling frequency, etc.
- **Modular Execution**: `main.py` orchestrates the pipeline (data generation, alignment, visualization) using the config files.

### 5. Performance Measurement
- Measures runtime for each alignment method and includes it in the results.

## Usage

```bash
python main.py
```

Edit main.py `generate_data` function's input and change data generation config file to see different test cases
```python
def main():
    
    # Step 1: Generate data
    print("Generating time series data...")
    generate_data(Config("configs/config_data_gen_1_delay.yaml"))
```

### Output:

* Generated data: Saved to data/low_freq_data.csv , data/high_freq_data.csv.
* Alignment results: Saved to data/alignment_result_*.json.
* **Visualizations: Saved as png files in data/**


## Experiments and Results

[Experiments and Results](experiments_results.md)
