import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 
import matchmaker.ux as ux
import matchmaker.position as position
from menu import menu
import yfinance as yf

st.set_page_config(page_title='Přehled otevřených pozic', layout='wide')
menu()

data.load_settings()

state = data.State()
state.load_session()

positions = st.session_state.positions if 'positions' in st.session_state else pd.DataFrame()

if state.trades.empty:
    st.caption('Nebyly importovány žádné obchody.')
    st.page_link("pages/1_import_trades.py", label="📥 Přejít na import obchodů")
    st.stop()

st.session_state.update(year=ux.add_years_filter(state.trades))

daily_rates = currency.load_daily_rates(st.session_state['settings']['currency_rates_dir'])

if state.trades is not None and not state.trades.empty:
    progress_text = st.caption('Probíhá načítání aktuálních cen instrumentů...')
    shown_trades = state.trades.sort_values(by='Date/Time')
    # Get a list of symbols that have a final accumulated quantity different from 0
    selected_year = st.session_state.get('year')
    if selected_year is None:
        selected_year = shown_trades['Date/Time'].dt.year.max()
        min_date = pd.Timestamp.min
    else:
        min_date = pd.Timestamp(f'{selected_year}-01-01 00:00:00') 
    
    max_date = pd.Timestamp(f'{selected_year}-12-31 23:59:59')
    open_positions = position.compute_open_positions(shown_trades, max_date)

    # Get current price of each instrument from Yahoo Finance
    # open_positions['Current Price'] = open_positions['Symbol'].apply(lambda symbol: yf.Ticker(symbol).info.get('regularMarketPrice'))
    progress_text.empty()
    if len(open_positions) == 0:
        st.markdown(f'Nebyly nalezeny žádné otevřené pozice - všechny obchody byly uzavřeny.')
    else:
        table_descriptor = ux.transaction_table_descriptor_native()
        column_order = ('Symbol', 'Accumulated Quantity', 'Current Price', 'Date/Time')
        column_config = table_descriptor['column_config']
        column_config['Date/Time'] = st.column_config.DateColumn("Poslední transakce", help="Datum poslední transakce s tímto instrumentem")
        trades_display = st.dataframe(open_positions, hide_index=True, column_order=column_order, column_config=column_config)

    # Display any mismatches in open positions if detected
    mismatches, _ = position.check_open_position_mismatches(shown_trades, positions, max_date)
    renames = state.symbols[(state.symbols['Date'] <= max_date) & (state.symbols['Date'] >= min_date)]
    if not renames.empty:
        st.warning('Nalezeny možné přejmenování instrumentů. Pokud se nejedná o správné párování, chybí obchody na jednom z těchto symbolů a je třeba je doplnit.')
        column_order = ('Symbol', 'Ticker', 'Year')
        column_config = {'Symbol': st.column_config.TextColumn("Původní", help="Původní symbol"), 
                         'Ticker': st.column_config.TextColumn("Nový", help="Nový symbol"),
                         'Year': st.column_config.NumberColumn("Rok", help="Rok, ve kterém byla provedena změna", format="%d")}
        st.dataframe(renames, hide_index=True, column_order=column_order, column_config=column_config)

    mismatches['Quantity'] = mismatches['Quantity'].fillna(0)
    mismatches['Accumulated Quantity'] = mismatches['Accumulated Quantity'].fillna(0)
    if not mismatches.empty:
        st.error('Nalezeny nesrovnalosti v otevřených pozicích. Bude třeba doplnit chybějící obchody.')
        table_descriptor = ux.transaction_table_descriptor_native()
        column_order = ('Symbol', 'Accumulated Quantity', 'Quantity', 'Date')
        table_descriptor['column_config']['Accumulated Quantity'] = st.column_config.NumberColumn("Počet dle transakcí", help="Spočítaná pozice ze všech nahraných transakcí", format="%f")
        table_descriptor['column_config']['Quantity'] = st.column_config.NumberColumn("Počet dle brokera", help="Pozice reportovaná brokerem v nahraném souboru", format="%f")
        table_descriptor['column_config']['Date'] = st.column_config.DateColumn("Poslední změna", help="Datum ke kterému broker spočítal pozice či byl proveden poslední obchod")
        column_config = table_descriptor['column_config']
        st.dataframe(mismatches, hide_index=True, column_order=column_order, column_config=column_config)