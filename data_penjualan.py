import streamlit as st
import pandas as pd
from datetime import datetime
import database
import prediction

st.set_page_config(page_title="Data Penjualan", page_icon="📊", layout="wide")

st.title("📥 Input Data Penjualan")
# st.write("Upload file Excel data penjualan untuk dimasukkan ke database")

with st.expander("ℹ️ Format File Excel"):
    st.write("""
    - Kolom: `No Faktur`, `Tgl Faktur`, `Nama Pelanggan`, `Keterangan Barang`, `Kuantitas`, `Jumlah`
    - Nama Barang harus sudah ada di database
    """)
    
uploaded_file = st.file_uploader(
    "Upload File Excel (.xlsx)",
    type=['xlsx'],
    help="Upload file Excel dengan format yang sesuai"
)
        
if uploaded_file is not None:
    try:
        df_raw = pd.read_excel(uploaded_file, header=None)

        EXPECTED_COLS = ["Tgl Faktur", "No. Faktur", "Nama Pelanggan", "Keterangan Barang", "Kuantitas", "Jumlah"]

        header_row_index = None

        for i, row in df_raw.iterrows():
            row_str = row.astype(str).str.upper()
            if all(any(col.upper() in cell for cell in row_str) for col in EXPECTED_COLS):
                header_row_index = i
                break

        df = pd.read_excel(uploaded_file, header=header_row_index)

        df = df.dropna(how="all")
        df = df[EXPECTED_COLS]
        df = database.clean_excel_apostrophe(df)

        st.success("✅ Data berhasil dibersihkan!")
                
        st.subheader("📋 Preview Data")
        st.dataframe(df.head(10))
        st.info(f"Total baris: {len(df)}")

        print(df.applymap(type).head())

        if st.button("📤 Upload Data", type="primary", use_container_width=True):
            with st.spinner("Mengupload data ke database..."):
                success_count, error_count, errors = database.insert_data_penjualan(df)
                        
            if success_count > 0:
                st.success(f"✅ Berhasil mengupload {success_count} baris data!")
                        
            if error_count > 0:
                st.warning(f"⚠️ {error_count} baris gagal diupload")
                            
                with st.expander("Lihat detail error"):
                    for error in errors[:20]:
                        st.error(error)
                                
                    if len(errors) > 20:
                        st.info(f"... dan {len(errors) - 20} error lainnya")
                        
    except Exception as e:
        st.error(f"❌ Error membaca file: {str(e)}")
        st.info("Pastikan file Excel Anda memiliki format yang benar")

    
        




st.divider()
    
st.header("🔍 Data Penjualan")
# st.caption("Data pada tabel ditampilkan dari tanggal terbaru")

# Filter tanggal
col1, col2 = st.columns([1, 3])

with col1:
    # Ambil semua tanggal unik dari data penjualan
    all_dates_query = "SELECT DISTINCT DATE(tgl_faktur) as tanggal FROM penjualan ORDER BY tanggal DESC"
    all_dates_result = database.run_query(all_dates_query)
    
    if all_dates_result:
        available_dates = [datetime.strptime(str(row['tanggal']), '%Y-%m-%d').date() for row in all_dates_result]
        
        # Date input dengan calendar
        selected_date = st.date_input(
            "Filter Tanggal",
            value=None,
            help="Pilih tanggal untuk filter data penjualan (kosongkan untuk tampilkan semua)"
        )
    else:
        selected_date = None
        st.info("Belum ada data penjualan")

