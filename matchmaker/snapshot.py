from io import StringIO
import pandas as pd
import streamlit as st
import matchmaker.trade as trade
import matchmaker.actions as action
import matchmaker.position as position

def is_snapshot(file):
    header = file.readline()
    header = header.decode('utf-8')
    file.seek(0)
    return header == 'Matchmaker snapshot\n'

@st.cache_data()
def save_snapshot(trades, actions, positions):
    serialized =  'Matchmaker snapshot\n'
    serialized += 'Section: Trades\n'
    serialized += trades.to_csv()
    serialized += 'Section: Actions\n'
    serialized += actions.to_csv(index=False)
    serialized += 'Section: Position History\n'
    serialized += positions.to_csv(index=False)
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
        if line == 'Section: Position History\n':
            break
        actions_csv += line    
    while True:
        line = file.readline().decode('utf-8')
        if not line:
            break
        positions_csv += line
        
    trades = pd.read_csv(StringIO(trades_csv))
    trades.set_index('Hash', inplace=True)
    trades = trade.convert_trade_columns(trades)
    actions = action.convert_action_columns(pd.read_csv(StringIO(actions_csv)))
    positions = position.convert_position_history_columns(pd.read_csv(StringIO(positions_csv)))
    return trades, actions, positions
