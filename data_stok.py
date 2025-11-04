import streamlit as st
import pandas as pd
from datetime import datetime
import database

st.title("📦 Upload Data Stok")
st.write("Upload file CSV data stok untuk dimasukkan ke database")
    
# Informasi format CSV
with st.expander("ℹ️ Format File CSV"):
    st.write("""
    **Kolom yang diperlukan dalam file CSV:**
    - `No Faktur`: Nomor faktur penjualan
    - `Tgl Faktur`: Tanggal faktur (format: YYYY-MM-DD atau DD/MM/YYYY)
    - `Nama Pelanggan`: Nama pelanggan
    - `Keterangan Barang`: Nama barang (harus sesuai dengan nama di tabel barang)
    - `Kuantitas`: Jumlah barang
    - `Jumlah`: Total harga (opsional)
            
    **Catatan:** Nama barang di CSV harus sudah ada di tabel barang di database!
    """)
        
# Upload file
uploaded_file = st.file_uploader(
    "Pilih file CSV",
    type=['csv'],
    help="Upload file CSV dengan format yang sesuai"
)