import streamlit as st
import database

barang_df = database.get_nama_barang()
# barang_list = barang_df.tolist()
barang = st.selectbox(
    "Pilih jenis barang", 
    barang_df
)

st.header(f"Prediksi Penjualan {barang}")

    