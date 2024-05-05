from menu import menu
import streamlit as st

menu()

st.subheader('Krutopřísný výpočet daní na burze')
st.caption('Postup: Importujte obchody. Zkontrolujte si, zda se dají všechny spárovat a případně doplňte chybějící pozice. Jakmile vše sedí, zobrazte si přehled daní a vyberte nejefektivnější párování. A hurá na daňové přiznání!')
st.caption('Aplikace nyní podporuje pouze importy z :blue[Interactive Brokers]. Pro započetí stačí přetáhnout myší vyexportované Activity Statements, z kterého si Taxlite načte Vaše transakce a korporátní akce.'
            'Nejjednodušší cesta k exportu je skrz Statements->Activity Statements, vybrat Yearly (roční) a postupně vyexportovat všechny roky. Není ale problém, i kdyby se exporty časově překrývaly.\n')
            
st.caption('Pro Vaše bezpečí Taxlite :blue[neukládá žádné informace] o Vašich obchodech na server, vše je ukládáno pouze do Vašeho prohlížeče. Vývojáři ani nikdo jiný je neuvidí. '
            'Celý interní stav aplikace si můžete kdykoliv stáhnout tlačítkem :red[Stáhnout vše v CSV] a uchovat na svém počítači, jelikož po zavření stránky nebo smazání session bude interní stav ztracen.\n')
st.caption('Kód aplikace je open-source a můžete si tato tvrzení kdykoliv ověřit kliknutím na odkaz na GitHub v záhlaví aplikace. Také si můžete stáhnout celý kód a spustit si Taxlite na svém počítači.\n')
st.page_link("pages/1_import_trades.py", label="📥 Nyní hurá na import obchodů")
st.divider()
st.caption('Chybí:')
st.caption('* neimportují se dividendy')
st.caption('* neimportují se korporátní akce')