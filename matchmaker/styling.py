import pandas as pd
import streamlit as st
from matchmaker.data import State

def color_trades_by_type(row):
    if row['Type'] == 'Expired':
        return ['background-color: #f0f0f0'] * len(row)  # subtle gray
    elif (row['Type'] == 'Assigned') & (~pd.isna(row['Option Type'])):
        return ['background-color: #fff4e6'] * len(row)  # subtle peach
    elif (row['Type'] == 'Assigned') & (pd.isna(row['Option Type'])):
        return ['background-color: #ffebd6'] * len(row)  # subtle peach
    elif (row['Type'] == 'Exercised') & (~pd.isna(row['Option Type'])):
        return ['background-color: #f0f0ff'] * len(row)  # subtle lavender
    elif (row['Type'] == 'Exercised') & (pd.isna(row['Option Type'])):
        return ['background-color: #e8e8ff'] * len(row)  # subtle lavender
    elif (row['Type'] == 'Long') & (~pd.isna(row['Option Type'])):
        return ['background-color: #e6ffe6'] * len(row)  # subtle green
    elif (row['Type'] == 'Long') & (pd.isna(row['Option Type'])):
        return ['background-color: #e6f7e6'] * len(row)  # subtle green
    elif (row['Type'] == 'Short') & (~pd.isna(row['Option Type'])):
        return ['background-color: #ffe6e6'] * len(row)  # subtle red
    elif (row['Type'] == 'Short') & (pd.isna(row['Option Type'])):
        return ['background-color: #ffe6e6'] * len(row)  # subtle red
    else:
        return ['background-color: #e6f7ff'] * len(row)  # subtle cyan

def color_trades_red_to_green(row, column, min_value, max_value):
    color = 'background-color: transparent'  # default color
    revenue = row[column]
    if revenue < 0 and min_value != 0:
        color = f'background-color: rgba(255, 0, 0, {0.5 * min(abs(revenue) / abs(min_value), 1)})'  # red gradient
    elif max_value != 0:
        color = f'background-color: rgba(0, 255, 0, {0.5 * min(revenue / max_value, 1)})'  # green gradient
    return [color] * len(row)

def color_trades_as_red(row):
    return ['color: darkred; background-color: #f9e2e3'] * len(row)

def format_trades(df : pd.DataFrame):
    return df.style.apply(color_trades_by_type, axis=1)

def format_paired_trades(df : pd.DataFrame):
    min_revenue = df['CZK Revenue'].min()
    max_revenue = df['CZK Revenue'].max()
    return df.style.apply(color_trades_red_to_green, axis=1, column='CZK Revenue', min_value=min_revenue, max_value=max_revenue)

def format_missing_trades(df : pd.DataFrame):
    return df.style.apply(color_trades_as_red, axis=1)