import pandas as pd
from bomtempo.core.data_loader import DataLoader
from bomtempo.core.ai_context import AIContext
import json

def inspect_data():
    loader = DataLoader()
    print("--- Loading All Data ---")
    # Force fresh load by clearing cache if needed or just calling load_all
    # and ensuring we see the prints from DataLoader
    data = loader.load_all()
    
    for key, df in data.items():
        print(f"\n--- {key.upper()} ({len(df)} rows) ---")
        if not df.empty:
            print(df.head(5).to_string())
            print(f"Columns: {list(df.columns)}")
        else:
            print("EMPTY")

    print("\n--- AI Context Generation ---")
    context = AIContext.get_dashboard_context(data)
    print(context)
    
    # Check for specific projects mentioned by user (3 projects/states)
    if 'contratos' in data and not data['contratos'].empty:
        df_c = data['contratos']
        print(f"\nColumns in CONTRATOS: {list(df_c.columns)}")
        if 'projeto' in df_c.columns:
            projects = df_c['projeto'].unique()
            print(f"Projects found: {projects}")
        else:
            print("Column 'projeto' NOT FOUND in contratos.")
            
        if 'localizacao' in df_c.columns:
            states = df_c['localizacao'].unique()
            print(f"States found: {states}")
        else:
            print("Column 'localizacao' NOT FOUND in contratos.")

if __name__ == "__main__":
    inspect_data()
