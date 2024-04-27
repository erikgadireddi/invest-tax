import pandas as pd
import numpy as np
import glob
import argparse
import re
import hashlib
import os

# Used to hash entire rows since there is no unique identifier for each row
def hash_row(row):
    row_str = row.to_string()
    hash_object = hashlib.sha256()
    hash_object.update(row_str.encode())
    hash_hex = hash_object.hexdigest()
    return hash_hex

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

def load_yearly_rates(directory):
    df = pd.read_csv(directory + '/CurrencyRatesYearly.csv')
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    df.set_index('Year', inplace=True)
    df = adjust_rates_columns(df)
    return df

# Load daily CNB rates
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

def add_accumulated_positions(trades):
    for symbol, group in trades.groupby('Symbol'):
        accumulated = 0
        for index, row in group.sort_values(by=['Date/Time']).iterrows():
            accumulated += row['Quantity']
            trades.loc[index, 'Accumulated Quantity'] = accumulated

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

def add_split_data(trades, tickers_dir):
    trades['Split Ratio'] = 1
    if tickers_dir is not None:
        for symbol, group in trades.groupby('Symbol'):
            filename = tickers_dir + '/' + symbol + '_data.csv'
            if os.path.exists(filename):
                try:
                    ticker = pd.read_csv(tickers_dir + '/' + symbol + '_data.csv')
                    ticker['Date'] = pd.to_datetime(ticker['Date'], format='%Y-%m-%d').dt.date
                    ticker.set_index('Date', inplace=True)
                    for index, row in group.iterrows():
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

# Load Trades CSV as DataFrame
def import_trades(directory, existing_trades=None, tickers_dir=None):
    # Go over all 'Activity' exports that contain all data and extract only the 'Trades' part
    data = None
    for f in glob.glob(directory + '/U*_*_*.csv'):
        # Only if matching U12345678_[optional_]20230101_20231231.csv
        if(re.match(r'.+U(\d+)_(\d{8})_(\d{8})', f)):
            # Read the file
            with open(f, 'r') as file:
                # Specify the column names
                column_names = ['Trades', 'Header', 'DataDiscriminator', 'Asset Category', 'Currency', 'Symbol', 'Date/Time', 'Quantity', 'T. Price', 'C. Price', 'Proceeds', 'Comm/Fee', 'Basis', 'Realized P/L', 'MTM P/L', 'Code', 'Extra']
                if data is None:
                    data = pd.read_csv(file, names=column_names)
                else:
                    data = pd.concat([data, pd.read_csv(file, names=column_names)], ignore_index = True)
                # Keep only lines with column values "Trades","Data","Order","Stocks"
                data = data[(data['Trades'] == 'Trades') & (data['Header'] == 'Data') & (data['DataDiscriminator'] == 'Order') & (data['Asset Category'] == 'Stocks')]
        else:
            print('Skipping file:', f)
    df = data
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

    # Filter DataFrame by Asset Category == 'Stocks' and DataDiscriminator == 'Data' (rest is partial sums and totals)
    df = df[(df['Asset Category'] == 'Stocks') & (df['DataDiscriminator'] == 'Order')]

    # Convert columns to correct types
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='%Y-%m-%d, %H:%M:%S')
    df['Year'] = df['Date/Time'].dt.year
    df['Quantity'] = pd.to_numeric(df['Quantity'].str.replace(',', ''), errors='coerce')
    # Convert the rest
    df = convert_trade_columns(df)
    # Set up the hash column as index
    df['Hash'] = df.apply(hash_row, axis=1)
    df.set_index('Hash', inplace=True)
    add_accumulated_positions(df)

    df = pd.concat([existing_trades, df])
    # Order by Date/Time
    df = df.sort_values(by=['Date/Time'])
    # Count the rows before removing duplicates
    count = len(df)
    df = df[~df.index.duplicated(keep='first')]
    if (count != len(df)):
        print('Duplicates found and removed:', count - len(df))

    add_split_data(df, tickers_dir)
    df['Quantity'] = df['Quantity'] * df['Split Ratio']
    df['T. Price'] = df['T. Price'] / df['Split Ratio']
    
    return df

def get_adjusted_price(ticker, date):
    pass

