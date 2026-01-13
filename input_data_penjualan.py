import streamlit as st
import pandas as pd
from datetime import datetime
import database

# Konfigurasi halaman
st.set_page_config(
    page_title="Data Penjualan",
    page_icon="",
    layout="wide"
)

# Header
# st.markdown("""
#     <div style='background-color: #28a745; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
#         <h1 style='color: white; text-align: center; margin: 0;'>
#             📦 KELOLA DATA BARANG
#         </h1>
#     </div>
# """, unsafe_allow_html=True)

st.header("Data Penjualan")

tab1, tab2, tab3 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Data Penjualan"])

# ================================================
# TAB 1 : INPUT MANUAL
# ================================================

with tab1:
    st.subheader("➕ Input Transaksi Baru")

    # Initialize session state untuk harga total
    if 'jumlah' not in st.session_state:
        st.session_state.jumlah = 0
    if 'harga_satuan' not in st.session_state:
        st.session_state.harga_satuan = 0

    # Data dummy untuk dropdown (nanti diganti dengan query database)
    data_customer = {
        "": {"nama": "Pilih Customer", "harga": []},
        "CUST001": {"nama": "PT. Maju Jaya", "harga": [50000, 75000, 100000]},
        "CUST002": {"nama": "CV. Berkah Sejahtera", "harga": [60000, 80000, 120000]},
        "CUST003": {"nama": "UD. Sumber Rezeki", "harga": [45000, 70000, 95000]}
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        no_faktur = st.text_input("No Faktur")
        
        tanggal = st.date_input(
            "Tanggal",
            value=datetime.now(),
            help="Pilih tanggal transaksi"
        )
        
        customer_id = st.selectbox(
            "Nama Customer",
            options=list(data_customer.keys()),
            format_func=lambda x: data_customer[x]["nama"],
            help="Pilih customer dari database"
        )
        
        # Jenis Barang
        jenis_barang = st.selectbox(
            "Jenis Barang:",
            options=list(database.get_all_nama_barang()),
            format_func=lambda x: data_barang[x],
            help="Pilih jenis barang dari database"
        )
    
    with col2:
        # Jumlah
        jumlah = st.number_input(
            "Jumlah:",
            min_value=0,
            step=1,
            format="%d",
            help="Masukkan jumlah barang",
            key="input_jumlah"
        )
        
        # Harga Satuan - dropdown dari data customer
        harga_options = data_customer[customer_id]["harga"] if customer_id else [0]
        harga_satuan = st.selectbox(
            "Harga Satuan:",
            options=harga_options,
            format_func=lambda x: f"Rp {x:,.0f}".replace(",", "."),
            help="Pilih harga satuan berdasarkan customer",
            disabled=(customer_id == "")
        )
        
        # Harga Total - otomatis calculate
        harga_total = jumlah * harga_satuan
        st.number_input(
            "Harga Total:",
            value=harga_total,
            disabled=True,
            format="%d",
            help="Harga total dihitung otomatis (Jumlah × Harga Satuan)"
        )
        
        # Tampilkan dalam format Rupiah
        st.markdown(f"""
            <div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px; border-left: 4px solid #0066cc;'>
                <p style='margin: 0; font-size: 14px; color: #666;'>Total yang harus dibayar:</p>
                <p style='margin: 0; font-size: 24px; font-weight: bold; color: #0066cc;'>
                    Rp {harga_total:,.0f}
                </p>
            </div>
        """.replace(",", "."), unsafe_allow_html=True)
        
        # Term of Payment
        top = st.selectbox(
            "Term of Payment:",
            options=["", "Cash", "Tempo 7 Hari", "Tempo 14 Hari", "Tempo 30 Hari", "Tempo 45 Hari"],
            help="Pilih metode pembayaran"
        )
    
    st.markdown("---")
    
    # Tombol Aksi
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 3])
    
    with col_btn1:
        if st.button("💾 Simpan", type="primary", use_container_width=True):
            # Validasi input
            if customer_id == "" or jenis_barang == "" or top == "":
                st.error("⚠️ Mohon lengkapi semua data yang diperlukan!")
            elif jumlah <= 0:
                st.error("⚠️ Jumlah harus lebih dari 0!")
            else:
                st.success(f"✅ Data transaksi No. {no_nota} berhasil disimpan!")
                # Di sini bisa tambahkan kode untuk menyimpan ke database
    
    with col_btn2:
        if st.button("🔄 Reset", use_container_width=True):
            st.rerun()

