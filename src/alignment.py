import numpy as np
import pandas as pd
from fastdtw import fastdtw
from scipy.signal import correlate
from scipy.interpolate import interp1d
import os

from .config import Config

def load_and_map_lowfq_to_highfq(data_folder):
    """
    interpolate low-frequency data to high-frequency timestamps (using zero-order hold)
    """
    low_freq_df = pd.read_csv(f'{data_folder}/low_freq_data.csv')
    high_freq_df = pd.read_csv(f'{data_folder}/high_freq_data.csv')
    
    low_freq_df.set_index('timestamp', inplace=True)
    high_freq_df.set_index('timestamp', inplace=True)
    
    # Interpolate low-frequency data to high-frequency timestamps with forward fill and backward fill for leading NaNs
    low_freq_interp = low_freq_df.reindex(high_freq_df.index).ffill().bfill()
    
    low_freq_interp.reset_index(inplace=True)
    high_freq_df.reset_index(inplace=True)
    
    return low_freq_interp, high_freq_df

def load_and_interpolate(data_folder, target_freq_hz, interpolation_method):
    """
    Resample both the low-frequency and high-frequency time series to a new frequency
    """
    # Load the data from CSV files
    low_freq_df = pd.read_csv(f'{data_folder}/low_freq_data.csv')
    high_freq_df = pd.read_csv(f'{data_folder}/high_freq_data.csv')
    
    # Determine the common time range
    start = max(low_freq_df['timestamp'].min(), high_freq_df['timestamp'].min())
    end = min(low_freq_df['timestamp'].max(), high_freq_df['timestamp'].max())
    dt = 1 / target_freq_hz  # Time step based on target frequency
    new_timestamps = np.arange(start, end, dt)  # New timestamp array
    
    # Interpolate low-frequency data
    f_low = interp1d(low_freq_df['timestamp'], low_freq_df['target_angle'],
                     kind=interpolation_method, bounds_error=False, fill_value='extrapolate')
    low_angles_resampled = f_low(new_timestamps)
    
    # Interpolate high-frequency data
    f_high = interp1d(high_freq_df['timestamp'], high_freq_df['motor_angle'],
                      kind=interpolation_method, bounds_error=False, fill_value='extrapolate')
    high_angles_resampled = f_high(new_timestamps)
    
    # Create resampled DataFrames
    low_freq_resampled = pd.DataFrame({
        'timestamp': new_timestamps,
        'target_angle': low_angles_resampled
    })
    high_freq_resampled = pd.DataFrame({
        'timestamp': new_timestamps,
        'motor_angle': high_angles_resampled
    })
    
    return low_freq_resampled, high_freq_resampled

def custom_dtw(series1, series2):
    """
    Implementation of Dynamic Time Warping (DTW) for two 1D series.

    For demonstration purpose, not for efficiency
    """
    n, m = len(series1), len(series2)

    # Step 1: Initialize the cost matrix
    # Cost matrix will store "cumulative cost" of aligning the two series "up to each point".
    # Dimensions is (n+1) x (m+1) to include a "start" position at (0, 0).
    # - Rows (i) correspond to indices in series1 (0 to n)
    # - Columns (j) correspond to indices in series2 (0 to m)
    cost_matrix = np.zeros((n + 1, m + 1))

    # Set the first row and column to infinity, except for (0, 0)
    # This will ensure the alignment must start at the beginning of both series (without doing this we might skip the start of one series).
    cost_matrix[0, :] = np.inf
    cost_matrix[:, 0] = np.inf
    cost_matrix[0, 0] = 0   # Starting point has zero cost
    
    # Step 2: Fill the cost matrix using dynamic programming
    # by loop through each point in series1 (i) and series2 (j)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            # local cost (difference) between the current points
            cost = abs(series1[i - 1] - series2[j - 1])

            # cumulative cost at (i, j) =  local cost + the minimum cost of reaching this point from 1 of 3 possible previous positions.
            cost_matrix[i, j] = cost + min(cost_matrix[i - 1, j],       # Step from above
                                           cost_matrix[i, j - 1],       # Step from left
                                           cost_matrix[i - 1, j - 1])   # Diagonal step
    
    # Step 3: Backtrack to find the optimal alignment path
    # Cost matrix now contains the minimum cost for aligning the series up to each point,
    # e.g. cost_matrix[n, m] is the 'total DTW distance', which is minimum cost to align both series fully.
    # So, trace backward from (n, m) to (0, 0) will find the path of matched points.
    path = []
    i, j = n, m             # start from the bottom-right corner of the cost matrix
    while i > 0 and j > 0:  # until reached top-left corner (0, 0)
        path.append((i - 1, j - 1))     # -1 because cost_matrix indices are offset by 1 from series indices

        # find minimum cost among the 3 possible previous positions
        min_cost = min(cost_matrix[i - 1, j], cost_matrix[i, j - 1], cost_matrix[i - 1, j - 1])
        if min_cost == cost_matrix[i - 1, j - 1]:
            i -= 1
            j -= 1
        elif min_cost == cost_matrix[i - 1, j]:
            i -= 1
        else:
            j -= 1

    # path is backward, need to reverse it to start from (0, 0)
    path.reverse()
    distance = cost_matrix[n, m]
    return distance, path

