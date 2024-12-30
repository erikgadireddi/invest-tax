import numpy as np
import pandas as pd
import streamlit as st
import matchmaker.data as data

# Ensure all columns are in non-string format
def convert_trade_columns(df):
    df['Date/Time'] = pd.to_datetime(df['Date/Time'])
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
    df['Proceeds'] = pd.to_numeric(df['Proceeds'], errors='coerce')
    df['Comm/Fee'] = pd.to_numeric(df['Comm/Fee'], errors='coerce')
    df['Basis'] = pd.to_numeric(df['Basis'], errors='coerce')
    df['Realized P/L'] = pd.to_numeric(df['Realized P/L'], errors='coerce')
    df['MTM P/L'] = pd.to_numeric(df['MTM P/L'], errors='coerce')
    df['T. Price'] = pd.to_numeric(df['T. Price'], errors='coerce')
    df['C. Price'] = pd.to_numeric(df['C. Price'], errors='coerce')
    if 'Code' in df.columns:
       df['Action'] = df['Code'].apply(lambda x: 'Open' if 'O' in x else 'Close' if 'C' in x else 'Unknown')
    # If action is not Transfer, then Type is Long if we're opening a position, Short if closing
    def get_type(row):
        if row['Quantity'] == 0:
            return None
        if row['Action'] == 'Transfer':
            return 'In' if row['Quantity'] > 0 else 'Out'
        if (row['Action'] == 'Close' and row['Quantity'] < 0) or (row['Action'] == 'Open' and row['Quantity'] > 0):
            return 'Long'
        return 'Short'
    df['Type'] = df.apply(get_type, axis=1)
    return df

# Process trades from raw DataFrame
def normalize_trades(df):
    df['Year'] = df['Date/Time'].dt.year
    df = convert_trade_columns(df)
    df['Orig. Quantity'] = df['Quantity']
    df['Orig. T. Price'] = df['T. Price']
    # Set up the hash column as index
    df['Hash'] = df.apply(data.hash_row, axis=1)
    df.set_index('Hash', inplace=True)
    # st.write('Imported', len(df), 'rows')
    return df

# Add newly created trades to existing trades, making necessary recomputations
def add_new_trades(new_trades, trades):
    trades = pd.concat([trades, normalize_trades(new_trades)])
    return process_after_import(trades)

# Merge two sets of processed trades together
@st.cache_data()
def merge_trades(existing, new):
    if existing is None:
        return new
    merged = pd.concat([existing, new])
    return merged[~merged.index.duplicated(keep='first')]

# Recompute dependent columns after importing new trades
@st.cache_data()
def process_after_import(trades, actions=None):
    trades = _adjust_for_splits(trades, actions)
    trades = _populate_extra_trade_columns(trades)
    return trades

# Add split data column to trades by consulting split actions
def _add_split_data(trades, split_actions):
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

# Add or refresh dynamically computed columns
@st.cache_data()
def _populate_extra_trade_columns(trades):
    trades = _add_accumulated_positions(trades)
    return trades

# Compute accumulated positions for each symbol by simulating all trades
@st.cache_data()
def _add_accumulated_positions(trades):
    trades = trades.sort_values(by=['Date/Time'])
    trades['Accumulated Quantity'] = trades.groupby('Symbol')['Quantity'].cumsum()
    return trades

# Adjust quantities and trade prices for splits
@st.cache_data()
def _adjust_for_splits(trades, split_actions):
    if split_actions is not None and not split_actions.empty:
        _add_split_data(trades, split_actions)
        trades['Quantity'] = trades['Orig. Quantity'] * trades['Split Ratio']
        trades['T. Price'] = trades['Orig. T. Price'] / trades['Split Ratio']
    return trades