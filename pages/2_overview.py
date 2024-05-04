import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 
import matchmaker.ux as ux
from menu import menu

st.set_page_config(page_title='Prehled', layout='wide')
menu()

data.load_settings()

trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
year = st.session_state.year if 'year' in st.session_state else None

if trades.empty:
    st.write('No trades loaded. Import some first.')
else:
    st.caption(str(len(trades)) + ' trades available.')

daily_rates = currency.load_daily_rates(st.session_state['settings']['currency_rates_dir'])
yearly_rates = currency.load_yearly_rates(st.session_state['settings']['currency_rates_dir'])

if trades is not None and not trades.empty:    
    currency.add_czk_conversion_to_trades(trades, daily_rates, use_yearly_rates=False)
    years = sorted(trades['Year'].unique())
    year_str = pills('Select year to view', ['All'] + [str(year) for year in years])
    year = int(year_str) if year_str != 'All' else None
    st.session_state.update(year=year)
    st.caption(f'Vysvětlivky k jednotlivým sloupcům jsou k dispozici na najetí myší.')
    shown_trades = trades[trades['Year'] == year] if year is not None else trades
    table_descriptor = ux.transaction_table_descriptor()
    trades_display = st.dataframe(shown_trades, hide_index=True, column_order=table_descriptor['column_order'], column_config=table_descriptor['column_config'])
    profit_czk = trades[trades['Year'] == year]['CZK Profit'].sum() if year is not None else trades['CZK Profit'].sum()
    if year is not None:
        st.caption(f'Profit tento rok dle brokera: :green[{profit_czk:.0f}] CZK') 
    else: 
        st.caption(f'Profit dle brokera: :green[{profit_czk:.0f}] CZK')
        
    suspicious_positions = shown_trades[((shown_trades['Accumulated Quantity'] < 0) & (shown_trades['Type'] == 'Long') & (shown_trades['Action'] == 'Close') | 
                                         (shown_trades['Accumulated Quantity'] > 0) & (shown_trades['Type'] == 'Short') & (shown_trades['Action'] == 'Close'))]
    if len(suspicious_positions) > 0:
        st.caption('Historie obsahuje long transakce vedoucí k negativním pozicím. Je možné, že nebyly nahrány všechny obchody či korporátní akce. Zkontrolujte, prosím, zdrojová data a případně doplňte chybějící transakce.')
        table_descriptor = ux.transaction_table_descriptor()
        st.dataframe(suspicious_positions, hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
        ux.add_trades_editor(trades, suspicious_positions.iloc[0])
