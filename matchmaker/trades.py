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

def add_split_data(trades, tickers_dir):
    if 'Split Ratio' not in trades.columns:
        trades['Split Ratio'] = np.nan
    if tickers_dir is not None:
        for symbol, group in trades.groupby('Symbol'):
            filename = tickers_dir + '/' + symbol + '_data.csv'
            if os.path.exists(filename):
                try:
                    ticker = pd.read_csv(tickers_dir + '/' + symbol + '_data.csv')
                    ticker['Date'] = pd.to_datetime(ticker['Date'], format='%Y-%m-%d').dt.date
                    ticker.set_index('Date', inplace=True)
                    for index, row in group[group['Split Ratio']==np.nan].iterrows():
                        ratio = 1
                        try:
                            ratio = ticker.loc[pd.to_datetime(row['Date/Time']).date(), 'Adj Ratio']
                        except KeyError:
                            print('No split data for', symbol, 'on', pd.to_datetime(row['Date/Time']).date())
                        trades.loc[index, 'Split Ratio'] = ratio
                        if ratio != 1:
                            print('Adjusted quantity for', symbol, 'from', row['Quantity'], 'to',  row['Quantity'] * ratio, ', ratio:', ratio)
                    
                except Exception as e:
                    print('Error reading', filename, ':', e)
    trades.fillna({'Split Ratio': 1}, inplace=True)

def add_accumulated_positions(trades):
    for symbol, group in trades.groupby('Symbol'):
        accumulated = 0
        for index, row in group.sort_values(by=['Date/Time']).iterrows():
            accumulated += row['Quantity']
            trades.loc[index, 'Accumulated Quantity'] = accumulated

@st.cache_data()
def populate_extra_trade_columns(trades, tickers_dir=None):
    add_split_data(trades, tickers_dir)
    trades['Quantity'] = trades['Quantity'] * trades['Split Ratio']
    trades['T. Price'] = trades['T. Price'] / trades['Split Ratio']
    add_accumulated_positions(trades)
    trades = trades.sort_values(by=['Date/Time'])

