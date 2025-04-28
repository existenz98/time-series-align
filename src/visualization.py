import pandas as pd
import matplotlib.pyplot as plt
import json
import os

def plot_raw_data(data_folder='data', save_path=None, figsize=(10, 6)):
    """
    Plot raw low-frequency and high-frequency time series data in a single figure.

    Args:
        save_path (str, optional): If provided, save the figure to this path instead of showing it
    """
    # Load generated raw data
    low_freq_df = pd.read_csv(f'{data_folder}/low_freq_data.csv')
    high_freq_df = pd.read_csv(f'{data_folder}/high_freq_data.csv')

    # a new figure to show both low and high freq data
    plt.figure(figsize=figsize)
    
    # Plot low-frequency data as a step (ladder) line
    plt.step(low_freq_df['timestamp'], low_freq_df['target_angle'], 
             label='Low-Freq Command', where='post', linestyle='-', color='orange')
    
    plt.plot(high_freq_df['timestamp'], high_freq_df['motor_angle'], 
             label='High-Freq Motor', linestyle='-', color='blue')
    
    # labels
    plt.xlabel('Time (s)')
    plt.ylabel('Angle (degrees)')
    plt.title('Raw Time Series Data')
    plt.legend()
    plt.grid(True)
    
    # save or show
    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()


def plot_alignment(data_folder='data', method='dtw_library', save_path=None, figsize=(8, 12)):
    """
    Plot alignment results

    Parameters:
    - method (str): Alignment method to visualize (e.g., 'dtw_library', 'cc_naive').
    """

    low_freq_file = os.path.join(data_folder, 'low_freq_resampled.csv')
    high_freq_file = os.path.join(data_folder, 'high_freq_resampled.csv')
    alignment_file = os.path.join(data_folder, f'alignment_result_{method}.json')

    low_freq_resampled = pd.read_csv(low_freq_file)
    high_freq_resampled = pd.read_csv(high_freq_file)
    with open(alignment_file, 'r') as f:
        alignment_result = json.load(f)

    # Create a figure with three subplots stacked vertically.
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=figsize, sharex=True, 
                                        gridspec_kw={'height_ratios': [3, 1, 1]})

    # --- Subplot 1: Time Series and Alignment Path ---
    # time series data
    ax1.plot(low_freq_resampled['timestamp'], low_freq_resampled['target_angle'], 
             label='Low-Freq Command', color='orange', linestyle='-', alpha=0.7)
    ax1.plot(high_freq_resampled['timestamp'], high_freq_resampled['motor_angle'], 
             label='High-Freq Motor', color='blue', linestyle='-', alpha=0.7)    
    # alignment lines
    path = alignment_result['path']
    for i, j in path:
        ax1.plot([low_freq_resampled['timestamp'].iloc[i], high_freq_resampled['timestamp'].iloc[j]],
                 [low_freq_resampled['target_angle'].iloc[i], high_freq_resampled['motor_angle'].iloc[j]],
                 color='gray', alpha=0.5, linewidth=0.5)
    # annotations for shift and jitter
    ax1.text(0.05, 0.95, f"Method: {method}\nScore: {alignment_result['score']:.3f}\nGlobal Shift: {alignment_result['global_shift']:.3f} s\nJitter: {alignment_result['jitter']:.3f} s",
             transform=ax1.transAxes, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.5))    
    # labels
    ax1.set_ylabel('Angle (degrees)')
    ax1.set_title(f'Alignment Result for {method}')
    ax1.legend()
    ax1.grid(True)

    # --- Subplot 2: Local Angle Error ---
    # calculate local angle error
    angle_errors = []
    error_timestamps = []
    for i, j in path:
        error = abs(low_freq_resampled['target_angle'].iloc[i] - high_freq_resampled['motor_angle'].iloc[j])
        angle_errors.append(error)
        error_timestamps.append(low_freq_resampled['timestamp'].iloc[i])
    # plot
    ax2.plot(error_timestamps, angle_errors, color='red', label='Local Angle Error', linestyle='-', marker='.', alpha=0.7)
    ax2.set_ylabel('Angle Error (degrees)')
    ax2.set_ylim(0, 15)   # angle error from 0 to 15 degrees
    ax2.set_title('Local Angle Error After Alignment')
    ax2.legend()
    ax2.grid(True)

    # --- Subplot 3: Local Jitter Intensity ---
    # calculate local jitter
    global_shift = alignment_result['global_shift']
    jitter_values = []
    jitter_timestamps = []
    for i, j in path:
        time_diff = high_freq_resampled['timestamp'].iloc[j] - low_freq_resampled['timestamp'].iloc[i]
        local_jitter = abs(time_diff - global_shift)
        jitter_values.append(local_jitter)
        jitter_timestamps.append(low_freq_resampled['timestamp'].iloc[i])
    # plot local jitter
    ax3.plot(jitter_timestamps, jitter_values, color='purple', label='Local Jitter', linestyle='-', marker='.', alpha=0.7)
    ax3.set_ylabel('Jitter (s)')
    ax3.set_ylim(0, 0.3)  # jitter from 0 to 0.3 seconds
    ax3.set_title('Local Jitter Intensity (Time Difference - Global Shift)')
    ax3.legend()
    ax3.grid(True)

    ax3.set_xlabel('Time (s)')
    
    plt.tight_layout()

    # Save or show the plot
    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
    else:
        plt.show()



# Example usage
if __name__ == "__main__":
    plot_raw_data('data')

    plot_alignment('data', 'dtw_library')
