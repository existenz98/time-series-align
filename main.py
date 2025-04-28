import os
import time
import json
from src.config import Config
from src.data_generator import generate_data
from src.alignment import align_data
from src.visualization import plot_raw_data, plot_alignment

def main():

    # Step 1: Generate data
    print("Generating time series data...")
    generate_data(Config("configs/config_data_gen_0_base.yaml"))

    # Step 2: Run alignment for each method
    config = Config('configs/config_alignment_default.yaml')
    data_folder = config.get('input_dir')

    methods = ['dtw_library', 'dtw_custom', 'cc_naive', 'cc_fft']   # all alignment methods to run
    print("Running alignment for methods:", methods)
    for method in methods:
        start_time = time.time()
        result = align_data(data_folder, method=method, config=config)
        result['runtime'] = time.time() - start_time
        
        # Save alignment result
        file_name = f"alignment_result_{method}.json"
        file_path = os.path.join(data_folder, file_name)
        with open(file_path, 'w') as f:
            json.dump(result, f)
        print(f"Result for '{method}' saved to '{file_path}'")
        print(f"  score={result['score']:.4f}, shift={result['global_shift']:.4f}, jitter={result['jitter']:.4f}, runtime={result['runtime']:.3f} seconds")

    # Step 3: Visualize results
    print("Generating visualizations...")
    # Plot raw data
    save_raw_path = os.path.join(data_folder, 'raw_data.png')
    plot_raw_data(data_folder, save_path=save_raw_path)

    # Plot alignment results for each method
    for method in methods:
        save_align_path = os.path.join(data_folder, f'alignment_{method}.png')
        plot_alignment(data_folder, method=method, save_path=save_align_path)

if __name__ == "__main__":
    main()
