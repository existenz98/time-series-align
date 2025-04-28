# Experiments and Results


## Alignment Methods Implemented

Goal: align low-frequency command signals with high-frequency motor readouts, addressing challenges like time shifts, jitter, and frequency differences.

In this project explored 2 category of methods: **`dtw` : DTW / Dyanmic Time Warping** and **`cc` : Cross-Correlation**.

### DTW
* **How it works:** not only time shifting, but also allow **'local time stretching and shinking'** (like a rubber band) to make the best match.
* **What is it best for:** **robust for matching signals that has high variations in time** domain, e.g. due to random network delays and jitters,   or due to same action performed slow or fast.
* **able to calculate 'local latency'**, which is error in time domain.

### CC
* **assumes strict time domain correctness**, only account for errors in spatial domain.

### Implemented 4 methods:

`dtw` 
  1. `dtw_custom`, is a custom DTW implementation from scratch with detailed comments, designed for educational purposes to illustrate the dynamic programming approach of DTW.  (also includes path cleaning to remove redundant one-to-many mappings at the start and end, that standard DTW method doesn't have)
  2. `dtw_library`, uses `fastdtw` lib to perform efficient DTW.  This method should give the same result as dtw_custom.

`cc`
  1. `cc_naive`, uses a brute-force cross-correlation approach, sliding one series over the other to find the global shift that maximizes the correlation coefficient, serving as a baseline for shift-based alignment. 
  2. `cc_fft`, FFT-based cross-correlation method, a faster alternative by efficiently computing the correlation across all shifts using the Fast Fourier Transform.

These methods were evaluated in terms of **matching score**, **global shift accuracy**, the ability of identifying **local time domain jitter**, and **local positional difference**.

The following is the demonstrate the difference between two category of methods: `cc` and `dtw`.

## Demo 1 Signal Delay
On top of average latency 100ms, add **150ms extra delay from 1sec to 2sec**.

config_data_gen_1_delay.yaml
```yaml
extra_delay_start_time: 1.0  # Start time for extra delay (seconds)
extra_delay_end_time: 2.0    # End time for extra delay (seconds)
extra_delay_amount: 0.15     # Additional delay during the extra delay period (seconds)
```
### Generated time series data:
<img src="docs/1_raw_data.png" alt="Raw Data" width="400px">

### DTW vs CC
<img src="docs/1_alignments.png" alt="DTW vs CC" width="400px">

#### In this case, DTW is better than CC

1. CC's correspondance is wrong (left), DTW finds correct local correspondance (right).

<img src="docs/1_cc_dtw.png" alt="CC vs DTW" width="600px">

2. DTW can **correctly attribute the difference of 2 time series to 'time distance' or 'jitter'**,  and have **very low 'spatial error'**

<img src="docs/1_dtw_error.png" alt="DTW" width="400px">

3. CC **incorrectly attribute the difference to spatial error**.

<img src="docs/1_cc_error.png" alt="CC" width="400px">


### Comparative Analysis


| Method        | Matching Score | Global Shift (s) | Jitter (s) | Runtime (s) |
|---------------|----------------|------------------|------------|-------------|
| dtw_library   |                |                  |            |             |
| dtw_custom    |                |                  |            |             |
| cc_naive      |                |                  |            |             |
| cc_fft        |                |                  |            |             |
