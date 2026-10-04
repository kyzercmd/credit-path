import pandas as pd
from pathlib import Path
import hashlib
import os

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

def save_data(tables: dict[str, pd.DataFrame], path: str = None) -> None:
    if path is None:
        path = str(DATA_DIR)
        
    os.makedirs(path, exist_ok=True)
    
    for name, df in tables.items():
        df.to_parquet(Path(path) / f"{name}.parquet", engine="fastparquet")

def load_data(path: str = None) -> dict[str, pd.DataFrame]:
    if path is None:
        path = str(DATA_DIR)
        
    tables = {}
    for name in ['customers', 'transactions', 'daily_balances', 'bills', 'customer_attributes']:
        tables[name] = pd.read_parquet(Path(path) / f"{name}.parquet", engine="fastparquet")
        
    return tables

def get_customer_ids(split: str = 'all') -> list[str]:
    data = load_data()
    cids = data['customers']['customer_id'].tolist()
    
    if split == 'all':
        return cids
        
    holdout = []
    train_cids = []
    for cid in cids:
        # holdout 20% by hash
        if int(hashlib.md5(cid.encode()).hexdigest(), 16) % 100 < 20:
            holdout.append(cid)
        else:
            train_cids.append(cid)
            
    if split in ('test', 'holdout'):
        return holdout
    elif split == 'train':
        return train_cids
    else:
        raise ValueError("Invalid split")

def get_split_dates() -> dict:
    return {'train_end': '2025-09-30', 'test_start': '2025-10-01'}
