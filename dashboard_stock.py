import streamlit as st
import database
import pandas as pd
from datetime import datetime

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

st.markdown("---")

# ================================================
# PENGECEKAN STOK HARIAN
# ================================================

st.header("🔍 Pengecekan Stok Harian")

st.markdown("""
### 🎯 Apa yang dilakukan button ini?

Button ini akan:
1. **Mengecek** apakah data stok hari ini sudah diinput
2. **Membandingkan** stok aktual dengan reorder point (dari database)
3. **Menampilkan** daftar barang yang perlu dibeli/reorder

⚠️ **PENTING**: 
- Pastikan sudah input data stok hari ini di halaman **Data Stok**
- Data rekomendasi berasal dari **Proses Akhir Bulan** di halaman Data Penjualan
""")

st.markdown("---")

# Cek data stok hari ini
check_stok = database.check_data_stok_hari_ini()

st.subheader("📊 Status Pengecekan")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Data Stok Hari Ini:**")
    if check_stok['exists']:
        st.success(f"✅ {check_stok['message']}")
    else:
        st.warning(f"⚠️ {check_stok['message']}")
        st.error("**PERHATIAN**: Input data stok hari ini dulu!")

with col2:
    st.markdown("**Data Rekomendasi:**")
    if latest_rekomendasi_date:
        st.success(f"✅ Rekomendasi tersedia (Update: {latest_rekomendasi_date.strftime('%d %b %Y')})")
    else:
        st.error("❌ Belum ada data rekomendasi")
        st.info("💡 Jalankan Proses Akhir Bulan di halaman Data Penjualan")

st.markdown("---")

# Button pengecekan
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    btn_check_stock = st.button(
        "🔍 Jalankan Pengecekan Stok Harian",
        type="primary",
        use_container_width=True,
        disabled=not check_stok['exists'] or not latest_rekomendasi_date,
        help="Bandingkan stok aktual hari ini dengan reorder point"
    )

