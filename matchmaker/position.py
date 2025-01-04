
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
    positions = trades.groupby('Ticker')[['Accumulated Quantity', 'Date/Time', 'Split Ratio']].last().reset_index()
    return positions[positions['Accumulated Quantity'] != 0]

# Compute open positions per symbol at a given time
def compute_open_positions_per_account(trades, time=pd.Timestamp.now(), account=None):
    trades = trades[trades['Date/Time'] <= time]
    if account is not None:
        trades = trades[trades['Account'] == account]
    positions = trades.groupby('Ticker')[['Account', 'Account Accumulated Quantity', 'Date/Time', 'Split Ratio']].last().reset_index()
    return positions[positions['Account Accumulated Quantity'] != 0]


def check_open_position_mismatches(trades, positions, max_date=pd.Timestamp.now()):
    # Walk through every snapshot of open positions and check if it matches what we can compute from our trades
    time_points = positions[(positions['Quantity'] != 0) & (positions['Date'] <= max_date)].groupby(['Date', 'Account'])
    mismatches = pd.DataFrame(columns=['Ticker', 'Date'])
    for (time, account), snapshot in time_points:
        # Join and check for quantity mismatches or missing symbols
        open_positions = compute_open_positions_per_account(trades, time, account)
        merged = snapshot.merge(open_positions, on=['Ticker', 'Account'], suffixes=('_snapshot', '_computed'), how='outer')
        merged['Quantity Mismatch'] = merged['Account Accumulated Quantity'].fillna(0) - merged['Quantity'].fillna(0) * merged['Split Ratio'].fillna(1)
        merged['Snapshot Date'] = time
        mismatches = pd.concat([mismatches, merged[merged['Quantity Mismatch'] != 0]])

    # Fill in the Date column from Date/Time in case it was NaT
    if len(mismatches) == 0:
        return mismatches, pd.DataFrame()
    
    mismatches.drop_duplicates(subset=['Ticker', 'Date'], inplace=True)
    mismatches.reset_index(drop=True, inplace=True)
    mismatches['Date'] = mismatches['Date'].fillna(mismatches['Date/Time'])
    guesses = pd.DataFrame(columns=['From', 'To', 'Action'])
    # Compute the date range for each symbol activity so we make filter out overlapping symbols from the guesses
    agg_funcs = {
        'Date/Time': ['min', 'max']
    }
    symbol_dates = trades.groupby('Ticker').agg(agg_funcs).reset_index()
    symbol_dates.columns = ['Ticker', 'First Activity', 'Last Activity']
    # Group by possibly renamed symbols and check if we have pairs of mismatches
    mismatches = mismatches.merge(symbol_dates, on='Ticker', how='left')
    guesses = pd.DataFrame(columns=['From', 'To', 'Action', 'Date'])
    grouped_mismatches = mismatches.sort_values(by='Last Activity').groupby([mismatches['Quantity Mismatch'].abs(), mismatches['Snapshot Date']])
    for name, group in grouped_mismatches:
        if len(group) == 2:
            # Don't consider the symbol to be renamed if both symbols have overlapping activity in the trade history
            from_row = group.iloc[0]
            to_row = group.iloc[1]
            if (not pd.isna(to_row['First Activity']) and not pd.isna(from_row['First Activity']) and from_row['Last Activity'] > to_row['First Activity']):
                continue
            action = 'Rename'
            row = pd.DataFrame([{'From': from_row['Ticker'], 'To': to_row['Ticker'], 'Action': action, 'Date': from_row['Snapshot Date'], 'Year': int(from_row['Snapshot Date'].year)}])
            guesses = pd.concat([guesses, row])

    if not guesses.empty:
        # Return only mismatches with no entry in guesses (From and To)
        mismatches = mismatches[~mismatches['Ticker'].isin(guesses['From'])]
        mismatches = mismatches[~mismatches['Ticker'].isin(guesses['To'])]
    return mismatches, guesses