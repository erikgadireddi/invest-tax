import pandas as pd
import numpy as np
import glob

# Load currency conversion rates from 'CurrencyRates.csv' as DataFrame
# Header is: Year,Currency,Value in CZK
# Example line: 2023,USD,20.5
def load_rates():
    df_rates = pd.read_csv('CurrencyRates.csv')
    df_rates['CZK Rate'] = pd.to_numeric(df_rates['CZK Rate'], errors='coerce')
    return df_rates

# Load Trades CSV as DataFrame
def load_trades(rates):
    # Merge with all Trades.[year].csv files in the same folder, skipping the first line (header) of each file
    df = None
    for f in glob.glob('../Trades.*.csv'):
        if df is None:
            df = pd.read_csv(f)
        else:
            df = pd.concat([df, pd.read_csv(f)], ignore_index = True)

    # First line is the headers: Trades,Header,DataDiscriminator,Asset Category,Currency,Symbol,Date/Time,Quantity,T. Price,C. Price,Proceeds,Comm/Fee,Basis,Realized P/L,MTM P/L,Code
    # Column	Descriptions
    # Trades	The trade number.
    # Header	Header record contains the report title and the date and time of the report.
    # DataDiscriminator	Indicates the type of data record. Possible values are: "Data", "DataTotals", "Header", "HeaderTotals", "Trades", "TradesTotals" and "Footer".
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

    # Convert Date/Time column to datetime type
    df['Date/Time'] = pd.to_datetime(df['Date/Time'], format='%Y-%m-%d, %H:%M:%S')
    # Extract year from Date/Time column and store it in new column 'Year'
    df['Year'] = df['Date/Time'].dt.year
    # Merge df with df_rates on Currency and Year columns, getting Value in CZK column from df_rates
    df = pd.merge(df, rates, on=['Currency', 'Year'])
    # Convert numeric columns to numeric type
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
    df['Proceeds'] = pd.to_numeric(df['Proceeds'], errors='coerce')
    df['Comm/Fee'] = pd.to_numeric(df['Comm/Fee'], errors='coerce')
    df['Basis'] = pd.to_numeric(df['Basis'], errors='coerce')
    df['Realized P/L'] = pd.to_numeric(df['Realized P/L'], errors='coerce')
    df['MTM P/L'] = pd.to_numeric(df['MTM P/L'], errors='coerce')
    df['T. Price'] = pd.to_numeric(df['T. Price'], errors='coerce')
    # Order by Date/Time
    df = df.sort_values(by=['Date/Time'])
    return df

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

def pair_buy_sell(trades):
    # Group all trades by Symbol into a new DataFrame
    # For each sell order (negative Proceeds), find enough corresponding buy orders (positive Proceeds) with the same Symbol to cover the sell order
    # Buy orders must be before the sell orders in time (Date/Time) and must have enough Quantity to cover the sell order
    # From the buy orders, compute the average price (T. Price) for the amount to cover the sell order and add it to the sell order as 'Covered Price'
    # If a sell order is not covered by any buy orders, it is ignored
    
    per_symbol = trades.groupby('Symbol')
    buys_all = pd.DataFrame()
    sells_all = pd.DataFrame()
    for symbol, group in per_symbol:
        group['Covered Price'] = 0
        group['Covered Quantity'] = 0
        group['FIFO P/L'] = 0
        group['LIFO P/L'] = 0
        # Find sell orders
        sells = group[group['Quantity'] < 0]
        for use_fifo in [True, False]:
            # Find buy orders. We'll use the quantity column to determine which buy orders were used to cover the sell orders
            buys = group[group['Quantity'] > 0]
            algo_name = 'FIFO P/L' if use_fifo else 'LIFO P/L'
            # For each sell order, find enough buy orders to cover it
            for index_s, sell in sells.iterrows():
                # Find enough buy orders to cover the sell order
                buys_to_cover = buys[(buys['Date/Time'] < sell['Date/Time']) & (buys['Quantity'] > 0)]
                # Sort according to FIFO/LIFO (ascending/descending)
                buys_to_cover = buys_to_cover.sort_values(by=['Date/Time'], ascending=use_fifo)
                covered_quantity = 0
                covered_cost = 0
                # If there are enough buy orders to cover the sell order
                for index_b, buy in buys_to_cover.iterrows():
                    # Reduce the quantity of the buy order by the quantity of the sell order
                    quantity = min(buy['Quantity'], -sell['Quantity'])
                    # Update the quantity of the buy order in the original DataFrame
                    buys.loc[index_b, 'Quantity'] -= quantity
                    sell['Quantity'] += quantity
                    # Add covered price to the sell order
                    covered_quantity += quantity
                    covered_cost += quantity * buy['T. Price']
                # Update the sell order with the covered price and quantity
                sells.loc[index_s, 'Covered Price'] = covered_cost
                sells.loc[index_s, 'Covered Quantity'] = covered_quantity
                covered_fraction = covered_quantity / -sells.loc[index_s, 'Quantity']
                sells.loc[index_s, algo_name] = ((sells.loc[index_s, 'Proceeds'] * covered_fraction) - sells.loc[index_s, 'Covered Price'])

        buys_all = pd.concat([buys_all, buys])
        sells_all = pd.concat([sells_all, sells])
    return buys_all, sells_all
    

# Load data
rates = load_rates()
trades = load_trades(rates)

# Pair buy and sell orders
buys, sells = pair_buy_sell(trades)
paired_sells = sells[sells['Quantity'] == -sells['Covered Quantity']]
unpaired_sells = sells[sells['Quantity'] != -sells['Covered Quantity']]

# Print unpaired sells
print('Unpaired sells:')
print(unpaired_sells)

# Get unique years from trades
years = trades['Year'].unique()

# Get statistics for last year
year = years.max()
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