def clean_path(path):
    """
    Cleaning up the DTW path
    remove redundant one-to-many mappings at the very beginning and end of the path
    """
    if not path:
        return []
    
    # Find the last index of the initial segment where the first index is constant
    i_start = path[0][0]  # e.g., 0
    k = 0
    while k < len(path) and path[k][0] == i_start:
        k += 1
    k -= 1  # k is now the index of the last pair with i_start (e.g., [0, 54])
    
    # Find the first index of the final segment where the second index is constant
    j_end = path[-1][1]  # e.g., 792
    m = len(path) - 1
    while m >= 0 and path[m][1] == j_end:
        m -= 1
    m += 1  # m is now the index of the first pair with j_end (e.g., [737, 792])
    
    # Return the cleaned path from index k to m inclusive
    return path[k:m+1]

def naive_cross_correlation(series1, series2, max_shift):
    """
    Naive cross-correlation to find the best shift within a specified range.

    Args:
        series1 (np.ndarray): First time series
        series2 (np.ndarray): Second time series
        max_shift (int): Maximum shift in samples

    Returns:
        tuple: (best_shift, max_corr) - Best shift in samples and corresponding correlation coefficient
    """
    if len(series1) != len(series2):
        raise ValueError("Series1 and Series2 must have the same length")
    
    n = len(series1)
    shifts = range(-max_shift, max_shift + 1)
    correlations = []
    
    for shift in shifts:
        if shift >= 0:
            a = series1[:-shift]
            b = series2[shift:]
        else:
            k = -shift
            a = series1[k:]
            b = series2[:-k]
        if len(a) < 2 or len(b) < 2:
            correlations.append(-1.0)  # Insufficient data for correlation
            continue
        corr = np.corrcoef(a, b)[0, 1]
        correlations.append(corr if not np.isnan(corr) else -1.0)
    
    best_shift = shifts[np.argmax(correlations)]
    max_corr = max(correlations)
    return best_shift, max_corr

def fft_cross_correlation(series1, series2, timestamps):
    """
    FFT-based cross-correlation to find the best shift.

    Args:
        series1 (np.ndarray): First time series
        series2 (np.ndarray): Second time series
        timestamps (np.ndarray): Timestamps of the series

    Returns:
        tuple: (shift_seconds, norm_corr) - Best shift in seconds and normalized correlation score
    """
    n = len(series1)
    cc = correlate(series1, series2, mode='full')
    lags = np.arange(-n + 1, n)
    best_lag = lags[np.argmax(cc)]
    
    # Normalize the cross-correlation score
    norm_factor = np.sqrt(np.sum(series1**2) * np.sum(series2**2))
    norm_corr = cc[np.argmax(cc)] / norm_factor  # Score between -1 and 1
    
    dt = timestamps[1] - timestamps[0]
    shift_seconds = - best_lag * dt
    return shift_seconds, norm_corr

