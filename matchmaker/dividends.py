import pandas as pd

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    return df