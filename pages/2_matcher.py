import pandas as pd
import streamlit as st
import matchmaker.currency as currency

st.set_page_config(page_title='Párování obchodů', layout='wide')

trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
year = st.session_state.year if 'year' in st.session_state else None

if trades.empty:
    st.write('No trades loaded. Import some first.')
else:
    st.caption(str(len(trades)) + ' trades available.')

daily_rates = currency.load_daily_rates(st.session_state['settings']['currency_rates_dir'])
yearly_rates = currency.load_yearly_rates(st.session_state['settings']['currency_rates_dir'])
# currency.add_czk_conversion_to_trades(trades, daily_rates, use_yearly_rates=False)

if trades is not None:    
    years = trades['Year'].unique()
    columns = st.columns(len(years))
    if year:
        trades_display = st.dataframe(trades[trades['Year'] == year], hide_index=True, height=600, column_order=('Symbol', 'Date/Time', 'Quantity', 'Currency', 'T. Price', 'CZK Proceeds', 'CZK Fee', 'CZK Profit', 'Accumulated Quantity', 'Action', 'Type'),
                        column_config={
                            'CZK Profit': st.column_config.NumberColumn("Profit CZK", format="%.1f"), 
                            'CZK Fee': st.column_config.NumberColumn("Fees CZK", format="%.1f"), 
                            'CZK Proceeds': st.column_config.NumberColumn("Proceeds CZK", format="%.1f"), 
                            'Accumulated Quantity': st.column_config.NumberColumn("Position")
                            })
        st.caption(f'FIFO profit this year: {trades[trades['Year'] == year]["CZK Profit"].sum():.2f} CZK')

    for i, year in enumerate(years):
        with columns[i]:
            st.button(str(year), key=year, on_click=lambda year=year: st.session_state.update(year=year))

