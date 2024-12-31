import glob
import re
import pandas as pd
import streamlit as st
import numpy as np
from io import StringIO
from matchmaker.trade import normalize_trades
import matchmaker.actions as actions
import matchmaker.position as position

def dataframe_from_lines_with_prefix(file, prefix):
    file.seek(0)
    file = [line.decode('utf-8') for line in file]
    # Filter file lines to those beginning with 'Trades'
    file_lines = [line for line in file if line.startswith(prefix)]
    if len(file_lines) == 0:
        return pd.DataFrame()
    file_data = StringIO('\n'.join(file_lines))
    return pd.read_csv(file_data)


# Import trades from IBKR format
# First line is the headers: Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
# Column	Descriptions
# Trades	The trade number.
# Header	Header record contains the report title and the date and time of the report.
# Asset Category	The asset category of the instrument. Possible values are: "Stocks", "Options", "Futures", "FuturesOptions
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
    if df.empty:
        df = pd.DataFrame(columns=['Corporate Actions', 'Header', 'Asset Category', 'Currency', 'Report Date', 'Date/Time', 'Description', 'Quantity', 'Proceeds', 'Value', 'Realized P/L', 'Action', 'Symbol', 'Ratio', 'Code'])
    df = df[df['Asset Category'] == 'Stocks']
    df.drop(columns=['Corporate Actions', 'Header', 'Asset Category'], inplace=True)
    
    def parse_action_text(text):
        action, symbol, ratio = parse_split_text(text)
        if not action:
            action, symbol, ratio = parse_spinoff_text(text)
        if not action:
            match = re.search(r'^(\w+)\(\w+\)', text)
            if match:
                action, symbol, ratio = 'Unknown', match.group(1), 0.0
        if not action and 'Dividend' in text:
            action, symbol, ratio = 'Dividend', None, None
        if not action:
            action, symbol, ratio = 'Unknown', None, None
        return action, symbol, ratio
    
    def parse_split_text(text):
        match = re.search(r'([\w\.]+)\(\w+\) Split (\d+) for (\d+)', text)
        if match:
            ratio = float(match.group(3)) / float(match.group(2))
            return 'Split', match.group(1), ratio
        return None, None, None
    
    def parse_spinoff_text(text):
        match = re.search(r'^(\w+)\(\w+\) Spinoff\s+(\d+) for (\d+) \((\w+),.+\)', text)
        if match:
            ratio = float(match.group(2)) / float(match.group(3))
            return 'Spinoff', match.group(4), ratio
        return None, None, None
    
    df['Quantity'] = pd.to_numeric(df['Quantity'].astype(str).str.replace(',', ''), errors='coerce')
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='%Y-%m-%d, %H:%M:%S')
    if not df.empty:
        df[['Action', 'Symbol', 'Ratio']] = df['Description'].apply(lambda x: pd.Series(parse_action_text(x)))
    df.drop(columns=['Code'], inplace=True)
    df = actions.convert_action_columns(df)
    return df

def import_open_positions(file, date_from, date_to):
    # Old format that doesn't reflect symbol changes
    df = dataframe_from_lines_with_prefix(file, 'Mark-to-Market Performance Summary,')
    if df.empty:
        # Mark-to-Market Performance Summary,Header,Asset Category,Symbol,Prior Quantity,Current Quantity,Prior Price,
        # Current Price,Mark-to-Market P/L Position,Mark-to-Market P/L Transaction,Mark-to-Market P/L Commissions,Mark-to-Market P/L Other,Mark-to-Market P/L Total,Code
        df = pd.DataFrame(columns=['Mark-to-Market Performance Summary', 'Header', 'Asset Category', 'Symbol', 'Prior Quantity', 'Current Quantity', 'Prior Price', 'Current Price',
                                'Mark-to-Market P/L Position','Mark-to-Market P/L Transaction','Mark-to-Market P/L Commissions','Mark-to-Market P/L Other','Mark-to-Market P/L Total','Code'])
    df = df[df['Asset Category'] == 'Stocks']
    df.drop(columns=['Mark-to-Market Performance Summary', 'Header', 'Asset Category', 'Code'], inplace=True)
    df['Prior Date'] = date_from
    df['Current Date'] = date_to
    return position.convert_position_history_columns(df)

