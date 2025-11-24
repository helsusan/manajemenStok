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
# PENGECEKAN STOK HARIAN (UPDATED WITH GUDANG INFO)
# ================================================

st.markdown("---")
st.header("🔍 Pengecekan Stok Harian")

btn_check_stock = st.button(
    "🔍 Jalankan Pengecekan Stok Harian",
    type="primary",
    use_container_width=True,
    help="Bandingkan stok aktual hari ini dengan reorder point"
)

if btn_check_stock:
    with st.spinner("🔄 Mengecek stok..."):
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
                st.subheader("🛒 Status Barang")
                
                # Hitung saran pembelian
                need_reorder['saran_pembelian'] = (
                    need_reorder['reorder_point'] + 
                    need_reorder['hasil_prediksi'] - 
                    need_reorder['stok_aktual']
                ).clip(lower=0).round(2)
                
                display_cols = [
                    'distribution_status', 'nama', 
                    'gudang_bjm', 'gudang_sby', 'stok_aktual',
                    'reorder_point', 'safety_stock', 'hasil_prediksi', 'saran_pembelian'
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
                            help="Stok di gudang BJM"
                        ),
                        "gudang_sby": st.column_config.NumberColumn(
                            "📦 SBY",
                            format="%d",
                            help="Stok di gudang SBY (perlu transfer)"
                        ),
                        "stok_aktual": st.column_config.NumberColumn("Total", format="%d"),
                        "reorder_point": st.column_config.NumberColumn("Reorder Point", format="%.2f"),
                        "safety_stock": st.column_config.NumberColumn("Safety Stock", format="%.2f"),
                        "hasil_prediksi": st.column_config.NumberColumn("Hasil Prediksi", format="%.2f"),
                        "saran_pembelian": st.column_config.NumberColumn(
                            "🛒 Saran",
                            format="%.2f",
                            help="Action: transfer dari SBY atau order ke supplier"
                        )
                    },
                    hide_index=True
                )
                
                # # Interpretasi status
                # st.markdown("---")
                # st.markdown("### 📖 Interpretasi Status:")
                
                # col1, col2 = st.columns(2)
                
                # with col1:
                #     st.markdown("""
                #     **⚠️ PERLU TRANSFER**
                #     - BJM kritis, tapi ada stok di SBY
                #     - **Action**: Transfer dari SBY ke BJM
                    
                #     **🔴 KRITIS**
                #     - BJM kritis, tidak ada stok di SBY
                #     - **Action**: Order ke supplier URGENT
                #     """)
                
                # with col2:
                #     st.markdown("""
                #     **📦 SBY MENUMPUK**
                #     - Total cukup, tapi banyak di SBY
                #     - **Action**: Transfer bertahap ke BJM
                    
                #     **✅ SEIMBANG**
                #     - Distribusi sudah baik
                #     - **Action**: Monitor saja
                #     """)
            
            else:
                st.success("🎉 Semua stok barang masih aman!")

