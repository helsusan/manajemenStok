import streamlit as st
from streamlit_option_menu import option_menu
import dashboard
import data

st.title("Program Manajemen Stok")

selected = option_menu(
    menu_title=None,
    options=["Dashboard", "Data"],
    icons=["house", "book"],
    orientation="horizontal",
    # styles={}
)

if selected == "Data":
    data.show()
else:
    dashboard.show()
