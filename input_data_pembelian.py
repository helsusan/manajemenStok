import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(
    page_title="Data Pembelian",
    page_icon="🛒",
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

st.header("Data Pembelian")

tab1, tab2, tab3 = st.tabs(["📝 Input Manual", "📤 Upload Excel", "📋 Daftar Pembelian"])

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
        
        data_supplier = new_database.get_all_data_supplier(columns="nama")
        nama_supplier = st.selectbox(
            "Nama Supplier",
            options=data_supplier["nama"].tolist(),
            help="Pilih supplier yang telah terdaftar"
        )
        
        data_barang = new_database.get_all_data_barang(columns="nama")
        jenis_barang = st.selectbox(
            "Jenis Barang",
            options=data_barang["nama"].tolist(),
            help="Pilih jenis barang yang telah terdaftar"
        )

        tipe_pembelian = st.selectbox(
            "Tipe Pembelian",
            options=["Barang", "Ongkir"],
            help="Barang = harga beli barang, Ongkir = biaya pengiriman"
        )

    with col2:
        kuantitas = st.number_input(
            "Kuantitas:",
            min_value=0,
            step=1,
            format="%d",
            key="input_kuantitas"
        )
        
        harga_satuan = new_database.get_harga_supplier(nama_supplier, jenis_barang)
        st.text_input(
            "Harga Satuan",
            value=f"Rp {harga_satuan:,.0f}".replace(",", "."),
            disabled=True
        )
        
        total = kuantitas * harga_satuan

        st.text_input(
            "Total ",
            value=f"Rp {total:,.0f}".replace(",", "."),
            disabled=True
        )

        top = st.number_input(
            "Term of Payment (hari)",
            min_value=0,
            step=1,
            format="%d",
            help="Pembayaran harus lunas dalam berapa hari"
        )
    
    st.markdown("---")
    
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
            "Nama Pelanggan": nama_supplier,
            "Keterangan Barang": jenis_barang,
            "Kuantitas": kuantitas,
            "Harga Satuan": float(harga_satuan),
            "Jumlah": float(total)
        }])

        success, failed, errors = new_database.insert_pembelian(df_input, default_top=top)

        if success > 0:
            st.success("✅ Transaksi berhasil disimpan")
        else:
            st.error("❌ Gagal menyimpan transaksi")
            if errors:
                st.error(errors[0])

# ================================================
# TAB 2 : UPLOAD EXCEL
# ================================================

