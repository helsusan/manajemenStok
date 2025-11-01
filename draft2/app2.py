import streamlit as st

pages = {
    "Manajemen Stok": [
        st.Page("home_page2.py", title="Prediksi Penjualan"),
    ],
    "Input Data": [
        st.Page("data_penjualan.py", title="Data Penjualan"),
        st.Page("data_stok.py", title="Data Stok"),
        st.Page("data_barang.py", title="Data Barang"),
    ],
}

pg = st.navigation(pages)
pg.run()