def get_statistics_czk(trades, sells, year):
    # Filter DataFrame by year
    df = trades[trades['Year'] == year]
    sells = sells[sells['Year'] == year]
    
    # Calculate total purchases and sales for given year in CZK through multiplying with 'CZK Rate' column
    purchases = (df[df['Proceeds'] < 0]['Proceeds'] * df[df['Proceeds'] < 0]['CZK Rate']).sum()
    sales = (df[df['Proceeds'] > 0]['Proceeds'] * df[df['Proceeds'] > 0]['CZK Rate']).sum()
    profit_loss_average = (df['Realized P/L'] * df['CZK Rate']).sum()
    profit_loss_fifo = (sells['FIFO P/L'] * sells['CZK Rate']).sum()
    profit_loss_lifo = (sells['LIFO P/L'] * sells['CZK Rate']).sum()
    commissions = (df['Comm/Fee'] * df['CZK Rate']).sum()
    return purchases, sales, commissions, profit_loss_average, profit_loss_fifo, profit_loss_lifo

def get_statistics_per_currency(trades, sells, year):
    # Filter DataFrame by year
    df = trades[trades['Year'] == year]
    sells = sells[sells['Year'] == year]
    
    purchases = df[df['Proceeds'] < 0].groupby('Currency')['Proceeds'].sum()
    sales = df[df['Proceeds'] > 0].groupby('Currency')['Proceeds'].sum()
    profit_loss_average = df.groupby('Currency')['Realized P/L'].sum()
    profit_loss_fifo = sells.groupby('Currency')['FIFO P/L'].sum()
    profit_loss_lifo = sells.groupby('Currency')['LIFO P/L'].sum()
    commissions = df.groupby('Currency')['Comm/Fee'].sum()

    return purchases, sales, commissions, profit_loss_average, profit_loss_fifo, profit_loss_lifo

def load_buy_sell_pairs(filename):
    pairs = pd.read_csv(filename)
    # Convert columns to correct types
    pairs['Buy Time'] = pd.to_datetime(pairs['Buy Time'])
    pairs['Sell Time'] = pd.to_datetime(pairs['Sell Time'])
    pairs['Quantity'] = pd.to_numeric(pairs['Quantity'], errors='coerce')
    pairs['Buy Price'] = pd.to_numeric(pairs['Buy Price'], errors='coerce')
    pairs['Sell Price'] = pd.to_numeric(pairs['Sell Price'], errors='coerce')
    pairs['Buy Cost'] = pd.to_numeric(pairs['Buy Cost'], errors='coerce')
    pairs['Sell Proceeds'] = pd.to_numeric(pairs['Sell Proceeds'], errors='coerce')
    pairs['Ratio'] = pd.to_numeric(pairs['Ratio'], errors='coerce')
    pairs['Taxable'] = pd.to_numeric(pairs['Taxable'], errors='coerce')
    return pairs
    
def fill_trades_covered_quantity(trades, sell_buy_pairs):
    trades['Covered Quantity'] = 0.0
    trades['Uncovered Quantity'] = trades.apply(lambda row: row['Quantity'] if row['Type'] == 'Long' else -row['Quantity'], axis=1)
    if sell_buy_pairs is not None:
        for index, row in sell_buy_pairs.iterrows():
            sell_index = row['Sell Transaction']
            buy_index = row['Buy Transaction']
            quantity = row['Quantity']
            trades.loc[buy_index, 'Covered Quantity'] += quantity
            trades.loc[buy_index, 'Uncovered Quantity'] -= quantity
            trades.loc[sell_index, 'Covered Quantity'] += quantity
            trades.loc[sell_index, 'Uncovered Quantity'] += quantity
    return trades
    
