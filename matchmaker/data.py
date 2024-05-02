# Used to hash entire rows since there is no unique identifier for each row
import hashlib
from io import StringIO
import json
import pandas as pd
import streamlit as st
from matchmaker.trades import convert_trade_columns
from matchmaker.actions import convert_action_columns

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

def is_snapshot(file):
    header = file.readline()
    header = header.decode('utf-8')
    file.seek(0)
    return header == 'Matchmaker snapshot\n'

@st.cache_data()
def save_snapshot(trades, actions):
    serialized =  'Matchmaker snapshot\n'
    serialized += 'Section: Trades\n'
    serialized += trades.to_csv()
    serialized += 'Section: Actions\n'
    serialized += actions.to_csv(index=False)
    return serialized

@st.cache_data()
def load_snapshot(file):
    header = file.readline().decode('utf-8')
    if header != 'Matchmaker snapshot\n':
        raise Exception('Not a Matchmaker snapshot')
    trades_header = file.readline().decode('utf-8')
    if trades_header != 'Section: Trades\n':
        raise Exception('No Trades section in snapshot')
    trades_csv = ''
    while True:
        line = file.readline().decode('utf-8')
        if line == 'Section: Actions\n':
            break
        trades_csv += line
    actions_csv = ''
    while True:
        line = file.readline().decode('utf-8')
        if not line:
            break
        actions_csv += line    

    trades = pd.read_csv(StringIO(trades_csv))
    trades.set_index('Hash', inplace=True)
    trades = convert_trade_columns(trades)
    actions = convert_action_columns(pd.read_csv(StringIO(actions_csv)))
    return trades, actions
