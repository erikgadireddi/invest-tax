import pandas as pd
import streamlit as st
from streamlit_pills import pills
from matchmaker.pairing import pair_buy_sell, strategies
import matchmaker.currency as currency
import matchmaker.data as data 
from menu import menu

def page():
    st.set_page_config(page_title='Párování obchodů', layout='wide')
    menu()
    data.load_settings()

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
            year_config[year] = {'strategy': 'FIFO', 'yearly_rates': True}

    else:
        st.caption(str(len(trades)) + ' trades available.')
        show_year = int(pills('Rok', [str(year) for year in years]))
        this_config = year_config[show_year]
        this_config['strategy'] = pills('Strategie párování', strategies, index=strategies.index(this_config['strategy']), key=f'strategy_{show_year}')
        this_config['yearly_rates'] = pills(f'Použíté kurzy', ['roční', 'denní'], index=0 if this_config['yearly_rates'] else 1, key=f'yearly_rates_{show_year}') == 'roční'
        show_strategy = year_config[show_year]['strategy']
        st.session_state.update(show_year=show_year)
        st.session_state.update(year_config=year_config)
        st.caption(f'Strategy for {show_year}: {show_strategy}')
        # Create a list of all years except the one selected
        other_years = [str(y) for y in years if y != show_year]
        buys, sells, sell_buy_pairs = pair_buy_sell(trades, pd.DataFrame(), show_strategy)
        if this_config['yearly_rates']:
            yearly_rates = currency.load_yearly_rates(st.session_state['settings']['currency_rates_dir'])
            pairs_in_czk = currency.add_czk_conversion_to_pairs(sell_buy_pairs, yearly_rates, True)
        else:
            daily_rates = currency.load_daily_rates(st.session_state['settings']['currency_rates_dir'])
            pairs_in_czk = currency.add_czk_conversion_to_pairs(sell_buy_pairs, daily_rates, False)
        pairs_in_czk['Percent Return'] = pairs_in_czk['Ratio'] * 100
        filtered_pairs = pairs_in_czk[pairs_in_czk['Sell Time'].dt.year == show_year]
        trades_display = st.dataframe(filtered_pairs, hide_index=True, height=600, 
                                    column_order=('Symbol','Quantity','Buy Time','Buy Price','Sell Time','Sell Price','Currency','Buy Cost','Sell Proceeds','Revenue',
                                                'CZK Revenue','Percent Return','Type','Taxable','Buy CZK Rate','Sell CZK Rate', 'CZK Cost','CZK Proceeds'),
                                    column_config={
                                        'Quantity': st.column_config.NumberColumn("Počet", help="Počet kusů daného instrumentu", format="%d" if show_strategy != 'AverageCost' else "%.2f"), 
                                        'Buy Time': st.column_config.DatetimeColumn("Datum nákupu", help="Datum nákupní transakce"), 
                                        'Sell Time': st.column_config.DatetimeColumn("Datum prodeje", help="Datum prodejní transakce"), 
                                        'Buy Price': st.column_config.NumberColumn("Nákup (hrubý)", help="Cena nákupu 1 kusu bez poplatků", format="%.2f"), 
                                        'Sell Price': st.column_config.NumberColumn("Prodej (hrubý)", help="Cena prodeje 1 kusu bez poplatků", format="%.2f"), 
                                        'Buy Cost': st.column_config.NumberColumn("Nákup (čistý)", help="Cena nákupu 1 kusu včetně poplatků", format="%.2f"), 
                                        'Sell Proceeds': st.column_config.NumberColumn("Prodej (čistý)", help="Cena prodeje 1 kusu včetně poplatků", format="%.2f"), 
                                        'Revenue': st.column_config.NumberColumn("Výdělek (čistý)", help="Zisk z prodeje mínus cena nákupu včetně poplatků", format="%.1f"), 
                                        'Currency': st.column_config.TextColumn("Měna", help="Měna v které bylo obchodováno"), 
                                        'Percent Return': st.column_config.NumberColumn("Návratnost", help="Návratnost obchodu po odečtení všech nákladů včetně poplatků", format="%.2f%%"), 
                                        'Taxable': st.column_config.CheckboxColumn("Daní se", help="Prodej se daní, pokud nebyl spárován s nákupem starším 3 let (časový test)"),
                                        'Type': st.column_config.TextColumn("Typ", help="Long nebo short pozice. Long pozice je standardní nákup instrumentu pro pozdější prodej s očekáváním zvýšení ceny. Short pozice je prodej instrumentu, který ještě nevlastníte, s očekáváním poklesu ceny a následného nákupu."),
                                        'Buy CZK Rate': st.column_config.NumberColumn("Nákupní kurz", help="Kurz měny v době nákupu", format="%.2f"),
                                        'Sell CZK Rate': st.column_config.NumberColumn("Prodejní kurz", help="Kurz měny v době prodeje", format="%.2f"),
                                        'CZK Cost': st.column_config.NumberColumn("Náklady v CZK", format="%.1f"), 
                                        'CZK Revenue': st.column_config.NumberColumn("Výdělek v CZK", format="%.1f"), 
                                        'CZK Proceeds': st.column_config.NumberColumn("Příjem v CZK", format="%.1f"), 
                                        'Accumulated Quantity': st.column_config.NumberColumn("Position")
                                        })
        
        unpaired_sells = sells[(sells['Year'] == show_year) & (sells['Uncovered Quantity'] != 0)]
        footer = f'Výdělek v CZK: :green[{filtered_pairs[filtered_pairs['Taxable'] == 1]["CZK Revenue"].sum():.2f}] CZK'
        if not unpaired_sells.empty:
            footer += f' | Pozor, :red[{len(unpaired_sells)}] nenapárovaných prodejů!'
        st.caption(footer)
        if not unpaired_sells.empty:
            st.subheader('Nenapárované obchody')
            st.dataframe(unpaired_sells, hide_index=True)

page()