def pair_buy_sell(trades, pairs, strategy):
    # Group all trades by Symbol into a new DataFrame
    # For each sell order (negative Proceeds), find enough corresponding buy orders (positive Proceeds) with the same Symbol to cover the sell order
    # Buy orders must be before the sell orders in time (Date/Time) and must have enough Quantity to cover the sell order
    # From the buy orders, compute the average price (T. Price) for the amount to cover the sell order and add it to the sell order as 'Covered Price'
    # If a sell order is not covered by any buy orders, it is ignored
    trades = fill_trades_covered_quantity(trades, pairs)
    # trades.round(3).to_csv('paired.order.quantities.csv')
    per_symbol = trades.groupby('Symbol')
    if pairs is None:
        pairs = pd.DataFrame(columns=['Buy Transaction', 'Sell Transaction', 'Symbol', 'Quantity', 'Buy Time', 'Buy Price', 'Sell Time', 'Sell Price', 'Buy Cost', 'Sell Proceeds', 'Ratio', 'Type', 'Taxable'])
    for symbol, group in per_symbol:
        # Find sell orders
        sells = group[group['Action'] == 'Close']
        # Find buy orders. We'll use the quantity column to determine which buy orders were used to cover the sell orders
        buys = group[group['Action'] == 'Open']
        # For each sell order, find enough buy orders to cover it
        for index_s, sell in sells.iterrows():
            # If already paired, skip
            if sell['Uncovered Quantity'] == 0:
                continue
            
            # if sell_buy_pairs[sell_buy_pairs['Sell Transaction'] == index_s]['Quantity'].sum() == -sell['Quantity'] if sell['Type'] == 'Long' else sell['Quantity']:
            #    continue
            
            if strategy == 'LIFO':
                # LIFO should prefer oldest not taxable transactions, then youngest taxable transactions
                commands = [('FIFO', 'IgnoreTaxable'), ('LIFO', 'All')]
            elif strategy == 'MaxLoss':
                commands = [('LIFO', 'TaxableLoss'), ('FIFO', 'IgnoreTaxable'), ('LIFO', 'All')]
            else:
                # FIFO is easy, just sort by Date/Time
                commands = [('FIFO', 'All')]

            # Find enough buy orders to cover the sell order
            buys_to_cover = buys[(buys['Date/Time'] <= sell['Date/Time']) & (buys['Uncovered Quantity'] > 0)]
            for strategy, match in commands:
                buys_to_cover = buys_to_cover.sort_values(by=['Date/Time'], ascending=strategy == 'FIFO')

                # If there are enough buy orders to cover the sell order
                for index_b, buy in buys_to_cover[buys_to_cover['Type'] == sell['Type']].iterrows():
                    taxable = (sell['Date/Time'] - buy['Date/Time']).days < 3*365
                    if (match == 'IgnoreTaxable' and taxable) or (match == 'TaxableLoss' and not taxable):
                        continue
                    # Reduce the quantity of the buy order by the quantity of the sell order
                    quantity = min(buy['Uncovered Quantity'], -sell['Uncovered Quantity'])
                    if quantity != 0:
                        # Treat short positions as reversed long positions
                        open = buy if buy['Type'] == 'Long' else sell
                        close = sell if buy['Type'] == 'Long' else buy
                        # Add covered price to the sell order, it might not be all
                        made_profit = (close['T. Price'] - open['T. Price']) > 0
                        if made_profit and match == 'TaxableLoss':
                            continue
                        sell['Uncovered Quantity'] += quantity
                        # Add the pair to the DataFrame, indexing by hashes of the buy and sell transactions
                        data = {'Sell Transaction': index_s, 'Buy Transaction': index_b, 'Symbol': symbol, 'Currency': buy['Currency'],
                                'Quantity': quantity, 'Buy Time': buy['Date/Time'], 'Sell Time': sell['Date/Time'],
                                'Buy Price': open['T. Price'], 
                                'Sell Price': close['T. Price'], 
                                'Buy Cost': open['T. Price'] - (open['Comm/Fee'] / open['Quantity']), 
                                'Sell Proceeds': close['T. Price'] - (close['Comm/Fee'] / close['Quantity']), 
                                'Ratio': close['T. Price']/open['T. Price'] if open['T. Price'] != 0 else 0, 'Type': close['Type'],
                                'Taxable': 1 if (sell['Date/Time'] - buy['Date/Time']).days < 3*365 else 0}
                        pairs = pd.concat([pairs, pd.DataFrame([data])], ignore_index=True)

                        # Update the original dataframes
                        buys.loc[index_b, 'Uncovered Quantity'] -= quantity
                        buys.loc[index_b, 'Covered Quantity'] += quantity
                        sells.loc[index_s, 'Covered Quantity'] += quantity
                        sells.loc[index_s, 'Uncovered Quantity'] += quantity

        # Propagate the changes back to the original DataFrame
        trades.loc[sells.index, 'Uncovered Quantity'] = sells['Uncovered Quantity']
        trades.loc[buys.index, 'Uncovered Quantity'] = buys['Uncovered Quantity']
        trades.loc[sells.index, 'Covered Quantity'] = sells['Covered Quantity']
        trades.loc[buys.index, 'Covered Quantity'] = buys['Covered Quantity']
    return trades[trades['Action'] == 'Open'], trades[trades['Action'] == 'Close'], pairs