def import_transfers(file):
    df = dataframe_from_lines_with_prefix(file, 'Transfers,')
    if df.empty:
        # Transfers,Header,Asset Category,,Currency,Symbol,Date,Type,Direction,Xfer Company,Xfer Account,Qty,Xfer Price,Market Value,Realized P/L,Cash Amount,Code
        df = pd.DataFrame(columns=['Transfers', 'Header', 'Asset Category', 'Currency', 'Symbol', 'Date', 'Type', 'Direction', 'Xfer Company', 'Xfer Account', 'Qty', 'Xfer Price', 'Market Value', 'Realized P/L', 'Cash Amount', 'Code'])
    df = df[df['Asset Category'] == 'Stocks']
    df['Date/Time'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df['Action'] = 'Transfer'
    df['Quantity'] = pd.to_numeric(df['Qty'].astype(str).str.replace(',', ''), errors='coerce')
    # If Type is 'In' then Quantity is positive, if 'Out' then negative
    df['Quantity'] = df.apply(lambda row: row['Quantity'] if row['Direction'] == 'In' else -row['Quantity'], axis=1)
    df['Proceeds'] = pd.to_numeric(df['Market Value'].astype(str).str.replace(',', ''), errors='coerce')
    df['Comm/Fee'] = 0
    df['Basis'] = 0
    df['Realized P/L'] = 0
    df['MTM P/L'] = 0
    df['T. Price'] = 0
    df['C. Price'] = 0
    df.drop(columns=['Transfers', 'Header', 'Asset Category', 'Date', 'Type', 'Direction', 'Xfer Company', 'Xfer Account', 'Qty', 'Xfer Price', 'Market Value', 'Cash Amount', 'Code'], inplace=True)
    return normalize_trades(df)

def generate_transfers_from_actions(actions):
    spinoffs = actions[actions['Action'] == 'Spinoff']
    transfers = pd.DataFrame()
    for index, spinoff in spinoffs.iterrows():
        transfer = {
            'Date/Time': spinoff['Date/Time'],
            'Currency': spinoff['Currency'],
            'Symbol': spinoff['Symbol'],
            'Quantity': spinoff['Quantity'],
            'Proceeds': 0,
            'Comm/Fee': 0,
            'Basis': 0,
            'Realized P/L': 0,
            'MTM P/L': 0,
            'T. Price': 0,
            'C. Price': 0,
            'Action': 'Transfer'
        }
        transfers = pd.concat([transfers, pd.DataFrame([transfer])], ignore_index=True)
    return normalize_trades(transfers)

@st.cache_data()
def import_activity_statement(file):
    file.seek(0)
    # 2nd line: Statement,Data,Title,Activity Statement
    # 3rd line: Statement,Data,Period,"April 13, 2020 - April 12, 2021"
    while line := file.readline().decode('utf-8'):
        if line.startswith('Statement,Data,Title,Activity Statement'):
            break
    match_period = re.match('Statement,Data,Period,"(.+) - (.+)"', file.readline().decode('utf-8'))
    if not match_period:
        raise Exception('No period in IBKR Activity Statement')
    # Convert to from and to dates
    from_date = pd.to_datetime(match_period.group(1), format='%B %d, %Y')
    to_date = pd.to_datetime(match_period.group(2), format='%B %d, %Y')    
    trades = import_trades(file)
    actions = import_corporate_actions(file)
    open_positions = import_open_positions(file, from_date, to_date)
    transfers = import_transfers(file)
    transfers = pd.concat([transfers, generate_transfers_from_actions(actions)])
    trades = pd.concat([trades, transfers])
    return trades, actions, open_positions

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
