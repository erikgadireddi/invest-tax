import glob
import numpy as np
import pandas as pd
import streamlit as st

def adjust_rates_columns(df):
    # Headers contain the divisor for the rates
    # Example header: 1 HKD|100 HUF|1000 IDR|1 ILS|100 INR|100 ISK|100 JPY
    # For headers that are greater than 1, divide the rows by that number
    for column in df.columns:
        divisor = int(column.split(' ')[0])
        df[column] = pd.to_numeric(df[column], errors='coerce')
        df[column] = df[column] / divisor
        # Update column name with currency code
        df.rename(columns={column: column.split(' ')[1]}, inplace=True)
    return df

@st.cache_data()
def load_yearly_rates(directory):
    df = pd.read_csv(directory + '/CurrencyRatesYearly.csv')
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    df.set_index('Year', inplace=True)
    df = adjust_rates_columns(df)
    return df

# Load daily CNB rates
@st.cache_data()
def load_daily_rates(directory):
    df = None
    for f in glob.glob(directory + '/CurrencyRatesDaily.*.csv'):
        if df is None:
            df = pd.read_csv(f)
        else:
            df = pd.concat([df, pd.read_csv(f)], ignore_index = True)
    df['Datum'] = pd.to_datetime(df['Datum'], format='%d.%m.%Y')
    df.set_index('Datum', inplace=True)
    df = adjust_rates_columns(df)
    return df

def get_adjusted_price(ticker, date):
    pass

@st.cache_data()
def add_czk_conversion_to_trades(trades, rates, use_yearly_rates=True):
    if use_yearly_rates:
        trades['CZK Rate'] = trades.apply(lambda row: rates.loc[row['Date/Time'].year, row['Currency']] if row['Date/Time'].year in rates.index else np.nan, axis=1)
    else:
        trades['CZK Rate'] = trades.apply(lambda row: rates.loc[rates.index[rates.index <= pd.to_datetime(row['Date/Time'].date())].max(), row['Currency']], axis=1)
    trades['CZK Proceeds'] = trades['Proceeds'] *  trades['CZK Rate']
    trades['CZK Commission'] = trades['Comm/Fee'] * trades['CZK Rate']
    trades['CZK Profit'] = trades['Realized P/L'] * trades['CZK Rate']
    return trades

def add_czk_conversion_to_pairs(trade_pairs, rates, use_yearly_rates=True):
    annotated_pairs = trade_pairs.copy()
    if use_yearly_rates:
        annotated_pairs['Buy CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[row['Buy Time'].year, row['Currency']] if row['Buy Time'].year in rates.index else np.nan, axis=1)
        annotated_pairs['Sell CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[row['Sell Time'].year, row['Currency']] if row['Sell Time'].year in rates.index else np.nan, axis=1)
    else:
        annotated_pairs['Buy CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[rates.index[rates.index <= pd.to_datetime(row['Buy Time'].date())].max(), row['Currency']], axis=1)
        annotated_pairs['Sell CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[rates.index[rates.index <= pd.to_datetime(row['Sell Time'].date())].max(), row['Currency']], axis=1)
    annotated_pairs['CZK Cost'] = annotated_pairs['Cost'] *  annotated_pairs['Buy CZK Rate']
    annotated_pairs['CZK Proceeds'] = annotated_pairs['Proceeds'] *  annotated_pairs['Sell CZK Rate']
    annotated_pairs['CZK Revenue'] = annotated_pairs['CZK Proceeds'] + annotated_pairs['CZK Cost']
    return annotated_pairs