# ================================================
# TAB 2 : UPLOAD EXCEL
# ================================================

with tab2:
    st.subheader("📤 Upload File Excel")
    
    with st.expander("ℹ️ Format file Excel data penjualan"):
        st.write("""
        - Kolom: `No Faktur`, `Tgl Faktur`, `Nama Pelanggan`, `Keterangan Barang`, `Kuantitas`, `Jumlah`
        - Nama Barang harus sudah ada di database
        """)
    
    uploaded_file = st.file_uploader(
        "Pilih file Excel",
        type=["xlsx"],
        help="Upload file Excel dengan format yang sesuai"
    )
    
    if uploaded_file is not None:
        try:
            df_raw = pd.read_excel(uploaded_file, header=None)

            EXPECTED_COLS = ["Tgl Faktur", "No. Faktur", "Nama Pelanggan", "Keterangan Barang", "Kuantitas", "Jumlah"]

            header_row_index = None

            for i, row in df_raw.iterrows():
                row_str = row.astype(str).str.upper()
                if all(any(col.upper() in cell for cell in row_str) for col in EXPECTED_COLS):
                    header_row_index = i
                    break

            df = pd.read_excel(uploaded_file, header=header_row_index)

            df = df.dropna(how="all")
            df = df[EXPECTED_COLS]
            df = database.clean_excel_apostrophe(df)

            st.success("✅ Data berhasil dibersihkan!")
                    
            st.subheader("📋 Preview Data")
            st.dataframe(df.head(10), use_container_width=True)
            st.info(f"Total baris: {len(df)}")

            if st.button("💾 Simpan", type="primary", use_container_width=True):
                with st.spinner("Mengupload data ke database..."):
                    success_count, error_count, errors = database.insert_data_transaksi(df)
                    success_count = len(df)
                    error_count = 0
                    errors = []
                            
                if success_count > 0:
                    st.success(f"✅ Berhasil mengupload {success_count} baris data!")
                            
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} baris gagal diupload")
                                
                    with st.expander("Lihat detail error"):
                        for error in errors[:20]:
                            st.error(error)
                                    
                        if len(errors) > 20:
                            st.info(f"... dan {len(errors) - 20} error lainnya")
        except Exception as e:
            st.error(f"❌ Error membaca file: {str(e)}")

# ================================================
# TAB 3 : TABEL PENJUALAN
# ================================================

