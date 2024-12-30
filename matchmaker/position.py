
import pandas as pd

def convert_position_history_columns(df):
    df['Prior Date'] = pd.to_datetime(df['Prior Date'])
    df['Current Date'] = pd.to_datetime(df['Current Date'])
    df['Prior Quantity'] = pd.to_numeric(df['Prior Quantity'], errors='coerce')
    df['Current Quantity'] = pd.to_numeric(df['Current Quantity'], errors='coerce')
    df['Prior Price'] = pd.to_numeric(df['Prior Price'], errors='coerce')
    df['Current Price'] = pd.to_numeric(df['Current Price'], errors='coerce')
    df['Mark-to-Market P/L Position'] = pd.to_numeric(df['Mark-to-Market P/L Position'], errors='coerce')
    df['Mark-to-Market P/L Transaction'] = pd.to_numeric(df['Mark-to-Market P/L Transaction'], errors='coerce')
    df['Mark-to-Market P/L Commissions'] = pd.to_numeric(df['Mark-to-Market P/L Commissions'], errors='coerce')
    df['Mark-to-Market P/L Other'] = pd.to_numeric(df['Mark-to-Market P/L Other'], errors='coerce')
    df['Mark-to-Market P/L Total'] = pd.to_numeric(df['Mark-to-Market P/L Total'], errors='coerce')
    return df

# Compute open positions per symbol at a given time
def compute_open_positions(trades, time=pd.Timestamp.now()):
    trades = trades[trades['Date/Time'] <= time]
    positions = trades.groupby('Symbol')[['Accumulated Quantity', 'Date/Time']].last().reset_index()
    return positions[positions['Accumulated Quantity'] != 0]

