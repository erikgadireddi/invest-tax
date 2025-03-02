import pandas as pd
import streamlit as st
import matchmaker.ibkr as ibkr
import matchmaker.snapshot as snapshot
import matchmaker.data as data

def convert_import_history_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert columns of the import history DataFrame to appropriate types.
    """
    df['From'] = pd.to_datetime(df['From'])
    df['To'] = pd.to_datetime(df['To'])
    df['Trade Count'] = pd.to_numeric(df['Trade Count'], errors='coerce')
    return df

def merge_import_intervals(imports: pd.DataFrame) -> pd.DataFrame:
    """ Merge intervals of imported trades together if they form a largerc ontinuous interval. """
    imports.sort_values(by=['Account', 'From'], inplace=True)
    merged_imports = []
    current_import = None

    for _, row in imports.iterrows():
        if current_import is None:
            current_import = row
        elif current_import['Account'] == row['Account'] and current_import['To'] >= row['From'] - pd.Timedelta(days=1):
            current_import['To'] = max(current_import['To'], row['To'])
            current_import['Trade Count'] += row['Trade Count']
        else:
            merged_imports.append(current_import)
            current_import = row

    if current_import is not None:
        merged_imports.append(current_import)

    imports = pd.DataFrame(merged_imports)
    return imports


def import_trade_file(file) -> data.State:
    try:
        if snapshot.is_snapshot(file):
            imported = snapshot.load_snapshot(file)
        else:
            imported = ibkr.import_activity_statement(file)
    except Exception as e:
        st.error(f'Error importing trades. File {file.name} does not contain the expected format. Error: {e}')
        return data.State()
    
    imported.normalize_tables()
    return imported
    