def print_statistics(trades, sells, year):
    # Get statistics for last year
    purchases, sales, commissions, profit_loss_avg, profit_loss_fifo, profit_loss_lifo = get_statistics_czk(trades, sells, year)

    # Print results so far. Format them as CZK currency with 2 decimal places and thousands separator
    print('Statistics for year ', year)
    print('Total purchases in CZK:', '{:,.2f}'.format(purchases))
    print('Total sales in CZK:', '{:,.2f}'.format(sales))
    print('Total IBKR profit/loss in CZK:', '{:,.2f}'.format(profit_loss_avg))
    print('Total FIFO profit/loss in CZK:', '{:,.2f}'.format(profit_loss_fifo))
    print('Total LIFO profit/loss in CZK:', '{:,.2f}'.format(profit_loss_lifo))
    print('Total commissions in CZK:', '{:,.2f}'.format(commissions))

    # Print paired sells
    print('Sells this year:')
    # Print all rows
    pd.set_option('display.max_rows', None)
    print(sells[sells['Year'] == year])

    # Also calculate in raw currencies
    purchases_raw, sales_raw, commissions_raw, profit_loss_avg_raw, profit_loss_fifo_raw, profit_loss_lifo_raw = get_statistics_per_currency(trades, sells, year)

    # Print results so far
    print('Total purchases per currency:', purchases_raw)
    print('Total sales per currency:', sales_raw)
    print('Total profit/loss per currency:', profit_loss_avg_raw)
    print('Total FIFO profit/loss per currency:', profit_loss_fifo_raw)
    print('Total LIFO profit/loss per currency:', profit_loss_lifo_raw)
    print('Total commissions per currency:', commissions_raw)

