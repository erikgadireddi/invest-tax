import pandas as pd
import streamlit as st
from matchmaker.data import State

def color_trades_by_type(row):
    if row['Type'] == 'Long':
        return ['color: green'] * len(row)
    elif row['Type'] == 'Short':
        return ['color: maroon'] * len(row)
    elif row['Type'] == 'Expired':
        return ['color: gray'] * len(row)
    elif row['Type'] == 'Assigned':
        return ['color: orange'] * len(row)
    elif row['Type'] == 'Exercised':
        return ['color: purple'] * len(row)
    else:
        return [''] * len(row)

def format_trades(df : pd.DataFrame):
    return df.style.apply(color_trades_by_type, axis=1)