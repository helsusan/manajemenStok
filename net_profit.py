import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import new_database

st.set_page_config(page_title="Net Profit Analysis", page_icon="💰", layout="wide")

st.title("💰 Laporan Net Profit (Laba Bersih)")
# st.markdown("Halaman ini menghitung Laba Bersih dengan mengurangi **Gross Profit** (Laba Kotor dari penjualan dikurangi HPP) dengan **Biaya Tambahan**.")

# ==================== FILTER PERIODE ====================
st.markdown("### 🔍 Filter Periode")
col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    start_date = st.date_input("Dari Tanggal", value=datetime.now().date() - timedelta(days=30))
with col_filter2:
    end_date = st.date_input("Sampai Tanggal", value=datetime.now().date())

if start_date > end_date:
    st.error("⚠️ Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'")
    st.stop()

st.markdown("---")

with st.spinner("Menghitung Net Profit..."):
    # ==================== 1. AMBIL DATA ====================
    # Ambil data pembelian & penjualan untuk perhitungan Gross Profit
    pembelian_df = new_database.get_pembelian_data(start_date, end_date)
    penjualan_df = new_database.get_penjualan_data(start_date, end_date)
    
    # Hitung Gross Profit (menggunakan fungsi FIFO yang sudah ada)
    gp_df = new_database.calculate_gross_profit_fifo(pembelian_df, penjualan_df)
    
    total_penjualan = gp_df['total_penjualan'].sum() if not gp_df.empty else 0
    total_hpp = gp_df['total_hpp'].sum() if not gp_df.empty else 0
    total_gross_profit = gp_df['gross_profit'].sum() if not gp_df.empty else 0

    # Ambil data Biaya Tambahan
    try:
        biaya_df = new_database.get_all_biaya_tambahan(start_date, end_date)
        total_biaya = biaya_df['jumlah'].sum() if not biaya_df.empty else 0
    except AttributeError:
        st.error("Fungsi 'get_all_biaya_tambahan' belum ditambahkan di new_database.py!")
        biaya_df = pd.DataFrame()
        total_biaya = 0

    # ==================== 2. HITUNG NET PROFIT ====================
    net_profit = total_gross_profit - total_biaya

    # ==================== 3. TAMPILAN METRIK (SCORECARD) ====================
    st.subheader("📊 Ringkasan Keuangan")
    
    # Baris Pertama: Komponen Gross Profit
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Penjualan", f"Rp {total_penjualan:,.0f}".replace(",", "."))
    col2.metric("Total HPP (Harga Pokok Penjualan)", f"Rp {total_hpp:,.0f}".replace(",", "."), delta="-")
    col3.metric("Total Gross Profit", f"Rp {total_gross_profit:,.0f}".replace(",", "."), delta="Laba Kotor")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Baris Kedua: Komponen Net Profit
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Gross Profit", f"Rp {total_gross_profit:,.0f}".replace(",", "."))
    c2.metric("Total Biaya Tambahan (Pengeluaran)", f"Rp {total_biaya:,.0f}".replace(",", "."), delta="-", delta_color="inverse")
    
    # Highlight Net Profit
    c3.markdown(f"""
        <div style="background-color: {'#d4edda' if net_profit >= 0 else '#f8d7da'}; padding: 10px; border-radius: 5px; text-align: center;">
            <h4 style="margin: 0; color: {'#155724' if net_profit >= 0 else '#721c24'};">Laba Bersih (Net Profit)</h4>
            <h2 style="margin: 0; color: {'#155724' if net_profit >= 0 else '#721c24'};">Rp {net_profit:,.0f}</h2>
        </div>
    """.replace(",", "."), unsafe_allow_html=True)

    st.markdown("---")

    # ==================== 4. DETAIL BIAYA TAMBAHAN ====================
    col_tabel1, col_tabel2 = st.columns([1, 1])
    
    with col_tabel1:
        st.subheader("📉 Rincian Biaya Tambahan")
        if not biaya_df.empty:
            df_display = biaya_df.copy()
            df_display['tanggal'] = pd.to_datetime(df_display['tanggal']).dt.strftime('%d %b %Y')
            df_display.rename(columns={
                'nama': 'Keterangan Biaya',
                'tanggal': 'Tanggal',
                'jumlah': 'Jumlah (Rp)'
            }, inplace=True)
            
            # Tampilkan tabel tanpa kolom ID
            st.dataframe(
                df_display[['Keterangan Biaya', 'Tanggal', 'Jumlah (Rp)']].style.format({"Jumlah (Rp)": "{:,.0f}"}), 
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Tidak ada pengeluaran/biaya tambahan pada periode ini.")

    with col_tabel2:
        st.subheader("📈 Komposisi Pengeluaran vs Laba")
        
        # Buat chart pie sederhana 
        if total_penjualan > 0:
            pie_data = pd.DataFrame({
                'Kategori': ['HPP', 'Biaya Tambahan', 'Net Profit'],
                'Nilai': [total_hpp, total_biaya, net_profit if net_profit > 0 else 0]
            })
            
            # Jika Net Profit negatif, kecualikan dari pie chart supaya tidak error
            pie_data = pie_data[pie_data['Nilai'] > 0]
            
            fig = px.pie(pie_data, values='Nilai', names='Kategori', title="Persentase Alokasi dari Penjualan")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data penjualan untuk menampilkan grafik komposisi.")