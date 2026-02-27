import streamlit as st
import pandas as pd
import plotly.express as px
import new_database
from datetime import datetime, timedelta

st.set_page_config(page_title="Stok Barang", page_icon="🗃️", layout="wide")

st.title("🗃️ Stok Barang")

tab1, tab2 = st.tabs(["📋 Stok Seluruh Barang", "🔍 Rincian per Barang"])

with tab1:
    st.markdown("### Stok Seluruh Barang")

    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        target_date = st.date_input("Pilih Tanggal", value=datetime.now().date(), key="target_date_all")
    
    with col_t2:
        search_term = st.text_input("🔍 Nama Barang", placeholder="Ketik nama barang untuk mencari...", key="search_all")
    
    with st.spinner("Menghitung stok seluruh barang..."):
        # Memanggil query database dari new_database.py
        df_all_stok = new_database.get_stok_seluruh_barang(target_date)

        # Terapkan filter pencarian jika diisi
        if search_term:
            df_all_stok = df_all_stok[df_all_stok['Nama Barang'].str.contains(search_term, case=False, na=False)]
        
        # Format Kolom Angka (Biar rapi ada koma pemisah ribuan)
        for col in ['Total Masuk', 'Total Keluar', 'Stok Akhir']:
            df_all_stok[col] = df_all_stok[col].apply(lambda x: f"{x:,.0f}".replace(",", "."))

        # Tampilkan DataFrame
        st.dataframe(
            df_all_stok,
            use_container_width=True,
            hide_index=True
        )

with tab2:
    st.markdown("### Stok Harian")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        # Ambil list barang dari database
        barang_list = new_database.get_barang_list_simple()
        if not barang_list.empty:
            barang_opts = dict(zip(barang_list['nama'], barang_list['id']))
            selected_nama_barang = st.selectbox("📦 Pilih Barang", options=list(barang_opts.keys()), key="select_brg_mutasi")
            selected_id_barang = barang_opts[selected_nama_barang]
        else:
            st.warning("Belum ada data barang.")
            st.stop()

    with col2:
        start_date = st.date_input("Dari Tanggal", value=datetime.now().date() - timedelta(days=30), key="start_date_mutasi")

    with col3:
        end_date = st.date_input("Sampai Tanggal", value=datetime.now().date(), key="end_date_mutasi")

    if start_date > end_date:
        st.error("Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'")
    else:
        with st.spinner("Memuat Kartu Stok..."):
            # 1. Ambil Stok Awal (Sebelum Start Date)
            stok_awal = new_database.get_stok_awal_barang(selected_id_barang, start_date)
            
            # 2. Ambil Pergerakan Harian (Antara Start Date - End Date)
            mutasi_df = new_database.get_mutasi_harian(selected_id_barang, start_date, end_date)

            total_masuk = mutasi_df['total_masuk'].sum() if not mutasi_df.empty else 0
            total_keluar = mutasi_df['total_keluar'].sum() if not mutasi_df.empty else 0
            stok_akhir = stok_awal + total_masuk - total_keluar

            # ==================== TAMPILAN SCORECARD ====================
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Stok Awal (Sebelum Periode)", f"{stok_awal:,.0f} pcs")
            c2.metric("Total Barang Masuk", f"{total_masuk:,.0f} pcs", delta_color="normal")
            c3.metric("Total Barang Keluar", f"{total_keluar:,.0f} pcs", delta_color="inverse")
            c4.metric("Stok Akhir", f"{stok_akhir:,.0f} pcs")

            # ==================== TABEL KARTU STOK ====================
            st.subheader("📋 Rincian Mutasi Harian")
            
            if mutasi_df.empty:
                st.info(f"Tidak ada pergerakan stok untuk barang **{selected_nama_barang}** pada periode ini.")
            else:
                # Menghitung Running Balance (Sisa Berjalan)
                running_balance = []
                current_stok = stok_awal
                
                for index, row in mutasi_df.iterrows():
                    current_stok = current_stok + row['total_masuk'] - row['total_keluar']
                    running_balance.append(current_stok)
                    
                mutasi_df['Sisa Stok'] = running_balance
                
                # Format Dataframe untuk Tampilan
                display_df = mutasi_df.copy()
                display_df['tanggal'] = pd.to_datetime(display_df['tanggal']).dt.strftime('%d %b %Y')
                display_df.rename(columns={
                    'tanggal': 'Tanggal',
                    'total_masuk': 'Barang Masuk',
                    'total_keluar': 'Barang Keluar'
                }, inplace=True)
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )

                # ==================== GRAFIK TREN STOK ====================
                st.markdown("---")
                st.subheader("📈 Grafik Pergerakan Stok")
                
                fig = px.line(
                    mutasi_df, 
                    x='tanggal', 
                    y='Sisa Stok', 
                    markers=True,
                    title=f"Tren Sisa Stok - {selected_nama_barang}",
                    labels={'Tanggal': 'Tanggal', 'Sisa Stok': 'Jumlah Stok (pcs)'}
                )
                # Menambahkan garis horizontal untuk menandakan angka 0
                fig.add_hline(y=0, line_dash="dash", line_color="red")
                st.plotly_chart(fig, use_container_width=True)

