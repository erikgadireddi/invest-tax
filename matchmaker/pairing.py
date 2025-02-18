
import pandas as pd
import streamlit as st

class Pairings:
    """ Holds the current state of the pairing process. """
    strategies = ['FIFO', 'LIFO', 'AverageCost', 'MaxLoss', 'MaxProfit']

    def __init__(self):
        self.reset()

    def reset(self):
        """ Trades that were paired together to form taxable pairs. """
        self.paired = pd.DataFrame()
        """ Trades that were not fully paired together. """
        self.unpaired = pd.DataFrame()
        """ Configuration of the pairing process. """
        self.config = {}

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_state(self):
        """ Used for streamlit caching. """
        return (self.paired, self.unpaired, self.config)

    def load_session(self):
        self.paired = st.session_state.paired_trades if 'pairing_paired' in st.session_state else pd.DataFrame()
        self.unpaired = st.session_state.unpaired_trades if 'pairing_unpaired' in st.session_state else pd.DataFrame()
        self.config = st.session_state.config if 'pairing_config' in st.session_state else {}

    def save_session(self):
        st.session_state.update(pairing_paired=self.paired)
        st.session_state.update(pairing_unpaired=self.unpaired)
        st.session_state.update(pairing_config=self.config)

    def recompute_pairings(self, trades: pd.DataFrame):
        """ Recompute the pairings from the trades. """


def fill_trades_covered_quantity(trades, sell_buy_pairs):
    """ Fill in the covered and uncovered quantities for each trade based on already created pairs. """
    def is_short_trade(row):
        def is_quantity_opposite_of_action(row : pd.Series):
            return (row['Quantity'] > 0 and row['Action'] == 'Close') or (row['Quantity'] < 0 and row['Action'] == 'Open')
        # The trade is borrowing stock or writing options 
        if row['Type'] == 'Short':
            return True
        # It is an assigned option (had to be short) or is assigning stock that opens or fulfills a short position
        if row['Type'] == 'Assigned' and (not pd.isna(row['Option Type'] or is_quantity_opposite_of_action(row))):
            return True
        # It is stock resulting from exercised call option and it closes a position (there should be an open short position) 
        if row['Type'] == 'Exercised' and pd.isna(row['Option Type']) and is_quantity_opposite_of_action(row):
            return True
        # Expired options could be owned or borrowed, only one of those is short
        if row['Type'] == 'Expired' and row['Quantity'] > 0:
            return True
        return False
    trades['Covered Quantity'] = 0.0
    trades['Uncovered Quantity'] = trades.apply(lambda row: row['Quantity'] if not is_short_trade(row) else -row['Quantity'], axis=1)
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

