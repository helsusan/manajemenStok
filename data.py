import streamlit as st
import pandas as pd
from datetime import datetime
import db_config

def get_id_barang(nama_barang):
    """
    Mendapatkan id_barang berdasarkan nama barang dari tabel barang
    """
    try:
        conn = db_config.get_connection()
        cursor = conn.cursor()
        query = "SELECT id FROM barang WHERE nama = %s"
        cursor.execute(query, (nama_barang,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result[0]
        else:
            return None
    except Exception as e:
        st.error(f"Error mencari barang: {e}")
        return None

def insert_penjualan_data(df):
    """
    Insert data penjualan dari DataFrame ke database
    """
    conn = db_config.get_connection()
    cursor = conn.cursor()
    success_count = 0
    error_count = 0
    errors = []
    
    for index, row in df.iterrows():
        try:
            # Ambil nama barang dari CSV
            nama_barang = row.get('nama_barang') or row.get('keterangan_barang') or row.get('barang')
            
            if pd.isna(nama_barang):
                errors.append(f"Baris {index + 2}: Nama barang kosong")
                error_count += 1
                continue
            
            # Cari id_barang dari tabel barang
            id_barang = get_id_barang(nama_barang)
            
            if not id_barang:
                errors.append(f"Baris {index + 2}: Barang '{nama_barang}' tidak ditemukan di database")
                error_count += 1
                continue
            
            # Ambil data lainnya dari CSV
            no_faktur = row.get('no_faktur') or row.get('nomor_faktur')
            tgl_faktur = row.get('tgl_faktur') or row.get('tanggal_faktur')
            nama_pelanggan = row.get('nama_pelanggan') or row.get('pelanggan')
            kuantitas = row.get('kuantitas') or row.get('qty') or row.get('jumlah_barang')
            jumlah = row.get('jumlah') or row.get('total') or row.get('total_harga')
            
            # Validasi data wajib
            if pd.isna(no_faktur) or pd.isna(tgl_faktur) or pd.isna(kuantitas):
                errors.append(f"Baris {index + 2}: Data wajib (no_faktur, tgl_faktur, atau kuantitas) kosong")
                error_count += 1
                continue
            
            # Konversi tanggal jika perlu
            if isinstance(tgl_faktur, str):
                try:
                    tgl_faktur = pd.to_datetime(tgl_faktur).strftime('%Y-%m-%d')
                except:
                    errors.append(f"Baris {index + 2}: Format tanggal tidak valid")
                    error_count += 1
                    continue
            
            # Query insert
            query = """
            INSERT INTO penjualan (no_faktur, tgl_faktur, nama_pelanggan, id_barang, kuantitas, jumlah)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            values = (
                str(no_faktur),
                tgl_faktur,
                str(nama_pelanggan) if not pd.isna(nama_pelanggan) else None,
                id_barang,
                int(kuantitas),
                float(jumlah) if not pd.isna(jumlah) else 0
            )
            
            cursor.execute(query, values)
            success_count += 1
            
        except Exception as e:
            errors.append(f"Baris {index + 2}: {str(e)}")
            error_count += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return success_count, error_count, errors

def show():
    """
    Halaman untuk upload data CSV
    """

    st.title("📊 Upload Data")

    barang = st.selectbox("Pilih data", ["Penjualan", "Stok", "Barang"])

    if(barang == "Penjualan"):
        st.write("Upload file CSV data penjualan untuk dimasukkan ke database")
    
        # Informasi format CSV
        with st.expander("ℹ️ Format File CSV"):
            st.write("""
            **Kolom yang diperlukan dalam file CSV:**
            - `No Faktur`: Nomor faktur penjualan
            - `Tgl Faktur`: Tanggal faktur (format: YYYY-MM-DD atau DD/MM/YYYY)
            - `Nama Pelanggan`: Nama pelanggan
            - `Keterangan Barang`: Nama barang (harus sesuai dengan nama di tabel barang)
            - `Kuantitas`: Jumlah barang
            - `Jumlah`: Total harga (opsional)
            
            **Catatan:** Nama barang di CSV harus sudah ada di tabel barang di database!
            """)
        
        # Upload file
        uploaded_file = st.file_uploader(
            "Pilih file CSV",
            type=['csv'],
            help="Upload file CSV dengan format yang sesuai"
        )
        
        if uploaded_file is not None:
            try:
                # Baca CSV
                df = pd.read_csv(uploaded_file)
                
                st.subheader("Preview Data")
                st.dataframe(df.head(10))
                st.info(f"Total baris: {len(df)}")
                
                # Tombol untuk upload
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if st.button("📤 Upload ke Database", type="primary", use_container_width=True):
                        with st.spinner("Mengupload data ke database..."):
                            success_count, error_count, errors = insert_penjualan_data(df)
                        
                        # Tampilkan hasil
                        if success_count > 0:
                            st.success(f"✅ Berhasil mengupload {success_count} baris data!")
                        
                        if error_count > 0:
                            st.warning(f"⚠️ {error_count} baris gagal diupload")
                            
                            with st.expander("Lihat detail error"):
                                for error in errors[:20]:  # Tampilkan maksimal 20 error pertama
                                    st.error(error)
                                
                                if len(errors) > 20:
                                    st.info(f"... dan {len(errors) - 20} error lainnya")
                
                with col2:
                    if st.button("🔄 Reset", use_container_width=True):
                        st.rerun()
                        
            except Exception as e:
                st.error(f"❌ Error membaca file: {str(e)}")
                st.info("Pastikan file CSV Anda memiliki format yang benar")

    elif(barang == "Stok"):
        st.write("Upload file CSV data stok untuk dimasukkan ke database")
    
        # Informasi format CSV
        with st.expander("ℹ️ Format File CSV"):
            st.write("""
            **Kolom yang diperlukan dalam file CSV:**
            - `No Faktur`: Nomor faktur penjualan
            - `Tgl Faktur`: Tanggal faktur (format: YYYY-MM-DD atau DD/MM/YYYY)
            - `Nama Pelanggan`: Nama pelanggan
            - `Keterangan Barang`: Nama barang (harus sesuai dengan nama di tabel barang)
            - `Kuantitas`: Jumlah barang
            - `Jumlah`: Total harga (opsional)
            
            **Catatan:** Nama barang di CSV harus sudah ada di tabel barang di database!
            """)
        
        # Upload file
        uploaded_file = st.file_uploader(
            "Pilih file CSV",
            type=['csv'],
            help="Upload file CSV dengan format yang sesuai"
        )
    
    elif(barang == "Barang"):
        # Section untuk menambah barang baru
        st.subheader("➕ Tambah Barang Baru")
        
        with st.form("form_tambah_barang"):
            nama_barang_baru = st.text_input("Nama Barang *", placeholder="Contoh: AQUA 600ML")
            
            submit_barang = st.form_submit_button("💾 Simpan Barang", type="primary", use_container_width=True)
            
            if submit_barang:
                if nama_barang_baru.strip() == "":
                    st.error("❌ Nama barang tidak boleh kosong!")
                else:
                    try:
                        conn = db_config.get_connection()
                        cursor = conn.cursor()
                        
                        # Cek apakah barang sudah ada
                        cursor.execute("SELECT id FROM barang WHERE nama = %s", (nama_barang_baru,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            st.warning(f"⚠️ Barang '{nama_barang_baru}' sudah ada di database!")
                        else:
                            # Insert barang baru
                            query = "INSERT INTO barang (nama, model_prediksi) VALUES (%s, %s)"
                            cursor.execute(query, (nama_barang_baru, "Mean"))
                            conn.commit()
                            st.success(f"✅ Barang '{nama_barang_baru}' berhasil ditambahkan!")
                        
                        cursor.close()
                        conn.close()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")





    # Divider
    st.divider()
    
    # Section untuk melihat data barang yang tersedia
    st.subheader("🔍 Daftar Barang di Database")
    
    if st.button("Tampilkan Daftar Barang"):
        try:
            results = db_config.run_query("SELECT id, nama, model_prediksi FROM barang ORDER BY nama")
            
            if results:
                df_barang = pd.DataFrame(results)
                st.dataframe(df_barang, use_container_width=True)
            else:
                st.warning("Tidak ada data barang di database")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")





    # Divider
    st.divider()
    
    # Section untuk melihat data barang yang tersedia
    st.subheader("🔍 Data Penjualan di Database")
    
    if st.button("Tampilkan Data Penjualan"):
        try:
            results = db_config.run_query("SELECT * FROM penjualan ORDER BY tgl_faktur")
            
            if results:
                df_penjualan = pd.DataFrame(results)
                st.dataframe(df_penjualan, use_container_width=True)
            else:
                st.warning("Tidak ada data penjualan di database")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")