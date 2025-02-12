# Used to hash entire rows since there is no unique identifier for each row
from matchmaker import trade
from matchmaker import position
import json
import pandas as pd
import numpy as np
import streamlit as st

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
        self.symbols = pd.DataFrame()
        self.paired_trades = pd.DataFrame()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def load_session(self):
        self.trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
        self.actions = st.session_state.actions if 'actions' in st.session_state else pd.DataFrame()
        self.positions = st.session_state.positions if 'positions' in st.session_state else pd.DataFrame()
        self.symbols = st.session_state.symbols if 'symbols' in st.session_state else pd.DataFrame()
        self.paired_trades = st.session_state.paired_trades if 'paired_trades' in st.session_state else pd.DataFrame()

    def save_session(self):
        st.session_state.update(trades=self.trades)
        st.session_state.update(actions=self.actions)
        st.session_state.update(positions=self.positions)
        st.session_state.update(symbols=self.symbols)
        st.session_state.update(paired_trades=self.paired_trades)

    def recompute_positions(self, added_trades = None):
        if added_trades is not None:
            new_symbols = pd.DataFrame(added_trades['Symbol'].unique(), columns=['Symbol'])
        else:
            all_symbols = pd.concat([self.trades['Symbol'], self.positions['Symbol']]).unique()
            new_symbols = pd.DataFrame(all_symbols, columns=['Symbol'])
            added_trades = self.trades

        new_symbols.set_index('Symbol', inplace=True)
        new_symbols['Ticker'] = new_symbols.index
        new_symbols['Change Date'] = pd.NaT
        new_symbols['Currency'] = new_symbols.index.map(lambda symbol: self.trades[self.trades['Symbol'] == symbol]['Currency'].iloc[0] if not self.trades[self.trades['Symbol'] == symbol].empty else None)
        self.symbols = pd.concat([self.symbols, new_symbols]).drop_duplicates()

        if len(added_trades) > 0:
            trade.adjust_for_splits(added_trades, self.actions)
            # Create a map of symbols that could be renamed (but we don't know for now)
            self.detect_and_apply_renames()
            self.trades = trade.compute_accumulated_positions(self.trades)
            self.positions['Date/Time'] = pd.to_datetime(self.positions['Date']) + pd.Timedelta(seconds=86399) # Add 23:59:59 to the date
            self.positions = trade.add_split_data(self.positions, self.actions)
            self.positions['Display Name'] = self.positions['Ticker']
            self.positions.drop(columns=['Ticker'], inplace=True)
            
            self.trades['Display Name'] = self.trades['Ticker'] + self.trades['Display Suffix'].fillna('')

    def add_manual_trades(self, new_trades):
        new_trades['Manual'] = True
        self.trades = pd.concat([self.trades, new_trades])
        self.recompute_positions()

    # Apply ticker renames by consulting the symbol rename table        
    def apply_renames(self):
        def rename_symbols(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
            df.drop(columns=['Ticker'], errors='ignore', inplace=True)
            df = df.merge(self.symbols[['Ticker', 'Change Date']], left_on='Symbol', right_index=True, how='left')
            df['Ticker'] = np.where(
                df['Change Date'].isna() | (df['Change Date'] > df[date_column]),
                df['Ticker'], 
                df['Symbol'])
            df.drop(columns=['Change Date'], inplace=True)
            return df

        self.trades = rename_symbols(self.trades.reset_index().rename(columns={'index': 'Hash'}), 'Date/Time').set_index('Hash')
        self.positions = rename_symbols(self.positions, 'Date')

    def detect_and_apply_renames(self):
        # Load renames table
        renames_table = st.session_state['settings']['rename_history_dir'] + '/renames.csv'
        renames = pd.read_csv(renames_table, parse_dates=['Change Date'])
        renames.set_index('Old', inplace=True)
        # Apply the renames to the symbols table
        self.symbols.drop(columns=['Change Date'], errors='ignore', inplace=True)
        self.symbols = self.symbols.merge(renames[['New', 'Change Date']], left_index=True, right_index=True, how='left')
        self.symbols['Ticker'] = self.symbols['New'].combine_first(self.symbols['Ticker'])
        self.symbols.drop(columns=['New'], inplace=True)

        # Now we can adjust the trades for the renames
        if len(renames) > 0:
            self.apply_renames()
            self.trades = trade.compute_accumulated_positions(self.trades)

        # Drop symbols that have no trades and are not mentioned in positions
        # self.symbols = self.symbols[self.symbols['Ticker'].isin(self.trades['Ticker']) | self.symbols['Ticker'].isin(self.positions['Ticker'])
        #                            | self.symbols['Ticker'].isin(self.trades['Ticker']) | self.symbols.index.isin(self.positions['Ticker'])]
