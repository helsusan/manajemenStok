import streamlit as st
import database
import pandas as pd
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Data Stok", page_icon="📦", layout="wide")

# ================================================
# SECTION 1: INPUT DATA STOK
# ================================================

st.title("📥 Input Data Stok")

col1, col2 = st.columns([2, 1])

with col1:
    with st.expander("ℹ️ Format File Excel"):
        st.write("""
        - Data yang di-input merupakan data stok harian
        - Kolom: `Nama Barang`, `Gudang BJM`, `Gudang SBY`
        - Nama Barang harus sudah ada di database
        """)

with col2:
    tanggal_stok = st.date_input(
        "Tanggal Stok",
        value=datetime.now(),
        help="Pilih tanggal untuk data stok ini"
    )

uploaded_file = st.file_uploader(
    "Upload File Excel (.xlsx, .xls)",
    type=['xlsx', 'xls'],
    help="Upload file Excel dengan format yang sudah ditentukan"
)

if uploaded_file is not None:
    try:
        # Read Excel
        df = pd.read_excel(uploaded_file)
        
        # Validasi kolom
        required_cols = ['Deskripsi Barang', 'BANJARMASIN', 'CENTRE']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            st.error(f"❌ Kolom yang hilang: {', '.join(missing_cols)}")
        else:
            st.success("✅ File berhasil dibaca!")
            
            # Preview data
            st.subheader("📋 Preview Data")
            st.dataframe(df, use_container_width=True)
            
            # Tombol submit
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("💾 Simpan ke Database", type="primary", use_container_width=True):
                    with st.spinner("Menyimpan data..."):
                        success, error, messages = database.insert_data_stok(df, tanggal_stok)
                        
                        if success > 0:
                            st.success(f"✅ Berhasil menyimpan {success} data stok!")
                            
                            # Trigger auto-update rekomendasi stok
                            st.info("💡 Jangan lupa update analisis stok di Dashboard Stok!")
                        else:
                            st.error(f"❌ Gagal menyimpan data")
                            for msg in messages:
                                st.error(msg)
            
            with col2:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.rerun()
    
    except Exception as e:
        st.error(f"❌ Error membaca file: {str(e)}")

st.markdown("---")

# ================================================
# SECTION 2: LIHAT DATA STOK
# ================================================

st.header("🔍 Data Stok")

# Info tanggal terbaru
latest_date = database.get_latest_stok_date()
if latest_date:
    st.info(f"📅 Data stok terakhir: **{latest_date.strftime('%d %B %Y')}**")
else:
    st.warning("⚠️ Belum ada data stok di database")

# Ambil semua data stok
all_stok = database.get_all_data_stok()

if len(all_stok) > 0:
    # Filter tanggal
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_date = st.selectbox(
            "Filter Tanggal",
            options=['Semua'] + sorted(all_stok['tanggal'].dt.date.unique().tolist(), reverse=True),
            help="Pilih tanggal untuk filter data"
        )
    
    # Filter data
    if filter_date != 'Semua':
        filtered_stok = all_stok[all_stok['tanggal'].dt.date == filter_date].copy()
    else:
        filtered_stok = all_stok.copy()
    
    # Format tampilan
    filtered_stok['tanggal'] = filtered_stok['tanggal'].dt.strftime('%d %b %Y')
    
    st.dataframe(
        filtered_stok,
        use_container_width=True,
        column_config={
            "tanggal": "Tanggal",
            "nama": "Nama Barang",
            "gudang_bjm": st.column_config.NumberColumn("Gudang BJM", format="%d"),
            "gudang_sby": st.column_config.NumberColumn("Gudang SBY", format="%d"),
            "total_stok": st.column_config.NumberColumn("Total Stok", format="%d")
        },
        hide_index=True
    )
else:
    st.info("💡 Belum ada data stok. Upload file Excel untuk menambahkan data.")

st.markdown("---")

# ================================================
# SECTION 3: KELOLA LEAD TIME
# ================================================

st.header("⏱️ Lead Time")

st.markdown("""
**Lead Time** adalah jeda waktu dari pemesanan produk ke supplier sampai barang tiba di Gudang Banjarmasin.
""")

# Ambil data barang dengan lead time
barang_lead_time = database.get_barang_with_lead_time()

if len(barang_lead_time) > 0:   
    # Info default
    st.info("💡 Default: Avg Lead Time = 7 hari, Max Lead Time = 10 hari (jika belum diisi)")
    
    # Buat editable dataframe
    edited_df = st.data_editor(
        barang_lead_time,
        use_container_width=True,
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "nama": st.column_config.TextColumn("Nama Barang", disabled=True),
            "avg_lead_time": st.column_config.NumberColumn(
                "⏱️ Avg Lead Time (hari)",
                min_value=1,
                max_value=365,
                step=1,
                help="Lead time rata-rata dalam kondisi normal"
            ),
            "max_lead_time": st.column_config.NumberColumn(
                "⏱️ Max Lead Time (hari)",
                min_value=1,
                max_value=365,
                step=1,
                help="Lead time maksimum (worst case scenario)"
            )
        },
        hide_index=True,
        num_rows="fixed"
    )
    
    # Validasi: Max harus >= Avg    
    validation_errors = []
    for idx, row in edited_df.iterrows():
        if row['max_lead_time'] < row['avg_lead_time']:
            validation_errors.append(
                f"❌ **{row['nama']}**: Max Lead Time ({row['max_lead_time']}) tidak boleh lebih kecil dari Avg Lead Time ({row['avg_lead_time']})"
            )
    
    if validation_errors:
        st.error("**Error Validasi:**")
        for error in validation_errors:
            st.error(error)
        st.warning("⚠️ Perbaiki error di atas sebelum menyimpan!")
    else:
        st.success("✅ Semua data valid!")
    
    # Tombol save
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("💾 Simpan Perubahan Lead Time", 
                     type="primary", 
                     use_container_width=True,
                     disabled=len(validation_errors) > 0):
            with st.spinner("Menyimpan perubahan..."):
                try:
                    for idx, row in edited_df.iterrows():
                        database.update_lead_time(
                            row['id'], 
                            row['max_lead_time'],
                            row['avg_lead_time']
                        )
                    
                    st.success("✅ Lead time berhasil diupdate!")
                    st.info("💡 Silakan lakukan 'Proses Akhir Bulan' untuk update rekomendasi dengan lead time baru")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
