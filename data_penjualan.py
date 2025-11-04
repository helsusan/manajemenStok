import streamlit as st
import pandas as pd
from datetime import datetime
import database

st.title("📊 Upload Data Penjualan")
st.write("Upload file CSV data penjualan untuk dimasukkan ke database")
    
# Informasi format CSV
with st.expander("ℹ️ Format File CSV"):
    st.write("""
    Kolom yang diperlukan dalam file CSV:
    - No Faktur
    - Tgl Faktur
    - Nama Pelanggan
    - Keterangan Barang
    - Kuantitas
    - Jumlah
            
    **Catatan:** Nama barang di CSV harus sudah ada di tabel barang di database!
    """)
        
# Upload file
uploaded_file = st.file_uploader(
    "Pilih file CSV",
    type=['csv'],
    help="Upload file CSV dengan format yang sesuai"
)
        
if uploaded_file is not None:
    try:
        # Baca CSV
        df = pd.read_csv(uploaded_file)
                
        st.subheader("Preview Data")
        st.dataframe(df.head(10))
        st.info(f"Total baris: {len(df)}")
                
        # Tombol untuk upload
        if st.button("📤 Upload", type="primary", use_container_width=True):
            with st.spinner("Mengupload data ke database..."):
                success_count, error_count, errors = database.insert_data_penjualan(df)
                        
            # Tampilkan hasil
            if success_count > 0:
                st.success(f"✅ Berhasil mengupload {success_count} baris data!")
                        
            if error_count > 0:
                st.warning(f"⚠️ {error_count} baris gagal diupload")
                            
                with st.expander("Lihat detail error"):
                    for error in errors[:20]:  # Tampilkan maksimal 20 error pertama
                        st.error(error)
                                
                    if len(errors) > 20:
                        st.info(f"... dan {len(errors) - 20} error lainnya")
                        
    except Exception as e:
        st.error(f"❌ Error membaca file: {str(e)}")
        st.info("Pastikan file CSV Anda memiliki format yang benar")

    
        



# Divider
st.divider()
    
# Section untuk melihat data barang yang tersedia
st.subheader("🔍 Data Penjualan")
st.write("ℹ️ Data pada tabel ditampilkan dari tanggal terbaru")
    
if st.button("Tampilkan Data Penjualan"):
    try:
        results = database.run_query("""SELECT no_faktur AS 'No Faktur',
                                     tgl_faktur AS 'Tgl Faktur',
                                     nama_pelanggan AS 'Nama Pelanggan',
                                     id_barang AS 'Keterangan Barang',
                                     kuantitas AS 'Kuantitas',
                                     jumlah AS 'Jumlah' FROM penjualan ORDER BY tgl_faktur DESC""")
            
        if results:
            df_penjualan = pd.DataFrame(results)
            st.dataframe(df_penjualan, use_container_width=True)
        else:
            st.warning("Tidak ada data penjualan di database")
                
    except Exception as e:
        st.error(f"Error: {str(e)}")