import streamlit as st
import pandas as pd
from datetime import datetime
import database

st.title("➕ Tambah Barang Baru")
 
with st.form("form_tambah_barang"):
    nama_barang_baru = st.text_input("Nama Barang *", placeholder="Contoh: AQUA 600ML")
            
    submit_barang = st.form_submit_button("💾 Simpan Barang", type="primary", use_container_width=True)
            
    if submit_barang:
        if nama_barang_baru.strip() == "":
            st.error("❌ Nama barang tidak boleh kosong!")
        else:
            try:
                conn = database.get_connection()
                cursor = conn.cursor()
                        
                # Cek apakah barang sudah ada
                cursor.execute("SELECT id FROM barang WHERE nama = %s", (nama_barang_baru,))
                existing = cursor.fetchone()
                        
                if existing:
                    st.warning(f"⚠️ Barang '{nama_barang_baru}' sudah ada di database!")
                else:
                    # Insert barang baru
                    query = "INSERT INTO barang (nama, model_prediksi) VALUES (%s, %s)"
                    cursor.execute(query, (nama_barang_baru, "Mean"))
                    conn.commit()
                    st.success(f"✅ Barang '{nama_barang_baru}' berhasil ditambahkan!")
                        
                cursor.close()
                conn.close()
                        
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")