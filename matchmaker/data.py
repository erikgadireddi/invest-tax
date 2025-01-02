# Used to hash entire rows since there is no unique identifier for each row
import hashlib
from io import StringIO
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