import pandas as pd
import urllib.request
import os
import numpy as np

url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00601/ai4i2020.csv"
output_path = "data/raw/ai4i2020.csv"
os.makedirs(os.path.dirname(output_path), exist_ok=True)

try:
    print("Attempting to download...")
    urllib.request.urlretrieve(url, output_path)
    print("Dataset source: downloaded")
except Exception as e:
    print(f"Download failed: {e}. Generating synthetic data...")
    np.random.seed(42)
    n_rows = 1000
    
    udi = np.arange(1, n_rows + 1)
    types = np.random.choice(['L', 'M', 'H'], size=n_rows, p=[0.6, 0.3, 0.1])
    product_id = [f"{t}{np.random.randint(10000, 99999)}" for t in types]
    air_temp = np.random.uniform(295, 305, size=n_rows)
    process_temp = np.random.uniform(305, 315, size=n_rows)
    rotational_speed = np.random.randint(1000, 2000, size=n_rows)
    torque = np.random.uniform(20, 80, size=n_rows)
    tool_wear = np.random.randint(0, 250, size=n_rows)
    temp_difference = process_temp - air_temp
    twf = (tool_wear > 220).astype(int)
    hdf = ((temp_difference > 8.5) & (rotational_speed < 1250)).astype(int)
    pwf = ((torque * rotational_speed > 115000) | (torque * rotational_speed < 26000)).astype(int)
    osf = ((tool_wear > 190) & (torque > 65)).astype(int)
    rnf = np.random.choice([0, 1], size=n_rows, p=[0.995, 0.005])
    machine_failure = ((twf + hdf + pwf + osf + rnf) > 0).astype(int)
    
    df = pd.DataFrame({
        'UDI': udi,
        'Product ID': product_id,
        'Type': types,
        'Air temperature [K]': air_temp,
        'Process temperature [K]': process_temp,
        'Rotational speed [rpm]': rotational_speed,
        'Torque [Nm]': torque,
        'Tool wear [min]': tool_wear,
        'Machine failure': machine_failure,
        'TWF': twf,
        'HDF': hdf,
        'PWF': pwf,
        'OSF': osf,
        'RNF': rnf
    })
    
    df.to_csv(output_path, index=False)
    print("Dataset source: synthetic")
