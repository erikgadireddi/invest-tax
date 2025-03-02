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
        column_order = ('Ticker', 'Accumulated Quantity', 'Current Price', 'Date/Time')
        column_config = table_descriptor['column_config']
        column_config['Date/Time'] = st.column_config.DateColumn("Poslední transakce", help="Datum poslední transakce s tímto instrumentem")
        trades_display = st.dataframe(open_positions, hide_index=True, column_order=column_order, column_config=column_config)
    # Display any mismatches in open positions if detected
    mismatches = position.check_open_position_mismatches(shown_trades, state.positions, state.symbols, max_date)
   
    renames = state.symbols[(state.symbols['Change Date'] <= max_date) & (state.symbols['Change Date'] >= min_date)]
    # Filter out renames that do not have a trade preceding its Change Date
    if not renames.empty:
        renames = renames[renames.apply(lambda row: any([shown_trades[(shown_trades['Symbol'] == row.name) & (pd.isna(row['Change Date']) | (shown_trades['Date/Time'] < row['Change Date']))].shape[0] > 0]), axis=1)]

    def show_rename_table(renames: pd.DataFrame, allow_edit: bool, caption: str = 'Nalezená přejmenování tickerů obchodovaných společností.'):
        renames['Year'] = renames['Change Date'].dt.year
        if not renames.empty:
            st.warning(caption)
            column_order = ('Symbol', 'Ticker', 'Year', 'Apply')
            column_config = {'Symbol': st.column_config.TextColumn("Původní", help="Původní symbol"), 
                            'Ticker': st.column_config.TextColumn("Nový", help="Nový symbol"),
                            'Year': st.column_config.NumberColumn("Rok", help="Rok, ve kterém byla provedena změna", format="%d"),
                            'Apply': st.column_config.CheckboxColumn("Použít", help="Použít nový symbol pro všechny transakce")}
                            
            if not allow_edit:
                st.dataframe(renames, hide_index=True, column_order=column_order, column_config=column_config)
            else:
                def on_change():
                    st.session_state['rename_changes_made'] = True
                return st.data_editor(renames, hide_index=True, column_order=column_order, column_config=column_config, disabled=('Symbol', 'Ticker', 'Year'), on_change=on_change)

    show_rename_table(renames, False)
    guessed_renames = position.detect_renames_in_mismatches(mismatches, state.symbols)
    if not guessed_renames.empty:
        guessed_renames['Apply'] = False
        guessed_renames = show_rename_table(guessed_renames, True, 'Odhadnutá přejmenování tickerů obchodovaných společností.')

    if st.session_state.get('rename_changes_made', False):
        if st.button("Aplikovat změny"):
            for index, row in guessed_renames.iterrows():
                if row['Apply']:
                    state.symbols.loc[row['Symbol'], 'Ticker'] = row['Ticker']
                    state.symbols.loc[row['Symbol'], 'Change Date'] = row['Change Date']
                    state.symbols.loc[row['Symbol'], 'Manual'] = True
            st.success("Aplikuji změny, prosím o strpení.")
            st.session_state['rename_changes_made'] = False
            state.recompute_positions()
            state.save_session()
            st.rerun()

    mismatches['Quantity'] = mismatches['Quantity'].fillna(0)
    mismatches['Account Accumulated Quantity'] = mismatches['Account Accumulated Quantity'].fillna(0)
    if not mismatches.empty:
        st.error('Nalezeny nesrovnalosti v otevřených pozicích. Bude třeba doplnit chybějící obchody.')
        table_descriptor = ux.transaction_table_descriptor_native()
        column_order = ('Date', 'Display Name', 'Account Accumulated Quantity', 'Quantity', 'Account', 'Date')
        table_descriptor['column_config']['Account Accumulated Quantity'] = st.column_config.NumberColumn("Počet dle transakcí", help="Spočítaná pozice ze všech nahraných transakcí", format="%f")
        table_descriptor['column_config']['Quantity'] = st.column_config.NumberColumn("Počet dle brokera", help="Pozice reportovaná brokerem v nahraném souboru", format="%f")
        table_descriptor['column_config']['Account'] = st.column_config.TextColumn("Účet u brokera", help="Název účtu, ke kterému se transakce vztahují. Každý účet má své vlastní pozice.")
        table_descriptor['column_config']['Date'] = st.column_config.DateColumn("Datum", help="Datum ke kterému broker spočítal pozice či byl proveden poslední obchod")
        column_config = table_descriptor['column_config']
        st.dataframe(mismatches, hide_index=True, column_order=column_order, column_config=column_config)