from menu import menu
import streamlit as st

menu()

st.subheader('Taxlite: optimalizace daní z obchodů burze')
st.markdown('''
Taxlite Vám pomůže optimalizovat daně z obchodů na burze. Aplikace je postavena na principu párování transakcí, kdy se snažíme co nejvíce snížit daňovou povinnost. 
Jelikož zákon nestanovuje, jaké párování transakcí musíte použít, je vzhledem k existenci 3letého daňového testu obvykle výhodnější použít jiné párování než FIFO (jako první se odprodávají nejstarší nákupy),
které ale obvykle je tím, co všichni brokeři i daňový poradci pro jednoduchost uplatní. Taxlite Vám umožní zvolit si mezi mnoha strategiemi párování a ukáže, který je pro Vás daňově nejvýhodnější.
''')
st.caption('''Postup: Importujte obchody. Zkontrolujte si, zda se dají všechny spárovat a případně doplňte chybějící pozice. Jakmile vše sedí, zobrazte si přehled daní a vyberte nejefektivnější párování. 
           Dokázali jsme Vás dostat do ztráty? Hurá odprodat ziskové pozice. Jste v zisku? Taxlite Vám ukáže, které ztrátové pozice odprodat. Jelikož se ztráta nepřenáší mezi roky, je velice důležité
           optimalizovat obchody tak, abyste ji nikdy nemuseli vykázat. Taxlite Vám pomůže toho dosáhnout.
           ''')
st.caption('Aplikace nyní podporuje pouze importy z :blue[Interactive Brokers].')
st.caption('Pro Vaše bezpečí Taxlite :blue[neukládá žádné informace] o Vašich obchodech na server, vše je ukládáno pouze do Vašeho prohlížeče. Vývojáři ani nikdo jiný je neuvidí. '
            'Celý interní stav aplikace si můžete kdykoliv stáhnout tlačítkem :red[Stáhnout vše v CSV] a uchovat na svém počítači, jelikož po zavření stránky nebo smazání session bude interní stav ztracen.\n')
st.caption('Kód aplikace je open-source a můžete si tato tvrzení kdykoliv ověřit kliknutím na odkaz na GitHub v záhlaví aplikace. Také si můžete stáhnout celý kód a spustit si Taxlite na svém počítači.\n')
st.page_link("pages/1_import_trades.py", label="📥 Nyní hurá na import obchodů")