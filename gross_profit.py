import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import new_database  # Pastikan file new_database.py ada di folder yang sama

st.set_page_config(
    page_title="Gross Profit Analysis",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Gross Profit Analysis Dashboard")

# ==================== FILTER SECTION (MAIN PAGE) ====================
# Menggunakan Expander agar filter bisa disembunyikan/dimunculkan, default terbuka
# with st.expander("🔍 Filter Data & Periode", expanded=True):
# Bagi layout menjadi 3 kolom
col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 2])

with col_filter1:
    st.subheader("1. Periode")
    st.markdown("**Ini teks bold biasa**")
    periode_option = st.radio(
        "Pilih Tipe Periode:",
        ["Keseluruhan", "Per Bulan", "Custom Range"],
        label_visibility="collapsed" # Menyembunyikan label text karena sudah ada subheader
    )

start_date = None
end_date = None

with col_filter2:
    st.subheader("2. Rentang Waktu")
    if periode_option == "Per Bulan":
        selected_month = st.date_input(
            "Pilih Bulan:",
            value=datetime.now(),
            max_value=datetime.now()
        )
        # Logic ambil awal & akhir bulan
        start_date = selected_month.replace(day=1)
        if selected_month.month == 12:
            end_date = selected_month.replace(day=31)
        else:
            end_date = (selected_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        
        st.info(f"📅 {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}")

    elif periode_option == "Custom Range":
        start_date = st.date_input("Dari Tanggal:", value=datetime.now() - timedelta(days=30))
        end_date = st.date_input("Sampai Tanggal:", value=datetime.now())
    
    else: # Keseluruhan
        st.info("📅 Menampilkan semua data historis")

with col_filter3:
    st.subheader("3. Filter Barang")
    # Ambil list barang dari database
    try:
        barang_list = new_database.get_barang_list_simple()
        filter_barang = st.multiselect(
            "Pilih Barang (Kosongkan untuk memilih semua):",
            options=barang_list['nama'].tolist(),
            default=None
        )
    except Exception as e:
        st.error("Gagal memuat list barang. Pastikan database terkoneksi.")
        filter_barang = None

st.markdown("---")

# ==================== MAIN CONTENT ====================
try:
    with st.spinner("Sedang menghitung Gross Profit (FIFO)..."):
        # 1. Ambil Data Mentah (Query ada di new_database.py)
        pembelian_df = new_database.get_pembelian_data(start_date, end_date)
        penjualan_df = new_database.get_penjualan_data(start_date, end_date)
    
    if pembelian_df.empty or penjualan_df.empty:
        st.warning("⚠️ Tidak ada data transaksi pembelian/penjualan untuk periode yang dipilih.")
    else:
        # 2. Hitung Logic FIFO (Logic ada di new_database.py)
        gp_df = new_database.calculate_gross_profit_fifo(pembelian_df, penjualan_df)
        
        # 3. Terapkan Filter Barang di Hasil Akhir
        if filter_barang:
            gp_df = gp_df[gp_df['nama_barang'].isin(filter_barang)]
        
        if gp_df.empty:
            st.warning("⚠️ Tidak ada data gross profit untuk barang yang dipilih.")
        else:
            # === SCORECARDS ===
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Penjualan",
                    f"Rp {gp_df['total_penjualan'].sum():,.0f}".replace(",", ".")
                )
            
            with col2:
                st.metric(
                    "Total HPP",
                    f"Rp {gp_df['total_hpp'].sum():,.0f}".replace(",", ".")
                )
            
            with col3:
                total_gp = gp_df['gross_profit'].sum()
                total_sales = gp_df['total_penjualan'].sum()
                # Hindari pembagian dengan nol
                persentase = (total_gp/total_sales*100) if total_sales > 0 else 0
                
                st.metric(
                    "Gross Profit",
                    f"Rp {total_gp:,.0f}".replace(",", "."),
                    delta=f"{persentase:.1f}% Margin"
                )
            
            with col4:
                avg_margin = gp_df['margin_persen'].mean()
                st.metric(
                    "Rata-rata Margin per Item",
                    f"{avg_margin:.1f}%"
                )
            
            st.markdown("---")
            
            # === TABS VISUALISASI ===
            tab1, tab2, tab3, tab4 = st.tabs([
                "📋 Tabel Detail", 
                "📊 Top Products", 
                "📈 Visualisasi",
                "📐 Detail Perhitungan"
            ])
            
            # TAB 1: TABEL
            with tab1:
                st.subheader("Detail Gross Profit per Barang")
                
                # Format untuk display agar rapi (Rp xxx.xxx)
                display_df = gp_df.copy()
                cols_to_format = ['total_penjualan', 'total_hpp', 'gross_profit']
                for col in cols_to_format:
                    display_df[col] = display_df[col].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                
                display_df['margin_persen'] = display_df['margin_persen'].apply(lambda x: f"{x:.2f}%")
                
                # Rename kolom biar bahasa Indonesia dan rapi
                display_df = display_df.rename(columns={
                    'nama_barang': 'Nama Barang',
                    'total_penjualan': 'Total Penjualan',
                    'total_hpp': 'Total HPP',
                    'gross_profit': 'Gross Profit',
                    'margin_persen': 'Margin (%)',
                    'qty_terjual': 'Qty Terjual'
                })
                
                st.dataframe(
                    display_df[['Nama Barang', 'Qty Terjual', 'Total Penjualan', 'Total HPP', 'Gross Profit', 'Margin (%)']],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Download CSV
                csv = gp_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Data (CSV)",
                    data=csv,
                    file_name=f"gross_profit_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            
            # TAB 2: TOP PRODUCTS
            with tab2:
                st.subheader("Top 10 Products by Gross Profit")
                
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    top10_profit = gp_df.nlargest(10, 'gross_profit')
                    fig1 = px.bar(
                        top10_profit,
                        x='gross_profit',
                        y='nama_barang',
                        orientation='h',
                        title='Top 10 by Gross Profit (Rp)',
                        labels={'gross_profit': 'Gross Profit', 'nama_barang': 'Barang'},
                        color='gross_profit',
                        color_continuous_scale='Greens'
                    )
                    fig1.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col_chart2:
                    top10_margin = gp_df.nlargest(10, 'margin_persen')
                    fig2 = px.bar(
                        top10_margin,
                        x='margin_persen',
                        y='nama_barang',
                        orientation='h',
                        title='Top 10 by Margin (%)',
                        labels={'margin_persen': 'Margin (%)', 'nama_barang': 'Barang'},
                        color='margin_persen',
                        color_continuous_scale='Blues'
                    )
                    fig2.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig2, use_container_width=True)
            
            # TAB 3: SCATTER & PIE
            with tab3:
                st.subheader("Visualisasi Gross Profit")
                
                col_vis1, col_vis2 = st.columns([2, 1])

                with col_vis1:
                    fig3 = px.scatter(
                        gp_df,
                        x='total_penjualan',
                        y='gross_profit',
                        size='qty_terjual',
                        color='margin_persen',
                        hover_data=['nama_barang'],
                        title='Penjualan vs Gross Profit (Ukuran Bubble = Qty Terjual)',
                        labels={
                            'total_penjualan': 'Total Penjualan (Rp)',
                            'gross_profit': 'Gross Profit (Rp)',
                            'margin_persen': 'Margin (%)'
                        },
                        color_continuous_scale='RdYlGn'
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                
                with col_vis2:
                    fig4 = px.pie(
                        gp_df.nlargest(10, 'gross_profit'),
                        values='gross_profit',
                        names='nama_barang',
                        title='Kontribusi Profit - Top 10'
                    )
                    st.plotly_chart(fig4, use_container_width=True)
            
            # TAB 4: DETAIL PER BARANG
            # with tab4:
                # st.subheader("Detail Analisis per Barang")
                
                # selected_barang = st.selectbox(
                #     "Pilih Barang untuk Detail:",
                #     options=gp_df['nama_barang'].tolist()
                # )
                
                # if selected_barang:
                #     barang_data = gp_df[gp_df['nama_barang'] == selected_barang].iloc[0]
                    
                #     c1, c2, c3 = st.columns(3)
                #     with c1:
                #         st.metric("Total Penjualan", f"Rp {barang_data['total_penjualan']:,.0f}".replace(",", "."))
                #         st.metric("Qty Terjual", f"{barang_data['qty_terjual']:,.0f}")
                    
                #     with c2:
                #         st.metric("Total HPP", f"Rp {barang_data['total_hpp']:,.0f}".replace(",", "."))
                #         hpp_unit = barang_data['total_hpp']/barang_data['qty_terjual'] if barang_data['qty_terjual'] > 0 else 0
                #         st.metric("HPP per Unit (Avg)", f"Rp {hpp_unit:,.0f}".replace(",", "."))
                    
                #     with c3:
                #         st.metric("Gross Profit", f"Rp {barang_data['gross_profit']:,.0f}".replace(",", "."))
                #         st.metric("Margin", f"{barang_data['margin_persen']:.2f}%")
                    
                #     st.markdown("---")
                #     # Tampilkan detail transaksi penjualan untuk barang ini
                #     st.markdown(f"#### Riwayat Penjualan: {selected_barang}")
                #     barang_id = barang_data['id_barang']
                #     penjualan_detail = penjualan_df[penjualan_df['id_barang'] == barang_id].copy()

                #     # Formatting Tanggal (TAMBAHAN)
                #     penjualan_detail['tanggal'] = pd.to_datetime(penjualan_detail['tanggal']).dt.strftime('%d %b %Y')
                    
                #     # Formatting untuk tabel kecil
                #     penjualan_detail['subtotal_fmt'] = penjualan_detail['subtotal'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                #     penjualan_detail['harga_fmt'] = penjualan_detail['harga_satuan'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
                    
                #     st.dataframe(
                #         penjualan_detail[['tanggal', 'no_nota', 'kuantitas', 'harga_fmt', 'subtotal_fmt']].rename(columns={
                #             'tanggal': 'Tanggal',
                #             'no_nota': 'No. Nota',
                #             'kuantitas': 'Qty',
                #             'harga_fmt': 'Harga Jual',
                #             'subtotal_fmt': 'Subtotal'
                #         }),
                #         use_container_width=True,
                #         hide_index=True
                #     )

            # TAB 4 : DETAIL PERHITUNGAN GROSS PROFIT
            with tab4:
                st.subheader("📐 Detail Perhitungan")
    
                # st.info("💡 **Kartu stok ini menampilkan tracking FIFO untuk setiap transaksi penjualan**. "
                #         "Setiap baris menunjukkan dari pembelian mana HPP diambil (metode FIFO).")
                
                selected_barang = st.selectbox(
                    "Pilih Barang untuk Kartu Stok:",
                    options=gp_df['nama_barang'].tolist(),
                    key='kartu_stok_barang'
                )
                
                if selected_barang:
                    barang_data = gp_df[gp_df['nama_barang'] == selected_barang].iloc[0]
                    barang_id = barang_data['id_barang']
                    
                    # === SUMMARY CARDS ===
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Total Qty Terjual",
                            f"{barang_data['qty_terjual']:,.0f} pcs"
                        )
                    
                    with col2:
                        st.metric(
                            "Total Penjualan",
                            f"Rp {barang_data['total_penjualan']:,.0f}".replace(",", ".")
                        )
                    
                    with col3:
                        st.metric(
                            "Total HPP",
                            f"Rp {barang_data['total_hpp']:,.0f}".replace(",", ".")
                        )
                    
                    with col4:
                        st.metric(
                            "Gross Profit",
                            f"Rp {barang_data['gross_profit']:,.0f}".replace(",", "."),
                            delta=f"{barang_data['margin_persen']:.2f}%"
                        )
                    
                    st.markdown("---")
                    
                    # === GENERATE KARTU STOK ===
                    kartu_stok = new_database.generate_kartu_stok_fifo(
                        barang_id, 
                        pembelian_df, 
                        penjualan_df
                    )
                    
                    if not kartu_stok.empty:
                        # === SECTION 1: RIWAYAT PEMBELIAN (Stock In) ===
                        st.markdown("### 📥 Riwayat Pembelian (Stock In)")
                        
                        pembelian_barang = pembelian_df[
                            (pembelian_df['id_barang'] == barang_id) & 
                            (pembelian_df['tipe'] == 'Barang')
                        ].copy()
                        
                        # Mapping ongkir
                        ongkir_map = {}
                        ongkir_rows = pembelian_df[
                            (pembelian_df['id_barang'] == barang_id) & 
                            (pembelian_df['tipe'] == 'Ongkir')
                        ]
                        for _, ongkir_row in ongkir_rows.iterrows():
                            key = (ongkir_row['tanggal'], ongkir_row['id_barang'])
                            ongkir_map[key] = float(ongkir_row['subtotal'])
                        
                        # Format pembelian untuk display
                        pembelian_display = []
                        for _, row in pembelian_barang.iterrows():
                            key = (row['tanggal'], barang_id)
                            ongkir = ongkir_map.get(key, 0)
                            hpp_unit = (row['subtotal'] + ongkir) / row['kuantitas']
                            
                            pembelian_display.append({
                                'Tanggal': pd.to_datetime(row['tanggal']).strftime('%d %b %Y'),
                                'No. Nota': row['no_nota'],
                                'Qty': f"{row['kuantitas']:.0f} pcs",
                                'Harga Barang': f"Rp {row['subtotal']:,.0f}".replace(",", "."),
                                'Ongkir': f"Rp {ongkir:,.0f}".replace(",", "."),
                                'HPP/pcs': f"Rp {hpp_unit:,.0f}".replace(",", "."),
                                'Total HPP': f"Rp {(row['subtotal'] + ongkir):,.0f}".replace(",", ".")
                            })
                        
                        st.dataframe(
                            pd.DataFrame(pembelian_display),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        st.markdown("---")
                        
                        # === SECTION 2: KARTU STOK PENJUALAN (Stock Out) ===
                        st.markdown("### 📤 Riwayat Penjualan (Stock Out)")
                        
                        # Format untuk display
                        kartu_display = kartu_stok.copy()
                        kartu_display['Tanggal'] = pd.to_datetime(kartu_display['tanggal']).dt.strftime('%d %b %Y')
                        kartu_display['No. Nota'] = kartu_display['no_nota']
                        kartu_display['Qty'] = kartu_display['qty'].apply(lambda x: f"{x:.0f} pcs")
                        kartu_display['Harga Jual'] = kartu_display['harga_jual'].apply(
                            lambda x: f"Rp {x:,.0f}".replace(",", ".")
                        )
                        kartu_display['HPP Avg/pcs'] = kartu_display['hpp_avg'].apply(
                            lambda x: f"Rp {x:,.0f}".replace(",", ".")
                        )
                        kartu_display['Total Penjualan'] = kartu_display['subtotal'].apply(
                            lambda x: f"Rp {x:,.0f}".replace(",", ".")
                        )
                        kartu_display['Total HPP'] = kartu_display['total_hpp'].apply(
                            lambda x: f"Rp {x:,.0f}".replace(",", ".")
                        )
                        kartu_display['Gross Profit'] = kartu_display['gross_profit'].apply(
                            lambda x: f"Rp {x:,.0f}".replace(",", ".")
                        )
                        kartu_display['Margin'] = kartu_display['margin_persen'].apply(
                            lambda x: f"{x:.2f}%"
                        )
                        
                        # Tampilkan tabel utama
                        st.dataframe(
                            kartu_display[[
                                'Tanggal', 'No. Nota', 'Qty', 'Harga Jual', 'HPP Avg/pcs',
                                'Total Penjualan', 'Total HPP', 'Gross Profit', 'Margin'
                            ]],
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # === SECTION 3: BREAKDOWN HPP PER TRANSAKSI ===
                        st.markdown("#### 🔍 Detail Alokasi HPP (FIFO)")
                        
                        with st.expander("📖 Lihat detail dari mana HPP setiap transaksi diambil"):
                            for idx, row in kartu_stok.iterrows():
                                st.markdown(f"**{row['no_nota']}** ({pd.to_datetime(row['tanggal']).strftime('%d %b %Y')}) - "
                                        f"{row['qty']:.0f} pcs:")
                                st.caption(f"└─ {row['hpp_breakdown']}")
                                if idx < len(kartu_stok) - 1:
                                    st.markdown("")
                        
                        # === DOWNLOAD BUTTON ===
                        st.markdown("---")
                        
                        # Prepare CSV export
                        export_df = kartu_stok.copy()
                        export_df['tanggal'] = pd.to_datetime(export_df['tanggal']).dt.strftime('%Y-%m-%d')
                        
                        csv = export_df.to_csv(index=False)
                        st.download_button(
                            label=f"📥 Download Kartu Stok {selected_barang} (CSV)",
                            data=csv,
                            file_name=f"kartu_stok_{selected_barang}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                        
                    else:
                        st.warning("⚠️ Tidak ada data kartu stok untuk barang ini.")

except Exception as e:
    st.error(f"❌ Terjadi kesalahan: {str(e)}")
    # st.exception(e) # Uncomment ini jika ingin melihat detail error teknis untuk debugging