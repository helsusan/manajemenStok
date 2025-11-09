import streamlit as st
import database
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import numpy as np

st.set_page_config(page_title="Dashboard Stok", page_icon="📊", layout="wide")

# st.title("📊 Rekomendasi Pembelian")

# ================================================
# HELPER FUNCTIONS - PERHITUNGAN STOK
# ================================================

def calculate_safety_stock_and_reorder(id_barang, lead_time):
    """
    Hitung Safety Stock dan Reorder Point berdasarkan data historis
    
    Returns:
        dict: {
            'avg_daily_usage': float,
            'max_daily_usage': float,
            'safety_stock': float,
            'reorder_point': float
        }
    """
    # Ambil data penjualan 12 bulan terakhir
    penjualan = database.get_all_data_penjualan(id_barang)
    
    if len(penjualan) == 0:
        return None
    
    # Hitung average daily usage (asumsi 30 hari per bulan)
    avg_monthly_sales = penjualan['kuantitas'].mean()
    avg_daily_usage = avg_monthly_sales / 30
    
    # Hitung maximum daily usage (dari bulan tertinggi)
    max_monthly_sales = penjualan['kuantitas'].max()
    max_daily_usage = max_monthly_sales / 30
    
    # Lead time dalam hari
    avg_lead_time = lead_time
    max_lead_time = lead_time * 1.5  # Asumsi worst case 150% dari lead time normal
    
    # Safety Stock = (Max daily usage × Max lead time) - (Avg daily usage × Avg lead time)
    safety_stock = (max_daily_usage * max_lead_time) - (avg_daily_usage * avg_lead_time)
    safety_stock = max(0, safety_stock)  # Tidak boleh negatif
    
    # Reorder Point = (Avg daily usage × Avg lead time) + Safety stock
    reorder_point = (avg_daily_usage * avg_lead_time) + safety_stock
    
    return {
        'avg_daily_usage': avg_daily_usage,
        'max_daily_usage': max_daily_usage,
        'safety_stock': round(safety_stock, 2),
        'reorder_point': round(reorder_point, 2)
    }

def analyze_all_stock():
    """
    Analisis stok untuk semua barang dan update rekomendasi
    """
    # Ambil data barang dengan lead time
    barang_list = database.get_barang_with_lead_time()
    
    # Ambil data stok terbaru
    latest_stok_date = database.get_latest_stok_date()
    
    if not latest_stok_date:
        return {'status': 'error', 'message': 'Belum ada data stok di database'}
    
    stok_latest = database.get_stok_by_date(latest_stok_date)
    
    results = []
    
    for idx, row in barang_list.iterrows():
        id_barang = row['id']
        nama_barang = row['nama']
        lead_time = row['lead_time']
        
        # Hitung safety stock dan reorder point
        calc_result = calculate_safety_stock_and_reorder(id_barang, lead_time)
        
        if calc_result is None:
            continue
        
        # Ambil stok aktual
        stok_row = stok_latest[stok_latest['id'] == id_barang]
        stok_aktual = stok_row['total_stok'].values[0] if len(stok_row) > 0 else 0
        stok_aktual = stok_aktual if not pd.isna(stok_aktual) else 0
        
        # Ambil prediksi bulan depan
        next_month = datetime.now().replace(day=1) + relativedelta(months=1)
        prediksi = database.get_data_prediksi(id_barang, 
                                             next_month.strftime('%Y-%m-%d'),
                                             next_month.strftime('%Y-%m-%d'))
        
        hasil_prediksi = prediksi['kuantitas'].values[0] if len(prediksi) > 0 else 0
        
        # Hitung saran stok
        # Saran stok = Reorder point + Prediksi bulan depan - Stok aktual
        saran_stok = calc_result['reorder_point'] + hasil_prediksi - stok_aktual
        saran_stok = max(0, round(saran_stok, 2))
        
        # Simpan ke database
        database.insert_rekomendasi_stok(
            id_barang=id_barang,
            lead_time=lead_time,
            safety_stock=calc_result['safety_stock'],
            reorder_point=calc_result['reorder_point'],
            stok_aktual=stok_aktual,
            hasil_prediksi=hasil_prediksi,
            saran_stok=saran_stok
        )
        
        results.append({
            'nama': nama_barang,
            'stok_aktual': stok_aktual,
            'reorder_point': calc_result['reorder_point'],
            'need_reorder': stok_aktual <= calc_result['reorder_point']
        })
    
    return {
        'status': 'success',
        'message': f'Analisis selesai untuk {len(results)} barang',
        'results': results
    }

