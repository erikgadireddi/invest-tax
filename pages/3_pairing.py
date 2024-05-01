import pandas as pd
import streamlit as st
from streamlit_pills import pills
from matchmaker.pairing import pair_buy_sell, strategies
import matchmaker.data as data 

def page():
    data.load_settings()
    st.set_page_config(page_title='Párování obchodů', layout='wide')

    trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
    show_year = st.session_state.show_year if 'show_year' in st.session_state else None
    year_config = st.session_state.year_config if 'year_config' in st.session_state else {}

    if trades.empty:
        st.write('No trades loaded. Import some first.')
        return
        
    # Matching configuration is a dictionary[year] of:
    #  strategy: FIFO, LIFO, AverageCost, MaxLoss, MaxProfit
    #  use_yearly_rates: bool
    strategies = ['FIFO', 'LIFO', 'AverageCost', 'MaxLoss', 'MaxProfit']
    years = trades['Year'].unique()
    for year in years:
        if year not in year_config:
            year_config[year] = {'strategy': 'FIFO', 'use_yearly_rates': True}

    else:
        st.caption(str(len(trades)) + ' trades available.')
        show_year = int(pills('Select year to view', [str(year) for year in years]))
        year_config[show_year]['strategy'] = pills('Select strategy', strategies, index=strategies.index(year_config[show_year]['strategy']), key=f'strategy_{show_year}')
        show_strategy = year_config[show_year]['strategy']
        st.session_state.update(show_year=show_year)
        st.session_state.update(year_config=year_config)
        st.caption(f'Strategy for {show_year}: {show_strategy}')
        # Create a list of all years except the one selected
        other_years = [str(y) for y in years if y != show_year]
        buys, sells, sell_buy_pairs = pair_buy_sell(trades, pd.DataFrame(), show_strategy, [show_year])
        sell_buy_pairs['Percent Return'] = sell_buy_pairs['Ratio'] * 100
        trades_display = st.dataframe(sell_buy_pairs[sell_buy_pairs['Sell Time'].dt.year == show_year], hide_index=True, height=600, 
                                    column_order=('Symbol','Quantity','Buy Time','Buy Price','Sell Time','Sell Price','Currency','Buy Cost','Sell Proceeds','Revenue',
                                                'Percent Return','Type','Taxable','Buy CZK Rate','Sell CZK Rate', 'CZK Cost','CZK Proceeds','CZK Revenue'),
                                    column_config={
                                        'Quantity': st.column_config.NumberColumn("Počet", help="Počet kusů daného instrumentu", format="%f"), 
                                        'Buy Time': st.column_config.DatetimeColumn("Datum nákupu", help="Datum nákupní transakce"), 
                                        'Sell Time': st.column_config.DatetimeColumn("Datum prodeje", help="Datum prodejní transakce"), 
                                        'Buy Price': st.column_config.NumberColumn("Nákup (hrubý)", help="Cena nákupu 1 kusu bez poplatků", format="%.2f"), 
                                        'Sell Price': st.column_config.NumberColumn("Prodej (hrubý)", help="Cena prodeje 1 kusu bez poplatků", format="%.2f"), 
                                        'Buy Cost': st.column_config.NumberColumn("Nákup (čistý)", help="Cena nákupu 1 kusu včetně poplatků", format="%.2f"), 
                                        'Sell Proceeds': st.column_config.NumberColumn("Prodej (čistý)", help="Cena prodeje 1 kusu včetně poplatků", format="%.2f"), 
                                        'Revenue': st.column_config.NumberColumn("Výdělek (čistý)", help="Zisk z prodeje mínus cena nákupu včetně poplatků", format="%.1f"), 
                                        'Currency': st.column_config.TextColumn("Měna", help="Měna v které bylo obchodováno"), 
                                        'Percent Return': st.column_config.NumberColumn("Návratnost", help="Návratnost obchodu po odečtení všech nákladů včetně poplatků", format="%.2f%%"), 
                                        'CZK Cost': st.column_config.NumberColumn("CZK Cost", format="%.1f"), 
                                        'CZK Revenue': st.column_config.NumberColumn("Revenue CZK", format="%.1f"), 
                                        'CZK Proceeds': st.column_config.NumberColumn("Proceeds CZK", format="%.1f"), 
                                        'Accumulated Quantity': st.column_config.NumberColumn("Position")
                                        })


page()