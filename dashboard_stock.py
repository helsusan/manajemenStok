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

# ================================================
# BARU: ANALISIS DISTRIBUSI GUDANG
# ================================================

st.header("🏭 Analisis Distribusi Gudang")

st.markdown("""
### 📍 Info Gudang:
- **Gudang BJM** (Banjarmasin): Gudang final, siap kirim ke customer
- **Gudang SBY** (Surabaya): Penyimpanan sementara, perlu transfer ke BJM

⚠️ **Catatan**: Stok di SBY belum bisa langsung dikirim ke customer!
""")

# Button analisis distribusi
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    btn_analyze_distribution = st.button(
        "🔍 Analisis Distribusi Gudang",
        type="secondary",
        use_container_width=True,
        help="Cek apakah ada barang yang perlu di-transfer dari SBY ke BJM"
    )

if btn_analyze_distribution:
    with st.spinner("🔄 Menganalisis distribusi gudang..."):
        analysis = database.analyze_gudang_distribution()
        
        st.success("✅ Analisis selesai!")
        
        st.markdown("---")
        st.subheader("📊 Hasil Analisis")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🚨 Perlu Transfer",
                len(analysis['need_transfer']),
                help="Barang yang BJM-nya kritis tapi ada stok di SBY"
            )
        
        with col2:
            st.metric(
                "🔴 BJM Kritis",
                len(analysis['bjm_critical']),
                help="Barang yang BJM-nya di bawah reorder point"
            )
        
        with col3:
            st.metric(
                "📦 SBY Menumpuk",
                len(analysis['sby_stockpile']),
                help="Barang yang stok SBY-nya terlalu banyak"
            )
        
        with col4:
            st.metric(
                "✅ Seimbang",
                len(analysis['balanced']),
                help="Distribusi stok sudah baik"
            )
        
        st.markdown("---")
        
        # ===== SECTION 1: URGENT - NEED TRANSFER =====
        if len(analysis['need_transfer']) > 0:
            st.subheader("🚨 URGENT: Barang yang Perlu Di-Transfer")
            st.error(f"**{len(analysis['need_transfer'])} barang** memerlukan transfer dari SBY ke BJM!")
            
            df_transfer = pd.DataFrame(analysis['need_transfer'])
            
            # Highlight urgent
            def highlight_urgent(row):
                if row['urgency'] == 'URGENT':
                    return ['background-color: #ffcccc'] * len(row)
                else:
                    return ['background-color: #ffffcc'] * len(row)
            
            st.dataframe(
                df_transfer,
                use_container_width=True,
                column_config={
                    "nama": "Nama Barang",
                    "gudang_bjm": st.column_config.NumberColumn(
                        "🏪 Stok BJM",
                        format="%d",
                        help="Stok di gudang Banjarmasin (siap kirim)"
                    ),
                    "gudang_sby": st.column_config.NumberColumn(
                        "📦 Stok SBY",
                        format="%d",
                        help="Stok di gudang Surabaya (perlu transfer)"
                    ),
                    "total_stok": st.column_config.NumberColumn(
                        "Total",
                        format="%d"
                    ),
                    "reorder_point": st.column_config.NumberColumn(
                        "Reorder Point",
                        format="%.2f"
                    ),
                    "transfer_needed": st.column_config.NumberColumn(
                        "🚚 Transfer Needed",
                        format="%.2f",
                        help="Jumlah yang disarankan untuk di-transfer"
                    ),
                    "urgency": st.column_config.TextColumn(
                        "⚠️ Urgency",
                        help="URGENT = BJM < safety stock, HIGH = BJM < reorder point"
                    ),
                    "reason": "Alasan"
                },
                hide_index=True
            )
            
            # Summary transfer
            total_transfer = df_transfer['transfer_needed'].sum()
            urgent_count = len(df_transfer[df_transfer['urgency'] == 'URGENT'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Unit Transfer", f"{total_transfer:,.0f}")
            
            with col2:
                st.metric("🚨 URGENT Priority", urgent_count)
            
            with col3:
                st.metric("⚠️ HIGH Priority", len(df_transfer) - urgent_count)
            
            st.warning("""
            ### 📌 Action Required:
            1. **URGENT items**: Transfer segera (dalam 1-2 hari)
            2. **HIGH items**: Transfer prioritas (dalam 3-5 hari)
            3. Koordinasi dengan tim logistik untuk jadwal transfer
            """)
        
        else:
            st.success("✅ Tidak ada barang yang perlu transfer urgent!")
        
        st.markdown("---")
        
        # ===== SECTION 2: BJM CRITICAL =====
        if len(analysis['bjm_critical']) > 0:
            st.subheader("🔴 BJM Kritis (Perlu Action)")
            
            df_critical = pd.DataFrame(analysis['bjm_critical'])
            
            st.dataframe(
                df_critical,
                use_container_width=True,
                column_config={
                    "nama": "Nama Barang",
                    "gudang_bjm": st.column_config.NumberColumn("🏪 Stok BJM", format="%d"),
                    "gudang_sby": st.column_config.NumberColumn("📦 Stok SBY", format="%d"),
                    "total_stok": st.column_config.NumberColumn("Total", format="%d"),
                    "reorder_point": st.column_config.NumberColumn("Reorder Point", format="%.2f"),
                    "safety_stock": st.column_config.NumberColumn("Safety Stock", format="%.2f"),
                    "gap": st.column_config.NumberColumn(
                        "Gap",
                        format="%.2f",
                        help="Selisih antara reorder point dan stok BJM"
                    ),
                    "reason": "Alasan"
                },
                hide_index=True
            )
            
            st.error("""
            ### ⚠️ Critical Items:
            - Barang-barang ini **SANGAT KRITIS**
            - Jika tidak ada stok di SBY: **Segera order ke supplier**
            - Jika ada stok di SBY: **Transfer URGENT** (sudah ada di tabel atas)
            """)
        
        st.markdown("---")
        
        # ===== SECTION 3: SBY STOCKPILE (MONITORING) =====
        if len(analysis['sby_stockpile']) > 0:
            with st.expander("📦 SBY Menumpuk (Monitoring)"):
                st.info("Barang-barang ini stok BJM-nya sudah aman, tapi SBY menumpuk")
                
                df_stockpile = pd.DataFrame(analysis['sby_stockpile'])
                
                st.dataframe(
                    df_stockpile,
                    use_container_width=True,
                    column_config={
                        "nama": "Nama Barang",
                        "gudang_bjm": st.column_config.NumberColumn("🏪 BJM", format="%d"),
                        "gudang_sby": st.column_config.NumberColumn("📦 SBY", format="%d"),
                        "total_stok": st.column_config.NumberColumn("Total", format="%d"),
                        "prediksi": st.column_config.NumberColumn("Prediksi", format="%.2f"),
                        "reason": "Keterangan"
                    },
                    hide_index=True
                )
                
                st.caption("""
                💡 **Catatan**: 
                - Tidak perlu action urgent
                - Monitor untuk antisipasi demand tinggi
                - Pertimbangkan transfer bertahap jika BJM mulai turun
                """)
        
        # ===== SECTION 4: BALANCED =====
        if len(analysis['balanced']) > 0:
            with st.expander(f"✅ Distribusi Seimbang ({len(analysis['balanced'])} barang)"):
                st.success("Barang-barang ini distribusinya sudah baik!")
                
                df_balanced = pd.DataFrame(analysis['balanced'])
                
                st.dataframe(
                    df_balanced[['nama', 'gudang_bjm', 'gudang_sby', 'total_stok', 'reorder_point']],
                    use_container_width=True,
                    column_config={
                        "nama": "Nama Barang",
                        "gudang_bjm": st.column_config.NumberColumn("🏪 BJM", format="%d"),
                        "gudang_sby": st.column_config.NumberColumn("📦 SBY", format="%d"),
                        "total_stok": st.column_config.NumberColumn("Total", format="%d"),
                        "reorder_point": st.column_config.NumberColumn("Reorder Point", format="%.2f")
                    },
                    hide_index=True
                )

st.markdown("---")

# ================================================
# PENGECEKAN STOK HARIAN (UPDATED WITH GUDANG INFO)
# ================================================

st.header("🔍 Pengecekan Stok Harian")

# ... (Bagian cek status data sama seperti sebelumnya) ...

# Button pengecekan
btn_check_stock = st.button(
    "🔍 Jalankan Pengecekan Stok Harian",
    type="primary",
    use_container_width=True,
    help="Bandingkan stok aktual hari ini dengan reorder point"
)

if btn_check_stock:
    with st.spinner("🔄 Mengecek stok..."):
        # Ambil data dengan info gudang
        check_stok = database.check_data_stok_hari_ini()
        rekomendasi_full = database.get_rekomendasi_stok_with_gudang()
        
        if len(rekomendasi_full) == 0:
            st.error("❌ Data tidak lengkap untuk pengecekan")
        else:
            # Filter yang perlu reorder
            need_reorder = rekomendasi_full[
                rekomendasi_full['stok_aktual'] <= rekomendasi_full['reorder_point']
            ].copy()
            
            # Sort by urgency
            need_reorder = need_reorder.sort_values('stok_aktual')
            
            st.success("✅ Pengecekan selesai!")
            
            # Summary
            st.markdown("---")
            st.subheader("📋 Hasil Pengecekan")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Barang Dicek", len(rekomendasi_full))
            
            with col2:
                st.metric("⚠️ Perlu Reorder", len(need_reorder))
            
            with col3:
                st.metric("✅ Stok Aman", len(rekomendasi_full) - len(need_reorder))
            
            st.markdown("---")
            
            # Tabel dengan info gudang
            if len(need_reorder) > 0:
                st.subheader("🛒 Barang yang Perlu Action")
                
                # Hitung saran pembelian
                need_reorder['saran_pembelian'] = (
                    need_reorder['reorder_point'] + 
                    need_reorder['hasil_prediksi'] - 
                    need_reorder['stok_aktual']
                ).clip(lower=0).round(2)
                
                display_cols = [
                    'distribution_status', 'nama', 
                    'gudang_bjm', 'gudang_sby', 'stok_aktual',
                    'reorder_point', 'safety_stock', 'saran_pembelian'
                ]
                
                st.dataframe(
                    need_reorder[display_cols],
                    use_container_width=True,
                    column_config={
                        "distribution_status": st.column_config.TextColumn(
                            "Status",
                            help="Status distribusi gudang"
                        ),
                        "nama": "Nama Barang",
                        "gudang_bjm": st.column_config.NumberColumn(
                            "🏪 BJM",
                            format="%d",
                            help="Stok di gudang BJM (siap kirim)"
                        ),
                        "gudang_sby": st.column_config.NumberColumn(
                            "📦 SBY",
                            format="%d",
                            help="Stok di gudang SBY (perlu transfer)"
                        ),
                        "stok_aktual": st.column_config.NumberColumn("Total", format="%d"),
                        "reorder_point": st.column_config.NumberColumn("Reorder Point", format="%.2f"),
                        "safety_stock": st.column_config.NumberColumn("Safety Stock", format="%.2f"),
                        "saran_pembelian": st.column_config.NumberColumn(
                            "🛒 Saran",
                            format="%.2f",
                            help="Action: transfer dari SBY atau order ke supplier"
                        )
                    },
                    hide_index=True
                )
                
                # Interpretasi status
                st.markdown("---")
                st.markdown("### 📖 Interpretasi Status:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    **⚠️ PERLU TRANSFER**
                    - BJM kritis, tapi ada stok di SBY
                    - **Action**: Transfer dari SBY ke BJM
                    
                    **🔴 KRITIS**
                    - BJM kritis, tidak ada stok di SBY
                    - **Action**: Order ke supplier URGENT
                    """)
                
                with col2:
                    st.markdown("""
                    **📦 SBY MENUMPUK**
                    - Total cukup, tapi banyak di SBY
                    - **Action**: Transfer bertahap ke BJM
                    
                    **✅ SEIMBANG**
                    - Distribusi sudah baik
                    - **Action**: Monitor saja
                    """)
            
            else:
                st.success("🎉 Semua stok barang masih aman!")

# ... (Rest of the code) ...

# ================================================
# INFO PERHITUNGAN (UPDATED)
# ================================================

with st.expander("📖 Informasi Gudang & Perhitungan"):
    st.markdown("""
    ### 🏭 Sistem Gudang:
    
    **Gudang SBY (Surabaya)**
    - Penyimpanan sementara
    - Barang belum siap kirim ke customer
    - Perlu transfer ke BJM terlebih dahulu
    
    **Gudang BJM (Banjarmasin)**
    - Gudang final/utama
    - Barang siap dikirim ke customer
    - Perhitungan reorder point berbasis stok BJM
    
    ---
    
    ### 🎯 Logic Pengecekan:
    
    1. **Hitung Total Stok** = BJM + SBY
    2. **Bandingkan dengan Reorder Point**
    3. **Analisis Distribusi**:
       - Jika BJM < Reorder Point & SBY > 0 → Perlu TRANSFER
       - Jika BJM < Reorder Point & SBY = 0 → Perlu ORDER
       - Jika BJM OK & SBY banyak → MONITOR
    
    ---
    
    ### 📊 Contoh Kasus:
    
    **CASE 1: Perlu Transfer**
    ```
    BJM: 50 unit
    SBY: 100 unit
    Total: 150 unit
    Reorder Point: 150 unit
    
    Status: ⚠️ PERLU TRANSFER
    Action: Transfer 100 unit dari SBY ke BJM
    Alasan: BJM kritis (< reorder point) tapi ada stok di SBY
    ```
    
    **CASE 2: Perlu Order**
    ```
    BJM: 40 unit
    SBY: 0 unit
    Total: 40 unit
    Reorder Point: 150 unit
    
    Status: 🔴 KRITIS
    Action: Order 110+ unit ke supplier
    Alasan: BJM kritis dan tidak ada backup di SBY
    ```
    
    **CASE 3: SBY Menumpuk**
    ```
    BJM: 200 unit
    SBY: 400 unit
    Total: 600 unit
    Reorder Point: 150 unit
    
    Status: 📦 SBY MENUMPUK
    Action: Transfer bertahap ke BJM (tidak urgent)
    Alasan: BJM aman tapi SBY terlalu banyak
    ```
    """)