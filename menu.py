import streamlit as st


def unauthenticated_menu():
    # Show a navigation menu for unauthenticated users
    st.sidebar.page_link("app.py", label="Popis")
    st.sidebar.page_link("pages/1_import_trades.py", label="Import obchodů")
    st.sidebar.page_link("pages/2_overview.py", label="Korekce / doplnění obchodů")
    st.sidebar.page_link("pages/3_symbols.py", label="Přehled podle symbolů")
    st.sidebar.page_link("pages/4_pairing.py", label="Daňový přehled")

def menu():
    # Determine if a user is logged in or not, then show the correct
    # navigation menu
    if "role" not in st.session_state or st.session_state.role is None:
        unauthenticated_menu()
        return

def menu_with_redirect():
    # Redirect users to the main page if not logged in, otherwise continue to
    # render the navigation menu
    if "role" not in st.session_state or st.session_state.role is None:
        st.switch_page("app.py")
    menu()