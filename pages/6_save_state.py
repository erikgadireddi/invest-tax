import pandas as pd
import streamlit as st
import matchmaker.data as data 
import matchmaker.snapshot as snapshot
from menu import menu

st.set_page_config(page_title='Uložení stavu', layout='centered', page_icon='💾')
menu()

data.load_settings()

state = data.State()
state.load_session()

if state.trades.empty:
    st.caption('Nebyly importovány žádné obchody.')
    st.page_link("pages/1_import_trades.py", label="📥 Přejít na import obchodů")
else:
    st.caption(str(len(state.trades)) + ' transakcí k dispozici.')

    trades_csv = snapshot.save_snapshot(state).encode('utf-8')
    st.download_button('📩 Stáhnout vše v CSV', trades_csv, 'taxlite_state.csv', 'text/csv', use_container_width=True, help='Stažením dostanete celý stav výpočtu pro další použití. Stačí příště přetáhnout do importu pro pokračování.')
    st.markdown("""
    Taxlite neukládá žádná Vaše data na server, ani Vás nežádá o vytvoření účtu. Ochrana Vašeho soukromí je na prvním místě. Jelikož data
    zůstávají pouze ve Vašem prohlížeči, je důležité si je pravidelně ukládat, abyste nepřišli o rozpracované obchody.
    
    ### Jak omylem nepřijít o data
    1. **Neobnovujte manuálně stránku** v prohlížeči, jelikož to vymaže veškerý rozpracovaný stav.
    2. Ukládejte si stav po větších změnách, ať se můžete kdykoliv vrátit k předchozímu kroku.
    3. Jakmile jste skončili s aktivním používáním, uložte si rozpracovaná data. Neaktivita v desítkách minut může způsobit odpojení.
    ### Jak ukládat a nahrávat rozpracovaná data
    1. Pravidelně zálohujte. Klikněte na tlačítko **"📩 Stáhnout vše v CSV"** a uložte soubor `taxlite_state.csv` do vašeho počítače.
    2. Při příštím spuštění aplikace přejděte na stránku **"Import obchodů"**.
    3. Nahrajte uložený soubor `taxlite_state.csv` zpět do aplikace pomocí importního formuláře.
    4. Aplikace načte uložený stav a můžete pokračovat tam, kde jste skončili.

    """)