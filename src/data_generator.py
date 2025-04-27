import os
import numpy as np
import pandas as pd
from .config import Config

def generate_low_freq_data(config):
    """
    Generate low-frequency command data.  with irregular timestamps and skips.

    Returns:
        tuple: (timestamps, angles) - Arrays of timestamps and target angles
    """
    duration = config.get('duration')
    nominal_freq = config.get('low_freq_hz')
    irregularity = config.get('low_freq_irregularity')
    skip_prob = config.get('low_freq_skip_prob')
    angle_amplitude = config.get('angle_amplitude')
    angle_freq = config.get('angle_freq')
    noise_std = config.get('low_freq_noise_std')
    
    # Generate nominal timestamps with jitter
    num_points = int(duration * nominal_freq)
    regular_timestamps = np.linspace(0, duration, num_points, endpoint=False)
    offsets = np.random.normal(0, irregularity, num_points)
    timestamps = regular_timestamps + offsets
    timestamps.sort()
    
    # Simulate skipped frames
    keep = np.random.rand(num_points) > skip_prob
    timestamps = timestamps[keep]
    
    # Linearly decreasing amplitude
    amplitudes = angle_amplitude * (1 - timestamps / (duration*2))

    # Generate target angles (sine wave with noise)
    angles = amplitudes * np.sin(2 * np.pi * angle_freq * timestamps) + \
             np.random.normal(0, noise_std, len(timestamps))
    
    return timestamps, angles

def simulate_network(low_freq_timestamps, low_freq_angles, config):
    """
    Simulate network transmission with delays, jitter, and packet loss.
    
    Args:
        low_freq_timestamps: Array of command timestamps
        low_freq_angles: Array of command angles

    Returns:
        tuple: (received_times, received_angles) - Arrays of received timestamps and angles
    """
    delay_mean = config.get('delay_mean')
    jitter_std = config.get('jitter_std')
    jitter_start_time = config.get('jitter_start_time', 0.0)  # Default to 0
    jitter_end_time = config.get('jitter_end_time', float('inf'))  # Default to infinity
    extra_delay_start_time = config.get('extra_delay_start_time', float('inf'))  # Default: no extra delay
    extra_delay_end_time = config.get('extra_delay_end_time', float('inf'))      # Default: no extra delay
    extra_delay_amount = config.get('extra_delay_amount', 0.0)                   # Default: 0 seconds
    loss_prob = config.get('loss_prob')

    # Initialize delays with the mean delay for all packets
    delays = np.full_like(low_freq_timestamps, delay_mean)
    
    # Apply jitter only within the specified time window
    in_window = (low_freq_timestamps >= jitter_start_time) & (low_freq_timestamps <= jitter_end_time)
    jitter = np.random.normal(0, jitter_std, len(low_freq_timestamps))
    delays[in_window] += jitter[in_window]  # Add jitter only to packets within the window

    # Apply extra delay within the specified extra delay window
    in_extra_delay_window = (low_freq_timestamps >= extra_delay_start_time) & (low_freq_timestamps <= extra_delay_end_time)
    delays[in_extra_delay_window] += extra_delay_amount

    delays = np.maximum(delays, 0)  # Ensure non-negative delays
    received_times = low_freq_timestamps + delays
    
    # Simulate packet loss
    keep = np.random.rand(len(received_times)) > loss_prob
    received_times = received_times[keep]
    low_freq_timestamps_kept = low_freq_timestamps[keep]  # Keep send times aligned with received times
    received_angles = low_freq_angles[keep]
    
    # Sort by receipt time, but keep track of original send times
    sorted_idx = np.argsort(received_times)
    received_times_sorted = received_times[sorted_idx]
    send_times_sorted = low_freq_timestamps_kept[sorted_idx]  # Corresponding send times
    received_angles_sorted = received_angles[sorted_idx]

    # Filter out packets that arrive out of order relative to send times
    filtered_received_times = []
    filtered_received_angles = []
    latest_send_time = -np.inf  # Track the latest send time of accepted packets

    for send_t, recv_t, angle in zip(send_times_sorted, received_times_sorted, received_angles_sorted):
        if send_t > latest_send_time:
            # Accept packet if it was sent later than the last accepted packet
            filtered_received_times.append(recv_t)
            filtered_received_angles.append(angle)
            latest_send_time = send_t
        # Else, discard if sent earlier but received after a later-sent packet

    return np.array(filtered_received_times), np.array(filtered_received_angles)


