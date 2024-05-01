import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 
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
    trades_display = st.dataframe(shown_trades, hide_index=True, height=600, 
                    column_order=('Symbol', 'Date/Time', 'Quantity', 'Currency', 'T. Price', 'Comm/Fee', 'CZK Proceeds', 'CZK Fee', 'CZK Profit', 'Accumulated Quantity', 'Action', 'Type'),
                    column_config={
                        'Currency': st.column_config.TextColumn("Měna", help="Měna v které bylo obchodováno"), 
                        'Quantity': st.column_config.NumberColumn("Počet", help="Počet kusů daného instrumentu", format="%f"), 
                        'Date/Time': st.column_config.DatetimeColumn("Čas transakce", help="Datum a čas transakce"), 
                        'T. Price': st.column_config.NumberColumn("Cena", help="Cena za 1 kus daného instrumentu", format="%f"), 
                        'Comm/Fee': st.column_config.NumberColumn("Poplatek",  help="Poplatek brokerovi za celou transakci. Při párování pozic bude rozpočítán.", format="%.1f"), 
                        'CZK Profit': st.column_config.NumberColumn("Zisk v CZK (přibližný)", help="Zisk je ve zdrojových datech obvykle počítán FIFO metodou a zde je přepočítán do CZK kurzem daného dne. "
                                                                    "Pro vykázání v daňovém přiznání nicméně musí být nákupní transakce přepočítána kurzem jejího vzniku.", format="%.1f"), 
                        'CZK Fee': st.column_config.NumberColumn("Fees CZK", format="%.1f"), 
                        'CZK Proceeds': st.column_config.NumberColumn("Objem v CZK", format="%.1f", help="Zaplacená (nákup) či získaná (prodej) částka v CZK, přepočtená kurzem daného dne"), 
                        'Accumulated Quantity': st.column_config.NumberColumn("Pozice", help="Otevřené pozice po této transakci. Negativní znamenají shorty. "
                                                                                "Pokud toto číslo nesedí s realitou, v importovaných transakcích se nenacházejí všechny obchody", format="%f"), 
                        'Action': st.column_config.TextColumn("Akce", help="Otevření nebo uzavření pozice. Shorty začínají prodejem a končí nákupem."),
                        'Type': st.column_config.TextColumn("Typ", help="Long nebo short pozice. Long pozice je standardní nákup instrumentu pro pozdější prodej s očekáváním zvýšení ceny. Short pozice je prodej instrumentu, který ještě nevlastníte, s očekáváním poklesu ceny a následného nákupu.")
                        })
    profit_czk = trades[trades['Year'] == year]['CZK Profit'].sum() if year is not None else trades['CZK Profit'].sum()
    if year is not None:
        st.caption(f'FIFO profit this year: :green[{profit_czk:.2f}] CZK') 
    else: 
        st.caption(f'FIFO profit: :green[{profit_czk:.2f}] CZK')
        
    suspicious_positions = shown_trades[((shown_trades['Accumulated Quantity'] < 0) & (shown_trades['Type'] == 'Long') & (shown_trades['Action'] == 'Close') | 
                                         (shown_trades['Accumulated Quantity'] > 0) & (shown_trades['Type'] == 'Short') & (shown_trades['Action'] == 'Close'))]
    if len(suspicious_positions) > 0:
        st.caption('Negative positions detected on long positions. Your data may be incomplete. Please check your imports.')
        st.dataframe(suspicious_positions, hide_index=True)
