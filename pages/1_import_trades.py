import pandas as pd
import numpy as np
import argparse
import streamlit as st
from matchmaker.trade import *
from matchmaker.ibkr import *
from matchmaker.pairing import *
from matchmaker.currency import *
from menu import menu
import matchmaker.data as data
import matchmaker.snapshot as snapshot

def import_trade_file(file):
    try:
        if snapshot.is_snapshot(file):
            return snapshot.load_snapshot(file)
        else:
            return import_activity_statement(file)
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

    trades = st.session_state.trades if 'trades' in st.session_state else pd.DataFrame()
    actions = st.session_state.actions if 'actions' in st.session_state else pd.DataFrame()
    positions = st.session_state.positions if 'positions' in st.session_state else pd.DataFrame()
    sell_buy_pairs = None
    process_years = None
    preserve_years = None

    def change_uploaded_files(trades, previous_uploads):
        if len(previous_uploads) > 0:
            trades.drop(trades.index, inplace=True)
            actions.drop(actions.index, inplace=True)
            positions.drop(positions.index, inplace=True)
        
    # Show file upload widget
    uploaded_files = st.file_uploader("Přetáhněte libovolné množství exportů (IBKR i Taxlite)", accept_multiple_files=True, type=['csv'], 
                                      on_change=lambda: change_uploaded_files(trades, uploaded_files), key='file_uploader', help='Upload IBKR Activity Statements or CSV files with trades.')
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
    trades_count = len(trades)
    loaded_count = 0
    # On upload, run import trades
    if uploaded_files:
        for uploaded_file in uploaded_files:
            import_state.write('Importuji transakce...')
            imported_trades, imported_actions, imported_positions = import_trade_file(uploaded_file)
            if len(imported_actions) > 0:
                actions = pd.concat([imported_actions, actions])
            # Merge open positions and drop duplicates
            positions = pd.concat([imported_positions, positions])
            positions.drop_duplicates(subset=['Symbol', 'Date'], inplace=True)
            loaded_count += len(imported_trades)
            import_state.write(f'Slučuji :blue[{len(imported_trades)}] obchodů...')
            trades = merge_trades(trades, imported_trades)
            import_message = f'Importováno :green[{len(trades) - trades_count}] obchodů.'
            import_state.write(import_message)

        import_state.write(f'Nalezeno :blue[{loaded_count}] obchodů, z nichž :green[{len(trades) - trades_count}] je nových.')
        actions.drop_duplicates(inplace=True)

        if len(trades) > 0:
            trades = process_after_import(trades, actions)
        st.session_state.trades = trades
        st.session_state.actions = actions
        st.session_state.positions = positions

    if (len(trades) == 0):
        return
    
    trades.sort_values(by=['Symbol', 'Date/Time'], inplace=True)
    st.caption(f':blue[{len(trades)}] nalezených obchodů.')
    st.dataframe(data=trades, hide_index=True, width=1100, height=500, column_order=('Symbol', 'Date/Time', 'Action', 'Quantity', 'Currency', 'T. Price', 'Proceeds', 'Comm/Fee', 'Realized P/L', 'Accumulated Quantity', 'Split Ratio'),
                    column_config={
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

    # Show imported splits
    if len(actions) > 0:
        splits = actions[actions['Action'] == 'Split'].copy()
        splits['Reverse Ratio'] = 1 / splits['Ratio']
        if len(splits) > 0:
            with st.expander(f'Splity, kterým rozumíme (:blue[{len(splits)}])'):
                st.dataframe(data=splits, hide_index=True, 
                            column_order=('Symbol', 'Date/Time', 'Reverse Ratio'),
                            column_config={
                                "Date/Time": st.column_config.DatetimeColumn("Datum", help="Čas splitu"),
                                'Reverse Ratio': st.column_config.NumberColumn("Poměr", help="Počet akcií, na které byla jedna akcie rozdělena", format="%f")})
        spinoffs = actions[actions['Action'] == 'Spinoff'].copy()
        if len(spinoffs) > 0:
            with st.expander(f'Vytvoření nových akcií (spinoffy), kterým rozumíme (:blue[{len(spinoffs)}])'):
                st.dataframe(data=spinoffs, hide_index=True, 
                            column_order=('Symbol', 'Date/Time', 'Quantity', 'Ratio', 'Description'),
                            column_config={
                                "Date/Time": st.column_config.DatetimeColumn("Datum", help="Čas spinoffu"),
                                'Quantity': st.column_config.NumberColumn("Počet", help="Počet nových akcií"),
                                'Ratio': st.column_config.NumberColumn("Poměr", help="Poměr nových akcií za staré", format="%.3f"),
                                'Description': st.column_config.NumberColumn("Popis", help="Textový popis spinoffu")})
        
        unparsed = actions[actions['Action'] == 'Unknown']
        if len(unparsed) > 0:
            with st.expander(f'Korporátní akce, které neznáme (:blue[{len(unparsed)}])'):
                st.dataframe(data=unparsed, hide_index=True, 
                             column_order=('Symbol', 'Date/Time', 'Description'),
                             column_config={
                                 "Date/Time": st.column_config.DatetimeColumn("Datum", help="Čas akce"),
                                 'Description': st.column_config.NumberColumn("Popis", help="Textový popis akce")})
    
    col1, spacer, col2 = st.columns([0.3, 0.3, 0.2])
    # Serve merged trades as CSV    
    with col1:
        if (len(trades) > 0):
            trades_csv = snapshot.save_snapshot(trades, actions, positions).encode('utf-8')
            st.download_button('📩 Stáhnout vše v CSV', trades_csv, 'merged_trades.csv', 'text/csv', use_container_width=True, help='Stažením dostanete celý stav výpočtu pro další použití. Stačí příště přetáhnout do importu pro pokračování.')
    # Clear uploaded files
    with col2:
        def clear_uploads():
            st.session_state.pop('file_uploader', None)
            st.session_state.pop('trades', None)
            st.session_state.pop('actions', None)
            st.session_state.pop('positions', None)
        st.button('🧹 Smazat obchody', on_click=lambda: clear_uploads(), use_container_width=True)
    
    return

    # Load data
    daily_rates = load_daily_rates(args.settings_dir)
    yearly_rates = load_yearly_rates(args.settings_dir)

    if args.load_trades is not None:
        trades = pd.read_csv(args.load_trades)
        trades = convert_trade_columns(trades)
        trades.set_index('Hash', inplace=True)
    if args.import_trades_dir is not None:
        trades = import_trades(args.import_trades_dir, trades, args.tickers_dir)
    if args.load_matched_trades is not None:
        sell_buy_pairs = load_buy_sell_pairs(args.load_matched_trades)
    if args.process_years is not None:
        process_years = [int(x) for x in args.process_years.split(',')]
    if args.preserve_years is not None:
        preserve_years = [int(x) for x in args.preserve_years.split(',')]

    # Pair buy and sell orders
    buys, sells, sell_buy_pairs = pair_buy_sell(trades, sell_buy_pairs, args.strategy, process_years, preserve_years)
    paired_sells = sells[sells['Uncovered Quantity'] == 0]
    unpaired_sells = sells[sells['Uncovered Quantity'] != 0]
    paired_buys = buys[buys['Uncovered Quantity'] == 0]
    unpaired_buys = buys[buys['Uncovered Quantity'] != 0]

    # Save unpaired sells to CSV
    sort_columns = ['Symbol', 'Date/Time']
    if args.save_trades:
        trades.drop(['Covered Quantity', 'Uncovered Quantity'], axis=1, inplace=False).sort_values(by=sort_columns).round(3).to_csv(args.save_trades, index=True)
    if args.save_trade_overview_dir:
        sells.round(3).sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/sells.csv', index=False)
        paired_sells.round(3).sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/sells.paired.csv', index=False)
        unpaired_sells.round(3).sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/sells.unpaired.csv', index=False)
        buys.round(3).sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/buys.csv', index=False)
        paired_buys.round(3).sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/buys.paired.csv', index=False)
        unpaired_buys.round(3).sort_values(by=sort_columns).to_csv(args.save_trade_overview_dir + '/buys.unpaired.csv', index=False)
    if args.save_matched_trades:
        sell_buy_pairs.round(3).to_csv(args.save_matched_trades, index=False)
        yearly_pairs = add_czk_conversion(sell_buy_pairs, yearly_rates, True)
        daily_pairs = add_czk_conversion(sell_buy_pairs, daily_rates, False)
        for year in sorted(trades['Year'].unique()):
            for pairs in [yearly_pairs, daily_pairs]:
                filtered_pairs = pairs[(pairs['Sell Time'].dt.year == year)].sort_values(by=['Symbol','Sell Time', 'Buy Time'])
                taxed_pairs = filtered_pairs[filtered_pairs['Taxable'] == 1]
                pairing_type = 'yearly' if pairs is yearly_pairs else 'daily'
                print(f'Pairing for year {year} using {pairing_type} rates in CZK: Proceeds {taxed_pairs["CZK Proceeds"].sum().round(0)}, '
                    f'Cost {taxed_pairs["CZK Cost"].sum().round(0)}, Revenue {taxed_pairs["CZK Revenue"].sum().round(0)}, '
                    f'Untaxed pairs: {len(filtered_pairs) - len(taxed_pairs)}')
                filtered_pairs[filtered_pairs['Sell Time'].dt.year == year].round(3).to_csv(args.save_matched_trades + ".{0}.{1}.csv".format(year, pairing_type), index=False)
            unpaired_sells[unpaired_sells['Year'] == year].round(3).to_csv(args.save_matched_trades + ".{0}.unpaired.csv".format(year), index=False)

if __name__ == "__main__":
    main()
