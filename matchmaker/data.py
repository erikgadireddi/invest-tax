# Used to hash entire rows since there is no unique identifier for each row
import hashlib
from matchmaker import trade
from matchmaker import position
import json
import pandas as pd
import streamlit as st


def hash_row(row):
    row_str = row.to_string()
    hash_object = hashlib.sha256()
    hash_object.update(row_str.encode())
    hash_hex = hash_object.hexdigest()
    return hash_hex

def load_settings():
    if st.session_state.get('settings') is None:
        with open('settings.json') as f:
            st.session_state['settings'] = json.load(f)

class State:
    def __init__(self):
        self.reset()  

    def reset(self):
        self.trades = pd.DataFrame()
        self.actions = pd.DataFrame()
        self.positions = pd.DataFrame()
        self.symbols = pd.DataFrame

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def load_session(self):
        self.trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
        self.actions = st.session_state.actions if 'actions' in st.session_state else pd.DataFrame()
        self.positions = st.session_state.positions if 'positions' in st.session_state else pd.DataFrame()
        self.symbols = st.session_state.symbols if 'symbols' in st.session_state else pd.DataFrame()

    def save_session(self):
        st.session_state.update(trades=self.trades)
        st.session_state.update(actions=self.actions)
        st.session_state.update(positions=self.positions)
        st.session_state.update(symbols=self.symbols)

    def recompute_positions(self, added_trades = None):
        if added_trades is not None:
            updated_tickers = added_trades['Ticker'].unique()
            new_symbols = pd.DataFrame(added_trades['Symbol'].unique(), columns=['Symbol'])
            new_symbols.set_index('Symbol', inplace=True)
            new_symbols['Ticker'] = new_symbols.index
            self.symbols = pd.concat([self.symbols, new_symbols]).drop_duplicates()
        else:
            all_symbols = pd.concat([self.trades['Symbol'], self.positions['Symbol']]).unique()
            self.symbols = pd.DataFrame(all_symbols, columns=['Symbol'])
            self.symbols.set_index('Symbol', inplace=True)
            self.symbols['Ticker'] = self.symbols.index
            added_trades = self.trades

        if len(added_trades) > 0:
            added_trades = trade.adjust_for_splits(added_trades, self.actions)
            # Create a map of symbols that could be renamed (but we don't know for now)
            self._apply_renames()
            self.trades = trade.compute_accumulated_positions(self.trades, self.symbols)
            self.positions['Date/Time'] = pd.to_datetime(self.positions['Date']) + pd.Timedelta(seconds=86399) # Add 23:59:59 to the date
            self.positions = trade.add_split_data(self.positions, self.actions)
            
            self.detect_and_apply_renames()
            self.trades['Display Name'] = self.trades['Ticker'] + self.trades['Display Suffix'].fillna('')

    def add_manual_trades(self, new_trades):
        self.trades = pd.concat([self.trades, new_trades])
        self.recompute_positions()

    # Apply ticker renames by consulting the symbol rename table        
    def _apply_renames(self):
        # Rename the symbols in trades 
        self.trades.drop(columns=['Ticker'], errors='ignore', inplace=True)
        self.trades = self.trades.reset_index().rename(columns={'index': 'Hash'})
        self.trades = self.trades.merge(self.symbols[['Ticker']], left_on='Symbol', right_index=True, how='left').set_index('Hash')
        # Rename the symbols in positions
        self.positions.drop(columns=['Ticker'], errors='ignore', inplace=True)
        self.positions = self.positions.merge(self.symbols[['Ticker']], left_on='Symbol', right_index=True, how='left')

    def detect_and_apply_renames(self):
        mismatches, renames = position.check_open_position_mismatches(self.trades, self.positions)
        for index, row in renames.iterrows():
            self.symbols.loc[self.symbols.index == row['From'], ['Ticker', 'Date']] = [row['To'], row['Date']] 
        # Now we can adjust the trades for the renames
        if len(renames) > 0:
            self._apply_renames()
            self.trades = trade.compute_accumulated_positions(self.trades, self.symbols)
