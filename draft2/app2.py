import streamlit as st

pages = {
    "Manajemen Stok": [
        st.Page("home_page2.py", title="Prediksi Penjualan"),
    ],
    "Input Data": [
        st.Page("data_page.py", title="Data Penjualan"),
    ],
}

pg = st.navigation(pages)
pg.run()