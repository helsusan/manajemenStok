import mysql.connector
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="trading_db"
    )

def clean_excel_apostrophe(df):   
    def clean_value(value):
        # Handle NaN/None
        if pd.isna(value):
            return None
        
        # Convert ke string dan strip
        str_value = str(value).strip()
        
        # Remove leading apostrophe
        if str_value.startswith("'"):
            str_value = str_value[1:]
        
        return str_value if str_value else None

    # Copy df agar tidak ubah yang asli
    df = df.copy()

    # --- Bersihkan Nama Kolom ---
    df.columns = [
        col[1:] if isinstance(col, str) and col.startswith("'") else col
        for col in df.columns
    ]

    # --- Bersihkan Isi Cell ---
    for col in df.columns:
        df[col] = df[col].apply(clean_value)

    return df

def format_currency(amount):
    if amount is None: return "Rp 0"
    return f"Rp {amount:,.0f}".replace(",", ".")

def show_detail_transaksi(jenis, id_ref):
    if jenis == 'piutang':
        data = get_detail_piutang(id_ref)
        history = get_pembayaran_history('piutang', id_ref)
        label_partner = "Customer"
    else:
        data = get_detail_hutang(id_ref)
        history = get_pembayaran_history('hutang', id_ref)
        label_partner = "Supplier"
        
    if data:
        st.subheader(f"{data['no_invoice']}")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**{label_partner}:** {data[label_partner.lower()]}")
            st.write(f"**Tanggal:** {data['tanggal_invoice']}")
            st.write(f"**Jatuh Tempo:** {data['tanggal_jatuh_tempo']}")
        with col2:
            st.write(f"**Total:** {format_currency(data[f'total_{jenis}'])}")
            st.write(f"**Sisa:** {format_currency(data[f'sisa_{jenis}'])}")
            st.write(f"**Status:** {data['status']}")
            
        st.markdown("---")
        st.write("📜 **Riwayat Pembayaran**")
        
        if not history.empty:
            # Format display
            display_hist = history.copy()
            display_hist['jumlah_bayar'] = display_hist['jumlah_bayar'].apply(lambda x: format_currency(float(x)))
            st.dataframe(
                display_hist[['no_pembayaran', 'tanggal_bayar', 'jumlah_bayar', 'metode_bayar', 'keterangan']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Belum ada riwayat pembayaran")

def render_payment_form(jenis, row):
    key_suffix = "p" if jenis == "piutang" else "h"
    col_sisa = f"sisa_{jenis}"
    
    with st.form(key=f"form_bayar_{key_suffix}_{row['id']}"):
        st.subheader("Form Pembayaran")
        c1, c2 = st.columns(2)
        with c1:
            tgl = st.date_input("Tanggal", value=datetime.now())
            jml = st.number_input(f"Jumlah (Max: {format_currency(row[col_sisa])})", 
                                  min_value=0.0, max_value=float(row[col_sisa]), 
                                  value=float(row[col_sisa]), step=1000.0)
        with c2:
            metode = st.selectbox("Metode", ["CASH", "TRANSFER", "GIRO", "LAINNYA"])
            ref = st.text_input("No Referensi")
        
        ket = st.text_area("Keterangan")
        
        cb1, cb2 = st.columns(2)
        with cb1: submit = st.form_submit_button("💾 Simpan", use_container_width=True)
        with cb2: cancel = st.form_submit_button("❌ Batal", use_container_width=True)
        
        if submit:
            if jml <= 0:
                st.error("Jumlah harus > 0")
            else:
                success, msg = process_pembayaran(
                    jenis, row['id'], tgl, jml, metode, ref, ket
                )
                if success:
                    st.success(f"✅ {msg}")
                    st.session_state[f'bayar_{key_suffix}_{row["id"]}'] = False
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        
        if cancel:
            st.session_state[f'bayar_{key_suffix}_{row["id"]}'] = False
            st.rerun()










# ================================================
# DATA BARANG
# ================================================

# Ambil semua data barang tapi bisa pilih kolomnya
def get_all_data_barang(columns="*"):
    conn = get_connection()
    
    if isinstance(columns, list):
        columns = ", ".join(columns)

    query = f"SELECT {columns} FROM barang"
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

# Cek apakah barang sudah ada di database
def check_barang_available(nama_barang):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id FROM barang WHERE nama = %s"
    cursor.execute(query, (nama_barang,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result is not None

# Ambil id barang berdasarkan nama
def get_barang_id(nama_barang):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id FROM barang WHERE nama = %s"
    cursor.execute(query, (nama_barang,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result[0] if result else None

# Input data barang ke database
# Bisa dipanggil manual 1x, atau dipanggil di dalam loop Excel berkali-kali
def insert_barang(nama, model_prediksi="Mean", p=None, d=None, q=None):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Validasi Nama
        if not nama or str(nama).strip() == "":
            raise ValueError("Nama barang tidak boleh kosong")
        
        nama = str(nama).strip()
        
        # Default Model jika None/Invalid
        if pd.isna(model_prediksi) or str(model_prediksi).strip() == "":
            model_prediksi = "Mean"
            
        if str(model_prediksi).upper() == "ARIMA":
            model_prediksi = "ARIMA"
        else:
            model_prediksi = "Mean"

        # Cek Duplikasi
        cursor.execute("SELECT id FROM barang WHERE nama = %s", (nama,))
        if cursor.fetchone():
            raise ValueError(f"Barang '{nama}' sudah ada")

        # Insert Query
        query = """
            INSERT INTO barang (nama, model_prediksi, p, d, q)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        # Handle nilai NaN dari Excel supaya jadi None (NULL) di database
        def clean_val(v):
            if pd.isna(v) or v == "": return None
            try: return int(float(v))
            except: return None

        cursor.execute(query, (nama, model_prediksi, clean_val(p), clean_val(d), clean_val(q)))
        conn.commit()
        
        return True, f"Barang '{nama}' berhasil disimpan"
        
    except Exception as e:
        return False, str(e)
        
    finally:
        cursor.close()
        conn.close()

# Update isi tabel barang
def update_barang(id_barang, nama, model_prediksi, p, d, q):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        UPDATE barang
        SET nama = %s,
            model_prediksi = %s,
            p = %s,
            d = %s,
            q = %s
        WHERE id = %s
    """
    cursor.execute(query, (nama, model_prediksi, p, d, q, int(id_barang)))

    conn.commit()
    cursor.close()
    conn.close()

# Hapus barang
def delete_barang(id_barang):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM barang WHERE id = %s",
        (int(id_barang),)
    )

    conn.commit()
    cursor.close()
    conn.close()

# Cek apakah barang tersebut ada di tabel lain
def check_related_data(id_barang):
    conn = get_connection()
    cursor = conn.cursor()

    related = {}

    checks = {
        "Customer Pricelist": "SELECT COUNT(*) FROM customer_pricelist WHERE id_barang = %s",
        "Supplier Pricelist": "SELECT COUNT(*) FROM supplier_pricelist WHERE id_barang = %s"
    }

    for name, query in checks.items():
        cursor.execute(query, (int(id_barang),))
        count = cursor.fetchone()[0]
        if count > 0:
            related[name] = count

    cursor.close()
    conn.close()

    return related













# ================================================
# DATA CUSTOMER
# ================================================

# Normalisasi nama customer pakai Tile Case
def normalize_customer_name(nama):
    if not nama or pd.isna(nama):
        return ""
    
    return str(nama).strip().title()

# Ambil semua data customer tapi bisa pilih kolomnya
def get_all_data_customer(columns="*"):
    conn = get_connection()
    
    if isinstance(columns, list):
        columns = ", ".join(columns)

    query = f"SELECT {columns} FROM customer"
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

# Cek apakah customer sudah ada di database
def check_customer_available(nama_cust):
    conn = get_connection()
    cursor = conn.cursor()

    nama_cust = normalize_customer_name(nama_cust)

    query = "SELECT id FROM customer WHERE nama = %s"
    cursor.execute(query, (nama_cust,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result is not None

# Ambil id customer berdasarkan nama
def get_customer_id(nama_cust):
    conn = get_connection()
    cursor = conn.cursor()

    nama_cust = normalize_customer_name(nama_cust)

    query = "SELECT id FROM customer WHERE nama = %s"
    cursor.execute(query, (nama_cust,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result[0] if result else None

# Input data customer ke database
# Bisa dipanggil manual 1x, atau dipanggil di dalam loop Excel berkali-kali
def insert_customer(nama):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Validasi Nama
        if not nama or str(nama).strip() == "":
            raise ValueError("Nama customer tidak boleh kosong")
        
        nama = normalize_customer_name(nama)

        # Cek Duplikasi
        cursor.execute("SELECT id FROM customer WHERE nama = %s", (nama,))
        if cursor.fetchone():
            raise ValueError(f"Customer '{nama}' sudah ada")

        # Insert Query
        query = """
            INSERT INTO customer (nama)
            VALUES (%s)
        """

        cursor.execute(query, (nama, ))
        conn.commit()
        
        return True, f"Customer '{nama}' berhasil disimpan"
        
    except Exception as e:
        return False, str(e)
        
    finally:
        cursor.close()
        conn.close()

# Update isi tabel customer
def update_customer(id_cust, nama):
    conn = get_connection()
    cursor = conn.cursor()

    nama = normalize_customer_name(nama)

    query = """
        UPDATE customer
        SET nama = %s
        WHERE id = %s
    """
    cursor.execute(query, (nama, int(id_cust)))

    conn.commit()
    cursor.close()
    conn.close()

# Hapus customer
def delete_customer(id_cust):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Delete pricelist first (foreign key constraint)
        cursor.execute("DELETE FROM customer_pricelist WHERE id_customer = %s", (int(id_cust),))
        
        # Then delete customer
        cursor.execute("DELETE FROM customer WHERE id = %s", (int(id_cust),))
        
        conn.commit()
        
    finally:
        cursor.close()
        conn.close()













# ================================================
# DATA CUSTOMER PRICELIST
# ================================================

# Ambil semua data customer pricelist tapi bisa pilih kolomnya
def get_all_data_customer_pricelist(columns="*"):
    conn = get_connection()
    
    if isinstance(columns, list):
        columns = ", ".join(columns)

    query = f"SELECT {columns} FROM customer_pricelist"
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

# Cek apakah kombinasi customer & pricelist sudah ada
def check_cust_pricelist_exists(id_customer, id_barang):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT id FROM customer_pricelist 
        WHERE id_customer = %s AND id_barang = %s
    """
    cursor.execute(query, (int(id_customer), int(id_barang)))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result is not None

# Insert / update customer pricelist
def upsert_customer_pricelist(id_customer, id_barang, harga):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if exists
        check_query = """
            SELECT id FROM customer_pricelist 
            WHERE id_customer = %s AND id_barang = %s
        """
        cursor.execute(check_query, (int(id_customer), int(id_barang)))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            update_query = """
                UPDATE customer_pricelist 
                SET harga = %s, updated_at = NOW()
                WHERE id = %s
            """
            cursor.execute(update_query, (int(harga), existing[0]))
        else:
            # Insert new
            insert_query = """
                INSERT INTO customer_pricelist (id_customer, id_barang, harga, updated_at)
                VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (int(id_customer), int(id_barang), int(harga)))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error upsert pricelist: {str(e)}")
        return False
        
    finally:
        cursor.close()
        conn.close()

# Update customer pricelist
def update_customer_pricelist(id_pricelist, harga):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        UPDATE customer_pricelist 
        SET harga = %s, updated_at = NOW()
        WHERE id = %s
    """
    cursor.execute(query, (int(harga), int(id_pricelist)))

    conn.commit()
    cursor.close()
    conn.close()

# Ambil semua data customer beserta pricelist nya
def get_customer_with_pricelist():
    conn = get_connection()
    
    query = """
        SELECT 
            c.id as id_customer,
            c.nama as customer,
            cp.id as id_pricelist,
            b.nama as barang,
            cp.harga,
            cp.updated_at
        FROM customer c
        LEFT JOIN customer_pricelist cp ON c.id = cp.id_customer
        LEFT JOIN barang b ON cp.id_barang = b.id
        WHERE cp.id IS NOT NULL
        ORDER BY c.nama, b.nama
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df

# Hapus customer pricelist
def delete_customer_pricelist(id_pricelist):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM customer_pricelist WHERE id = %s",
        (int(id_pricelist),)
    )

    conn.commit()
    cursor.close()
    conn.close()

def get_harga_customer(nama_cust, jenis_barang):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT cp.harga
        FROM customer c
        JOIN customer_pricelist cp ON c.id = cp.id_customer
        JOIN barang b ON cp.id_barang = b.id
        WHERE c.nama = %s AND b.nama = %s
        LIMIT 1
    """

    cursor.execute(query, (nama_cust, jenis_barang))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result[0] if result else None










# ================================================
# DATA SUPPLIER
# ================================================

# Normalisasi nama supplier pakai Tile Case
def normalize_supplier_name(nama):
    if not nama or pd.isna(nama):
        return ""
   
    return str(nama).strip().title()

# Ambil semua data supplier tapi bisa pilih kolomnya
def get_all_data_supplier(columns="*"):
    conn = get_connection()
   
    if isinstance(columns, list):
        columns = ", ".join(columns)

    query = f"SELECT {columns} FROM supplier"
    df = pd.read_sql(query, conn)
    conn.close()
   
    return df

# Cek apakah supplier sudah ada di database
def check_supplier_available(nama_supp):
    conn = get_connection()
    cursor = conn.cursor()

    nama_supp = normalize_supplier_name(nama_supp)

    query = "SELECT id FROM supplier WHERE nama = %s"
    cursor.execute(query, (nama_supp,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result is not None

# Ambil id supplier berdasarkan nama
def get_supplier_id(nama_supp):
    conn = get_connection()
    cursor = conn.cursor()

    nama_supp = normalize_supplier_name(nama_supp)

    query = "SELECT id FROM supplier WHERE nama = %s"
    cursor.execute(query, (nama_supp,))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result[0] if result else None

# Input data supplier ke database
# Bisa dipanggil manual 1x, atau dipanggil di dalam loop Excel berkali-kali
def insert_supplier(nama):
    conn = get_connection()
    cursor = conn.cursor()
   
    try:
        # Validasi Nama
        if not nama or str(nama).strip() == "":
            raise ValueError("Nama supplier tidak boleh kosong")
       
        nama = normalize_supplier_name(nama)

        # Cek Duplikasi
        cursor.execute("SELECT id FROM supplier WHERE nama = %s", (nama,))
        if cursor.fetchone():
            raise ValueError(f"Customer '{nama}' sudah ada")

        # Insert Query
        query = """
            INSERT INTO supplier (nama)
            VALUES (%s)
        """

        cursor.execute(query, (nama, ))
        conn.commit()
       
        return True, f"Supplier '{nama}' berhasil disimpan"
       
    except Exception as e:
        return False, str(e)
       
    finally:
        cursor.close()
        conn.close()

# Update isi tabel supplier
def update_supplier(id_supp, nama):
    conn = get_connection()
    cursor = conn.cursor()

    nama = normalize_supplier_name(nama)

    query = """
        UPDATE supplier
        SET nama = %s
        WHERE id = %s
    """
    cursor.execute(query, (nama, int(id_supp)))

    conn.commit()
    cursor.close()
    conn.close()

# Hapus supplier
def delete_supplier(id_supp):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Delete pricelist first (foreign key constraint)
        cursor.execute("DELETE FROM supplier_pricelist WHERE id_supplier = %s", (int(id_supp),))
       
        # Then delete supplier
        cursor.execute("DELETE FROM supplier WHERE id = %s", (int(id_supp),))
       
        conn.commit()
       
    finally:
        cursor.close()
        conn.close()











# ================================================
# DATA SUPPLIER PRICELIST
# ================================================

# Ambil semua data supplier pricelist tapi bisa pilih kolomnya
def get_all_data_supplier_pricelist(columns="*"):
    conn = get_connection()
   
    if isinstance(columns, list):
        columns = ", ".join(columns)

    query = f"SELECT {columns} FROM supplier_pricelist"
    df = pd.read_sql(query, conn)
    conn.close()
   
    return df

# Cek apakah kombinasi supplier & pricelist sudah ada
def check_supp_pricelist_exists(id_supplier, id_barang):
    conn = get_connection()
    cursor = conn.cursor()
   
    query = """
        SELECT id FROM supplier_pricelist
        WHERE id_supplier = %s AND id_barang = %s
    """
    cursor.execute(query, (int(id_supplier), int(id_barang)))
    result = cursor.fetchone()
   
    cursor.close()
    conn.close()
   
    return result is not None

# Insert / update supplier pricelist
def upsert_supplier_pricelist(id_supplier, id_barang, harga):
    conn = get_connection()
    cursor = conn.cursor()
   
    try:
        # Check if exists
        check_query = """
            SELECT id FROM supplier_pricelist
            WHERE id_supplier = %s AND id_barang = %s
        """
        cursor.execute(check_query, (int(id_supplier), int(id_barang)))
        existing = cursor.fetchone()
       
        if existing:
            # Update existing
            update_query = """
                UPDATE supplier_pricelist
                SET harga = %s, updated_at = NOW()
                WHERE id = %s
            """
            cursor.execute(update_query, (int(harga), existing[0]))
        else:
            # Insert new
            insert_query = """
                INSERT INTO supplier_pricelist (id_supplier, id_barang, harga, updated_at)
                VALUES (%s, %s, %s, NOW())
            """
            cursor.execute(insert_query, (int(id_supplier), int(id_barang), int(harga)))
       
        conn.commit()
        return True
       
    except Exception as e:
        print(f"Error upsert pricelist: {str(e)}")
        return False
       
    finally:
        cursor.close()
        conn.close()

# Update supplier pricelist
def update_supplier_pricelist(id_pricelist, harga):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        UPDATE supplier_pricelist
        SET harga = %s, updated_at = NOW()
        WHERE id = %s
    """
    cursor.execute(query, (int(harga), int(id_pricelist)))

    conn.commit()
    cursor.close()
    conn.close()

# Ambil semua data supplier beserta pricelist nya
def get_supplier_with_pricelist():
    conn = get_connection()
   
    query = """
        SELECT
            c.id as id_supplier,
            c.nama as supplier,
            cp.id as id_pricelist,
            b.nama as barang,
            cp.harga,
            cp.updated_at
        FROM supplier c
        LEFT JOIN supplier_pricelist cp ON c.id = cp.id_supplier
        LEFT JOIN barang b ON cp.id_barang = b.id
        WHERE cp.id IS NOT NULL
        ORDER BY c.nama, b.nama
    """
    df = pd.read_sql(query, conn)
    conn.close()
   
    return df

# Hapus supplier pricelist
def delete_supplier_pricelist(id_pricelist):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM supplier_pricelist WHERE id = %s",
        (int(id_pricelist),)
    )

    conn.commit()
    cursor.close()
    conn.close()











# ================================================
# DATA PENJUALAN
# ================================================

# Cek apakah sudah ada penjualan dengan no_nota, tanggal, dan customer yang sama
def get_existing_penjualan(no_nota, tanggal, id_customer):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT id, total 
        FROM penjualan 
        WHERE no_nota = %s AND tanggal = %s AND id_customer = %s
        LIMIT 1
    """
    cursor.execute(query, (str(no_nota), tanggal, int(id_customer)))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if result:
        return {"id": result[0], "total": float(result[1])}
    return None

# Insert data penjualan
def insert_penjualan(df, default_top=None):
    conn = get_connection()
    cursor = conn.cursor()
    success_count = 0
    errors = []

    try:
        conn.start_transaction()

        penjualan_cache = {}
        
        for index, row in df.iterrows():
            # ======================
            # VALIDASI BARANG
            # ======================
            nama_barang = row.get('Keterangan Barang')
            if pd.isna(nama_barang):
                raise Exception(f"Baris {index + 2}: Nama barang kosong")

            id_barang = get_barang_id(nama_barang)
            if not id_barang:
                raise Exception(f"Baris {index + 2}: Barang '{nama_barang}' tidak ditemukan")

            # ======================
            # DATA HEADER
            # ======================
            no_nota = row.get('No. Faktur')
            tanggal = row.get('Tgl Faktur')
            nama_pelanggan = row.get('Nama Pelanggan')

            if pd.isna(no_nota) or pd.isna(tanggal):
                raise Exception(f"Baris {index + 2}: No nota atau tanggal kosong")

            id_customer = None
            if not pd.isna(nama_pelanggan):
                id_customer = get_customer_id(nama_pelanggan)
                if not id_customer:
                    raise Exception(f"Baris {index + 2}: Customer '{nama_pelanggan}' tidak ditemukan")
                
            # TOP → prioritas DataFrame → fallback ke default
            top = row.get("TOP") if "TOP" in df.columns else default_top

            # ======================
            # CEK DATABASE DULU (UNTUK INPUT MANUAL)
            # ======================
            if no_nota not in penjualan_cache:
                # Cek apakah transaksi sudah ada di database
                cursor.execute("""
                    SELECT id, total 
                    FROM penjualan 
                    WHERE no_nota = %s AND tanggal = %s AND id_customer = %s
                    LIMIT 1
                """, (str(no_nota), tanggal, id_customer))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Transaksi sudah ada di database, gunakan yang ada
                    penjualan_cache[no_nota] = {
                        "id": existing[0],
                        "total": float(existing[1])
                    }
                else:
                    # Transaksi belum ada, buat baru
                    query_penjualan = """
                    INSERT INTO penjualan (no_nota, tanggal, id_customer, total, top)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        query_penjualan,
                        (
                            str(no_nota),
                            tanggal,
                            id_customer,
                            0,          # total diupdate belakangan
                            top
                        )
                    )
                    id_penjualan = cursor.lastrowid
                    penjualan_cache[no_nota] = {
                        "id": id_penjualan,
                        "total": 0
                    }

            # Ambil id_penjualan dari cache
            id_penjualan = penjualan_cache[no_nota]["id"]

            # ======================
            # DETAIL PENJUALAN
            # ======================
            kuantitas = row.get("Kuantitas")
            jumlah = row.get("Jumlah")
            harga_satuan = row.get("Harga Satuan")

            if pd.isna(kuantitas):
                raise Exception(f"Baris {index+2}: Kuantitas tidak valid")

            kuantitas = int(kuantitas)

            # LOGIKA HARGA SATUAN
            if not pd.isna(harga_satuan):
                harga_satuan = float(harga_satuan)
                subtotal = kuantitas * harga_satuan
            else:
                if pd.isna(jumlah):
                    raise Exception(f"Baris {index+2}: Jumlah kosong")
                subtotal = float(jumlah)
                harga_satuan = subtotal / kuantitas

            # ======================
            # CEK APAKAH BARANG SUDAH ADA DI DETAIL
            # ======================
            cursor.execute("""
                SELECT id, kuantitas, subtotal 
                FROM penjualan_detail 
                WHERE id_penjualan = %s AND id_barang = %s
                LIMIT 1
            """, (id_penjualan, id_barang))
            
            existing_detail = cursor.fetchone()
            
            if existing_detail:
                # Barang sudah ada, UPDATE kuantitas dan subtotal
                detail_id = existing_detail[0]
                old_kuantitas = existing_detail[1]
                old_subtotal = float(existing_detail[2])
                
                new_kuantitas = old_kuantitas + kuantitas
                new_subtotal = old_subtotal + subtotal
                
                query_update = """
                UPDATE penjualan_detail
                SET kuantitas = %s, subtotal = %s
                WHERE id = %s
                """
                cursor.execute(query_update, (new_kuantitas, new_subtotal, detail_id))
                
                # Update total penjualan (tambah selisihnya aja)
                penjualan_cache[no_nota]["total"] += subtotal
                
            else:
                # Barang belum ada, INSERT baru
                query_detail = """
                INSERT INTO penjualan_detail
                (id_penjualan, id_barang, kuantitas, harga_satuan, subtotal)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(
                    query_detail,
                    (id_penjualan, id_barang, kuantitas, harga_satuan, subtotal)
                )
                
                penjualan_cache[no_nota]["total"] += subtotal

            success_count += 1

        # ======================
        # UPDATE TOTAL PENJUALAN
        # ======================
        for data in penjualan_cache.values():
            cursor.execute(
                "UPDATE penjualan SET total = %s WHERE id = %s",
                (data["total"], data["id"])
            )

        conn.commit()
        cursor.close()
        conn.close()
        return success_count, 0, []

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        errors.append(str(e))
        return 0, df.shape[0], errors

# Ambil daftar tanggal transaksi
def get_penjualan_dates():
    conn = get_connection()
    query = """
        SELECT DISTINCT DATE(tanggal) AS tanggal
        FROM penjualan
        ORDER BY tanggal DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df['tanggal'].tolist()

# Ambil data penjualan
def get_data_penjualan(tanggal=None, customer=None, barang=None):
    conn = get_connection()

    query = """
        SELECT
            p.id,
            p.no_nota,
            p.tanggal,
            c.nama AS nama_customer,
            b.nama AS nama_barang,
            pd.kuantitas,
            pd.subtotal,
            p.total AS total_nota,
            p.top AS top
        FROM penjualan p
        JOIN penjualan_detail pd ON p.id = pd.id_penjualan
        JOIN barang b ON pd.id_barang = b.id
        LEFT JOIN customer c ON p.id_customer = c.id
        WHERE 1=1
    """

    params = []

    if tanggal:
        query += " AND DATE(p.tanggal) = %s"
        params.append(tanggal)

    if customer and customer != "Semua":
        query += " AND c.nama = %s"
        params.append(customer)

    if barang and barang != "Semua":
        query += " AND b.nama = %s"
        params.append(barang)

    query += " ORDER BY p.tanggal DESC, p.no_nota DESC"

    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# Hapus penjualan
def delete_penjualan(id_penjualan):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM penjualan_detail WHERE id_penjualan = %s",
            (int(id_penjualan),)
        )
        cursor.execute(
            "DELETE FROM penjualan WHERE id = %s",
            (int(id_penjualan),)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()











# ================================================
# DATA PIUTANG
# ================================================

# Ambil semua data piutang buat dashboard
def get_piutang_summary():
    conn = get_connection()
    query = """
    SELECT 
        COUNT(*) as total_invoice,
        COALESCE(SUM(total), 0) as total_piutang,
        COALESCE(SUM(terbayar), 0) as total_terbayar,
        COALESCE(SUM(sisa), 0) as sisa_piutang,
        COALESCE(SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END), 0) as total_overdue
    FROM piutang
    WHERE sisa > 0
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df.iloc[0] if not df.empty else None

# Ambil data piutang sesuai filter
def get_filtered_piutang(start_date, end_date, id_customer=None, status=None, search=None):
    conn = get_connection()
    
    # Alias kolom agar sesuai dengan logic UI user
    query = """
    SELECT 
        p.id,
        p.no_nota as no_invoice,
        c.nama as customer,
        p.tanggal as tanggal_invoice,
        p.due_date as tanggal_jatuh_tempo,
        p.total as total_piutang,
        p.terbayar as total_terbayar,
        p.sisa as sisa_piutang,
        p.status,
        CASE 
            WHEN p.status = 'OVERDUE' THEN DATEDIFF(CURDATE(), p.due_date)
            ELSE 0 
        END as hari_overdue
    FROM piutang p
    JOIN customer c ON p.id_customer = c.id
    WHERE p.tanggal BETWEEN %s AND %s
    """
    params = [start_date, end_date]
    
    if id_customer and id_customer != 0:
        query += " AND p.id_customer = %s"
        params.append(id_customer)
        
    if status and status != "Semua":
        query += " AND p.status = %s"
        params.append(status)
        
    if search:
        query += " AND p.no_nota LIKE %s"
        params.append(f"%{search}%")
        
    query += " ORDER BY p.due_date ASC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# Ambil semua data piutang
def get_detail_piutang(id_piutang):
    conn = get_connection()
    query = """
    SELECT p.*, c.nama as customer, 
           p.no_nota as no_invoice, p.tanggal as tanggal_invoice, 
           p.due_date as tanggal_jatuh_tempo, p.total as total_piutang, 
           p.terbayar as total_terbayar, p.sisa as sisa_piutang
    FROM piutang p
    JOIN customer c ON p.id_customer = c.id
    WHERE p.id = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (int(id_piutang),))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result











# ================================================
# DATA HUTANG
# ================================================

# Ambil semua data hutang buat dashboard
def get_hutang_summary():
    conn = get_connection()
    query = """
    SELECT 
        COUNT(*) as total_invoice,
        COALESCE(SUM(total), 0) as total_hutang,
        COALESCE(SUM(terbayar), 0) as total_terbayar,
        COALESCE(SUM(sisa), 0) as sisa_hutang,
        COALESCE(SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END), 0) as total_overdue
    FROM hutang
    WHERE sisa > 0
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df.iloc[0] if not df.empty else None

# Ambil data piutang sesuai filter
def get_filtered_hutang(start_date, end_date, id_supplier=None, status=None, search=None):
    conn = get_connection()
    
    query = """
    SELECT 
        h.id,
        h.no_nota as no_invoice,
        s.nama as supplier,
        h.tanggal as tanggal_invoice,
        h.due_date as tanggal_jatuh_tempo,
        h.total as total_hutang,
        h.terbayar as total_terbayar,
        h.sisa as sisa_hutang,
        h.status,
        CASE 
            WHEN h.status = 'OVERDUE' THEN DATEDIFF(CURDATE(), h.due_date)
            ELSE 0 
        END as hari_overdue
    FROM hutang h
    JOIN supplier s ON h.id_supplier = s.id
    WHERE h.tanggal BETWEEN %s AND %s
    """
    params = [start_date, end_date]
    
    if id_supplier and id_supplier != 0:
        query += " AND h.id_supplier = %s"
        params.append(id_supplier)
        
    if status and status != "Semua":
        query += " AND h.status = %s"
        params.append(status)
        
    if search:
        query += " AND h.no_nota LIKE %s"
        params.append(f"%{search}%")
        
    query += " ORDER BY h.due_date ASC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# Ambil semua data piutang
def get_detail_hutang(id_hutang):
    conn = get_connection()
    query = """
    SELECT h.*, s.nama as supplier,
           h.no_nota as no_invoice, h.tanggal as tanggal_invoice, 
           h.due_date as tanggal_jatuh_tempo, h.total as total_hutang, 
           h.terbayar as total_terbayar, h.sisa as sisa_hutang
    FROM hutang h
    JOIN supplier s ON h.id_supplier = s.id
    WHERE h.id = %s
    """
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query, (int(id_hutang),))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result











# ================================================
# DASHBOARD REKAPAN HUTANG & PIUTANG
# ================================================

def get_overdue_alerts(table_name):
    conn = get_connection()
    col_sisa = 'sisa' if table_name == 'piutang' else 'sisa' # sama nama kolomnya
    
    # Alert Overdue
    q_overdue = f"SELECT COUNT(*) as jml, COALESCE(SUM({col_sisa}), 0) as total FROM {table_name} WHERE status = 'OVERDUE'"
    
    # Alert Jatuh Tempo Minggu Ini
    q_due_week = f"""
    SELECT COUNT(*) as jml, COALESCE(SUM({col_sisa}), 0) as total
    FROM {table_name}
    WHERE due_date BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)
    AND status != 'LUNAS'
    """
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute(q_overdue)
    res_overdue = cursor.fetchone()
    
    cursor.execute(q_due_week)
    res_due_week = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return res_overdue, res_due_week

def get_pembayaran_history(jenis, id_ref):
    conn = get_connection()
    table = "pembayaran_piutang" if jenis == "piutang" else "pembayaran_hutang"
    col_ref = "id_piutang" if jenis == "piutang" else "id_hutang"
    
    query = f"""
    SELECT * FROM {table}
    WHERE {col_ref} = %s
    ORDER BY tanggal_bayar DESC
    """
    df = pd.read_sql(query, conn, params=(int(id_ref),))
    conn.close()
    return df

def process_pembayaran(jenis, id_ref, tanggal_bayar, jumlah_bayar, metode, referensi, keterangan):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        table_bayar = "pembayaran_piutang" if jenis == "piutang" else "pembayaran_hutang"
        table_main = "piutang" if jenis == "piutang" else "hutang"
        col_ref = "id_piutang" if jenis == "piutang" else "id_hutang"
        prefix = "PAY-AR" if jenis == "piutang" else "PAY-AP"
        
        # 1. Generate Nomor Pembayaran
        cursor.execute(f"SELECT COUNT(*) FROM {table_bayar}")
        count = cursor.fetchone()[0] + 1
        date_str = datetime.now().strftime('%Y%m%d')
        no_pembayaran = f"{prefix}-{date_str}-{count:04d}"
        
        # 2. Insert Pembayaran
        query_insert = f"""
        INSERT INTO {table_bayar} 
        ({col_ref}, no_pembayaran, tanggal_bayar, jumlah_bayar, metode_bayar, no_referensi, keterangan)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_insert, (id_ref, no_pembayaran, tanggal_bayar, jumlah_bayar, metode, referensi, keterangan))
        
        # 3. Update Saldo Utama (Menggunakan nama kolom asli DB: total, terbayar, sisa)
        query_update = f"""
        UPDATE {table_main}
        SET terbayar = terbayar + %s,
            sisa = total - (terbayar + %s),
            status = CASE 
                WHEN (total - (terbayar + %s)) <= 0 THEN 'LUNAS'
                ELSE status
            END
        WHERE id = %s
        """
        # Note: Logic sisa di sini sedikit tricky karena kita update terbayar dulu di memory query
        # Tapi logic SQL 'terbayar + %s' itu aman karena merujuk nilai row saat ini.
        # Parameter dikirim 3x (jumlah, jumlah, jumlah)
        
        cursor.execute(query_update, (jumlah_bayar, jumlah_bayar, jumlah_bayar, id_ref))
        
        conn.commit()
        return True, "Pembayaran berhasil disimpan"
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()