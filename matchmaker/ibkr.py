import glob
import re
import pandas as pd
import streamlit as st
import numpy as np
from .trade import normalize_trades
import matchmaker.actions as actions
from io import StringIO

def dataframe_from_lines_with_prefix(file, prefix):
    file.seek(0)
    file = [line.decode('utf-8') for line in file]
    # Filter file lines to those beginning with 'Trades'
    file_lines = [line for line in file if line.startswith(prefix)]
    if len(file_lines) == 0:
        return pd.DataFrame(columns=['Corporate Actions', 'Header', 'Asset Category', 'Date/Time', 'Currency', 'Symbol', 'Quantity', 'Ratio', 'Description', 'Proceeds', 'Value', 'Realized P/L', 'Action', 'Code'])
    file_data = StringIO('\n'.join(file_lines))
    return pd.read_csv(file_data)


# Import trades from IBKR format
# First line is the headers: Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
# Column	Descriptions
# Trades	The trade number.
# Header	Header record contains the report title and the date and time of the report.
# Asset Category	The asset category of the instrument. Possibl   e values are: "Stocks", "Options", "Futures", "FuturesOptions
# Symbol	    The symbol of the instrument you traded.
# Date/Time	The date and the time of the execution.
# Quantity	The number of units for the transaction.
# T. Price	The transaction price.
# C. Price	The closing price of the instrument.
# Proceeds	Calculated by mulitplying the quantity and the transaction price. The proceeds figure will be negative for buys and positive for sales.
# Comm/Fee	The total amount of commission and fees for the transaction.
# Basis	    The basis of an opening trade is the inverse of proceeds plus commission and tax amount. For closing trades, the basis is the basis of the opening trade.

# Data begins on the second line
# Example line: Trades,Data,Order,Stocks,CZK,CEZ,"2023-08-03, 08:44:03",250,954,960,-238500,-763.2,239263.2,0,1500,O
def import_trades(file):
    df = dataframe_from_lines_with_prefix(file, 'Trades')
    df = df[(df['Trades'] == 'Trades') & (df['Header'] == 'Data') & (df['DataDiscriminator'] == 'Order') & (df['Asset Category'] == 'Stocks')]
    # Filter DataFrame by Asset Category == 'Stocks' and DataDiscriminator == 'Data' (rest is partial sums and totals)
    df = df[(df['Asset Category'] == 'Stocks') & (df['DataDiscriminator'] == 'Order')]
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='%Y-%m-%d, %H:%M:%S')
    df['Quantity'] = pd.to_numeric(df['Quantity'].astype(str).str.replace(',', ''), errors='coerce')
    return normalize_trades(df)

def import_corporate_actions(file):
    df = dataframe_from_lines_with_prefix(file, 'Corporate Actions,')
    df = df[df['Asset Category'] == 'Stocks']
    df.drop(columns=['Corporate Actions', 'Header', 'Asset Category'], inplace=True)
    df['Action'] = df['Description'].apply(lambda x: 'Dividend' if 'Dividend' in x else 'Split' if 'Split' in x else 'Unknown')
    
    def parse_action_symbol(text):
        match = re.search(r'^(\w+)\(\w+\)', text)
        if match:
            return match.group(1)
        return None
    
    def parse_split_text(text):
        match = re.search(r'([\w\.]+)\(\w+\) Split (\d+) for (\d+)', text)
        if match:
            return match.group(1), int(match.group(2)), int(match.group(3))
        return None, None, None
    
    def get_split_ratio(text):
        ticker, before, after = parse_split_text(text)
        if before is not None and after is not None:
            return float(after) / before
        return np.nan
    
    df['Quantity'] = pd.to_numeric(df['Quantity'].astype(str).str.replace(',', ''), errors='coerce')
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='%Y-%m-%d, %H:%M:%S')
    df['Symbol'] = df['Description'].apply(lambda x: parse_action_symbol(x))    
    df['Ratio'] = df[df['Action'] == 'Split']['Description'].apply(lambda x: get_split_ratio(x))
    df = actions.convert_action_columns(df)
    return df

@st.cache_data()
def import_activity_statement(file):
    trades = import_trades(file)
    actions = import_corporate_actions(file)
    return trades, actions

def import_all_statements(directory, tickers_dir=None):
    # Go over all 'Activity' exports that contain all data and extract only the 'Trades' part
    data = None
    for f in glob.glob(directory + '/U*_*_*.csv'):
        # Only if matching U12345678_[optional_]20230101_20231231.csv
        if(re.match(r'.+U(\d+)_(\d{8})_(\d{8})', f)):
            # Read the file 
            with open(f, 'r') as file:
                data = import_activity_statement(file, data, tickers_dir)
                yield data
        else:
            print('Skipping file:', f)
