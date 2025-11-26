import streamlit as st
import database
import pandas as pd
from datetime import datetime, timedelta
import calendar

st.set_page_config(page_title="Dashboard Stok", page_icon="📊", layout="wide")

# ================================================
# STATUS DATA
# ================================================

st.header("📅 Status Data Terkini")

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
            "🔄 Update Rekomendasi",
            latest_rekomendasi_date.strftime('%d %b %Y'),
            help="Tanggal update rekomendasi terakhir (dari Proses Akhir Bulan)"
        )
    else:
        st.metric("🔄 Update Rekomendasi", "-", help="Belum ada rekomendasi")

# Status hari ini
today = datetime.now().date()
with col3:
    if latest_stok_date:
        if hasattr(latest_stok_date, 'date'):
            latest_stok_date_only = latest_stok_date.date()
        else:
            latest_stok_date_only = latest_stok_date
            
        if latest_stok_date_only == today:
            st.success("✅ Stok Hari Ini Ada")
        else:
            st.warning("⚠️ Belum Input Stok Hari Ini")
    else:
        st.error("❌ Belum Ada Data Stok")

# ================================================
# PENGECEKAN STOK HARIAN (UPDATED WITH GUDANG INFO)
# ================================================

st.markdown("---")
st.header("🔍 Pengecekan Stok Harian")

btn_check_stock = st.button(
    "Jalankan Pengecekan Stok Harian",
    type="primary",
    use_container_width=True,
    help="Bandingkan stok aktual hari ini dengan reorder point"
)

