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
    "Upload File Excel (.xlsx)",
    type=['xlsx'],
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
            
            if st.button("📤 Upload Data", type="primary", use_container_width=True):
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
    # Ambil semua tanggal unik yang ada datanya
    available_dates = sorted(all_stok['tanggal'].dt.date.unique().tolist(), reverse=True)
    
    # Filter tanggal dengan calendar
    col1, col2 = st.columns([1, 3])
    with col1:
        # Info untuk user
        # st.caption(f"📅 Ada {len(available_dates)} tanggal dengan data stok")
        
        # Date picker
        filter_date = st.date_input(
            "Pilih Tanggal",
            value=latest_date if latest_date else datetime.now().date(),
            min_value=min(available_dates),
            max_value=max(available_dates),
            help="Hanya tanggal yang memiliki data stok yang bisa dipilih"
        )

        # Selectbox dengan format tanggal yang readable
        # date_options = {date.strftime('%d %b %Y'): date for date in available_dates}
        
        # selected_date_str = st.selectbox(
        #     "Pilih Tanggal",
        #     options=list(date_options.keys()),
        #     index=0,  # Default ke tanggal terbaru (index 0 karena sudah sorted desc)
        #     help="Hanya menampilkan tanggal yang memiliki data stok"
        # )
        
        # filter_date = date_options[selected_date_str]
        
        # Cek apakah tanggal yang dipilih ada datanya
        if filter_date not in available_dates:
            st.warning(f"⚠️ Tidak ada data stok pada {filter_date.strftime('%d %b %Y')}")
            st.info(f"💡 Pilih salah satu dari {len(available_dates)} tanggal yang tersedia")
            filter_date = available_dates[0]  # Default ke tanggal terbaru
    
    # Filter data berdasarkan tanggal yang dipilih
    filtered_stok = all_stok[all_stok['tanggal'].dt.date == filter_date].copy()
    
    if len(filtered_stok) > 0:
        # Format tampilan
        filtered_stok['tanggal'] = filtered_stok['tanggal'].dt.strftime('%d %b %Y')
        
        # Tambahkan kolom ID untuk tracking (hidden nanti)
        # Buat identifier unik: tanggal + id_barang (karena tabel stok pakai composite key)
        # Kita perlu menambahkan kolom id_barang dulu ke query
        
        # Re-query dengan id_barang
        conn = database.get_connection()
        query = """
        SELECT s.tanggal, s.id_barang, b.nama, s.gudang_bjm, s.gudang_sby,
               (s.gudang_bjm + s.gudang_sby) as total_stok
        FROM stok s
        JOIN barang b ON s.id_barang = b.id
        WHERE DATE(s.tanggal) = %s
        ORDER BY b.nama
        """
        filtered_stok = pd.read_sql(query, conn, params=(filter_date,))
        conn.close()
        
        filtered_stok['tanggal'] = pd.to_datetime(filtered_stok['tanggal']).dt.strftime('%d %b %Y')
        
        # Tambahkan kolom checkbox untuk delete
        filtered_stok.insert(0, 'Hapus', False)
        
        # Tampilkan dengan data editor
        edited_stok = st.data_editor(
            filtered_stok,
            use_container_width=True,
            column_config={
                "Hapus": st.column_config.CheckboxColumn(
                    "Pilih",
                    help="Centang untuk menghapus data",
                    default=False
                ),
                "tanggal": st.column_config.TextColumn("Tanggal", disabled=True),
                "id_barang": None,  # Hide
                "nama": st.column_config.TextColumn("Nama Barang", disabled=True),
                "gudang_bjm": st.column_config.NumberColumn("Gudang BJM", format="%d", disabled=True),
                "gudang_sby": st.column_config.NumberColumn("Gudang SBY", format="%d", disabled=True),
                "total_stok": st.column_config.NumberColumn("Total Stok", format="%d", disabled=True)
            },
            hide_index=True,
            key="stok_editor"
        )
        
        # Handle delete
        selected_for_delete = edited_stok[edited_stok['Hapus'] == True]
        
        if len(selected_for_delete) > 0:
            st.warning(f"⚠️ {len(selected_for_delete)} data akan dihapus dari tanggal {filter_date.strftime('%d %b %Y')}")
            
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                    try:
                        conn = database.get_connection()
                        cursor = conn.cursor()
                        
                        deleted_count = 0
                        for idx, row in selected_for_delete.iterrows():
                            # Delete berdasarkan composite key: tanggal + id_barang
                            delete_query = "DELETE FROM stok WHERE DATE(tanggal) = %s AND id_barang = %s"
                            cursor.execute(delete_query, (filter_date, int(row['id_barang'])))
                            deleted_count += 1
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"✅ Berhasil menghapus {deleted_count} data stok!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        st.caption(f"📊 Total: {len(filtered_stok)} barang pada {filter_date.strftime('%d %b %Y')}")
    else:
        st.info(f"💡 Tidak ada data stok pada {filter_date.strftime('%d %b %Y')}")
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
    # st.info("💡 Default: Avg Lead Time = 7 hari, Max Lead Time = 10 hari (jika belum diisi)")
    
    st.markdown("---")
    
    # ===== SECTION BULK UPDATE =====
    st.subheader("🔄 Update Lead Time Massal")
    st.caption("Isi nilai di bawah, lalu centang barang yang ingin diupdate secara bersamaan")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        bulk_avg_lead = st.number_input(
            "Avg Lead Time (hari)",
            min_value=1,
            max_value=365,
            value=7,
            step=1,
            help="Lead time rata-rata untuk semua barang yang dipilih",
            key="bulk_avg"
        )
    
    with col2:
        bulk_max_lead = st.number_input(
            "Max Lead Time (hari)",
            min_value=1,
            max_value=365,
            value=10,
            step=1,
            help="Lead time maksimum untuk semua barang yang dipilih",
            key="bulk_max"
        )
    
    # Validasi bulk input
    if bulk_max_lead < bulk_avg_lead:
        st.error("❌ Max Lead Time tidak boleh lebih kecil dari Avg Lead Time!")
    
    st.markdown("---")
    
    # ===== TABEL DENGAN CHECKBOX =====
    st.subheader("📋 Daftar Barang & Lead Time")
    
    # Tambahkan kolom checkbox
    barang_lead_time.insert(0, 'Pilih', False)
    
    # Buat editable dataframe
    edited_df = st.data_editor(
        barang_lead_time,
        use_container_width=True,
        column_config={
            "Pilih": st.column_config.CheckboxColumn(
                "Pilih",
                help="Centang untuk update massal",
                default=False,
                width="small"
            ),
            # "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
            "id": None,
            "nama": st.column_config.TextColumn("Nama Barang", disabled=True, width="medium"),
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
        num_rows="fixed",
        key="lead_time_editor"
    )
    
    # Validasi: Max harus >= Avg untuk setiap row
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

    
    # Hitung berapa yang dicentang
    selected_items = edited_df[edited_df['Pilih'] == True]
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Tombol update massal
        if len(selected_items) > 0:
            if st.button(
                f"🔄 Update {len(selected_items)} Barang Terpilih", 
                type="secondary",
                use_container_width=True,
                disabled=(len(validation_errors) > 0 or bulk_max_lead < bulk_avg_lead)
            ):
                with st.spinner("Mengupdate lead time massal..."):
                    try:
                        update_count = 0
                        for idx, row in selected_items.iterrows():
                            database.update_lead_time(
                                int(row['id']), 
                                bulk_max_lead,  # Pakai nilai dari input bulk
                                bulk_avg_lead
                            )
                            update_count += 1
                        
                        st.success(f"✅ Berhasil update {update_count} barang dengan Avg={bulk_avg_lead}, Max={bulk_max_lead}!")
                        st.info("💡 Silakan lakukan 'Proses Akhir Bulan' untuk update rekomendasi dengan lead time baru")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        else:
            st.button(
                "🔄 Update Massal", 
                disabled=True,
                use_container_width=True,
                help="Centang barang yang ingin diupdate"
            )
    
    with col2:
        # Tombol save perubahan manual (edit langsung di tabel)
        if st.button(
            "💾 Simpan Perubahan", 
            type="primary",
            use_container_width=True,
            disabled=len(validation_errors) > 0
        ):
            with st.spinner("Menyimpan perubahan..."):
                try:
                    for idx, row in edited_df.iterrows():
                        database.update_lead_time(
                            int(row['id']), 
                            int(row['max_lead_time']),
                            int(row['avg_lead_time'])
                        )
                    
                    st.success("✅ Lead time berhasil diupdate!")
                    st.info("💡 Silakan lakukan 'Proses Akhir Bulan' untuk update rekomendasi dengan lead time baru")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")