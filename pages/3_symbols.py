import pandas as pd
import streamlit as st
from streamlit_pills import pills
import matchmaker.currency as currency
import matchmaker.data as data 
import matchmaker.ux as ux
from menu import menu

st.set_page_config(page_title='Doplnění obchodů', layout='wide')
menu()

data.load_settings()

trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
symbol = st.session_state.symbol if 'symbol' in st.session_state else None

if trades.empty:
    st.caption('Nebyly importovány žádné obchody.')
    st.page_link("pages/1_import_trades.py", label="📥 Přejít na import obchodů")
else:
    st.caption(str(len(trades)) + ' trades available.')

yearly_rates = currency.load_yearly_rates(st.session_state['settings']['currency_rates_dir'])

if trades is not None and not trades.empty:
    year = st.selectbox('Zobrazuji symboly', [0] + sorted(trades['Year'].unique()), index=0, key='year', format_func=lambda x: 'Všechny' if x == 0 else f's transakcemi od roku {x}')
    if year == 0:
        symbols = sorted(trades['Symbol'].unique())
    else:
        symbols = sorted(trades[trades['Year'] >= year]['Symbol'].unique())
    symbol = pills('Vyberte symbol pro inspekci', options=symbols)
    st.caption(f'Vysvětlivky k jednotlivým sloupcům jsou k dispozici na najetí myší.')
    shown_trades = trades[trades['Symbol'] == symbol].sort_values(by='Date/Time')
    if shown_trades.empty:
        st.caption(f'Pro symbol {symbol} nebyly nalezeny žádné obchody.')
    else:
        table_descriptor = ux.transaction_table_descriptor_native()
        trades_display = st.dataframe(shown_trades, hide_index=True, column_order=table_descriptor['column_order'], column_config=table_descriptor['column_config'])
        profit = shown_trades['Realized P/L'].sum()
        held_position = shown_trades['Accumulated Quantity'].iloc[-1]
        if held_position != 0:
            st.markdown(f'**Držené pozice: :blue[{held_position:.0f}]**')
        st.caption(f'Realizovaný profit dle brokera: :green[{profit:.0f}] {shown_trades["Currency"].iloc[0]}')
            
        suspicious_positions = shown_trades[((shown_trades['Accumulated Quantity'] < 0) & (shown_trades['Type'] == 'Long') & (shown_trades['Action'] == 'Close') | 
                                            (shown_trades['Accumulated Quantity'] > 0) & (shown_trades['Type'] == 'Short') & (shown_trades['Action'] == 'Close'))]
        if len(suspicious_positions) > 0:
            st.caption('Historie obsahuje long transakce vedoucí k negativním pozicím. Je možné, že nebyly nahrány všechny obchody či korporátní akce. Zkontrolujte, prosím, zdrojová data a případně doplňte chybějící transakce.')
            table_descriptor = ux.transaction_table_descriptor_native()
            st.dataframe(suspicious_positions, hide_index=True, column_config=table_descriptor['column_config'], column_order=table_descriptor['column_order'])
            ux.add_trades_editor(trades, suspicious_positions.iloc[0])
