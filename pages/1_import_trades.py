import pandas as pd
import numpy as np
import argparse
import streamlit as st
import matchmaker.styling as styling
import matchmaker.data as data
import matchmaker.snapshot as snapshot
import matchmaker.trade as trade
import matchmaker.ibkr as ibkr
import matchmaker.imports as imports
from menu import menu

def import_trade_file(file):
    try:
        if snapshot.is_snapshot(file):
            return snapshot.load_snapshot(file)
        else:
            return ibkr.import_activity_statement(file)
    except Exception as e:
        st.error(f'Error importing trades. File {file.name} does not contain the expected format. Error: {e}')
        return pd.DataFrame()
    

def main():
    st.set_page_config(page_title='Krutopřísný tradematcher', layout='centered')
    menu()
    data.load_settings()
    # st.header('Taxonomy Matchmaker')
    st.subheader('Import transkací z Interactive Brokers')
    
    # Process command-line arguments
    parser = argparse.ArgumentParser(description='Process command-line arguments')

    # Add the arguments
    parser.add_argument('--settings-dir', type=str, help='Path to CurrencyRates.csv file')
    parser.add_argument('--import-trades-dir', type=str, help='Path to Trades CSV files')
    parser.add_argument('--tickers-dir', type=str, help='Path to load historic ticker data to adjust prices for splits')
    parser.add_argument('--load-trades', type=str, help='Path to load processed trades file')
    parser.add_argument('--save-trades', type=str, help='Path to save processed trades file after import')
    parser.add_argument('--process-years', type=str, help='List of years to process, separated by commas. If not specified, all years are processed.')
    parser.add_argument('--preserve-years', type=str, help='List of years to keep unchanged, separated by commas. If not specified, all years are preserved.')
    parser.add_argument('--strategy', type=str, default='fifo', help='Strategy to use for pairing buy and sell orders. Available: fifo, lifo, average-cost, max-loss. max-profit')
    parser.add_argument('--save-trade-overview-dir', type=str, help='Directory to output overviews of matched trades')
    parser.add_argument('--load-matched-trades', type=str, help='Paired trades input to load')
    parser.add_argument('--save-matched-trades', type=str, help='Save updated paired trades')
    
    # Parse the arguments
    args = parser.parse_args()

    state = data.State()
    state.load_session()

    def change_uploaded_files(previous_uploads):
        if len(previous_uploads) > 0:
            state.reset()
        
    # Show file upload widget
    uploaded_files = st.file_uploader("Přetáhněte libovolné množství exportů (IBKR i Taxlite)", accept_multiple_files=True, type=['csv'], 
                                      on_change=lambda: change_uploaded_files(uploaded_files), key='file_uploader', help='Upload IBKR Activity Statements or CSV files with trades.')
    # Save newly uploaded files to session
    # Load list of filenames from session state
    st.session_state.uploaded_files = [f.name for f in uploaded_files]

    st.markdown('Po vyexportování historie všech obchodů je stačí zde všechny přetáhnout a aplikace je zpracuje. Také můžete přetáhnout export stavu Taxlite, pokud jste si jej stáhli.',
                unsafe_allow_html=True)
    with st.expander(f'Jak získat exporty z :blue[Interactive Brokers]'):
        st.markdown('''Aplikace nyní podporuje pouze importy z :blue[Interactive Brokers].
                    Nejjednodušší cesta k exportu je skrz web IB kliknout v horním menu na Statements, vybrat Activity Statements, následně zvolit Yearly (roční), formát CSV a postupně vyexportovat všechny roky, kdy jste obchodovali.
                    \nJelikož nejdelší období, které můžete zvolit, je rok, může být nutné udělat postupně několik exportů. Všechny najednou je pak můžete myší přetáhnout sem. Nevadí, pokud se budou překrývat. Můžete také kdykoliv
                    přidat další exporty či kombinovat z exporty z Taxlite.''')

    with st.expander(f'Bezpečnost a jak nepřijít o stav výpočtů z :green[Taxlite]'):
        st.markdown('''Pro Vaše soukromí Taxlite neukládá žádné informace o Vašich obchodech na server, vše je ukládáno pouze do Vašeho prohlížeče. Vývojáři ani nikdo jiný je neuvidí. 
                    Toto zároveň znamená, že pokud zavřete stránku nebo smažete session, všechny obchody budou zahozeny. Je proto důležité se stav výpočtů pravidelně ukládat stažením do CSV souboru, 
                    který si můžete kdykoliv zase nahrát a pokračovat v práci.
                    \nCelý interní stav aplikace si můžete kdykoliv stáhnout tlačítkem :red[Stáhnout vše v CSV] a uchovat na svém počítači, jelikož po zavření stránky nebo smazání session bude interní stav ztracen.
                    Následně ho můžete importovat stejným způsobem, jakým importujete exporty z Interactive Brokers. V případě poptávky mohu dodělat i ukládání stavu na server.
                    ''')
        st.caption('Kód aplikace je open-source a můžete si tato tvrzení kdykoliv ověřit kliknutím na odkaz na GitHub v záhlaví aplikace. Kdykoliv si také můžete stáhnout celý kód a spustit si Taxlite na svém počítači.\n')
    import_state = st.caption('')
    trades_count = len(state.trades)
    loaded_count = 0
    # On upload, run import trades
    if uploaded_files:
        for uploaded_file in uploaded_files:
            import_state.write('Importuji transakce...')
            imported = import_trade_file(uploaded_file)
            import_state.write(f'Slučuji :blue[{len(imported.trades)}] obchodů...')
            loaded_count += state.merge_trades(imported, loaded_count > 0)
            import_message = f'Importováno :green[{len(state.trades) - trades_count}] obchodů.'
            import_state.write(import_message)
        state.actions.drop_duplicates(inplace=True)
        state.imports = imports.merge_import_intervals(state.imports)

    if loaded_count > 0:
        import_state.write(f'Nalezeno :blue[{loaded_count}] obchodů, z nichž :green[{len(state.trades) - trades_count}] je nových.')
        state.recompute_positions()
        state.save_session()

    if (len(state.trades) == 0):
        return
    
    state.trades.sort_values(by=['Symbol', 'Date/Time'], inplace=True)
    st.caption(f':blue[{len(state.trades)}] nahraných obchodů celkem')
    st.dataframe(data=styling.format_trades(state.trades), hide_index=True, width=1100, height=500, column_order=('Display Name', 'Date/Time', 'Action', 'Quantity', 'Currency', 'T. Price', 'Proceeds', 'Comm/Fee', 'Realized P/L', 'Accumulated Quantity', 'Split Ratio'),
                    column_config={
                        'Display Name': st.column_config.TextColumn("Název", help="Název instrumentu"),
                        'Date/Time': st.column_config.DatetimeColumn("Datum", help="Čas obchodu"),
                        'Action': st.column_config.TextColumn("Akce", help="Typ obchodu: Buy, Sell, Dividend, Split, Transfer"),
                        'Realized P/L': st.column_config.NumberColumn("Profit", format="%.1f"), 
                        'Proceeds': st.column_config.NumberColumn("Objem", format="%.1f"), 
                        'Comm/Fee': st.column_config.NumberColumn("Poplatky", format="%.1f"), 
                        'T. Price': st.column_config.NumberColumn("Cena", format="%.1f", help="Cena jednoho kusu instrumentu"),
                        'Quantity': st.column_config.NumberColumn("Počet", help="Počet kusů daného instrumentu", format="%f"), 
                        'Accumulated Quantity': st.column_config.NumberColumn("Pozice", help="Otevřené pozice po této transakci. Negativní znamenají shorty. "
                                                                                "Pokud toto číslo nesedí s realitou, v importovaných transakcích se nenacházejí všechny obchody", format="%f"),
                        'Split Ratio': st.column_config.NumberColumn("Split", help="Poměr akcií po splitu", format="%f"),})
    
    account_count = len(state.imports['Account'].unique())
    with st.expander(f"Účty, z kterých jsme nahráli data (:blue[{account_count}])"):
        st.dataframe(data=state.imports, hide_index=True, 
                    column_order=('Account', 'From', 'To', 'Trade Count'), 
                    column_config={
                        'Account': st.column_config.TextColumn("Účet", help="Název importovaného účtu."),
                        'From': st.column_config.DateColumn("Od", help="Začátek období"), 
                        'To': st.column_config.DateColumn("Do", help="Začátek období"),
                        'Trade Count': st.column_config.NumberColumn("Počet obchodů", help="Počet obchodů v tomto období", format="%d")
                        })

    # Show imported splits
    if len(state.actions) > 0:
        splits = state.actions[state.actions['Action'] == 'Split'].copy()
        splits['Reverse Ratio'] = 1 / splits['Ratio']
        if len(splits) > 0:
            with st.expander(f'Splity, kterým rozumíme (:blue[{len(splits)}])'):
                st.dataframe(data=splits, hide_index=True, 
                            column_order=('Symbol', 'Date/Time', 'Reverse Ratio'),
                            column_config={
                                "Date/Time": st.column_config.DatetimeColumn("Datum", help="Čas splitu"),
                                'Reverse Ratio': st.column_config.NumberColumn("Poměr", help="Počet akcií, na které byla jedna akcie rozdělena", format="%f")})
        spinoffs = state.actions[(state.actions['Action'] == 'Spinoff') | (state.actions['Action'] == 'Acquisition')].copy()
        if len(spinoffs) > 0:
            with st.expander(f'Vytvoření nových akcií (spinoffy), kterým rozumíme (:blue[{len(spinoffs)}])'):
                st.dataframe(data=spinoffs, hide_index=True, 
                            column_order=('Symbol', 'Date/Time', 'Quantity', 'Ratio', 'Description'),
                            column_config={
                                "Date/Time": st.column_config.DatetimeColumn("Datum", help="Čas spinoffu"),
                                'Quantity': st.column_config.NumberColumn("Počet", help="Počet nových akcií"),
                                'Ratio': st.column_config.NumberColumn("Poměr", help="Poměr nových akcií za staré", format="%.3f"),
                                'Description': st.column_config.NumberColumn("Popis", help="Textový popis spinoffu")})
        
        unparsed = state.actions[state.actions['Action'] == 'Unknown']
        if len(unparsed) > 0:
            with st.expander(f'Korporátní akce, které neznáme (:blue[{len(unparsed)}])'):
                st.dataframe(data=unparsed, hide_index=True, 
                             column_order=('Symbol', 'Date/Time', 'Description'),
                             column_config={
                                 "Date/Time": st.column_config.DatetimeColumn("Datum", help="Čas akce"),
                                 'Description': st.column_config.NumberColumn("Popis", help="Textový popis akce")})
    
    col1, spacer, col2 = st.columns([0.3, 0.3, 0.2])
    # Serve merged trades as CSV    
    # Clear uploaded files
    with col2:
        def clear_uploads():
            st.session_state.pop('file_uploader', None)
            state.reset()
            state.save_session()
        st.button('🧹 Smazat obchody', on_click=lambda: clear_uploads(), use_container_width=True)
    
    return

if __name__ == "__main__":
    main()