# ================================================
# INFO STATUS DATA
# ================================================

st.header("📅 Status Data Stok Terkini")

col1, col2, col3 = st.columns(3)

# Tanggal stok terakhir
latest_stok_date = database.get_latest_stok_date()
with col1:
    if latest_stok_date:
        st.metric(
            "📦 Data Stok Terakhir",
            latest_stok_date.strftime('%d %b %Y'),
            help="Tanggal data stok paling baru di database"
        )
    else:
        st.metric("📦 Data Stok Terakhir", "-", help="Belum ada data")

# Tanggal rekomendasi terakhir
latest_rekomendasi_date = database.get_latest_rekomendasi_date()
with col2:
    if latest_rekomendasi_date:
        st.metric(
            "🔄 Analisis Terakhir",
            latest_rekomendasi_date.strftime('%d %b %Y'),
            help="Tanggal analisis rekomendasi terakhir"
        )
    else:
        st.metric("🔄 Analisis Terakhir", "-", help="Belum ada analisis")

# Status sinkronisasi
with col3:
    if latest_stok_date and latest_rekomendasi_date:
        if latest_stok_date.date() == latest_rekomendasi_date.date():
            st.success("✅ Data Tersinkron")
        elif latest_stok_date.date() > latest_rekomendasi_date.date():
            st.warning("⚠️ Perlu Update Analisis")
        else:
            st.info("ℹ️ Analisis Lebih Baru")
    else:
        st.info("ℹ️ Belum ada data lengkap")

# ================================================
# BUTTON ANALISIS
# ================================================

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    btn_analyze = st.button(
        "🔄 Analisis Stok Terbaru",
        type="primary",
        use_container_width=True,
        help="Hitung ulang safety stock, reorder point, dan saran pembelian"
    )

if btn_analyze:
    if not latest_stok_date:
        st.error("❌ Belum ada data stok. Silakan input data stok terlebih dahulu.")
    else:
        with st.spinner("Menganalisis data stok..."):
            result = analyze_all_stock()
            
            if result['status'] == 'success':
                st.success(f"✅ {result['message']}")
                
                # Hitung barang yang perlu reorder
                need_reorder_count = sum(1 for r in result['results'] if r['need_reorder'])
                
                if need_reorder_count > 0:
                    st.warning(f"⚠️ {need_reorder_count} barang mencapai reorder point!")
                else:
                    st.info("✅ Semua stok barang masih aman")
                
                st.rerun()
            else:
                st.error(f"❌ {result['message']}")

st.markdown("---")

# ================================================
# TABEL REKOMENDASI PEMBELIAN
# ================================================

st.header("🛒 Rekomendasi Pembelian")

rekomendasi = database.get_rekomendasi_stok()