# Query data penjualan
try:
    if selected_date:
        # Filter berdasarkan tanggal
        query = """
        SELECT 
            p.id,
            p.no_faktur AS 'No Faktur',
            p.tgl_faktur AS 'Tgl Faktur',
            p.nama_pelanggan AS 'Nama Pelanggan',
            b.nama AS 'Nama Barang',
            p.kuantitas AS 'Kuantitas',
            p.jumlah AS 'Jumlah' 
        FROM penjualan p
        JOIN barang b ON p.id_barang = b.id
        WHERE DATE(p.tgl_faktur) = %s
        ORDER BY p.tgl_faktur DESC
        """
        conn = database.get_connection()
        df_penjualan = pd.read_sql(query, conn, params=(selected_date,))
        conn.close()
    else:
        # Tampilkan semua data
        results = database.run_query("""
            SELECT 
                p.id,
                p.no_faktur AS 'No Faktur',
                p.tgl_faktur AS 'Tgl Faktur',
                p.nama_pelanggan AS 'Nama Pelanggan',
                b.nama AS 'Nama Barang',
                p.kuantitas AS 'Kuantitas',
                p.jumlah AS 'Jumlah' 
            FROM penjualan p
            JOIN barang b ON p.id_barang = b.id
            ORDER BY p.tgl_faktur DESC
        """)
        df_penjualan = pd.DataFrame(results) if results else pd.DataFrame()
    
    if not df_penjualan.empty:
        # FORMAT TANGGAL → 24 Nov 2025
        df_penjualan['Tgl Faktur'] = pd.to_datetime(df_penjualan['Tgl Faktur']).dt.strftime('%d %b %Y')
        
        # Tambahkan kolom select untuk delete
        df_penjualan.insert(0, 'Hapus', False)
        
        # Tampilkan dengan data_editor
        edited_df = st.data_editor(
            df_penjualan,
            use_container_width=True,
            column_config={
                "Hapus": st.column_config.CheckboxColumn(
                    "Pilih",
                    help="Centang untuk menghapus data",
                    default=False
                ),
                "id": None,  # Hide ID column
                "Tgl Faktur": st.column_config.TextColumn("Tgl Faktur"),
                "Nama Barang": st.column_config.TextColumn("Nama Barang")
            },
            disabled=["No Faktur", "Tgl Faktur", "Nama Pelanggan", "Nama Barang", "Kuantitas", "Jumlah"],
            hide_index=True,
            key="penjualan_editor"
        )
        
        # Tombol delete
        selected_for_delete = edited_df[edited_df['Hapus'] == True]
        
        if len(selected_for_delete) > 0:
            st.warning(f"⚠️ {len(selected_for_delete)} data akan dihapus")
            
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                    try:
                        conn = database.get_connection()
                        cursor = conn.cursor()
                        
                        deleted_count = 0
                        for idx, row in selected_for_delete.iterrows():
                            delete_query = "DELETE FROM penjualan WHERE id = %s"
                            cursor.execute(delete_query, (int(row['id']),))
                            deleted_count += 1
                        
                        conn.commit()
                        cursor.close()
                        conn.close()
                        
                        st.success(f"✅ Berhasil menghapus {deleted_count} data!")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        # Info jumlah data
        st.caption(f"📊 Total: {len(df_penjualan)} data")
    else:
        st.warning("Tidak ada data penjualan" + (f" pada tanggal {selected_date}" if selected_date else ""))
        
except Exception as e:
    st.error(f"Error: {str(e)}")
    
        




# st.divider()

# st.header("📅 Proses Akhir Bulan")

# with st.expander("ℹ️ Tujuan Proses"):
#     st.write("""
#     Proses ini akan melakukan:
#     - Generate prediksi untuk bulan depan
#     - Hitung safety stock & reorder point untuk bulan depan
             
#     ⚠️ **Penting**: Jalankan proses ini SETELAH input semua data penjualan bulan ini!
#     """)
    
# # st.markdown("---")

# col1, col2 = st.columns(2)

# with col1:
#     latest_penjualan = database.get_latest_penjualan_date()
#     st.caption(f"📍**Data penjualan terakhir:** {latest_penjualan if latest_penjualan else '-'}")

# with col2:
#     next_month = (datetime.now().replace(day=1) + pd.DateOffset(months=1)).strftime('%B %Y')
#     st.caption(f"🔮 **Prediksi untuk bulan**: {next_month}")

# # st.markdown("---")

# if st.button("Jalankan Proses Akhir Bulan", type="primary", use_container_width=True):
    
#     with st.spinner("Memproses..."):
#         progress_bar = st.progress(0)
#         status_text = st.empty()
        
#         status_text.text("1/2: Generate prediksi untuk semua barang...")
#         progress_bar.progress(30)
        
#         results = prediction.process_end_of_month()
        
#         progress_bar.progress(100)
#         status_text.text("Selesai!")
        
#         st.success("✅ Proses akhir bulan selesai!")
        
#         col1, col2 = st.columns(2)
        
#         with col1:
#             st.metric("✅ Prediksi Berhasil", len(results['prediksi_success']))
#             st.metric("✅ Rekomendasi Berhasil", len(results['rekomendasi_success']))
        
#         with col2:
#             st.metric("❌ Prediksi Gagal", len(results['prediksi_failed']))
#             st.metric("❌ Rekomendasi Gagal", len(results['rekomendasi_failed']))
        
#         if results['prediksi_failed']:
#             with st.expander("❌ Detail Error Prediksi"):
#                 for nama, error in results['prediksi_failed']:
#                     st.error(f"**{nama}**: {error}")

#         if results['rekomendasi_failed']:
#             with st.expander("❌ Detail Error Rekomendasi"):
#                 for nama, error in results['rekomendasi_failed']:
#                     st.error(f"**{nama}**: {error}")