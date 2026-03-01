import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import new_database
from io import BytesIO

st.set_page_config(
    page_title="Gross Profit Analysis",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Gross Profit Analysis")

# ==================== FILTER SECTION (MAIN PAGE) ====================
col_filter1, col_filter2, col_filter3 = st.columns([1, 1, 2])

with col_filter1:
    st.subheader("1. Periode")
    periode_option = st.radio(
        "Pilih Tipe Periode:",
        ["Keseluruhan", "Per Bulan", "Custom Range Tanggal"],
        label_visibility="collapsed"
    )

start_date = None
end_date = None

with col_filter2:
    st.subheader("2. Rentang Waktu")
    if periode_option == "Per Bulan":
        col_b, col_t = st.columns(2)
        
        bulan_list = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                      "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        with col_b:
            selected_month_name = st.selectbox("Pilih Bulan:", bulan_list, index=datetime.now().month - 1)
            
        with col_t:
            current_year = datetime.now().year
            # Pilihan tahun dari 5 tahun lalu hingga tahun saat ini
            selected_year = st.selectbox("Pilih Tahun:", range(current_year - 5, current_year + 1), index=5)
            
        selected_month_int = bulan_list.index(selected_month_name) + 1
        
        start_date = datetime(selected_year, selected_month_int, 1).date()
        if selected_month_int == 12:
            end_date = datetime(selected_year, 12, 31).date()
        else:
            end_date = (datetime(selected_year, selected_month_int, 28) + timedelta(days=4)).replace(day=1).date() - timedelta(days=1)
        
        st.info(f"📅 {start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}")

    elif periode_option == "Custom Range Tanggal":
        selected_date = st.date_input(
            "Tanggal",
            value=[],
        )

        start_date, end_date = None, None
        if len(selected_date) == 2:
            start_date, end_date = selected_date
        elif len(selected_date) == 1:
            start_date = end_date = selected_date[0]
    
    else:
        st.info("📅 Menampilkan semua data historis")

with col_filter3:
    st.subheader("3. Filter Barang")
    try:
        barang_list = new_database.get_barang_list_simple()
        filter_barang = st.multiselect(
            "Nama Barang",
            options=barang_list['nama'].tolist(),
            default=None,
            help="Kosongkan untuk memilih semua."
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
            tab1, tab2, tab3 = st.tabs([
                "📋 Tabel Gross Profit", 
                "📐 Detail Perhitungan",
                "📊 Visualisasi"
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
                
                # Download Excel
                output = BytesIO()
                gp_df.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)

                tanggal_download = datetime.now().strftime("%d-%m-%Y")
                
                st.download_button(
                    label="📥 Download Data (Excel)",
                    data=output,
                    file_name=f"Gross Profit_{tanggal_download}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # TAB 2 : DETAIL PERHITUNGAN GROSS PROFIT
            with tab2:
                st.subheader("📐 Detail Perhitungan")
                
                selected_barang = st.selectbox(
                    "Pilih Barang",
                    options=gp_df['nama_barang'].tolist(),
                    key='kartu_stok_barang'
                )
                
                if selected_barang:
                    barang_data = gp_df[gp_df['nama_barang'] == selected_barang].iloc[0]
                    barang_id = barang_data['id_barang']

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
                        
                        # Prepare Excel export
                        output = BytesIO()
                        gp_df.to_excel(output, index=False, engine='openpyxl')
                        output.seek(0)
                        
                        st.download_button(
                            label="📥 Download Data (Excel)",
                            data=output,
                            file_name=f"gross profit_{selected_barang}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                    else:
                        st.warning("⚠️ Tidak ada data kartu stok untuk barang ini.")

            # TAB 3: TOP PRODUCTS + VISUALISASI
            with tab3:
                st.subheader("Top 10 Products")
                
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
                
                st.markdown("---")
                st.subheader("Penjualan vs Gross Profit")
                
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

except Exception as e:
    st.error(f"❌ Terjadi kesalahan: {str(e)}")
    # st.exception(e) # Uncomment ini jika ingin melihat detail error teknis untuk debugging