if len(rekomendasi) > 0:
    # Filter: Hanya barang yang mencapai reorder point
    need_reorder = rekomendasi[rekomendasi['stok_aktual'] <= rekomendasi['reorder_point']].copy()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        show_all = st.checkbox("Tampilkan semua barang", value=False, 
                               help="Centang untuk melihat semua barang, tidak hanya yang perlu reorder")
    
    with col2:
        st.metric("⚠️ Perlu Reorder", len(need_reorder))
    
    # Pilih data yang akan ditampilkan
    display_data = rekomendasi if show_all else need_reorder
    
    if len(display_data) > 0:
        # Format data untuk display
        display_data = display_data.copy()
        display_data['status'] = display_data.apply(
            lambda row: '🔴 REORDER!' if row['stok_aktual'] <= row['reorder_point'] else '✅ Aman',
            axis=1
        )
        
        # Urutkan: yang perlu reorder di atas
        display_data = display_data.sort_values(
            by=['stok_aktual', 'reorder_point'],
            ascending=[True, False]
        )
        
        # Pilih kolom yang akan ditampilkan
        cols_to_show = [
            'status', 'nama', 'stok_aktual', 'reorder_point', 
            'safety_stock', 'hasil_prediksi', 'saran_stok', 'lead_time'
        ]
        
        st.dataframe(
            display_data[cols_to_show],
            use_container_width=True,
            column_config={
                "status": st.column_config.TextColumn("Status", width="small"),
                "nama": st.column_config.TextColumn("Nama Barang", width="medium"),
                "stok_aktual": st.column_config.NumberColumn("Stok Aktual", format="%d"),
                "reorder_point": st.column_config.NumberColumn("Reorder Point", format="%.2f"),
                "safety_stock": st.column_config.NumberColumn("Safety Stock", format="%.2f"),
                "hasil_prediksi": st.column_config.NumberColumn("Prediksi Bulan Depan", format="%.2f"),
                "saran_stok": st.column_config.NumberColumn("Saran Pembelian", format="%.2f", 
                    help="Jumlah yang disarankan untuk dibeli"),
                "lead_time": st.column_config.NumberColumn("Lead Time (hari)", format="%d")
            },
            hide_index=True
        )
        
        # Summary
        if not show_all:
            st.markdown("---")
            st.subheader("📋 Ringkasan Rekomendasi")
            
            total_saran = display_data['saran_stok'].sum()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Barang Perlu Reorder", len(display_data))
            
            with col2:
                st.metric("Total Saran Pembelian", f"{total_saran:,.0f}")
            
            with col3:
                avg_lead_time = display_data['lead_time'].mean()
                st.metric("Rata-rata Lead Time", f"{avg_lead_time:.1f} hari")
    else:
        st.success("✅ Tidak ada barang yang perlu reorder saat ini!")
        st.balloons()

else:
    st.info("💡 Belum ada data rekomendasi. Klik tombol 'Analisis Stok Terbaru' untuk memulai.")

# ================================================
# INFORMASI PERHITUNGAN
# ================================================

# st.markdown("---")
# st.subheader("📖 Informasi Perhitungan")

# with st.expander("🔍 Cara Kerja Perhitungan"):
#     st.markdown("""
#     ### Formula yang Digunakan:
    
#     1. **Average Daily Usage**
#        - Rata-rata penjualan per hari = (Rata-rata penjualan bulanan) / 30
    
#     2. **Safety Stock**
#        ```
#        Safety Stock = (Maximum daily usage × Maximum lead time) 
#                     - (Average daily usage × Average lead time)
#        ```
#        - Maximum lead time diasumsikan 150% dari lead time normal
    
#     3. **Reorder Point**
#        ```
#        Reorder Point = (Average daily usage × Average lead time) + Safety Stock
#        ```
    
#     4. **Saran Pembelian**
#        ```
#        Saran Stok = Reorder Point + Prediksi Bulan Depan - Stok Aktual
#        ```
    
#     ### Status Reorder:
#     - 🔴 **REORDER**: Stok aktual ≤ Reorder point → Perlu segera pesan!
#     - ✅ **Aman**: Stok aktual > Reorder point → Stok masih mencukupi
    
#     ### Catatan:
#     - Data penjualan historis 12 bulan terakhir digunakan untuk perhitungan
#     - Lead time dapat disesuaikan per barang di halaman Data Stok
#     - Analisis perlu di-update setiap ada data stok baru
#     """)

# # Footer
# st.markdown("---")
# st.caption(f"""
# 💡 **Tips:**
# - Lakukan analisis ulang setiap ada update data stok baru
# - Perhatikan barang dengan status 🔴 REORDER untuk segera diorder
# - Sesuaikan Lead Time di halaman Data Stok jika kondisi berubah
# - Saran pembelian sudah memperhitungkan prediksi penjualan bulan depan
# """)

# st.caption(f"🕒 Last viewed: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")