def add_czk_conversion(trade_pairs, rates, use_yearly_rates=True):
    annotated_pairs = trade_pairs.copy()
    if use_yearly_rates:
        annotated_pairs['Buy CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[row['Buy Time'].year, row['Currency']] if row['Buy Time'].year in rates.index else np.nan, axis=1)
        annotated_pairs['Sell CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[row['Sell Time'].year, row['Currency']] if row['Sell Time'].year in rates.index else np.nan, axis=1)
    else:
        annotated_pairs['Buy CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[pd.to_datetime(row['Buy Time'].date()), row['Currency']] if pd.to_datetime(row['Buy Time'].date()) in rates.index else np.nan, axis=1)
        annotated_pairs['Sell CZK Rate'] = annotated_pairs.apply(lambda row: rates.loc[pd.to_datetime(row['Sell Time'].date()), row['Currency']] if pd.to_datetime(row['Sell Time'].date()) in rates.index else np.nan, axis=1)
    annotated_pairs['CZK Cost'] = annotated_pairs['Buy Cost'] * annotated_pairs['Quantity'] * annotated_pairs['Buy CZK Rate']
    annotated_pairs['CZK Proceeds'] = annotated_pairs['Sell Proceeds'] * annotated_pairs['Quantity'] * annotated_pairs['Sell CZK Rate']
    annotated_pairs['CZK Revenue'] = annotated_pairs['CZK Proceeds'] - annotated_pairs['CZK Cost']
    return annotated_pairs
    

def main():
    # Process command-line arguments
    parser = argparse.ArgumentParser(description='Process command-line arguments')

    # Add the arguments
    parser.add_argument('--settings-dir', type=str, required=True, help='Path to CurrencyRates.csv file')
    parser.add_argument('--import-trades-dir', type=str, help='Path to Trades CSV files')
    parser.add_argument('--tickers-dir', type=str, help='Path to load historic ticker data to adjust prices for splits')
    parser.add_argument('--load-trades', type=str, help='Path to load processed trades file')
    parser.add_argument('--save-trades', type=str, help='Path to save processed trades file after import')
#    parser.add_argument('--compute', action='store_true', help='Compute statistics')
    parser.add_argument('--save-trade-overview-dir', type=str, help='Directory to output overviews of matched trades')
    parser.add_argument('--load-matched-trades', type=str, help='Paired trades input to load')
    parser.add_argument('--save-matched-trades', type=str, help='Save updated paired trades')
    
    # Parse the arguments
    args = parser.parse_args()

    if args.import_trades_dir is None and args.load_trades is None:
        print('No input directory or processed trades file specified. Exiting.')
        return

    # Load data
    daily_rates = load_daily_rates(args.settings_dir)
    yearly_rates = load_yearly_rates(args.settings_dir)
    trades = None
    sell_buy_pairs = None

    if args.load_trades is not None:
        trades = pd.read_csv(args.load_trades)
        trades = convert_trade_columns(trades)
        trades.set_index('Hash', inplace=True)
    if args.import_trades_dir is not None:
        trades = import_trades(args.import_trades_dir, trades, args.tickers_dir)
    if args.load_matched_trades is not None:
        sell_buy_pairs = load_buy_sell_pairs(args.load_matched_trades)

    # Pair buy and sell orders
    buys, sells, sell_buy_pairs = pair_buy_sell(trades, sell_buy_pairs, 'MaxLoss')
    paired_sells = sells[sells['Uncovered Quantity'] == 0]
    unpaired_sells = sells[sells['Uncovered Quantity'] != 0]
    paired_buys = buys[buys['Uncovered Quantity'] == 0]
    unpaired_buys = buys[buys['Uncovered Quantity'] != 0]

    # Save unpaired sells to CSV
    sort_columns = ['Symbol', 'Date/Time']
    if args.save_trades:
        trades.drop(['Covered Quantity', 'Uncovered Quantity'], axis=1, inplace=False).sort_values(by=sort_columns).to_csv(args.save_trades, index=True)
    if args.save_trade_overview_dir:
        sells.sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/sells.csv', index=False)
        paired_sells.sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/sells.paired.csv', index=False)
        unpaired_sells.sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/sells.unpaired.csv', index=False)
        buys.sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/buys.csv', index=False)
        paired_buys.sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/buys.paired.csv', index=False)
        unpaired_buys.sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/buys.unpaired.csv', index=False)
    if args.save_matched_trades:
        sell_buy_pairs.round(3).to_csv(args.save_matched_trades, index=False)
        yearly_pairs = add_czk_conversion(sell_buy_pairs, yearly_rates, True)
        daily_pairs = add_czk_conversion(sell_buy_pairs, daily_rates, False)
        for year in sorted(trades['Year'].unique()):
            for pairs in [yearly_pairs, daily_pairs]:
                filtered_pairs = pairs[(pairs['Sell Time'].dt.year == year)]  
                taxed_pairs = filtered_pairs[filtered_pairs['Taxable'] == 1]
                pairing_type = 'yearly' if pairs is yearly_pairs else 'daily'
                print(f'Pairing for year {year} using {pairing_type} rates in CZK: Proceeds {taxed_pairs["CZK Proceeds"].sum().round(0)}, '
                    f'Cost {taxed_pairs["CZK Cost"].sum().round(0)}, Revenue {taxed_pairs["CZK Revenue"].sum().round(0)}, '
                    f'Untaxed pairs: {len(filtered_pairs) - len(taxed_pairs)}')
                filtered_pairs[filtered_pairs['Sell Time'].dt.year == year].round(3).to_csv(args.save_matched_trades + ".{0}.{1}.csv".format(year, pairing_type), index=False)
            unpaired_sells[unpaired_sells['Year'] == year].round(3).to_csv(args.save_matched_trades + ".{0}.unpaired.csv".format(year), index=False)

    # if args.compute:
    #     # Get unique years from trades
    #     years = trades['Year'].unique()
    #     # Get statistics for last year
    #     year = years.max()
    #     print_statistics(trades, sells, year)


if __name__ == "__main__":
    main()
