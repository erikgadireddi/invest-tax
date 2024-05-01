import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 

data.load_settings()
st.set_page_config(page_title='Prehled', layout='centered')

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
    years = trades['Year'].unique()
    year = int(pills('Select year to view', [str(year) for year in years]))
    st.session_state.update(year=year)
    if year:
        trades_display = st.dataframe(trades[trades['Year'] == year], hide_index=True, height=600, column_order=('Symbol', 'Date/Time', 'Quantity', 'Currency', 'T. Price', 'CZK Proceeds', 'CZK Fee', 'CZK Profit', 'Accumulated Quantity', 'Action', 'Type'),
                        column_config={
                            'CZK Profit': st.column_config.NumberColumn("Profit CZK", format="%.1f"), 
                            'CZK Fee': st.column_config.NumberColumn("Fees CZK", format="%.1f"), 
                            'CZK Proceeds': st.column_config.NumberColumn("Proceeds CZK", format="%.1f"), 
                            'Accumulated Quantity': st.column_config.NumberColumn("Position")
                            })
        profit_czk = trades[trades['Year'] == year]['CZK Profit'].sum()
        st.caption(f'FIFO profit this year: :green[{profit_czk:.2f}] CZK')
