import streamlit as st
import database
import prediction
from datetime import datetime

barang_df = database.get_all_nama_barang()
# barang_list = barang_df.tolist()
barang = st.selectbox(
    "Pilih jenis barang", 
    barang_df
)

# st.header(f"Prediksi Penjualan {barang}")

info_barang = database.get_data_barang(barang)

print(info_barang)