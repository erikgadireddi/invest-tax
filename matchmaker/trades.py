import os
import numpy as np
import pandas as pd
import streamlit as st

def convert_trade_columns(df):
    df['Date/Time'] = pd.to_datetime(df['Date/Time'])
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
    df['Proceeds'] = pd.to_numeric(df['Proceeds'], errors='coerce')
    df['Comm/Fee'] = pd.to_numeric(df['Comm/Fee'], errors='coerce')
    df['Basis'] = pd.to_numeric(df['Basis'], errors='coerce')
    df['Realized P/L'] = pd.to_numeric(df['Realized P/L'], errors='coerce')
    df['MTM P/L'] = pd.to_numeric(df['MTM P/L'], errors='coerce')
    df['T. Price'] = pd.to_numeric(df['T. Price'], errors='coerce')
    df['Action'] = df['Code'].apply(lambda x: 'Open' if 'O' in x else 'Close' if 'C' in x else 'Unknown')
    df['Type'] = df.apply(lambda row: 'Long' if (row['Action'] == 'Open' and row['Quantity'] > 0) or (row['Action'] == 'Close' and row['Quantity'] < 0) else 'Short', axis=1)
    return df

@st.cache_data()
def import_raw_trades(file):
    df = pd.read_csv(file)
    df.set_index('Hash', inplace=True)
    df = convert_trade_columns(df)
    return df, pd.DataFrame()

@st.cache_data()
def merge_trades(existing, new):
    if existing is None:
        return new
    merged = pd.concat([existing, new])
    return merged[~merged.index.duplicated(keep='first')]

def add_split_data(trades, split_actions):
    split_actions = split_actions[split_actions['Action'] == 'Split']
    if 'Split Ratio' not in trades.columns:
        trades['Split Ratio'] = np.nan
    if not split_actions.empty:
        # Enhance trades with Split Ratio column by looking up same symbol in split_actions
        #  and summing all ratio columns that have a date sooner than the row in trades    
        split_actions = split_actions.sort_values(by='Date/Time', ascending=True)
        split_actions['Cumulative Ratio'] = split_actions.groupby('Symbol')['Ratio'].cumprod()
        trades['Split Ratio'] = 1 / trades.apply(lambda row: split_actions[(split_actions['Symbol'] == row['Symbol']) & (split_actions['Date/Time'] > row['Date/Time'])]['Cumulative Ratio'].min(), axis=1)
        split_actions.drop(columns=['Cumulative Ratio'], inplace=True)
    trades.fillna({'Split Ratio': 1}, inplace=True)

@st.cache_data()
def add_accumulated_positions(trades):
    trades = trades.sort_values(by=['Date/Time'])
    trades['Accumulated Quantity'] = trades.groupby('Symbol')['Quantity'].cumsum()
    return trades

@st.cache_data()
def populate_extra_trade_columns(trades):
    trades = add_accumulated_positions(trades)
    trades = trades.sort_values(by=['Date/Time'])
    return trades

@st.cache_data()
def adjust_for_splits(trades, split_actions):
    if split_actions is not None and not split_actions.empty:
        add_split_data(trades, split_actions)
        trades['Quantity'] = trades['Orig. Quantity'] * trades['Split Ratio']
        trades['T. Price'] = trades['Orig. T. Price'] / trades['Split Ratio']
    return trades