import streamlit as st

pages = {
    "Input Data": [
        st.Page("input_data_barang.py", title="Data Barang"),
        st.Page("input_data_penjualan.py", title="Data Penjualan"),
    ],
}

pg = st.navigation(pages)
pg.run()