with tab2:
    st.subheader("📤 Upload File Excel")
    
    with st.expander("ℹ️ Format file Excel data pembelian"):
        st.write("""
        - Kolom wajib: `No Faktur`, `Tgl Faktur`, `Nama Pelanggan`, `Keterangan Barang`, `Kuantitas`, `Jumlah`
        - Kolom opsional: `TOP`
        - Nama Barang dan Supplier harus sudah ada di database
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
            top_excel = st.number_input(
                "Term of Payment untuk seluruh data (hari)",
                min_value=0,
                step=1,
                format="%d",
                help="Semua transaksi dari file Excel pembayarannya harus lunas dalam berapa hari"
            )

            if st.button("💾 Simpan", type="primary", use_container_width=True):
                if top_excel == "":
                    st.error("⚠️ Term of Payment wajib diisi")
                    st.stop()
                with st.spinner("Mengupload data ke database..."):
                    success_count, error_count, errors = new_database.insert_pembelian(df, default_top=top_excel)
                            
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
    st.subheader("📋 Daftar Transaksi Pembelian")

    with st.expander("ℹ️ Info edit & hapus transaksi"):
        st.write("""
        - Pilih checkbox untuk menandai transaksi yang akan dihapus. Klik tombol `Hapus Data Terpilih` untuk menghapus transaksi yang ditandai.
        - Jika ingin edit data, hapus data lama dan input kembali pada tab `Input Manual`.
        
        ⚠️ Menghapus transaksi bersifat permanen dan tidak dapat dikembalikan
        """)

    col1, col2, col3 = st.columns([1.5, 1.5, 1.5])

    with col1:
        selected_date = st.date_input(
            "Filter Tanggal",
            value=None,
            help="Kosongkan untuk tampilkan semua data"
        )

    with col2:
        data_supplier = new_database.get_all_data_supplier(columns="nama")
        supplier_options = ["Semua"] + data_supplier["nama"].tolist()
        selected_pelanggan = st.selectbox("👤 Nama Supplier", supplier_options)

    with col3:
        data_barang = new_database.get_all_data_barang(columns="nama")
        barang_options = ["Semua"] + data_barang["nama"].tolist()
        selected_barang = st.selectbox("📦 Nama Barang", barang_options)

    # ======================
    # AMBIL DATA
    # ======================
    df_pembelian = new_database.get_data_pembelian(
        tanggal=selected_date,
        supplier=selected_pelanggan,
        barang=selected_barang
    )

    if not df_pembelian.empty:
        df_pembelian['tanggal'] = pd.to_datetime(df_pembelian['tanggal']).dt.strftime('%d %b %Y')

        df_pembelian['subtotal'] = df_pembelian['subtotal'].apply(
            lambda x: f"Rp {x:,.0f}".replace(",", ".")
        )

        if 'total_nota' in df_pembelian.columns:
            df_pembelian['total_nota'] = df_pembelian['total_nota'].apply(
                lambda x: f"Rp {x:,.0f}".replace(",", ".")
            )

        # Hitung total transaksi yang tertampil
        total_transaksi = len(df_pembelian)
        st.info(f"Menampilkan {total_transaksi} transaksi")

        # Tambah kolom checkbox untuk hapus
        df_pembelian.insert(0, 'Hapus', False)

        # Prepare kolom untuk ditampilkan (hide id)
        df_display = df_pembelian[['Hapus', 'no_nota', 'tanggal', 'nama_supplier', 'nama_barang', 'kuantitas', 'subtotal', 'total_nota', 'top']].copy()

        column_config = {
            "Hapus": st.column_config.CheckboxColumn("Pilih"),
            "no_nota": st.column_config.TextColumn("No. Faktur"),
            "tanggal": st.column_config.TextColumn("Tanggal"),
            "nama_supplier": st.column_config.TextColumn("Supplier"),
            "nama_barang": st.column_config.TextColumn("Barang"),
            "kuantitas": st.column_config.NumberColumn("Qty"),
            "subtotal": st.column_config.TextColumn("Subtotal"),
            "total_nota": st.column_config.TextColumn("Total"),
            "top": st.column_config.NumberColumn("Terms of Payment (hari)"),
        }

        edited_df = st.data_editor(
            df_display,
            hide_index=True,
            use_container_width=True,
            disabled=["no_nota", "tanggal", "nama_supplier", "nama_barang", "kuantitas", "subtotal", "total_nota", "top"],
            column_config=column_config,
            key="pembelian_editor"
        )

        # Ambil baris yang dicentang
        selected_rows = edited_df[edited_df['Hapus'] == True]

        if not selected_rows.empty:
            # Ambil ID dari dataframe asli berdasarkan index yang sama
            selected_ids = df_pembelian.loc[selected_rows.index, 'id'].unique()
            
            st.warning(f"⚠️ {len(selected_ids)} transaksi akan dihapus")

            if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                try:
                    with st.spinner("Menghapus data..."):
                        for pid in selected_ids:
                            new_database.delete_pembelian(pid)

                    st.success("✅ Data berhasil dihapus")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Gagal menghapus data: {str(e)}")
    else:
        st.warning("⚠️ Tidak ada data transaksi sesuai filter")


# Footer
# st.markdown("---")
# st.markdown("""
#     <div style='text-align: center; color: #666; padding: 10px;'>
#         <small>📦 Sistem Kelola Data Barang | Developed with Streamlit</small>
#     </div>
# """, unsafe_allow_html=True)