def simulate_pd_control(received_times, received_angles, config):
    """
    Simulate high-frequency PD control process with physical disturbances integrated.
    """
    high_freq = config.get('high_freq_hz')
    duration = config.get('duration')
    tau = config.get('motor_time_constant')
    physical_errors = config.get('physical_errors', {})

    dt = 1 / high_freq
    alpha = 1 - np.exp(-dt / tau)  # Base first-order lag coefficient

    high_freq_timestamps = np.arange(0, duration, dt)
    motor_angle = 0.0  # Initial angle
    motor_angles = []

    cmd_idx = 0
    for t in high_freq_timestamps:
        # Get latest received command
        while cmd_idx < len(received_times) and received_times[cmd_idx] <= t:
            cmd_idx += 1
        current_target = received_angles[cmd_idx - 1] if cmd_idx > 0 else 0.0

        # Adjust alpha and add noise based on disturbances
        alpha_effective = alpha  # Default responsiveness
        noise = 0.0  # Default noise

        # Heavy object: Slows movement by reducing alpha
        if 'heavy_object' in physical_errors:
            start = physical_errors['heavy_object'].get('start_time', -np.inf)
            end = physical_errors['heavy_object'].get('end_time', np.inf)
            if start <= t <= end:
                reduction_factor = physical_errors['heavy_object'].get('reduction_factor', 0.2)
                alpha_effective *= reduction_factor  # Slows response

        # Overheating: Reduces torque (via alpha) and adds noise
        if 'overheat' in physical_errors:
            start = physical_errors['overheat'].get('start_time', -np.inf)
            end = physical_errors['overheat'].get('end_time', np.inf)
            if start <= t <= end:
                torque_reduction = physical_errors['overheat'].get('torque_reduction', 0.5)
                alpha_effective *= torque_reduction  # Simulate reduced torque
                prob = physical_errors['overheat'].get('probability', 0.0)
                if np.random.rand() < prob:
                    noise_std = physical_errors['overheat'].get('noise_std', 0.0)
                    noise = np.random.normal(0, noise_std)  # Erratic behavior

        # Update motor angle with effective alpha and noise
        motor_angle = (1 - alpha_effective) * motor_angle + alpha_effective * current_target + noise

        # Hitting a wall: Enforce position constraint
        if 'hit_wall' in physical_errors:
            start = physical_errors['hit_wall'].get('start_time', -np.inf)
            end = physical_errors['hit_wall'].get('end_time', np.inf)
            if start <= t <= end:
                max_angle = physical_errors['hit_wall'].get('max_angle', np.inf)
                motor_angle = min(motor_angle, max_angle)

        motor_angles.append(motor_angle)

    return high_freq_timestamps, np.array(motor_angles)

def simulate_pd_control_kp_kd(received_times, received_angles, config):
    """
    Simulate high-frequency PD control to generate motor angles
    """
    # Extract config parameters
    high_freq = config.get('high_freq_hz')
    duration = config.get('duration')
    kp = config.get('pd_control_kp', 2.0)  # Proportional gain (default 2.0)
    kd = config.get('pd_control_kd', 0.1)  # Derivative gain (default 0.1)

    dt = 1 / high_freq
    high_freq_timestamps = np.arange(0, duration, dt)
    motor_angle = 0.0  # Initial angle
    motor_velocity = 0.0  # Initial velocity
    motor_angles = []
    previous_error = 0.0
    cmd_idx = 0

    for t in high_freq_timestamps:
        # Get the latest received command
        while cmd_idx < len(received_times) and received_times[cmd_idx] <= t:
            cmd_idx += 1
        current_target = received_angles[cmd_idx - 1] if cmd_idx > 0 else 0.0

        # position error
        error = current_target - motor_angle
        error_derivative = (error - previous_error) / dt if t > 0 else 0.0
        previous_error = error

        # PD control (proportional + derivative terms)
        acceleration = kp * error + kd * error_derivative

        # Update motor velocity and position
        motor_velocity += acceleration * dt
        motor_angle += motor_velocity * dt

        motor_angles.append(motor_angle)
    
    return high_freq_timestamps, np.array(motor_angles)

def save_data(low_freq_timestamps, low_freq_angles, high_freq_timestamps, high_freq_angles, config):
    """
    Save low- and high-frequency data to CSV files.
    """
    output_dir = config.get('output_dir', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    low_freq_df = pd.DataFrame({'timestamp': low_freq_timestamps, 'target_angle': low_freq_angles})
    low_freq_df.to_csv(os.path.join(output_dir, 'low_freq_data.csv'), index=False)
    
    high_freq_df = pd.DataFrame({'timestamp': high_freq_timestamps, 'motor_angle': high_freq_angles})
    high_freq_df.to_csv(os.path.join(output_dir, 'high_freq_data.csv'), index=False)

def generate_data(config):
    """
    Orchestrate the data generation process reflecting the physical flow.
    """
    # Step 1: Generate teleoperator user's command data
    low_freq_timestamps, low_freq_angles = generate_low_freq_data(config)
    
    # Step 2: Simulate network transport with jitter and loss
    received_times, received_angles = simulate_network(low_freq_timestamps, low_freq_angles, config)
    
    # Step 3: Simulate high-frequency PD control process
    high_freq_timestamps, motor_angles = simulate_pd_control(received_times, received_angles, config)
    # apply physical disturbances to motor angles

    # Step 4: DO SOMETHING CRAZY to generate negative data (should have low matching score)
    if config.get('crazy_errors', {}).get('flip', False):
        motor_angles = np.flip(motor_angles)    # reverse the order
    if config.get('crazy_errors', {}).get('negate', False):
        motor_angles = - motor_angles           # negate the values
    
    
    # Step 5: Save the generated data
    save_data(low_freq_timestamps, low_freq_angles, high_freq_timestamps, motor_angles, config)


# Example usage
if __name__ == "__main__":
    config = Config('configs/config_data_gen_0_base.yaml')
    generate_data(config)
