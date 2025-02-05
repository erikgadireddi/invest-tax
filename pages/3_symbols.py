import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 
import matchmaker.ux as ux
import matchmaker.position as position
from menu import menu

st.set_page_config(page_title='Doplnění obchodů', layout='wide')
menu()

data.load_settings()

state = data.State()
state.load_session()

if state.trades.empty:
    st.caption('Nebyly importovány žádné obchody.')
    st.page_link("pages/1_import_trades.py", label="📥 Přejít na import obchodů")

yearly_rates = currency.load_yearly_rates(st.session_state['settings']['currency_rates_dir'])

if state.trades is not None and not state.trades.empty:
    year = st.selectbox('Zobrazuji symboly', [0] + sorted(state.trades['Year'].unique()), index=0, key='year', format_func=lambda x: 'Všechny' if x == 0 else f's transakcemi od roku {x}')
    if year is None or year == 0:
        symbols = sorted(state.trades['Ticker'].unique())
    else:
        symbols = sorted(state.trades[state.trades['Year'] >= year]['Ticker'].unique())
    if len(symbols) == 0:
        st.caption('Pro zvolené období nebyly nalezeny žádné transakce.')
        st.stop()
        
    symbol = pills('Vyberte symbol pro inspekci', options=symbols)
    st.caption(f'Vysvětlivky k jednotlivým sloupcům jsou k dispozici na najetí myší.')
    shown_trades = state.trades[state.trades['Ticker'] == symbol].sort_values(by='Date/Time')
    if shown_trades.empty:
        st.caption(f'Pro symbol {symbol} nebyly nalezeny žádné obchody.')
    else:
        table_descriptor = ux.transaction_table_descriptor_native()
        trades_display = st.dataframe(shown_trades, hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
        profit = shown_trades['Realized P/L'].sum()
        held_position = shown_trades['Accumulated Quantity'].iloc[-1]
        if held_position != 0:
            st.markdown(f'**Držené pozice: :blue[{held_position:.0f}]**')
        st.caption(f'Realizovaný profit dle brokera: :green[{profit:.0f}] {shown_trades["Currency"].iloc[0]}')
            
        manual_trades = shown_trades[shown_trades['Manual'] == True]
        if not manual_trades.empty:
            st.caption('Manuálně přidané obchody, které můžete dále upravit:')
            def edit_manual_trades():
                st.session_state['changes_made'] = True
            column_order = ('Display Name', 'Date/Time', 'Quantity', 'Currency', 'T. Price', 'Comm/Fee', 'Realized P/L', 'Account')
            edited_trades = st.data_editor(manual_trades, hide_index=True, column_config=table_descriptor['column_config'], column_order=column_order, num_rows="fixed", disabled=("Display Name", "Currency"), on_change=edit_manual_trades)

            if st.session_state.get('changes_made', False):
                if st.button("Přepočítat změny"):
                    # Merge edited trades back into the main DataFrame
                    edited_trades['Orig. Quantity'] = edited_trades['Quantity']
                    edited_trades['Orig. T. Price'] = edited_trades['T. Price']
                    edited_trades['Split Ratio'] = 1.0
                    state.trades.update(edited_trades)
                    trades_to_drop = edited_trades[edited_trades['Quantity'] == 0].index
                    state.trades.drop(trades_to_drop, inplace=True)
                    state.recompute_positions()
                    state.save_session()
                    st.session_state['changes_made'] = False
                    st.rerun()

        suspicious_positions = shown_trades[((shown_trades['Accumulated Quantity'] < 0) & (shown_trades['Type'] == 'Long') & (shown_trades['Action'] == 'Close') | 
                                            (shown_trades['Accumulated Quantity'] > 0) & (shown_trades['Type'] == 'Short') & (shown_trades['Action'] == 'Close'))]
        if len(suspicious_positions) > 0:
            st.error('Historie obsahuje long transakce vedoucí k negativním pozicím. Je možné, že nebyly nahrány všechny obchody či korporátní akce. Zkontrolujte, prosím, zdrojová data a případně doplňte chybějící transakce.')
            table_descriptor = ux.transaction_table_descriptor_native()
            st.dataframe(suspicious_positions, hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
            ux.add_trades_editor(state, suspicious_positions.iloc[0])

        mismatches, _ = position.check_open_position_mismatches(shown_trades, state.positions)
        mismatches = mismatches[mismatches['Ticker'] == symbol]
        mismatches['Quantity'] = mismatches['Quantity'].fillna(0)
        if not mismatches.empty:
            st.caption('Toto jsou nalezené nesrovnalosti v otevřených pozicích, které mohou pomoci identifikovat data a množství chybějících obchodů.')
            table_descriptor = ux.transaction_table_descriptor_native()
            column_order = ('Date', 'Ticker', 'Account Accumulated Quantity', 'Quantity', 'Account', 'Date')
            table_descriptor['column_config']['Account Accumulated Quantity'] = st.column_config.NumberColumn("Počet dle transakcí", help="Spočítaná pozice ze všech nahraných transakcí", format="%f")
            table_descriptor['column_config']['Quantity'] = st.column_config.NumberColumn("Počet dle brokera", help="Pozice reportovaná brokerem v nahraném souboru", format="%f")
            table_descriptor['column_config']['Account'] = st.column_config.TextColumn("Účet u brokera", help="Název účtu, ke kterému se transakce vztahují. Každý účet má své vlastní pozice.")
            table_descriptor['column_config']['Date'] = st.column_config.DateColumn("Datum", help="Datum ke kterému broker spočítal pozice či byl proveden poslední obchod")
            column_config = table_descriptor['column_config']
            st.dataframe(mismatches, hide_index=True, column_order=column_order, column_config=column_config)
