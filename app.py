from menu import menu
import streamlit as st

menu()

st.subheader('Krutopřísný výpočet daní na burze')
st.caption('Postup: Importujte obchody. Zkontrolujte si, zda se dají všechny spárovat a případně doplňte chybějící pozice. Jakmile vše sedí, zobrazte si přehled daní a vyberte nejefektivnější párování. A hurá na daňové přiznání!')
st.divider()
st.caption('Import a párování funguje')
st.caption('Chybí:')
st.caption('* párování vždy ovlivní všechny roky')
st.caption('* nelze manuálně upravit vstupní data')
st.caption('* neimportují se dividendy')
st.caption('* neimportují se korporátní akce')
st.caption('* splity se neukládají do merged csv')