if btn_check_stock:
    with st.spinner("🔄 Mengecek stok..."):
        check_stok = database.check_data_stok_hari_ini()
        
        # PERUBAHAN: Load data rekomendasi
        rekomendasi = database.get_rekomendasi_stok()
        
        if len(rekomendasi) == 0:
            st.error("❌ Belum ada data rekomendasi. Jalankan Proses Akhir Bulan terlebih dahulu.")
        else:
            # PERUBAHAN 2: Cek apakah perlu update saran_stok
            need_update = False
            
            # Ambil tanggal stok terakhir & tanggal rekomendasi terakhir
            latest_stok = database.get_latest_stok_date()
            latest_rekomendasi = database.get_latest_rekomendasi_date()
            
            # Convert ke date untuk perbandingan
            if latest_stok and hasattr(latest_stok, 'date'):
                latest_stok_date = latest_stok.date()
            elif latest_stok:
                latest_stok_date = latest_stok
            else:
                latest_stok_date = None
            
            if latest_rekomendasi and hasattr(latest_rekomendasi, 'date'):
                latest_rekomendasi_date = latest_rekomendasi.date()
            elif latest_rekomendasi:
                latest_rekomendasi_date = latest_rekomendasi
            else:
                latest_rekomendasi_date = None
            
            # PERUBAHAN 3: Cek apakah tanggal berbeda
            if latest_stok_date and latest_rekomendasi_date:
                if latest_stok_date != latest_rekomendasi_date:
                    need_update = True
                    st.info(f"🔄 Mendeteksi data stok baru ({latest_stok_date}), menghitung ulang saran stok...")
            
            # PERUBAHAN 4: Update saran_stok jika perlu
            if need_update:
                with st.spinner("📊 Menghitung ulang saran stok..."):
                    # Ambil data stok terbaru (hanya BJM)
                    stok_data = database.get_stok_by_date(latest_stok_date)
                    
                    # Loop untuk update setiap barang
                    update_count = 0
                    for idx, row in rekomendasi.iterrows():
                        id_barang = row['id_barang']
                        reorder_point = row['reorder_point']
                        hasil_prediksi = row['hasil_prediksi']
                        
                        # Ambil stok BJM dari data stok terbaru
                        stok_row = stok_data[stok_data['id'] == id_barang]
                        if len(stok_row) > 0:
                            stok_bjm = stok_row['gudang_bjm'].values[0]
                            stok_bjm = stok_bjm if not pd.isna(stok_bjm) else 0
                        else:
                            stok_bjm = 0
                        
                        # PERUBAHAN 5: Hitung saran stok dalam bentuk HARIAN
                        # Formula: (Reorder Point + Prediksi Bulanan/30) - Stok BJM
                        next_month = datetime.now().replace(day=1) + timedelta(days=32)
                        next_month = next_month.replace(day=1)
                        days_in_next_month = calendar.monthrange(next_month.year, next_month.month)[1]

                        avg_daily_usage = hasil_prediksi / days_in_next_month
                        saran_stok_harian = reorder_point + avg_daily_usage - stok_bjm
                        saran_stok_harian = max(0, round(saran_stok_harian, 2))
                        
                        # Update ke database
                        database.update_saran_stok(
                            id_barang=id_barang,
                            stok_bjm=stok_bjm,
                            saran_stok=saran_stok_harian,
                            tgl_update=latest_stok_date
                        )
                        
                        update_count += 1
                    
                    st.success(f"✅ Berhasil update saran stok untuk {update_count} barang!")
                    
                    # Reload data setelah update
                    rekomendasi = database.get_rekomendasi_stok()
            
            # PERUBAHAN 6: Ambil data stok untuk display (BJM & SBY)
            if latest_stok_date:
                stok_display = database.get_stok_by_date(latest_stok_date)
                
                # Merge dengan rekomendasi
                merged = pd.merge(
                    rekomendasi,
                    stok_display[['id', 'gudang_bjm', 'gudang_sby']],
                    left_on='id_barang',
                    right_on='id',
                    how='left'
                )
            else:
                # Kalau tidak ada data stok, tetap tampilkan tapi tanpa info gudang
                merged = rekomendasi.copy()
                merged['gudang_bjm'] = 0
                merged['gudang_sby'] = 0
            
            # PERUBAHAN 7: Tambahkan status berdasarkan BJM vs Reorder Point
            def get_status(row):
                bjm = row['gudang_bjm'] if not pd.isna(row['gudang_bjm']) else 0
                sby = row['gudang_sby'] if not pd.isna(row['gudang_sby']) else 0
                rop = row['reorder_point']
                safety = row['safety_stock']
                saran_stok = row['saran_stok'] if not pd.isna(row['saran_stok']) else 0
                
                if bjm <= rop:
                    if sby >= saran_stok:
                        return '⚠️ TRANSFER'
                    else:
                        return '🔴 REORDER'
                else:
                    return '✅ AMAN'
            
            merged['status'] = merged.apply(get_status, axis=1)
            
            # Sort: yang kritis di atas
            merged = merged.sort_values(['status', 'gudang_bjm'])
            
            st.success("✅ Pengecekan selesai!")
            
            # Summary
            st.markdown("---")
            st.subheader("📋 Hasil Pengecekan")
            
            # Hitung summary
            kritis = len(merged[merged['status'] == '🔴 REORDER'])
            perlu_reorder = len(merged[merged['status'] == '⚠️ TRANSFER'])
            aman = len(merged[merged['status'] == '✅ AMAN'])
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Barang", len(merged))
            
            with col2:
                st.metric("🔴 Reorder", kritis)
            
            with col3:
                st.metric("⚠️ Transfer", perlu_reorder)
            
            with col4:
                st.metric("✅ Aman", aman)
            
            st.markdown("---")
            
            # PERUBAHAN 8: Tabel menampilkan SEMUA barang
            st.subheader("📊 Status Stok Semua Barang")
            
            # Kolom yang ditampilkan
            display_cols = [
                'status', 'nama', 
                'gudang_bjm', 'gudang_sby',
                'reorder_point', 'safety_stock', 
                'hasil_prediksi', 'saran_stok'
            ]
            
            st.dataframe(
                merged[display_cols],
                use_container_width=True,
                column_config={
                    "status": st.column_config.TextColumn(
                        "Status",
                        help="Status berdasarkan BJM vs Reorder Point"
                    ),
                    "nama": "Nama Barang",
                    "gudang_bjm": st.column_config.NumberColumn(
                        "🏪 Stok BJM",
                        format="%d",
                        help="Stok di gudang BJM (basis perhitungan)"
                    ),
                    "gudang_sby": st.column_config.NumberColumn(
                        "📦 Stok SBY",
                        format="%d",
                        help="Stok di gudang SBY (informasi saja)"
                    ),
                    "reorder_point": st.column_config.NumberColumn(
                        "Reorder Point", 
                        format="%.2f",
                        help="Batas untuk order (dalam unit harian)"
                    ),
                    "safety_stock": st.column_config.NumberColumn(
                        "Safety Stock", 
                        format="%.2f",
                        help="Buffer stok (dalam unit harian)"
                    ),
                    "hasil_prediksi": st.column_config.NumberColumn(
                        "Prediksi (Harian)", 
                        format="%.2f",
                        help="Prediksi penjualan bulan depan"
                    ),
                    "saran_stok": st.column_config.NumberColumn(
                        "🛒 Saran Pembelian (Harian)",
                        format="%.2f",
                        help="Saran pembelian stok untuk gudang BJM"
                    )
                },
                hide_index=True
            )