if btn_check_stock:
    with st.spinner("🔄 Mengecek stok..."):
        # Ambil data stok hari ini
        stok_hari_ini = database.get_stok_by_date(check_stok['last_date'])
        
        # Ambil data rekomendasi (reorder point)
        rekomendasi = database.get_rekomendasi_stok()
        
        if len(stok_hari_ini) == 0 or len(rekomendasi) == 0:
            st.error("❌ Data tidak lengkap untuk pengecekan")
        else:
            # Gabungkan data
            merged = pd.merge(
                stok_hari_ini,
                rekomendasi[['id_barang', 'avg_lead_time', 'max_lead_time', 'reorder_point', 
                            'safety_stock', 'hasil_prediksi']],
                left_on='id',
                right_on='id_barang',
                how='inner'
            )
            
            # Filter: hanya yang perlu reorder (stok <= reorder point)
            need_reorder = merged[merged['total_stok'] <= merged['reorder_point']].copy()
            
            # Hitung saran pembelian
            need_reorder['saran_pembelian'] = (
                need_reorder['reorder_point'] + 
                need_reorder['hasil_prediksi'] - 
                need_reorder['total_stok']
            ).clip(lower=0).round(2)
            
            # Sort berdasarkan urgency (stok paling sedikit di atas)
            need_reorder = need_reorder.sort_values('total_stok')
            
            # Tampilkan hasil
            st.success("✅ Pengecekan selesai!")
            
            st.markdown("---")
            st.subheader("📋 Hasil Pengecekan")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Barang Dicek", len(merged))
            
            with col2:
                st.metric("⚠️ Perlu Reorder", len(need_reorder), 
                         delta=f"{(len(need_reorder)/len(merged)*100):.1f}%")
            
            with col3:
                st.metric("✅ Stok Aman", len(merged) - len(need_reorder))
            
            st.markdown("---")
            
            # Tabel barang yang perlu reorder
            if len(need_reorder) > 0:
                st.subheader("🛒 Barang yang Perlu Dibeli")
                st.warning(f"**{len(need_reorder)} barang** mencapai atau di bawah reorder point!")
                
                # Format untuk display
                display_cols = [
                    'nama', 'total_stok', 'reorder_point', 'safety_stock',
                    'hasil_prediksi', 'saran_pembelian', 'avg_lead_time', 'max_lead_time'
                ]
                
                st.dataframe(
                    need_reorder[display_cols],
                    use_container_width=True,
                    column_config={
                        "nama": "Nama Barang",
                        "total_stok": st.column_config.NumberColumn(
                            "Stok Aktual", 
                            format="%d",
                            help="Stok saat ini di gudang"
                        ),
                        "reorder_point": st.column_config.NumberColumn(
                            "Reorder Point", 
                            format="%.2f",
                            help="Batas minimum stok sebelum perlu order"
                        ),
                        "safety_stock": st.column_config.NumberColumn(
                            "Safety Stock", 
                            format="%.2f",
                            help="Buffer stok untuk antisipasi"
                        ),
                        "hasil_prediksi": st.column_config.NumberColumn(
                            "Prediksi Bulan Depan", 
                            format="%.2f",
                            help="Estimasi penjualan bulan depan"
                        ),
                        "saran_pembelian": st.column_config.NumberColumn(
                            "🛒 Saran Pembelian", 
                            format="%.2f",
                            help="Jumlah yang disarankan untuk dibeli"
                        ),
                        "avg_lead_time": st.column_config.NumberColumn(
                            "Avg Lead Time", 
                            format="%d hari",
                            help="Lead time rata-rata"
                        ),
                        "max_lead_time": st.column_config.NumberColumn(
                            "Max Lead Time", 
                            format="%d hari",
                            help="Lead time maksimum (worst case)"
                        )
                    },
                    hide_index=True
                )
                
                # Summary pembelian
                st.markdown("---")
                st.subheader("💰 Ringkasan Saran Pembelian")
                
                total_saran = need_reorder['saran_pembelian'].sum()
                avg_avg_lead_time = need_reorder['avg_lead_time'].mean()
                avg_max_lead_time = need_reorder['max_lead_time'].mean()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Unit Disarankan", f"{total_saran:,.0f}")
                
                with col2:
                    st.metric("Rata-rata Avg Lead Time", f"{avg_avg_lead_time:.1f} hari")
                
                with col3:
                    st.metric("Rata-rata Max Lead Time", f"{avg_max_lead_time:.1f} hari")
                
                with col4:
                    max_lead = need_reorder['max_lead_time'].max()
                    st.metric("Lead Time Terlama", f"{max_lead} hari")
                
                # Info penting
                st.info("""
                💡 **Tips Pembelian:**
                - Prioritaskan barang dengan **stok terendah** (paling atas tabel)
                - Perhatikan **Lead Time** - order lebih awal untuk barang dengan lead time lama
                - **Saran Pembelian** sudah memperhitungkan prediksi demand bulan depan
                - **Max Lead Time** digunakan untuk perhitungan safety stock (antisipasi worst case)
                """)
                
            else:
                st.success("🎉 Semua stok barang masih aman!")
                st.info("✅ Tidak ada barang yang perlu direorder saat ini")
                st.balloons()

st.markdown("---")

# ================================================
# TABEL REKOMENDASI LENGKAP (OPSIONAL)
# ================================================

with st.expander("📊 Lihat Semua Data Rekomendasi"):
    rekomendasi_all = database.get_rekomendasi_stok()
    
    if len(rekomendasi_all) > 0:
        # Tambahkan status
        rekomendasi_all['status'] = rekomendasi_all.apply(
            lambda row: '🔴 REORDER!' if row['stok_aktual'] <= row['reorder_point'] else '✅ Aman',
            axis=1
        )
        
        cols_to_show = [
            'status', 'nama', 'stok_aktual', 'reorder_point', 
            'safety_stock', 'hasil_prediksi', 'saran_stok', 
            'avg_lead_time', 'max_lead_time', 'tgl_update'
        ]
        
        st.dataframe(
            rekomendasi_all[cols_to_show],
            use_container_width=True,
            column_config={
                "avg_lead_time": st.column_config.NumberColumn("Avg Lead Time", format="%d hari"),
                "max_lead_time": st.column_config.NumberColumn("Max Lead Time", format="%d hari"),
            },
            hide_index=True
        )
    else:
        st.info("Belum ada data rekomendasi. Jalankan Proses Akhir Bulan terlebih dahulu.")