@st.cache_data()
def pair_buy_sell(trades: pd.DataFrame, pairs: pd.DataFrame, strategy: str, from_year: int = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """ Pair buy and sell trades to create taxable pairs. Return unmatched sells for diagnostics. """
    # Group all trades by Symbol into a new DataFrame
    # For each sell order (negative Proceeds), find enough corresponding buy orders (positive Proceeds) with the same Symbol to cover the sell order
    # Buy orders must be before the sell orders in time (Date/Time) and must have enough Quantity to cover the sell order
    # From the buy orders, compute the average price (T. Price) for the amount to cover the sell order and add it to the sell order as 'Covered Price'
    # If a sell order is not covered by any buy orders, it is ignored
    
    # Drop all rows from pairs that are after the from_year
    if from_year is not None and pairs is not None and not pairs.empty:
        pairs = pairs[pairs['Sell Time'].dt.year < from_year]
    
    trades = fill_trades_covered_quantity(trades, pairs)
    # trades.round(3).to_csv('paired.order.quantities.csv')
    per_symbol = trades.groupby('Display Name')
    if pairs is None:
        pairs = pd.DataFrame(columns=['Buy Transaction', 'Sell Transaction', 'Display Name', 'Quantity', 'Buy Time', 'Buy Price', 'Sell Time', 'Sell Price', 'Buy Cost', 'Sell Proceeds', 'Revenue', 'Ratio', 'Type', 'Taxable'])
    for symbol, group in per_symbol:
        # Find sell orders
        sells = group[group['Action'] == 'Close']
        # Find buy orders. We'll use the quantity column to determine which buy orders were used to cover the sell orders
        buys = group[group['Action'] == 'Open']
        # For each sell order, find enough buy orders to cover it
        for index_s, sell in sells.iterrows():
            # If already paired, skip
            if sell['Uncovered Quantity'] == 0 or sell['Year'] < from_year:
                continue
            
            if strategy == 'LIFO':
                # LIFO should prefer oldest not taxable transactions, then youngest taxable transactions
                commands = [('FIFO', 'IgnoreTaxable'), ('LIFO', 'All')]
            elif strategy == 'AverageCost':
                # Pair like IBKR would compute P/L from average price of all buy orders
                commands = [('AverageCost', 'All')]
            elif strategy == 'MaxLoss':
                commands = [('MaxProfit', 'IgnoreTaxable'), ('MaxLoss', 'All')]
            elif strategy == 'MaxProfit':
                commands = [('MaxLose', 'IgnoreTaxable'), ('MaxProfit', 'All')]
            elif strategy == 'FIFO':
                # FIFO is easy, just sort by Date/Time
                commands = [('FIFO', 'All')]
            else:
                st.error(f'Unknown strategy: {strategy}')
                return trades, pairs

            # We sell using IBKR average price, meaning we need to always pair the same fraction of each buy order
            for match_strategy, filter in commands:
                # Find enough buy orders to cover the sell order
                buys_to_cover = buys[(buys['Date/Time'] <= sell['Date/Time']) & (buys['Uncovered Quantity'] > 0)]
                if match_strategy == 'MaxLoss' or match_strategy == 'MaxProfit':
                    buys_to_cover = buys_to_cover.sort_values(by=['T. Price'], ascending=match_strategy == 'MaxProfit')
                else:
                    buys_to_cover = buys_to_cover.sort_values(by=['Date/Time'], ascending=match_strategy == 'FIFO')
                    
                if match_strategy == 'AverageCost':
                    total_uncovered = buys_to_cover['Uncovered Quantity'].sum()
                    sell_fraction = -sell['Uncovered Quantity'] / total_uncovered            

                # If there are enough buy orders to cover the sell order
                for index_b, buy in buys_to_cover[buys_to_cover['Quantity'].apply(lambda x: x * sell['Quantity'] < 0)].iterrows():
                    if sell['Uncovered Quantity'] == 0:
                        break
                    
                    taxable = (sell['Date/Time'] - buy['Date/Time']).days < 3*365
                    if (filter == 'IgnoreTaxable' and taxable) or (filter == 'TaxableLoss' and not taxable):
                        continue
                    
                    # Determine the maximum quantity available to cover the sell order
                    if match_strategy == 'AverageCost':
                        quantity = buy['Uncovered Quantity'] * sell_fraction # Proportional to the total uncovered quantity
                    else:
                        assert (buy['Uncovered Quantity'] * sell['Uncovered Quantity']) < 0, f"Buy and sell quantities must have opposite signs. Buy: {buy['Uncovered Quantity']}, Sell: {sell['Uncovered Quantity']} for {symbol} at {sell['Date/Time']}"
                        quantity = min(buy['Uncovered Quantity'], -sell['Uncovered Quantity'])
                    
                    if quantity != 0:
                        # Treat short positions as reversed long positions
                        open = buy if buy['Quantity'] > 0 else sell
                        close = sell if buy['Quantity'] > 0 else buy
                        # Add covered price to the sell order, it might not be all
                        made_profit = (close['T. Price'] - open['T. Price']) > 0
                        if made_profit and filter == 'TaxableLoss':
                            continue
                        sell['Uncovered Quantity'] += quantity
                        # Add the pair to the DataFrame, indexing by hashes of the buy and sell transactions
                        data = {'Sell Transaction': index_s, 'Buy Transaction': index_b, 'Display Name': symbol, 'Currency': buy['Currency'],
                                'Quantity': quantity, 'Buy Time': buy['Date/Time'], 'Sell Time': sell['Date/Time'],
                                'Buy Price': open['T. Price'], 
                                'Sell Price': close['T. Price'], 
                                'Buy Cost': open['T. Price'] - (open['Comm/Fee'] / open['Quantity']), 
                                'Sell Proceeds': close['T. Price'] - (close['Comm/Fee'] / close['Quantity']), 
                                'Cost': (open['Proceeds'] + open['Comm/Fee']) * quantity / open['Quantity'], 
                                'Proceeds': -(close['Proceeds'] + close['Comm/Fee']) * quantity / close['Quantity'],
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
    
    if pairs.empty:
        return trades[trades['Action'] == 'Open'], trades[trades['Action'] == 'Close'], pd.DataFrame()
    
    pairs['Revenue'] = pairs['Proceeds'] + pairs['Cost']
    return trades[trades['Uncovered Quantity'] != 0], pairs.sort_values(by=['Display Name','Sell Time', 'Buy Time'])
