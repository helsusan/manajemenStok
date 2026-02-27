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

        if not data_supplier.empty:
            data_supplier = data_supplier.sort_values("nama")

        nama_supplier = st.selectbox(
            "Nama Supplier",
            options=data_supplier["nama"].tolist(),
            help="Pilih supplier yang telah terdaftar"
        )
        
        data_barang = new_database.get_all_data_barang(columns="nama")

        if not data_barang.empty:
            data_barang = data_barang.sort_values("nama")

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
        satuan_barang = new_database.get_satuan_barang(jenis_barang)

        col_qty, col_sat = st.columns([2, 1])
        with col_qty:
            kuantitas = st.number_input(
                "Kuantitas:",
                min_value=0,
                step=1,
                format="%d",
                key="input_kuantitas"
            )
        with col_sat:
            st.text_input("Satuan", value=satuan_barang, disabled=True)
        
        harga_satuan = new_database.get_harga_supplier(nama_supplier, jenis_barang)

        if harga_satuan is None:
            harga_satuan = 0

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

        default_top = new_database.get_top_supplier(nama_supplier) if nama_supplier else 0
        
        top = st.number_input(
            "Terms of Payment (hari)",
            min_value=0,
            step=1,
            value=int(default_top),
            format="%d",
            help="Pembayaran harus lunas dalam berapa hari (Otomatis menggunakan default customer)"
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
        # Ambil data transaksi berdasarkan supplier saja (agar bisa mengecek seluruh barang di nota tersebut)
        df_existing = new_database.get_data_pembelian(
            supplier=nama_supplier
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
        # BENTUK DATAFRAME SESUAI INSERT_PEMBELIAN
        # ======================
        df_input = pd.DataFrame([{
            "No. Faktur": no_faktur,
            "Tgl Faktur": tanggal,
            "Nama Supplier": nama_supplier,
            "Keterangan Barang": jenis_barang,
            "Kuantitas": kuantitas,
            "Harga Satuan": float(harga_satuan),
            "Jumlah": float(total),
            "Tipe": tipe_pembelian
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
        - Kolom wajib: `No Faktur`, `Tgl Faktur`, `Nama Supplier`, `Keterangan Barang`, `Kuantitas`, `Jumlah`
        - Kolom opsional: `Satuan`, `Harga Satuan`, `TOP`
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

            EXPECTED_COLS = ["Tgl Faktur", "No. Faktur", "Nama Supplier", "Keterangan Barang", "Kuantitas", "Jumlah"]

            header_row_index = None

            for i, row in df_raw.iterrows():
                row_str = row.astype(str).str.upper()
                if all(any(col.upper() in cell for cell in row_str) for col in EXPECTED_COLS):
                    header_row_index = i
                    break

            df = pd.read_excel(uploaded_file, header=header_row_index)

            # Identifikasi kolom yang akan dipakai
            actual_cols = [col for col in EXPECTED_COLS if col in df.columns]

            # Cek jika excel memiliki kolom opsional
            if "Satuan" in df.columns:
                actual_cols.append("Satuan")
            if "Harga Satuan" in df.columns:
                actual_cols.append("Harga Satuan")
            if "TOP" in df.columns:
                actual_cols.append("TOP")

            df = df.dropna(how="all")
            df = df[EXPECTED_COLS]
            df = new_database.clean_excel_apostrophe(df)

            mismatch_errors = []

            # 1. PENGECEKAN SATUAN BARANG
            if "Satuan" in df.columns:
                df_barang_db = new_database.get_all_data_barang(["nama", "satuan"])
                dict_satuan_db = dict(zip(df_barang_db['nama'].str.upper(), df_barang_db['satuan'].astype(str).str.lower()))
                
                for idx, row in df.iterrows():
                    excel_nama = str(row.get('Keterangan Barang')).strip().upper()
                    excel_satuan = str(row.get('Satuan')).strip().lower()
                    
                    if not pd.isna(row.get('Satuan')) and excel_nama in dict_satuan_db:
                        db_satuan = dict_satuan_db[excel_nama]
                        if excel_satuan != db_satuan:
                            mismatch_errors.append(f"Baris {idx + header_row_index + 2}: Barang '{row['Keterangan Barang']}' (Satuan Excel: {row['Satuan']} | Satuan DB: {db_satuan})")
            
            # 2. PENGECEKAN HARGA SATUAN
            if "Harga Satuan" in df.columns:
                for idx, row in df.iterrows():
                    customer = str(row.get('Nama Pelanggan')).strip()
                    barang = str(row.get('Keterangan Barang')).strip()
                    excel_price = row.get('Harga Satuan')
                    
                    if pd.notna(excel_price):
                        db_price = new_database.get_harga_customer(customer, barang)
                        if db_price is None:
                            db_price = 0
                        
                        # Toleransi perbedaan koma / desimal kecil (jika selisih >= 1 Rupiah, anggap beda)
                        if abs(float(excel_price) - float(db_price)) >= 1:
                            mismatch_errors.append(f"Baris {idx + header_row_index + 2}: Harga Satuan '{barang}' untuk '{customer}' tidak sesuai! (Excel: Rp {float(excel_price):,.0f} | DB: Rp {float(db_price):,.0f})")
            else:
                # 3. JIKA TIDAK ADA KOLOM HARGA SATUAN, HITUNG OTOMATIS
                # Mencegah error pembagian dengan 0 (ZeroDivisionError)
                df["Harga Satuan"] = df.apply(
                    lambda row: float(row["Jumlah"]) / float(row["Kuantitas"]) if float(row["Kuantitas"]) > 0 else 0, 
                    axis=1
                )
            
            # Jika ada error dari satuan ATAU harga satuan, blokir proses
            if mismatch_errors:
                st.error("❌ Terdapat ketidaksesuaian data (Satuan / Harga) dengan yang ada di database. Upload dibatalkan.")
                with st.expander("Lihat detail error"):
                    for err in mismatch_errors:
                        st.error(err)
                st.stop()

            # AUTO-DETECT TIPE (BARANG vs ONGKIR)
            def detect_tipe(nama_barang):
                # Kata kunci untuk mendeteksi ongkir
                keywords = ['ONGKIR', 'PENGIRIMAN', 'EKSPEDISI', 'DELIVERY', 'JASA ANGKUT', 'KURIR', 'FREIGHT']
                
                if pd.isna(nama_barang):
                    return 'BARANG'
                    
                nama_upper = str(nama_barang).upper()
                if any(k in nama_upper for k in keywords):
                    return 'ONGKIR'
                return 'BARANG'

            # Buat kolom tipe secara otomatis
            df['tipe'] = df['Keterangan Barang'].apply(detect_tipe)

            st.success("✅ Data berhasil dibersihkan!")
                    
            st.subheader("📋 Preview Data")
            st.dataframe(df.head(10), use_container_width=True)
            st.info(f"Total baris: {len(df)}")

            if st.button("💾 Simpan", type="primary", use_container_width=True):
                with st.spinner("Mengupload data ke database..."):
                    success_count, error_count, errors = new_database.insert_pembelian(df, default_top=None)
                            
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
            "📅 Tanggal",
            value=[],
            help="Kosongkan untuk tampilkan semua."
        )

        start_date, end_date = None, None
        if len(selected_date) == 2:
            start_date, end_date = selected_date
        elif len(selected_date) == 1:
            start_date = end_date = selected_date[0]

    with col2:
        data_supplier = new_database.get_all_data_supplier(columns="nama")

        if not data_supplier.empty:
            data_supplier = data_supplier.sort_values("nama")

        supplier_options = ["Semua"] + data_supplier["nama"].tolist()
        selected_Supplier = st.selectbox("👤 Nama Supplier", supplier_options)

    with col3:
        data_barang = new_database.get_all_data_barang(columns="nama")

        if not data_barang.empty:
            data_barang = data_barang.sort_values("nama")

        barang_options = ["Semua"] + data_barang["nama"].tolist()
        selected_barang = st.selectbox("📦 Nama Barang", barang_options)

    # ======================
    # AMBIL DATA
    # ======================
    df_pembelian = new_database.get_data_pembelian(
        start_date=start_date,
        end_date=end_date,
        supplier=selected_Supplier,
        barang=selected_barang
    )

    if not df_pembelian.empty:
        df_pembelian['tanggal'] = pd.to_datetime(df_pembelian['tanggal']).dt.strftime('%d %b %Y')

        if 'harga_satuan' in df_pembelian.columns:
            df_pembelian['harga_satuan'] = df_pembelian['harga_satuan'].apply(
                lambda x: f"Rp {x:,.0f}".replace(",", ".") if pd.notna(x) else "Rp 0"
            )

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
        df_display = df_pembelian[['Hapus', 'no_nota', 'tanggal', 'nama_supplier', 'nama_barang', 'satuan', 'kuantitas', 'harga_satuan', 'subtotal', 'total_nota', 'top']].copy()

        column_config = {
            "Hapus": st.column_config.CheckboxColumn("Pilih"),
            "no_nota": st.column_config.TextColumn("No. Faktur"),
            "tanggal": st.column_config.TextColumn("Tanggal"),
            "nama_supplier": st.column_config.TextColumn("Supplier"),
            "nama_barang": st.column_config.TextColumn("Barang"),
            "satuan": st.column_config.TextColumn("Satuan"),
            "kuantitas": st.column_config.NumberColumn("Qty"),
            "harga_satuan": st.column_config.TextColumn("Price"),
            "subtotal": st.column_config.TextColumn("Subtotal"),
            "total_nota": st.column_config.TextColumn("Total"),
            "top": st.column_config.NumberColumn("TOP"),
        }

        edited_df = st.data_editor(
            df_display,
            hide_index=True,
            use_container_width=True,
            disabled=["no_nota", "tanggal", "nama_supplier", "nama_barang", "satuan", "kuantitas", "harga_satuan", "subtotal", "total_nota", "top"],
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