
import pandas as pd

def convert_position_history_columns(df):
    df['Prior Date'] = pd.to_datetime(df['Prior Date'])
    df['Date'] = pd.to_datetime(df['Current Date'])
    df['Prior Quantity'] = pd.to_numeric(df['Prior Quantity'], errors='coerce')
    df['Quantity'] = pd.to_numeric(df['Current Quantity'], errors='coerce')
    df['Prior Price'] = pd.to_numeric(df['Prior Price'], errors='coerce')
    df['Price'] = pd.to_numeric(df['Current Price'], errors='coerce')
    df['Mark-to-Market P/L Position'] = pd.to_numeric(df['Mark-to-Market P/L Position'], errors='coerce')
    df['Mark-to-Market P/L Transaction'] = pd.to_numeric(df['Mark-to-Market P/L Transaction'], errors='coerce')
    df['Mark-to-Market P/L Commissions'] = pd.to_numeric(df['Mark-to-Market P/L Commissions'], errors='coerce')
    df['Mark-to-Market P/L Other'] = pd.to_numeric(df['Mark-to-Market P/L Other'], errors='coerce')
    df['Mark-to-Market P/L Total'] = pd.to_numeric(df['Mark-to-Market P/L Total'], errors='coerce')
    return df

# Compute open positions per symbol at a given time
def compute_open_positions(trades, time=pd.Timestamp.now()):
    trades = trades[trades['Date/Time'] <= time]
    positions = trades.groupby('Symbol')[['Accumulated Quantity', 'Date/Time', 'Split Ratio']].last().reset_index()
    return positions[positions['Accumulated Quantity'] != 0]

def check_open_position_mismatches(trades, positions, max_date=pd.Timestamp.now()):
    # Walk through every snapshot of open positions and check if it matches what we can compute from our trades
    time_points = positions[(positions['Quantity'] != 0) & (positions['Date'] <= max_date)].groupby('Date')
    mismatches = pd.DataFrame()
    for time, snapshot in time_points:
        open_positions = compute_open_positions(trades, time)
        # Join and check for quantity mismatches or missing symbols
        merged = snapshot.merge(open_positions, on='Symbol', suffixes=('_snapshot', '_computed'), how='outer')
        merged['Quantity Mismatch'] = merged['Accumulated Quantity'].fillna(0) - merged['Quantity'].fillna(0) * merged['Split Ratio'].fillna(1)
        merged['Snapshot Date'] = time
        mismatches = pd.concat([mismatches, merged[merged['Quantity Mismatch'] != 0]])

    # Fill in the Date column from Date/Time in case it was NaT
    mismatches.drop_duplicates(subset=['Symbol', 'Date'], inplace=True)
    mismatches.reset_index(drop=True, inplace=True)
    mismatches['Date'] = mismatches['Date'].fillna(mismatches['Date/Time'])
    # Group by possibly renamed symbols and check if we have pairs of mismatches
    guesses = pd.DataFrame(columns=['From', 'To', 'Action'])
    grouped_mismatches = mismatches.sort_values(by='Snapshot Date').groupby([mismatches['Quantity Mismatch'].abs(), mismatches['Snapshot Date']])
    for name, group in grouped_mismatches:
        if len(group) == 2:
            to_symbol = group.iloc[0]['Symbol']
            from_symbol = group.iloc[1]['Symbol']
            action = 'Rename'
            row = pd.DataFrame([{'From': from_symbol, 'To': to_symbol, 'Action': action}])
            guesses = pd.concat([guesses, row])

    if not guesses.empty:
        # Return only mismatches with no entry in guesses (From and To)
        mismatches = mismatches[~mismatches['Symbol'].isin(guesses['From'])]
        mismatches = mismatches[~mismatches['Symbol'].isin(guesses['To'])]
    return mismatches, guesses