# col1, col2, col3 = st.columns([2, 1, 1])

# with col1:
#     # Ambil list barang dari database
#     barang_list = new_database.get_barang_list_simple()
#     if not barang_list.empty:
#         barang_opts = dict(zip(barang_list['nama'], barang_list['id']))
#         selected_nama_barang = st.selectbox("📦 Pilih Barang:", options=list(barang_opts.keys()))
#         selected_id_barang = barang_opts[selected_nama_barang]
#     else:
#         st.warning("Belum ada data barang.")
#         st.stop()

# with col2:
#     start_date = st.date_input("Dari Tanggal:", value=datetime.now().date() - timedelta(days=30))

# with col3:
#     end_date = st.date_input("Sampai Tanggal:", value=datetime.now().date())

# if start_date > end_date:
#     st.error("Tanggal 'Dari' tidak boleh lebih besar dari 'Sampai'")
#     st.stop()

# st.markdown("---")

# # ==================== PROSES DATA ====================
# with st.spinner("Memuat Kartu Stok..."):
#     # 1. Ambil Stok Awal (Sebelum Start Date)
#     stok_awal = new_database.get_stok_awal_barang(selected_id_barang, start_date)
    
#     # 2. Ambil Pergerakan Harian (Antara Start Date - End Date)
#     mutasi_df = new_database.get_mutasi_harian(selected_id_barang, start_date, end_date)

#     total_masuk = mutasi_df['total_masuk'].sum() if not mutasi_df.empty else 0
#     total_keluar = mutasi_df['total_keluar'].sum() if not mutasi_df.empty else 0
#     stok_akhir = stok_awal + total_masuk - total_keluar

#     # ==================== TAMPILAN SCORECARD ====================
#     c1, c2, c3, c4 = st.columns(4)
#     c1.metric("Stok Awal (Sebelum Periode)", f"{stok_awal:,.0f} pcs")
#     c2.metric("Total Barang Masuk", f"{total_masuk:,.0f} pcs", delta_color="normal")
#     c3.metric("Total Barang Keluar", f"{total_keluar:,.0f} pcs", delta_color="inverse")
#     c4.metric("Stok Akhir", f"{stok_akhir:,.0f} pcs")

#     # ==================== TABEL KARTU STOK ====================
#     st.subheader("📋 Rincian Mutasi Harian")
    
#     if mutasi_df.empty:
#         st.info(f"Tidak ada pergerakan stok untuk barang **{selected_nama_barang}** pada periode ini.")
#     else:
#         # Menghitung Running Balance (Sisa Berjalan)
#         running_balance = []
#         current_stok = stok_awal
        
#         for index, row in mutasi_df.iterrows():
#             current_stok = current_stok + row['total_masuk'] - row['total_keluar']
#             running_balance.append(current_stok)
            
#         mutasi_df['Sisa Stok'] = running_balance
        
#         # Format Dataframe untuk Tampilan
#         display_df = mutasi_df.copy()
#         display_df['tanggal'] = pd.to_datetime(display_df['tanggal']).dt.strftime('%d %b %Y')
#         display_df.rename(columns={
#             'tanggal': 'Tanggal',
#             'total_masuk': 'Barang Masuk',
#             'total_keluar': 'Barang Keluar'
#         }, inplace=True)
        
#         st.dataframe(
#             display_df,
#             use_container_width=True,
#             hide_index=True
#         )

#         # ==================== GRAFIK TREN STOK ====================
#         st.markdown("---")
#         st.subheader("📈 Grafik Pergerakan Stok")
        
#         fig = px.line(
#             mutasi_df, 
#             x='tanggal', 
#             y='Sisa Stok', 
#             markers=True,
#             title=f"Tren Sisa Stok - {selected_nama_barang}",
#             labels={'tanggal': 'Tanggal', 'Sisa Stok': 'Jumlah Stok (pcs)'}
#         )
#         # Menambahkan garis horizontal untuk menandakan angka 0
#         fig.add_hline(y=0, line_dash="dash", line_color="red")
#         st.plotly_chart(fig, use_container_width=True)