# ================================================
# INFORMASI PERHITUNGAN
# ================================================

st.markdown("---")
st.subheader("📖 Cara Kerja Perhitungan")

with st.expander("🔍 Formula dan Penjelasan"):
    st.markdown("""
    ### 📐 Formula yang Digunakan:
    
    #### 1. Average Daily Usage
    ```
    Average Daily Usage = (Rata-rata Penjualan Bulanan) / 30 hari
    ```
    
    #### 2. Maximum Daily Usage
    ```
    Maximum Daily Usage = (Penjualan Bulanan Tertinggi) / 30 hari
    ```
    
    #### 3. Safety Stock
    ```
    Safety Stock = (Max Daily Usage × Max Lead Time) - (Avg Daily Usage × Avg Lead Time)
    ```
    **Penjelasan:**
    - Menggunakan **Max Lead Time** untuk worst case scenario
    - Safety stock = buffer untuk mengantisipasi:
      - Keterlambatan pengiriman (lead time lebih lama)
      - Lonjakan demand mendadak
    
    #### 4. Reorder Point
    ```
    Reorder Point = (Avg Daily Usage × Avg Lead Time) + Safety Stock
    ```
    **Penjelasan:**
    - Menggunakan **Avg Lead Time** untuk kondisi normal
    - Plus safety stock sebagai buffer
    
    #### 5. Saran Pembelian
    ```
    Saran Pembelian = Reorder Point + Prediksi Bulan Depan - Stok Aktual
    ```
    
    ---
    
    ### 🎯 Contoh Perhitungan Lengkap:
    
    **Data:**
    - Rata-rata penjualan: 300 unit/bulan
    - Penjualan tertinggi: 450 unit/bulan
    - Avg Lead Time: 7 hari
    - Max Lead Time: 10 hari
    - Stok aktual: 50 unit
    - Prediksi bulan depan: 320 unit
    
    **Step 1:** Hitung daily usage
    ```
    Avg Daily Usage = 300 / 30 = 10 unit/hari
    Max Daily Usage = 450 / 30 = 15 unit/hari
    ```
    
    **Step 2:** Hitung Safety Stock
    ```
    Safety Stock = (15 × 10) - (10 × 7)
                 = 150 - 70
                 = 80 unit
    ```
    
    **Step 3:** Hitung Reorder Point
    ```
    Reorder Point = (10 × 7) + 80
                  = 70 + 80
                  = 150 unit
    ```
    
    **Step 4:** Hitung Saran Pembelian
    ```
    Saran = 150 + 320 - 50
          = 420 unit
    ```
    
    **Kesimpulan:**
    - Ketika stok mencapai **150 unit**, segera order!
    - Disarankan beli **420 unit** untuk:
      - Mencapai reorder point (150)
      - Memenuhi prediksi demand bulan depan (320)
      - Dikurangi stok yang ada (50)
    
    ---
    
    ### 💡 Mengapa Ada 2 Jenis Lead Time?
    
    **Avg Lead Time:**
    - Untuk perhitungan reorder point (kondisi normal)
    - Lebih realistic untuk operasional sehari-hari
    - Contoh: Biasanya barang datang dalam 7 hari
    
    **Max Lead Time:**
    - Untuk perhitungan safety stock (worst case)
    - Antisipasi keterlambatan atau masalah pengiriman
    - Contoh: Pernah ada keterlambatan sampai 10 hari
    
    Dengan kombinasi ini, sistem menjadi:
    - **Efisien**: Reorder point tidak terlalu tinggi (pakai avg)
    - **Aman**: Safety stock cukup untuk antisipasi masalah (pakai max)
    
    ---
    
    ### ⚠️ Status Reorder:
    - 🔴 **REORDER!**: Stok aktual ≤ Reorder Point → **Segera order!**
    - ✅ **Aman**: Stok aktual > Reorder Point → Stok masih mencukupi
    """)

# Footer
st.markdown("---")
st.caption(f"🕒 Last viewed: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")