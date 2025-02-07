import pandas as pd
import streamlit as st
from matchmaker.data import State

def color_trades_by_type(row):
    if row['Type'] == 'Long':
        return ['background-color: #d4edda'] * len(row)  # lighter green
    elif row['Type'] == 'Short':
        return ['background-color: #f8d7da'] * len(row)  # lighter red
    elif row['Type'] == 'Expired':
        return ['background-color: #e2e3e5'] * len(row)  # lighter gray
    elif row['Type'] == 'Assigned':
        return ['background-color: #ffe5d4'] * len(row)  # lighter salmon
    elif row['Type'] == 'Exercised':
        return ['background-color: #e6e6fa'] * len(row)  # lighter thistle
    else:
        return ['background-color: #d1ecf1'] * len(row)  # lighter cyan

def color_paired_trades_by_revenue(row, min_revenue, max_revenue):
    revenue = row['Revenue']
    if revenue < 0 and min_revenue != 0:
        color = f'background-color: rgba(255, 0, 0, {0.5 * min(abs(revenue) / abs(min_revenue), 1)})'  # red gradient
    elif  max_revenue != 0:
        color = f'background-color: rgba(0, 255, 0, {0.5 * min(revenue / max_revenue, 1)})'  # green gradient
    return [color] * len(row)

def color_trades_as_red(row):
    return ['color: darkred; background-color: #f9e2e3'] * len(row)

def format_trades(df : pd.DataFrame):
    return df.style.apply(color_trades_by_type, axis=1)

def format_paired_trades(df : pd.DataFrame):
    min_revenue = df['Revenue'].min()
    max_revenue = df['Revenue'].max()
    return df.style.apply(color_paired_trades_by_revenue, axis=1, min_revenue=min_revenue, max_revenue=max_revenue)

def format_missing_trades(df : pd.DataFrame):
    return df.style.apply(color_trades_as_red, axis=1)