import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 
import matchmaker.ux as ux
import matchmaker.trade as trade
import matchmaker.styling as styling
from menu import menu

st.set_page_config(page_title='Doplnění obchodů', layout='wide')
menu()

data.load_settings()

state = data.State()
state.load_session()

if state.trades.empty:
    st.caption('Nebyly importovány žádné obchody.')
    st.page_link("pages/1_import_trades.py", label="📥 Přejít na import obchodů")
else:
    st.caption(str(len(state.trades)) + ' transakcí k dispozici.')


if state.trades is not None and not state.trades.empty:    
    daily_rates = currency.load_daily_rates(st.session_state['settings']['currency_rates_dir'])
    yearly_rates = currency.load_yearly_rates(st.session_state['settings']['currency_rates_dir'])
    trades = currency.add_czk_conversion_to_trades(state.trades, daily_rates, use_yearly_rates=False)
    year=ux.add_years_filter(trades)
    st.session_state.update(year=year)
    st.caption(f'Vysvětlivky k jednotlivým sloupcům jsou k dispozici na najetí myší.')
    shown_trades = trades[trades['Year'] == year] if year is not None else trades
    table_descriptor = ux.transaction_table_descriptor_czk()
    trades_display = st.dataframe(styling.format_trades(shown_trades), hide_index=True, column_order=table_descriptor['column_order'], column_config=table_descriptor['column_config'])
    profit_czk = trades[trades['Year'] == year]['CZK Profit'].sum() if year is not None else trades['CZK Profit'].sum()
    if year is not None:
        st.caption(f'Profit tento rok dle brokera: :green[{profit_czk:,.0f}] CZK') 
    else: 
        st.caption(f'Profit dle brokera: :green[{profit_czk:,.0f}] CZK')
        
    missing_history = trade.per_account_transfers_with_missing_transactions(shown_trades)
    if len(missing_history) > 0:
        with st.container(border=False):
            st.error('Historie obsahuje převody pozic mezi účty, kterým chybí nákupní transakce. Pro efektivní párování je třeba doplnit chybějící obchody, aby nákupní cena a datum mohly být použity pro daňové optimalizace.')
            table_descriptor = ux.transaction_table_descriptor_czk()
            st.dataframe(styling.format_trades(missing_history), hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
            ux.add_trades_editor(state, missing_history.iloc[0], 'missing_transfers')   
    else:
        suspicious_positions = trade.positions_with_missing_transactions(shown_trades)
        if len(suspicious_positions) > 0:
            with st.container(border=False):
                st.error('Historie obsahuje transakce, kterým nesedí výsledné pozice. Je možné, že nebyly nahrány všechny obchody či korporátní akce. Zkontrolujte, prosím, zdrojová data a případně doplňte chybějící transakce.')
                symbols = sorted(suspicious_positions['Symbol'].unique())
                symbol = pills('Vyberte symbol pro doplnění', options=symbols)
                shown_mismatches = suspicious_positions[suspicious_positions['Symbol'] == symbol]
                table_descriptor = ux.transaction_table_descriptor_czk()
                st.dataframe(styling.format_missing_trades(shown_mismatches), hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
                max_negative = -shown_mismatches['Accumulated Quantity'].min()
                max_positive = shown_mismatches['Accumulated Quantity'].max()
                suggested_row = shown_mismatches.iloc[0].copy()
                if max_positive > 0:
                    st.caption(f'Pro symbol {symbol} chybí short prodeje **:green[{max_positive}]** pozic')
                    suggested_row['Accumulated Quantity'] = -max_positive
                if max_negative > 0:
                    st.caption(f'Pro symbol {symbol} chybí nákupy **:red[{max_negative}]** pozic')
                    suggested_row['Accumulated Quantity'] = max_negative
                ux.add_trades_editor(state, suggested_row, 'suspicious_positions')
        else:
            st.caption('Nebyly nalezeny žádné nesrovnalosti v otevřených pozicích. Skvělá práce 🎉, nyní můžeme vše započítat do daňového přehledu!')

    missing_incoming_history, missing_outgoing_history = trade.transfers_with_missing_transactions(shown_trades)
    if (len(missing_incoming_history) > 0):
        with st.container(border=False):
            st.error('Historie obsahuje příjem instrumentů z cizích účtů, ke kterým je třeba doplnit chybějící nákupy, aby nákupní cena a datum mohly být použity pro daňové optimalizace.')
            table_descriptor = ux.transaction_table_descriptor_czk()
            table_descriptor['column_config']['Target'] = st.column_config.TextColumn("Účet", help="Název účtu, odkud byly převedeny instrumenty.")
            table_descriptor['column_order'] = ('Target',) + table_descriptor['column_order']
            st.dataframe(missing_incoming_history, hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
            missing_incoming_history = missing_incoming_history.reset_index()
            matching_trade = trades[(trades['Display Name'] == missing_incoming_history.iloc[0]['Display Name']) & 
                                     (trades['Target'] == missing_incoming_history.iloc[0]['Target'])]
            ux.add_trades_editor(state, matching_trade.iloc[0], 'incoming_history', None, missing_incoming_history['Display Name'], missing_incoming_history['Target'])