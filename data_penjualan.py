import streamlit as st
import pandas as pd
from datetime import datetime
import database
import prediction

st.set_page_config(page_title="Input Sales", page_icon="📊", layout="wide")

st.title("📊 Upload Data Penjualan")
st.write("Upload file Excel data penjualan untuk dimasukkan ke database")

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
                
        st.subheader("Preview Data")
        st.dataframe(df.head(10))
        st.info(f"Total baris: {len(df)}")

        print(df.applymap(type).head())

        if st.button("📤 Upload", type="primary", use_container_width=True):
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

    
        




st.divider()

st.subheader("📅 Proses Akhir Bulan")

st.markdown("""
### 🎯 Tujuan Proses Ini:
Setelah input laporan penjualan bulanan, klik button di bawah untuk:
1. **Generate Prediksi Official** untuk bulan depan (disimpan di database)
2. **Hitung Safety Stock & Reorder Point** untuk bulan depan
3. **Simpan Rekomendasi Pembelian**

⚠️ **Penting**: Jalankan proses ini SETELAH input semua data penjualan bulan ini!
""")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Status Data")
    latest_penjualan = database.get_latest_penjualan_date()
    st.info(f"Data penjualan terakhir: {latest_penjualan if latest_penjualan else '-'}")

with col2:
    st.subheader("🔮 Prediksi Bulan Depan")
    next_month = (datetime.now().replace(day=1) + pd.DateOffset(months=1)).strftime('%B %Y')
    st.info(f"Akan generate prediksi untuk: **{next_month}**")

st.markdown("---")

if st.button("🚀 Jalankan Proses Akhir Bulan", type="primary", use_container_width=True):
    
    with st.spinner("Memproses..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("1/2: Generate prediksi untuk semua barang...")
        progress_bar.progress(30)
        
        results = prediction.process_end_of_month()
        
        progress_bar.progress(100)
        status_text.text("Selesai!")
        
        st.success("✅ Proses akhir bulan selesai!")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("✅ Prediksi Berhasil", len(results['prediksi_success']))
            st.metric("✅ Rekomendasi Berhasil", len(results['rekomendasi_success']))
        
        with col2:
            st.metric("❌ Prediksi Gagal", len(results['prediksi_failed']))
            st.metric("❌ Rekomendasi Gagal", len(results['rekomendasi_failed']))
        
        if results['prediksi_failed']:
            with st.expander("❌ Detail Error Prediksi"):
                for nama, error in results['prediksi_failed']:
                    st.error(f"**{nama}**: {error}")

        if results['rekomendasi_failed']:
            with st.expander("❌ Detail Error Rekomendasi"):
                for nama, error in results['rekomendasi_failed']:
                    st.error(f"**{nama}**: {error}")