with tab3:
    st.subheader("📋 Daftar Transaksi Penjualan")
    
    # Filter tanggal
    col1, col2, col3, col4 = st.columns([1.2, 1.5, 1.5, 3])
    
    with col1:
        # Simulasi data tanggal (nanti ganti dengan query database)
        all_dates_query = "SELECT DISTINCT DATE(tgl_faktur) as tanggal FROM penjualan ORDER BY tanggal DESC"
        all_dates_result = database.run_query(all_dates_query)
        
        # Sementara data dummy
        available_dates = [datetime.now().date()]
        
        # Date input dengan calendar
        selected_date = st.date_input(
            "Filter Tanggal",
            value=None,
            help="Kosongkan untuk tampilkan semua data"
        )
    
    with col2:
        pelanggan_list = database.run_query("""
            SELECT DISTINCT nama_pelanggan
            FROM penjualan
            ORDER BY nama_pelanggan
        """)
        pelanggan_options = ["Semua"] + [p[0] for p in pelanggan_list]

        selected_pelanggan = st.selectbox(
            "👤 Nama Pelanggan",
            pelanggan_options
        )

    with col3:
        barang_list = database.run_query("""
            SELECT DISTINCT b.nama
            FROM barang b
            JOIN penjualan p ON p.id_barang = b.id
            ORDER BY b.nama
        """)
        barang_options = ["Semua"] + [b[0] for b in barang_list]

        selected_barang = st.selectbox(
            "📦 Nama Barang",
            barang_options
        )
    
    # Query data transaksi
    try:
        query = """
            SELECT 
                p.id,
                p.no_faktur AS 'No Faktur',
                p.tgl_faktur AS 'Tgl Faktur',
                p.nama_pelanggan AS 'Nama Pelanggan',
                b.nama AS 'Nama Barang',
                p.kuantitas AS 'Kuantitas',
                p.jumlah AS 'Jumlah'
            FROM penjualan p
            JOIN barang b ON p.id_barang = b.id
            WHERE 1=1
        """

        params = []

        if selected_date:
            query += " AND DATE(p.tgl_faktur) = %s"
            params.append(selected_date)

        if selected_pelanggan != "Semua":
            query += " AND p.nama_pelanggan = %s"
            params.append(selected_pelanggan)

        if selected_barang != "Semua":
            query += " AND b.nama = %s"
            params.append(selected_barang)

        query += " ORDER BY p.tgl_faktur DESC"

        conn = database.get_connection()
        df_penjualan = pd.read_sql(query, conn, params=params)
        conn.close()
            
        if not df_penjualan.empty:
            # FORMAT TANGGAL → 13 Jan 2025
            df_penjualan['Tgl Faktur'] = pd.to_datetime(df_penjualan['Tgl Faktur']).dt.strftime('%d %b %Y')
            
            # Format harga ke Rupiah
            df_penjualan['Jumlah'] = df_penjualan['Jumlah'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            
            # Tambahkan kolom select untuk delete
            df_penjualan.insert(0, 'Hapus', False)
            
            # Tampilkan dengan data_editor
            edited_df = st.data_editor(
                df_penjualan,
                use_container_width=True,
                column_config={
                    "Hapus": st.column_config.CheckboxColumn(
                        "Pilih",
                        help="Centang untuk menghapus data",
                        default=False
                    ),
                    "id": None,  # Hide ID column
                    "Tgl Faktur": st.column_config.TextColumn("Tgl Faktur"),
                    "Nama Customer": st.column_config.TextColumn("Nama Customer"),
                    "Nama Barang": st.column_config.TextColumn("Nama Barang"),
                    "Kuantitas": st.column_config.TextColumn("Kuantitas"),
                    "Jumlah": st.column_config.TextColumn("Jumlah")
                },
                disabled=["No Faktur", "Tgl Faktur", "Nama Pelanggan", "Nama Barang", "Kuantitas", "Jumlah"],
                hide_index=True,
                key="penjualan_editor"
            )
            
            # Tombol delete
            selected_for_delete = edited_df[edited_df['Hapus'] == True]
            
            if len(selected_for_delete) > 0:
                st.warning(f"⚠️ {len(selected_for_delete)} data akan dihapus")
                
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                        try:
                            conn = database.get_connection()
                            cursor = conn.cursor()
                            
                            deleted_count = 0
                            for idx, row in selected_for_delete.iterrows():
                                delete_query = "DELETE FROM transaksi WHERE id = %s"
                                cursor.execute(delete_query, (int(row['id']),))
                                deleted_count += 1
                            
                            conn.commit()
                            cursor.close()
                            conn.close()
                            
                            st.success(f"✅ Berhasil menghapus {deleted_count} data!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            
            # Info jumlah data
            st.caption(f"📊 Total: {len(df_penjualan)} data")
        else:
            st.warning("Tidak ada data transaksi" + (f" pada tanggal {selected_date}" if selected_date else ""))
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Footer
# st.markdown("---")
# st.markdown("""
#     <div style='text-align: center; color: #666; padding: 10px;'>
#         <small>📦 Sistem Kelola Data Barang | Developed with Streamlit</small>
#     </div>
# """, unsafe_allow_html=True)