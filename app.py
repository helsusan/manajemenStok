import streamlit as st

pages = {
    "Dashboard": [
        st.Page("proses_bulanan.py", title="Proses Akhir Bulan"),
        st.Page("dashboard_sales.py", title="Prediksi Penjualan"),
        st.Page("dashboard_stock.py", title="Manajemen Stok"),
    ],
    "Input Data": [
        st.Page("data_penjualan.py", title="Data Penjualan"),
        st.Page("data_stok.py", title="Data Stok"),
        st.Page("data_barang.py", title="Data Barang"),
    ],
}

pg = st.navigation(pages)
pg.run()