import streamlit as st
from streamlit_option_menu import option_menu
import home_page
import data_page

st.title("Program Manajemen Stok")

selected = option_menu(
    menu_title=None,
    options=["Dashboard", "Data"],
    icons=["house", "book"],
    orientation="horizontal",
    # styles={}
)

if selected == "Data":
    data_page.show()
else:
    home_page.show()
