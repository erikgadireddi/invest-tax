import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 
import matchmaker.ux as ux
from menu import menu
import yfinance as yf

st.set_page_config(page_title='Přehled otevřených pozic', layout='wide')
menu()

data.load_settings()

trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
symbol = st.session_state.symbol if 'symbol' in st.session_state else None

if trades.empty:
    st.caption('Nebyly importovány žádné obchody.')
    st.page_link("pages/1_import_trades.py", label="📥 Přejít na import obchodů")

daily_rates = currency.load_daily_rates(st.session_state['settings']['currency_rates_dir'])

if trades is not None and not trades.empty:
    progress_text = st.caption('Probíhá načítání aktuálních cen instrumentů...')
    shown_trades = trades.sort_values(by='Date/Time')
    # Get a list of symbols that have a final accumulated quantity different from 0
    positions = shown_trades.groupby('Symbol')[['Accumulated Quantity', 'Date/Time']].last().reset_index()
    open_positions = positions[positions['Accumulated Quantity'] != 0]
    # Get current price of each instrument from Yahoo Finance
    # open_positions['Current Price'] = open_positions['Symbol'].apply(lambda symbol: yf.Ticker(symbol).info.get('regularMarketPrice'))
    progress_text.empty()
    if len(open_positions) == 0:
        st.markdown(f'Nebyly nalezeny žádné otevřené pozice - všechny obchody byly uzavřeny.')
    else:
        table_descriptor = ux.transaction_table_descriptor_native()
        column_order = ('Symbol', 'Accumulated Quantity', 'Current Price', 'Date/Time')
        column_config = table_descriptor['column_config']
        column_config['Date/Time'] = st.column_config.DatetimeColumn("Poslední transakce", help="Čas poslední transakce s tímto instrumentem")
        trades_display = st.dataframe(open_positions, hide_index=True, column_order=column_order, column_config=column_config)
