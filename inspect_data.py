
import asyncio
import os
import sys
import pandas as pd

# Add project root to path
sys.path.append(os.getcwd())

from bomtempo.core.data_loader import DataLoader

def inspect_current_data():
    print("--- Inspecting Current Data ---")
    loader = DataLoader()
    data = loader.load_all()
    
    # 1. Geography
    if "contratos" in data:
        df = data["contratos"]
        if "localizacao" in df.columns:
            print("\nLocation Distribution (Contratos):")
            print(df["localizacao"].value_counts())
        
    # 2. Date Ranges
    if "obras" in data:
        df = data["obras"]
        if "data" in df.columns:
            print(f"\nObras Date Range: {df['data'].min()} to {df['data'].max()}")
            
    # 3. Contract Totals
    if "contratos" in data:
        print(f"\nTotal Contracts: {len(data['contratos'])}")

    # 4. Check for missing links
    if "contratos" in data and "obras" in data:
        contratos_ids = set(data["contratos"]["contrato"].unique())
        obras_ids = set(data["obras"]["contrato"].unique())
        print(f"\nContracts without Obras: {contratos_ids - obras_ids}")
        print(f"Obras without Contracts: {obras_ids - contratos_ids}")

if __name__ == "__main__":
    inspect_current_data()
