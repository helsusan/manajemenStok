import streamlit as st
import pandas as pd
from datetime import datetime
import database
import prediction

st.set_page_config(page_title="Proses Bulanan", page_icon="📅", layout="wide")

st.header("📅 Proses Bulanan")
st.info("⚠️ **Penting**: Selalu jalankan proses ini SETELAH input data penjualan")

with st.expander("ℹ️ Tujuan Proses"):
    st.write("""
    Proses ini akan melakukan:
    - Generate prediksi untuk bulan depan
    - Hitung safety stock & reorder point untuk bulan depan
    """)
    
# st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    latest_penjualan = database.get_latest_penjualan_date()
    # Format tanggal jika ada data
    if latest_penjualan:
        latest_penjualan_str = latest_penjualan.strftime('%d %b %Y')
    else:
        latest_penjualan_str = '-'
    
    st.caption(f"📍**Data penjualan terakhir:** {latest_penjualan_str}")

with col2:
    next_month = (datetime.now().replace(day=1) + pd.DateOffset(months=1)).strftime('%B %Y')
    st.caption(f"🔮 **Prediksi untuk bulan**: {next_month}")

# st.markdown("---")

if st.button("Jalankan Proses Akhir Bulan", type="primary", use_container_width=True):
    
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