def align_data(data_folder, method='dtw_library', config=None):
    """
    Align two time series using the specified method.

    Args:
        data_folder (str): Path to the folder containing the data CSV files
        method (str): Alignment method ('dtw_library', 'dtw_custom', 'cc_naive', 'cc_fft')
        config (dict, optional): Configuration dictionary for method-specific parameters

    Returns:
        dict: Alignment results including method, global_shift, path, and score
    """

    # Extract resampling parameters from config
    target_freq_hz = config.get('resampler', {}).get('target_freq_hz', 200)
    interpolation_method = config.get('resampler', {}).get('interpolation_method', 'linear')
    
    # Load and resample the data
    low_freq_resampled, high_freq_resampled = load_and_interpolate(
        data_folder, target_freq_hz, interpolation_method
    )
    # save
    output_dir = config.get('output_dir', "data")
    low_freq_resampled.to_csv(os.path.join(output_dir, 'low_freq_resampled.csv'), index=False)
    high_freq_resampled.to_csv(os.path.join(output_dir, 'high_freq_resampled.csv'), index=False)

    low_angles = low_freq_resampled['target_angle'].values
    high_angles = high_freq_resampled['motor_angle'].values
    timestamps = low_freq_resampled['timestamp'].values

    dt = timestamps[1] - timestamps[0]
    jitter = 0.0  # jitter, standard deviation of shifts
    
    if method == 'dtw_custom':
        distance, path = custom_dtw(low_angles, high_angles)
        path = clean_path(path)     # remove redundant mappings at start and end
        shifts = [timestamps[j] - timestamps[i] for i, j in path]
        global_shift = np.mean(shifts)
        jitter = np.std(shifts) if len(shifts) > 1 else 0.0  # Standard deviation of shifts
        # correlation coefficient as 'matching score'
        aligned_series1 = [low_angles[i] for i, j in path]
        aligned_series2 = [high_angles[j] for i, j in path]        
        score = np.corrcoef(aligned_series1, aligned_series2)[0, 1] if len(path) > 1 else 0.0

    elif method == 'dtw_library':
        distance, path = fastdtw(low_angles, high_angles, dist=lambda x, y: abs(x - y))
        path = clean_path(path)     # remove redundant mappings at start and end
        shifts = [timestamps[j] - timestamps[i] for i, j in path]
        global_shift = np.mean(shifts)
        jitter = np.std(shifts) if len(shifts) > 1 else 0.0  # Standard deviation of shifts
        # compute correlation coefficient as the score
        aligned_series1 = [low_angles[i] for i, j in path]
        aligned_series2 = [high_angles[j] for i, j in path]        
        score = np.corrcoef(aligned_series1, aligned_series2)[0, 1] if len(path) > 1 else 0.0

    elif method == 'cc_naive':
        max_shift = config.get('max_shift', 100)  # Default max_shift of 100 samples
        best_shift_samples, corr = naive_cross_correlation(low_angles, high_angles, max_shift)
        global_shift = best_shift_samples * dt
        jitter = 0.0  # No jitter for global shift methods
        shift_samples = int(round(global_shift / dt))
        path = [(i, i + shift_samples) for i in range(len(low_angles)) 
                if 0 <= i + shift_samples < len(high_angles)]
        score = corr

    elif method == 'cc_fft':
        shift_seconds, corr = fft_cross_correlation(low_angles, high_angles, timestamps)
        global_shift = shift_seconds
        jitter = 0.0  # No jitter for global shift methods
        shift_samples = int(round(global_shift / dt))
        path = [(i, i + shift_samples) for i in range(len(low_angles)) 
                if 0 <= i + shift_samples < len(high_angles)]
        score = corr
    
    else:
        raise ValueError(f"Unknown alignment method: {method}")
    
    return {
        'method': method,
        'global_shift': global_shift,
        'jitter': jitter,
        'path': path,
        'score': score
    }



# Example usage
if __name__ == "__main__":
    import json
    import time

    config = Config('configs/config_alignment_default.yaml')
    data_folder = config.get('input_dir')

    # all alignment methods to run
    methods = ['dtw_library', 'dtw_custom', 'cc_naive', 'cc_fft']
    for method in methods:
        start_time = time.time()
        result = align_data(data_folder, method=method, config=config)
        result['runtime'] = time.time() - start_time
        
        file_name = f"alignment_result_{method}.json"
        file_path = os.path.join(data_folder, file_name)
        with open(file_path, 'w') as f:
            json.dump(result, f)
        print(f"Result for '{method}' method saved to '{file_path}'")
        print(f"  score={result['score']:.4f}, shift={result['global_shift']:.4f}, jitter={result['jitter']:.4f}, runtime={result['runtime']:.3f} seconds")




