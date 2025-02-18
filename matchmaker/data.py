# Used to hash entire rows since there is no unique identifier for each row
from matchmaker import trade
from matchmaker import position
import json
import pandas as pd
import numpy as np
import streamlit as st
import hashlib

def load_settings():
    if st.session_state.get('settings') is None:
        with open('settings.json') as f:
            st.session_state['settings'] = json.load(f)


class State:
    """ Hold the state of the application concerning imported trades and their subsequent processing. """
    def __init__(self):
        self.reset()  

    def reset(self):
        """ History of all trades, including stock and option transfers, exercises, assignments, and all related operations. Index: hash of the entire row  """
        self.trades = pd.DataFrame()
        """ History of corporate actions, including stock splits, spin-offs, acquisitions, etc."""
        self.actions = pd.DataFrame()
        """ Open positions snapshots parsed from the imported data, usually from the end of the imported intervals """
        self.positions = pd.DataFrame()
        """ Symbols appearing in the trades and positions, their currency and optionally their renamed name. Used to group together multiple symbols that refer to the same asset. Index: raw symbol present in statements """
        self.symbols = pd.DataFrame()
        """ Trades that were paired together to form taxable pairs. """
        self.paired_trades = pd.DataFrame()
        """ Trades that were not fully paired together. """
        self.unpaired_trades = pd.DataFrame()
        """ Descriptor of the imported data noting the account names, imported date range and the number of trades. """
        self.imports = pd.DataFrame()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_state(self):
        """ Used for streamlit caching. """
        return (self.trades, self.actions, self.positions, self.symbols, self.imports, self.paired_trades, self.unpaired_trades)
    
    def load_session(self):
        self.trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
        self.actions = st.session_state.actions if 'actions' in st.session_state else pd.DataFrame()
        self.positions = st.session_state.positions if 'positions' in st.session_state else pd.DataFrame()
        self.symbols = st.session_state.symbols if 'symbols' in st.session_state else pd.DataFrame()
        self.paired_trades = st.session_state.paired_trades if 'paired_trades' in st.session_state else pd.DataFrame()
        self.unpaired_trades = st.session_state.unpaired_trades if 'unpaired_trades' in st.session_state else pd.DataFrame()
        self.imports = st.session_state.imports if 'imports' in st.session_state else pd.DataFrame()

    def save_session(self):
        st.session_state.update(trades=self.trades)
        st.session_state.update(actions=self.actions)
        st.session_state.update(positions=self.positions)
        st.session_state.update(symbols=self.symbols)
        st.session_state.update(paired_trades=self.paired_trades)
        st.session_state.update(unpaired_trades=self.unpaired_trades)
        st.session_state.update(imports=self.imports)

    def recompute_positions(self, added_trades = None):
        """ 
        Recompute past and present positions of the entire portfolio. 
        Includes modifying the trades by applying splits and symbol renames.
        """
        if added_trades is not None:
            new_symbols = pd.DataFrame(added_trades['Symbol'].unique(), columns=['Symbol'])
        else:
            all_symbols = pd.concat([self.trades['Symbol'], self.positions['Symbol']]).unique()
            new_symbols = pd.DataFrame(all_symbols, columns=['Symbol'])
            added_trades = self.trades

        # Populate the symbols table with symbols in these trades
        new_symbols.set_index('Symbol', inplace=True)
        new_symbols['Ticker'] = new_symbols.index
        new_symbols['Change Date'] = pd.NaT
        new_symbols['Currency'] = new_symbols.index.map(lambda symbol: self.trades[self.trades['Symbol'] == symbol]['Currency'].iloc[0] if not self.trades[self.trades['Symbol'] == symbol].empty else None)
        self.symbols = pd.concat([self.symbols, new_symbols]).drop_duplicates()
        # Auto-generated symbols need to yield priority to possibly manually added symbols
        self.symbols = self.symbols[~self.symbols.duplicated(keep='first')]

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

    def merge_trades(self, other: 'State') -> int:
        """ Merge another state into this one, returning the number of new trades. """
        self.imports = pd.concat([self.imports, other.imports]).drop_duplicates()
        if len(other.actions) > 0:
            self.actions = pd.concat([other.actions, self.actions])
        # Merge open positions and drop duplicates
        self.positions = pd.concat([other.positions, self.positions])
        self.positions.drop_duplicates(subset=['Symbol', 'Date'], inplace=True)
        self.positions.reset_index(drop=True, inplace=True)
        before = len(self.trades)
        self.trades = trade.merge_trades(other.trades, self.trades)
        imported_count = len(self.trades) - before
        if imported_count > 0:
            self.invalidate_pairs(other.trades['Date/Time'].min())
        return imported_count

    def add_manual_trades(self, new_trades):
        new_trades['Manual'] = True
        new_trades['Ticker'] = new_trades['Symbol']
        new_trades['Display Name'] = new_trades['Symbol']
        self.trades = pd.concat([self.trades, new_trades])
        self.trades.drop_duplicates(inplace=True) # Someone could put in two identical manual trades as there is a preset date. Let's remove them as they would cause trouble with duplicate indices.
        self.invalidate_pairs(new_trades['Date/Time'].min())
        self.recompute_positions()

    def invalidate_pairs(self, date_since: pd.Timestamp):
        """ Invalidate all pairs (partial invalidation won't help now). """
        self.paired_trades = pd.DataFrame()
        self.unpaired_trades = pd.DataFrame()

    def apply_renames(self):
        """ Apply symbol renames by looking them up in the symbols table . """
        def rename_symbols(df: pd.DataFrame, date_column: str) -> pd.DataFrame:
            
            # Symbols contain a history of renames of each symbol. We need to select the most recent rename that is older than the trade date.
            # Entries with no change date are considered to be the original symbol and applies if no other row matches.
            df['Ticker'] = df.apply(
                lambda row: self.symbols.loc[
                    (self.symbols.index == row['Symbol']) & 
                    ((self.symbols['Change Date'].isna()) | (self.symbols['Change Date'] >= row[date_column]))
                ].sort_values(by='Change Date', na_position='last').iloc[0]['Ticker'],
                axis=1
            )
            return df

        manual_trades = self.trades[self.trades['Manual'] == True]
        imported_trades = rename_symbols(self.trades[self.trades['Manual'] == False].reset_index().rename(columns={'index': 'Hash'}), 'Date/Time').set_index('Hash')
        self.trades = pd.concat([imported_trades, manual_trades])
        self.positions = rename_symbols(self.positions, 'Date')

    def detect_and_apply_renames(self):
        """ 
        Consult the rename history dataset and and apply it to symbols that do not have an override already set.
        Then perform the renames and recompute the position history.
        """
        # Load renames table and adjust to match the symbols table
        renames_table = st.session_state['settings']['rename_history_dir'] + '/renames.csv'
        renames = pd.read_csv(renames_table, parse_dates=['Change Date'])
        renames.rename(columns={'New': 'Ticker', 'Old': 'Symbol'}, inplace=True)
        renames.drop(columns=['New Company Name'], inplace=True)
        renames.set_index('Symbol', inplace=True)

        # Apply the renames to the symbols table
        kept_symbols = self.symbols[self.symbols['Change Date'].isna()]
        assert all(kept_symbols['Ticker'] == kept_symbols.index), "We should have just automatically generated symbols here."
        active_renames = renames[renames.index.isin(self.symbols.index)]
        active_renames['Currency'] = active_renames.index.map(lambda symbol: kept_symbols.loc[symbol]['Currency'])
        self.symbols = pd.concat([kept_symbols, active_renames]).drop_duplicates().sort_values(by=['Change Date', 'Symbol'], na_position='last')
        # TODO: The currency doesn't need to be the same in case it was another company that took over the symbol. We'll need to get it from the trades table later. 


        # Now we can adjust the trades for the renames
        if len(renames) > 0:
            self.apply_renames()
            self.trades = trade.compute_accumulated_positions(self.trades)

