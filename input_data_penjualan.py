import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

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

tab1, tab2, tab3 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Daftar Penjualan"])

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
    
    col1, col2 = st.columns(2)
    
    with col1:
        no_faktur = st.text_input("No Faktur")
        
        tanggal = st.date_input(
            "Tanggal",
            value=datetime.now(),
            help="Pilih tanggal transaksi",
            format="DD/MM/YYYY"
        )
        
        data_customer = new_database.get_all_data_customer(columns="nama")
        nama_customer = st.selectbox(
            "Nama Customer",
            options=data_customer["nama"].tolist(),
            help="Pilih customer yang telah terdaftar"
        )
        
        data_barang = new_database.get_all_data_barang(columns="nama")
        jenis_barang = st.selectbox(
            "Jenis Barang",
            options=data_barang["nama"].tolist(),
            help="Pilih jenis barang yang telah terdaftar"
        )

    with col2:
        kuantitas = st.number_input(
            "Kuantitas:",
            min_value=0,
            step=1,
            format="%d",
            key="input_kuantitas"
        )
        
        harga_satuan = new_database.get_harga_customer(nama_customer, jenis_barang)
        st.text_input(
            "Harga Satuan",
            value=f"Rp {harga_satuan:,.0f}".replace(",", "."),
            disabled=True
        )
        
        total = kuantitas * harga_satuan        
        st.markdown(f"""
            <div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px; border-left: 4px solid #0066cc;'>
                <p style='margin: 0; font-size: 14px; color: #666;'>Total yang harus dibayar:</p>
                <p style='margin: 0; font-size: 24px; font-weight: bold; color: #0066cc;'>
                    Rp {total:,.0f}
                </p>
            </div>
        """.replace(",", "."), unsafe_allow_html=True)

        top = st.selectbox(
            "Term of Payment:",
            options=["", "Cash", "Tempo 7 Hari", "Tempo 14 Hari", "Tempo 30 Hari", "Tempo 45 Hari"],
            help="Pilih terms of payment"
        )
    
    # Tombol Aksi
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([1, 1, 1, 3])
    
    with col_btn1:
        if st.button("💾 Simpan", type="primary", use_container_width=True, key="btn_input_manual"):
            # ======================
            # VALIDASI SEDERHANA
            # ======================
            if not no_faktur:
                st.error("No Faktur wajib diisi")
                st.stop()

            if kuantitas <= 0:
                st.error("Kuantitas harus lebih dari 0")
                st.stop()

            # ======================
            # BENTUK DATAFRAME SESUAI INSERT_PENJUALAN
            # ======================
            df_input = pd.DataFrame([{
                "No. Faktur": no_faktur,
                "Tgl Faktur": tanggal,
                "Nama Pelanggan": nama_customer,
                "Keterangan Barang": jenis_barang,
                "Kuantitas": kuantitas,
                "Harga Satuan": float(harga_satuan),
                "Jumlah": float(total)
            }])

            success, failed, errors = new_database.insert_penjualan(df_input, default_top=top)

            if success > 0:
                st.success("✅ Transaksi berhasil disimpan")
            else:
                st.error("❌ Gagal menyimpan transaksi")
                if errors:
                    st.error(errors[0])

            # Validasi input
            # if customer_id == "" or jenis_barang == "" or top == "":
            #     st.error("⚠️ Mohon lengkapi semua data yang diperlukan!")
            # elif jumlah <= 0:
            #     st.error("⚠️ Jumlah harus lebih dari 0!")
            # else:
            #     st.success(f"✅ Data transaksi No. {no_nota} berhasil disimpan!")
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
        - Kolom wajib: `No Faktur`, `Tgl Faktur`, `Nama Pelanggan`, `Keterangan Barang`, `Kuantitas`, `Jumlah`
        - Kolom opsional: `TOP`
        - Nama Barang dan Customer harus sudah ada di database
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
            df = new_database.clean_excel_apostrophe(df)

            st.success("✅ Data berhasil dibersihkan!")
                    
            st.subheader("📋 Preview Data")
            st.dataframe(df.head(10), use_container_width=True)
            st.info(f"Total baris: {len(df)}")

            # ======================
            # INPUT TOP
            # ======================
            top_excel = st.selectbox(
                "Term of Payment untuk seluruh data:",
                options=[
                    "",
                    "Cash",
                    "Tempo 7 Hari",
                    "Tempo 14 Hari",
                    "Tempo 30 Hari",
                    "Tempo 45 Hari"
                ],
                help="TOP ini akan diterapkan ke semua transaksi dari file Excel"
            )

            if st.button("💾 Simpan", type="primary", use_container_width=True):
                if top_excel == "":
                    st.error("⚠️ Term of Payment wajib dipilih")
                    st.stop()
                with st.spinner("Mengupload data ke database..."):
                    success_count, error_count, errors = new_database.insert_penjualan(df, default_top=top_excel)
                    # success_count = len(df)
                    # error_count = 0
                    # errors = []
                            
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

    col1, col2, col3, col4 = st.columns([1.2, 1.5, 1.5, 3])

    with col1:
        selected_date = st.date_input(
            "Filter Tanggal",
            value=None,
            help="Kosongkan untuk tampilkan semua data"
        )

    with col2:
        data_customer = new_database.get_all_data_customer(columns="nama")
        customer_options = ["Semua"] + data_customer["nama"].tolist()
        selected_pelanggan = st.selectbox("👤 Nama Pelanggan", customer_options)

    with col3:
        data_barang = new_database.get_all_data_barang(columns="nama")
        barang_options = ["Semua"] + data_barang["nama"].tolist()
        selected_barang = st.selectbox("📦 Nama Barang", barang_options)

    # ======================
    # AMBIL DATA
    # ======================
    df_penjualan = new_database.get_penjualan_data(
        tanggal=selected_date,
        customer=selected_pelanggan,
        barang=selected_barang
    )

    if not df_penjualan.empty:
        df_penjualan['tanggal'] = pd.to_datetime(df_penjualan['tanggal']).dt.strftime('%d %b %Y')
        df_penjualan['subtotal'] = df_penjualan['subtotal'].apply(
            lambda x: f"Rp {x:,.0f}".replace(",", ".")
        )

        df_penjualan.insert(0, 'Hapus', False)

        edited_df = st.data_editor(
            df_penjualan,
            hide_index=True,
            use_container_width=True,
            disabled=True,
            column_config={
                "Hapus": st.column_config.CheckboxColumn("Pilih"),
                "id": None
            }
        )

        selected = edited_df[edited_df['Hapus'] == True]

        if not selected.empty:
            st.warning(f"⚠️ {len(selected)} transaksi akan dihapus")

            if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                for pid in selected['id'].unique():
                    database.delete_penjualan(pid)

                st.success("✅ Data berhasil dihapus")
                st.rerun()
    else:
        st.warning("Tidak ada data transaksi")


# Footer
# st.markdown("---")
# st.markdown("""
#     <div style='text-align: center; color: #666; padding: 10px;'>
#         <small>📦 Sistem Kelola Data Barang | Developed with Streamlit</small>
#     </div>
# """, unsafe_allow_html=True)