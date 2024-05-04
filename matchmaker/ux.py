import pandas as pd
import streamlit as st

def transaction_table_descriptor():
   return {
       'column_order' : ('Symbol', 'Date/Time', 'Quantity', 'Currency', 'T. Price', 'Comm/Fee', 'CZK Proceeds', 'CZK Fee', 'CZK Profit', 'Accumulated Quantity', 'Action', 'Type'),
       'column_config' : {
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
                        }
       }
   
def add_trades_editor(trades, selected_trade=None, callback=None):
    with st.form(key='add_buy_form'):
        st.caption('Zde můžete přidat chybějící nákup k prodeji')
        def create_dataframe(trades, symbol, date, quantity, price):
            return pd.DataFrame({'Symbol': [symbol], 'Currency': trades[trades['Symbol']==symbol]['Currency'].values[0], 'Date/Time': [pd.to_datetime(date)], 'Quantity': [quantity], 'T. Price': [price], 'Action': ['Open'], 'Type': ['Long'],
                                   'Proceeds': [-quantity*price], 'Comm/Fee': [0], 'Basis': [0], 'Realized P/L': [0], 'MTM P/L': [0]})
        if selected_trade is None:
            selected_trade = trades.iloc[0]
        symbolcol, datecol, quantitycol, pricecol, buttoncol, spacer_ = st.columns([1, 1, 1, 1, 1, 3])
        with symbolcol:
            symbols = trades['Symbol'].unique()
            symbol_to_add = st.selectbox('Symbol', symbols, index=symbols.tolist().index(selected_trade['Symbol']))
        with datecol:
            date_to_add = st.date_input('Datum nákupu', value=selected_trade['Date/Time'], max_value=trades['Date/Time'].max())
        with quantitycol:
            quantity_to_add = st.number_input('Počet kusů', min_value=1.0, value=abs(selected_trade['Accumulated Quantity']), step=1.0)
        with pricecol:
            price_to_add = st.number_input('Cena za kus', min_value=0.0, value=selected_trade['T. Price'], step=0.01)
        with buttoncol:
            st.container(height=12, border=False)
            st.form_submit_button('Přidat nákup', on_click=lambda: callback(create_dataframe(trades, symbol_to_add, date_to_add, quantity_to_add, price_to_add)))