import pandas as pd
import streamlit as st
from streamlit_pills import pills
from matchmaker.pairing import pair_buy_sell, strategies
import matchmaker.currency as currency
import matchmaker.data as data 
import matchmaker.ux as ux
import matchmaker.trade as trade
from menu import menu
import copy

def page():
    st.set_page_config(page_title='Daňový přehled', layout='wide')
    menu()
    data.load_settings()

    state = data.State()
    state.load_session()
    # Trades we previously tried to pair. Will be used to check when recomputation is needed.
    computed_trades = st.session_state.computed_trades if 'computed_trades' in st.session_state else pd.DataFrame()
    match_config = st.session_state.match_config if 'match_config' in st.session_state else {}
    paired_trades = st.session_state.paired_trades if 'paired_trades' in st.session_state else pd.DataFrame()
    buys = st.session_state.buys if 'buys' in st.session_state else pd.DataFrame()
    sells = st.session_state.sells if 'sells' in st.session_state else pd.DataFrame()
    previous_config = copy.deepcopy(match_config)
    if state.trades.empty:
        st.caption('Nebyly importovány žádné obchody.')
        st.page_link("pages/1_import_trades.py", label="📥 Přejít na import obchodů")
        return
        
    st.caption(str(len(state.trades)) + ' obchodů k dispozici.')
    # Matching configuration is a dictionary[year] of:
    #  strategy: FIFO, LIFO, AverageCost, MaxLoss, MaxProfit
    #  use_yearly_rates: bool
    trades = state.trades[(state.trades['Action'] == 'Open') | (state.trades['Action'] == 'Close')] # Filter out transfers and other transactions
    strategies = ['FIFO', 'LIFO', 'AverageCost', 'MaxLoss', 'MaxProfit']
    st.session_state.update(year=ux.add_years_filter(trades, False, 'Rok pro párování'))
    years = sorted(trades['Year'].unique())
    show_year = st.session_state.get('year')
    if show_year is None:
        show_year = years[-1]
    for year in years:
        if year not in match_config:
            match_config[year] = {'strategy': 'FIFO', 'yearly_rates': True}
    
    this_config = match_config[show_year]
    this_config['strategy'] = pills('Strategie párování', strategies, index=strategies.index(this_config['strategy']), key=f'strategy_{show_year}')
    this_config['yearly_rates'] = pills(f'Použíté kurzy', ['roční', 'denní'], index=0 if this_config['yearly_rates'] else 1, key=f'yearly_rates_{show_year}') == 'roční'
    show_strategy = match_config[show_year]['strategy']
    st.caption(f'Strategie pro rok {show_year}: {show_strategy} | {"roční" if this_config["yearly_rates"] else "denní"} kurzy')
    
    # Needs recompute only if strategy changed. Empty strategy means this page was opened for the first time.
    # Also needs recompute if we have new trades or the trades changed.
    need_recompute = len(computed_trades) != len(trades) or not computed_trades.equals(trades)
    if not need_recompute:
        for year in years:
            if len(previous_config) == 0 or match_config[year]['strategy'] != previous_config[year]['strategy']:
                need_recompute = True
                break
        
    if need_recompute:
        buys, sells, paired_trades = pair_buy_sell(trades, paired_trades, show_strategy, show_year)
        st.session_state.update(buys=buys)
        st.session_state.update(sells=sells)
        st.session_state.update(paired_trades=paired_trades)
        st.session_state.update(computed_trades=trades)
        # Update all higher years to use the same strategy
        for year in years[years.index(show_year)+1:]:
            match_config[year]['strategy'] = this_config['strategy']

    st.session_state.update(match_config=match_config)
    st.session_state.update(show_year=show_year)

    if paired_trades.empty:
        st.caption('Nebyly nalezeny žádné párované obchody.')
        return
    
    if this_config['yearly_rates']:
        yearly_rates = currency.load_yearly_rates(st.session_state['settings']['currency_rates_dir'])
        pairs_in_czk = currency.add_czk_conversion_to_pairs(paired_trades, yearly_rates, True)
    else:
        daily_rates = currency.load_daily_rates(st.session_state['settings']['currency_rates_dir'])
        pairs_in_czk = currency.add_czk_conversion_to_pairs(paired_trades, daily_rates, False)
    pairs_in_czk['Percent Return'] = pairs_in_czk['Ratio'] * 100
    filtered_pairs = pairs_in_czk[pairs_in_czk['Sell Time'].dt.year == show_year]
    #print(filtered_pairs)
    trades_display = st.dataframe(filtered_pairs, hide_index=True, height=600, 
                                column_order=('Display Name','Quantity','Buy Time','Buy Price','Sell Time','Sell Price','Currency','Buy Cost','Sell Proceeds','Revenue',
                                            'CZK Revenue','Percent Return','Type','Taxable','Buy CZK Rate','Sell CZK Rate', 'CZK Cost','CZK Proceeds'),
                                column_config={
                                    'Display Name': st.column_config.TextColumn("Název", help="Název instrumentu"),
                                    'Quantity': st.column_config.NumberColumn("Počet", help="Počet kusů daného instrumentu", format="%d" if show_strategy != 'AverageCost' else "%.2f"), 
                                    'Buy Time': st.column_config.DatetimeColumn("Datum nákupu", help="Datum nákupní transakce"), 
                                    'Sell Time': st.column_config.DatetimeColumn("Datum prodeje", help="Datum prodejní transakce"), 
                                    'Buy Price': st.column_config.NumberColumn("Nákup (hrubý)", help="Cena nákupu 1 kusu bez poplatků", format="%.2f"), 
                                    'Sell Price': st.column_config.NumberColumn("Prodej (hrubý)", help="Cena prodeje 1 kusu bez poplatků", format="%.2f"), 
                                    'Buy Cost': st.column_config.NumberColumn("Nákup (čistý)", help="Cena nákupu 1 kusu včetně poplatků", format="%.2f"), 
                                    'Sell Proceeds': st.column_config.NumberColumn("Prodej (čistý)", help="Cena prodeje 1 kusu včetně poplatků", format="%.2f"), 
                                    'Revenue': st.column_config.NumberColumn("Výdělek (čistý)", help="Zisk z prodeje mínus cena nákupu včetně poplatků", format="%.1f"), 
                                    'Currency': st.column_config.TextColumn("Měna", help="Měna v které bylo obchodováno"), 
                                    'Percent Return': st.column_config.NumberColumn("Návratnost", help="Návratnost obchodu po odečtení všech nákladů včetně poplatků", format="%.0f%%"), 
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
    proceeds_sum = filtered_pairs[filtered_pairs["Taxable"] == 1]["CZK Proceeds"].sum()
    taxable_sum = filtered_pairs[filtered_pairs["Taxable"] == 1]["CZK Revenue"].sum()
    if proceeds_sum > 100000:
        print(f"The proceeds_sum is: {proceeds_sum:.2f}")
        footer = f'Danitelný výdělek v CZK: :blue[{taxable_sum:,.0f}] CZK'
    else:
        print(f"The proceeds_sum is: {proceeds_sum:.2f}")
        footer = f'Výdělek v CZK: :blue[{taxable_sum:,.0f}] CZK se numusí danit, pokud jsou v formuláři všechny obchody fyzické osoby za tento rok.'
    footer = f'Danitelný výdělek v CZK: :blue[{taxable_sum:,.0f}] CZK'
    untaxed_revenue = filtered_pairs[filtered_pairs['Taxable'] == 0]['CZK Revenue'].sum()
    if untaxed_revenue > 0:
        footer += f' | Osvobozený výdělek v CZK: :green[{untaxed_revenue:,.0f}] CZK'
    
    if not unpaired_sells.empty:
        footer += f' | Pozor, jsou zde nenapárované prodeje: :red[{len(unpaired_sells)}]'
    st.caption(footer)
    if not unpaired_sells.empty:
        st.subheader('Nenapárované obchody')
        table_descriptor = ux.transaction_table_descriptor_czk()
        st.dataframe(unpaired_sells, hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
        ux.add_trades_editor(state, unpaired_sells.iloc[0])

page()