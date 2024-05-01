import glob
import re
from .data import hash_row
from .trades import convert_trade_columns
from io import StringIO
import pandas as pd
import streamlit as st

@st.cache_data()
def import_activity_statement(file):
    # column_names = ['Trades', 'Header', 'DataDiscriminator', 'Asset Category', 'Currency', 'Symbol', 'Date/Time', 'Quantity', 'T. Price', 'C. Price', 'Proceeds', 'Comm/Fee', 'Basis', 'Realized P/L', 'MTM P/L', 'Code', 'Extra']
    # Decode file as utf-8
    file = [line.decode('utf-8') for line in file]
    # Filter file lines to those beginning with 'Trades'
    file_lines = [line for line in file if line.startswith('Trades')]
    file_data = StringIO('\n'.join(file_lines))
    df = pd.read_csv(file_data)
    # Keep only lines with column values "Trades","Data","Order","Stocks"
    df = df[(df['Trades'] == 'Trades') & (df['Header'] == 'Data') & (df['DataDiscriminator'] == 'Order') & (df['Asset Category'] == 'Stocks')]
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

    # Filter DataFrame by Asset Category == 'Stocks' and DataDiscriminator == 'Data' (rest is partial sums and totals)
    df = df[(df['Asset Category'] == 'Stocks') & (df['DataDiscriminator'] == 'Order')]

    # Convert columns to correct types
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='%Y-%m-%d, %H:%M:%S')
    df['Year'] = df['Date/Time'].dt.year
    df['Quantity'] = pd.to_numeric(df['Quantity'].astype(str).str.replace(',', ''), errors='coerce')
    # Convert the rest
    df = convert_trade_columns(df)
    # Set up the hash column as index
    df['Hash'] = df.apply(hash_row, axis=1)
    df.set_index('Hash', inplace=True)
    # st.write('Imported', len(df), 'rows')
    return df

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
