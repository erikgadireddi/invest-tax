import pandas as pd
import numpy as np
import glob

# Load currency conversion rates from 'CurrencyRates.csv' as DataFrame
# Header is: Year,Currency,Value in CZK
# Example line: 2023,USD,20.5
def load_rates():
    df_rates = pd.read_csv('CurrencyRates.csv')
    df_rates['Value in CZK'] = pd.to_numeric(df_rates['Value in CZK'], errors='coerce')
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
    return df

def get_statistics(trades, year):
    # Filter DataFrame by year
    df = trades[trades['Year'] == year]
    
    # Calculate total purchases and sales for given year in CZK through multiplying with 'Value in CZK' column
    purchases = (df[df['Proceeds'] < 0]['Proceeds'] * df[df['Proceeds'] < 0]['Value in CZK']).sum()
    sales = (df[df['Proceeds'] > 0]['Proceeds'] * df[df['Proceeds'] > 0]['Value in CZK']).sum()
    
    # Calculate total commissions filtered for given year
    commissions = (df['Comm/Fee'] * df['Value in CZK']).sum()
    return purchases, sales, commissions

# Load data
rates = load_rates()
trades = load_trades(rates)

# Get unique years from trades
years = trades['Year'].unique()

# Get statistics for last year
year = years.max()
total_purchases, total_sales, total_commissions = get_statistics(trades, year)

# Print results so far. Format them as CZK currency with 2 decimal places and thousands separator
print('Statistics for year ', year)
print('Total purchases in CZK:', '{:,.2f}'.format(total_purchases))
print('Total sales in CZK:', '{:,.2f}'.format(total_sales))
print('Total commissions in CZK:', '{:,.2f}'.format(total_commissions))

# Also calculate in raw currencies
# Calculate total purchases and sales for year 2023 separately for each currency
currency_total_purchases = df[df['Proceeds'] < 0].groupby('Currency')['Proceeds'].sum()
currency_total_sales = df[df['Proceeds'] > 0].groupby('Currency')['Proceeds'].sum()
# Calculate total commissions as well
currency_total_commissions = df.groupby('Currency')['Comm/Fee'].sum()

# Print results so far
print('Total purchases per currency:', currency_total_purchases)
print('Total sales per currency:', currency_total_sales)
print('Total commissions per currency:', currency_total_commissions)


