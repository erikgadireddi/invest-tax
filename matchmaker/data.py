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

    def recompute_positions(self):
        if len(self.trades) > 0:
            self.trades = trade.adjust_for_splits(self.trades, self.actions)
            # Create a map of symbols that could be renamed (but we don't know for now)
            all_symbols = pd.concat([self.trades['Symbol'], self.positions['Symbol']]).unique()
            self.symbols = pd.DataFrame(all_symbols, columns=['Symbol'])
            self.symbols['Ticker'] = self.symbols['Symbol']
            self.trades = trade.compute_accumulated_positions(self.trades, self.symbols)
            self.positions.drop(columns=['Ticker'], errors='ignore', inplace=True)
            self.positions = self.positions.merge(self.symbols[['Symbol', 'Ticker']], on='Symbol', how='left')
            self.positions['Date/Time'] = pd.to_datetime(self.positions['Date']) + pd.Timedelta(seconds=86399) # Add 23:59:59 to the date
            self.positions = trade.add_split_data(self.positions, self.actions)
            mismatches, renames = position.check_open_position_mismatches(self.trades, self.positions)
            for index, row in renames.iterrows():
                self.symbols.loc[self.symbols['Symbol'] == row['From'], ['Ticker', 'Date']] = [row['To'], row['Date']] # Use this in 5_positions instead of guesses
            # Now we can adjust the trades for the renames
            if len(renames) > 0:
                self.trades = trade.compute_accumulated_positions(self.trades, self.symbols)
                self.positions.drop(columns=['Ticker'], inplace=True)
                self.positions = self.positions.merge(self.symbols[['Symbol', 'Ticker']], on='Symbol', how='left')
            self.trades['Display Name'] = self.trades['Ticker'] + self.trades['Display Suffix'].fillna('')