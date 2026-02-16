import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(
    page_title="Data Penjualan",
    page_icon="🛍️",
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

        if not data_customer.empty:
            data_customer = data_customer.sort_values("nama")

        nama_customer = st.selectbox(
            "Nama Customer",
            options=data_customer["nama"].tolist(),
            help="Pilih customer yang telah terdaftar"
        )
        
        data_barang = new_database.get_all_data_barang(columns="nama")

        if not data_barang.empty:
            data_barang = data_barang.sort_values("nama")

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

        if harga_satuan is None:
            harga_satuan = 0

        st.text_input(
            "Harga Satuan",
            value=f"Rp {harga_satuan:,.0f}".replace(",", "."),
            disabled=True
        )
        
        total = kuantitas * harga_satuan        
        # st.markdown(f"""
        #     <div style='background-color: #e8f4f8; padding: 10px; border-radius: 5px; border-left: 4px solid #0066cc;'>
        #         <p style='margin: 0; font-size: 14px; color: #666;'>Total yang harus dibayar:</p>
        #         <p style='margin: 0; font-size: 24px; font-weight: bold; color: #0066cc;'>
        #             Rp {total:,.0f}
        #         </p>
        #     </div>
        # """.replace(",", "."), unsafe_allow_html=True)

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
        # CEK VALIDASI NOTA & DUPLIKASI
        # ======================
        # Ambil data transaksi berdasarkan customer saja (agar bisa mengecek seluruh barang di nota tersebut)
        df_existing = new_database.get_data_penjualan(
            customer=nama_customer
        )
        
        if not df_existing.empty:
            # Bersihkan dan samakan tipe data
            df_existing["no_nota_str"] = df_existing["no_nota"].astype(str).str.strip()
            df_existing["tanggal_date"] = pd.to_datetime(df_existing["tanggal"]).dt.date
            df_existing["qty_int"] = df_existing["kuantitas"].fillna(0).astype(int)
            df_existing["top_int"] = df_existing["top"].fillna(0).astype(int)
            
            # Cari apakah Nota & Tanggal ini sudah ada di database
            same_nota = df_existing[
                (df_existing["no_nota_str"] == str(no_faktur).strip()) &
                (df_existing["tanggal_date"] == tanggal)
            ]
            
            if not same_nota.empty:
                # 1️⃣ CEK KONSISTENSI TOP
                # Ambil nilai TOP yang sudah tersimpan untuk nota ini
                existing_top = same_nota.iloc[0]["top_int"]
                
                if existing_top != int(top):
                    st.error(f"❌ Input Gagal: No Faktur '{no_faktur}' sudah tersimpan dengan TOP {existing_top} hari. Dalam 1 nota, TOP tidak boleh berbeda!")
                    st.stop()
                
                # 2️⃣ CEK DUPLIKASI BARANG & QTY (Mencegah input dobel)
                duplicate = same_nota[
                    (same_nota["nama_barang"] == jenis_barang) &
                    (same_nota["qty_int"] == int(kuantitas))
                ]
                
                if not duplicate.empty:
                    st.warning(f"⚠️ Transaksi untuk faktur {no_faktur} dengan barang {jenis_barang} (Qty: {kuantitas}) sudah pernah diinput!")
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

# ================================================
# TAB 2 : UPLOAD EXCEL
# ================================================

with tab2:
    st.subheader("📤 Upload File Excel")
    
    with st.expander("ℹ️ Format file Excel data penjualan"):
        st.write("""
        - Kolom wajib: `No. Faktur`, `Tgl Faktur`, `Nama Pelanggan`, `Keterangan Barang`, `Kuantitas`, `Jumlah`
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
                    success_count, error_count, errors = new_database.insert_penjualan(df, default_top=top_excel)
                            
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
        data_customer = new_database.get_all_data_customer(columns="nama")

        if not data_customer.empty:
            data_customer = data_customer.sort_values("nama")

        customer_options = ["Semua"] + data_customer["nama"].tolist()
        selected_pelanggan = st.selectbox("👤 Nama Customer", customer_options)

    with col3:
        data_barang = new_database.get_all_data_barang(columns="nama")

        if not data_barang.empty:
            data_barang = data_barang.sort_values("nama")

        barang_options = ["Semua"] + data_barang["nama"].tolist()
        selected_barang = st.selectbox("📦 Nama Barang", barang_options)

    # ======================
    # AMBIL DATA
    # ======================
    df_penjualan = new_database.get_data_penjualan(
        tanggal=selected_date,
        customer=selected_pelanggan,
        barang=selected_barang
    )

    if not df_penjualan.empty:
        df_penjualan['tanggal'] = pd.to_datetime(df_penjualan['tanggal']).dt.strftime('%d %b %Y')

        df_penjualan['subtotal'] = df_penjualan['subtotal'].apply(
            lambda x: f"Rp {x:,.0f}".replace(",", ".")
        )

        if 'total_nota' in df_penjualan.columns:
            df_penjualan['total_nota'] = df_penjualan['total_nota'].apply(
                lambda x: f"Rp {x:,.0f}".replace(",", ".")
            )

        # Hitung total transaksi yang tertampil
        total_transaksi = len(df_penjualan)
        st.info(f"Menampilkan {total_transaksi} transaksi")

        # Tambah kolom checkbox untuk hapus
        df_penjualan.insert(0, 'Hapus', False)

        # Prepare kolom untuk ditampilkan (hide id)
        df_display = df_penjualan[['Hapus', 'no_nota', 'tanggal', 'nama_customer', 'nama_barang', 'kuantitas', 'subtotal', 'total_nota', 'top']].copy()

        column_config = {
            "Hapus": st.column_config.CheckboxColumn("Pilih"),
            "no_nota": st.column_config.TextColumn("No. Faktur"),
            "tanggal": st.column_config.TextColumn("Tanggal"),
            "nama_customer": st.column_config.TextColumn("Customer"),
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
            disabled=["no_nota", "tanggal", "nama_customer", "nama_barang", "kuantitas", "subtotal", "total_nota", "top"],
            column_config=column_config,
            key="penjualan_editor"
        )

        # Ambil baris yang dicentang
        selected_rows = edited_df[edited_df['Hapus'] == True]

        if not selected_rows.empty:
            # Ambil ID dari dataframe asli berdasarkan index yang sama
            selected_ids = df_penjualan.loc[selected_rows.index, 'id'].unique()
            
            st.warning(f"⚠️ {len(selected_ids)} transaksi akan dihapus")

            if st.button("🗑️ Hapus Data Terpilih", type="primary"):
                try:
                    with st.spinner("Menghapus data..."):
                        for pid in selected_ids:
                            new_database.delete_penjualan(pid)

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