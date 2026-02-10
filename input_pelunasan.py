import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(
    page_title="Pelunasan Hutang & Piutang",
    page_icon="🛍️",
    layout="wide"
)

# Header
# st.markdown("""
#     <div style='background-color: #28a745; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
#         <h1 style='color: white; text-align: center; margin: 0;'>
#             📦 KELOLA DATA BARANG
#         </h1>
#     </div>
# """, unsafe_allow_html=True)

st.header("Pelunasan Hutang & Piutang")

tab1, tab2 = st.tabs(["📝 Hutang", "📤 Piutang"])

# ================================================
# TAB 1 : PELUNASAN HUTANG
# ================================================

with tab1:
    st.subheader("➕ Input Pelunasan Hutang")

# ================================================
# TAB 2 : PELUNASAN PIUTANG
# ================================================

with tab2:
    st.subheader("➕ Input Pelunasan Piutang")