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
def insert_barang(nama, satuan=None, model_prediksi="Mean", p=None, d=None, q=None):
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
            INSERT INTO barang (nama, satuan, model_prediksi, p, d, q)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        # Handle nilai NaN dari Excel supaya jadi None (NULL) di database
        def clean_val(v):
            if pd.isna(v) or v == "": return None
            try: return int(float(v))
            except: return None

        cursor.execute(query, (nama, satuan, model_prediksi, clean_val(p), clean_val(d), clean_val(q)))
        conn.commit()
        
        return True, f"Barang '{nama}' berhasil disimpan"
        
    except Exception as e:
        return False, str(e)
        
    finally:
        cursor.close()
        conn.close()

# Update isi tabel barang
def update_barang(id_barang, nama, satuan, model_prediksi, p, d, q):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        UPDATE barang
        SET nama = %s,
            satuan = %s,
            model_prediksi = %s,
            p = %s,
            d = %s,
            q = %s
        WHERE id = %s
    """
    cursor.execute(query, (nama, satuan, model_prediksi, p, d, q, int(id_barang)))

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

def get_satuan_barang(nama_barang):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT satuan FROM barang WHERE nama = %s", (nama_barang,))
        result = cursor.fetchone()
        if result and result[0]:
            return result[0]
        return "-"
    except Exception as e:
        return "-"
    finally:
        cursor.close()
        conn.close()













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
def insert_customer(nama, top=0):
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
            INSERT INTO customer (nama, top)
            VALUES (%s, %s)
        """

        cursor.execute(query, (nama, top))
        conn.commit()
        
        return True, f"Customer '{nama}' berhasil disimpan"
        
    except Exception as e:
        return False, str(e)
        
    finally:
        cursor.close()
        conn.close()

# Update isi tabel customer
def update_customer(id_cust, nama, top):
    conn = get_connection()
    cursor = conn.cursor()

    nama = normalize_customer_name(nama)

    query = """
        UPDATE customer
        SET nama = %s, top = %s
        WHERE id = %s
    """
    cursor.execute(query, (nama, top, int(id_cust)))

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

def get_top_customer(nama_cust):
    conn = get_connection()
    cursor = conn.cursor()
    nama_cust = normalize_customer_name(nama_cust)
    query = "SELECT top FROM customer WHERE nama = %s LIMIT 1"
    cursor.execute(query, (nama_cust,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result and result[0] is not None else 0













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
def insert_supplier(nama, top=0):
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
            INSERT INTO supplier (nama, top)
            VALUES (%s, %s)
        """

        cursor.execute(query, (nama, top))
        conn.commit()
       
        return True, f"Supplier '{nama}' berhasil disimpan"
       
    except Exception as e:
        return False, str(e)
       
    finally:
        cursor.close()
        conn.close()

# Update isi tabel supplier
def update_supplier(id_supp, nama, top):
    conn = get_connection()
    cursor = conn.cursor()

    nama = normalize_supplier_name(nama)

    query = """
        UPDATE supplier
        SET nama = %s, top = %s
        WHERE id = %s
    """
    cursor.execute(query, (nama, top, int(id_supp)))

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

def get_top_supplier(nama_supp):
    conn = get_connection()
    cursor = conn.cursor()
    nama_supp = normalize_supplier_name(nama_supp)
    query = "SELECT top FROM supplier WHERE nama = %s LIMIT 1"
    cursor.execute(query, (nama_supp,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result and result[0] is not None else 0











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

def get_harga_supplier(nama_supp, jenis_barang):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT sp.harga
        FROM supplier s
        JOIN supplier_pricelist sp ON s.id = sp.id_supplier
        JOIN barang b ON sp.id_barang = b.id
        WHERE s.nama = %s AND b.nama = %s
        LIMIT 1
    """

    cursor.execute(query, (nama_supp, jenis_barang))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return result[0] if result else None











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
            top = row.get("TOP") if "TOP" in df.columns and pd.notna(row.get("TOP")) else default_top
            if pd.isna(top) or top is None:
                # Ambil default dari customer
                cursor.execute("SELECT top FROM customer WHERE id = %s", (id_customer,))
                cust_top = cursor.fetchone()
                top = cust_top[0] if cust_top else 0

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
        # UPDATE TOTAL PENJUALAN & CREATE PIUTANG
        # ======================
        for no_nota, data in penjualan_cache.items():
            # Update total penjualan
            cursor.execute(
                "UPDATE penjualan SET total = %s WHERE id = %s",
                (data["total"], data["id"])
            )
            
            # Ambil data lengkap penjualan untuk create piutang
            cursor.execute("""
                SELECT tanggal, id_customer, total, top 
                FROM penjualan 
                WHERE id = %s
            """, (data["id"],))
            
            penjualan_data = cursor.fetchone()
            
            if penjualan_data:
                ualan = penjualan_data[0]
                id_cust = penjualan_data[1]
                total_penjualan = float(penjualan_data[2])
                top_value = penjualan_data[3]
                
                # Jika TOP > 0, buat piutang
                if top_value and int(top_value) > 0:
                    # Hitung due_date
                    due_date = tanggal_penjualan + timedelta(days=int(top_value))
                    
                    # Cek apakah piutang sudah ada
                    cursor.execute("""
                        SELECT id FROM piutang 
                        WHERE id_penjualan = %s
                    """, (data["id"],))
                    
                    if not cursor.fetchone():
                        # Insert piutang baru
                        cursor.execute("""
                            INSERT INTO piutang 
                            (id_penjualan, no_nota, tanggal, due_date, id_customer, 
                             total, terbayar, sisa, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, 'BELUM_LUNAS', CURDATE(), CURDATE())
                        """, (
                            data["id"],
                            no_nota,
                            tanggal_penjualan,
                            due_date,
                            id_cust,
                            total_penjualan,
                            total_penjualan  # sisa = total
                        ))

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
def get_data_penjualan(start_date=None, end_date=None, customer=None, barang=None, no_nota=None, id_penjualan=None):
    conn = get_connection()

    query = """
        SELECT
            p.id,
            p.no_nota,
            p.tanggal,
            c.nama AS nama_customer,
            b.nama AS nama_barang,
            b.satuan AS satuan,
            pd.kuantitas,
            pd.harga_satuan,
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

    if start_date and end_date:
        query += " AND DATE(p.tanggal) BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    elif start_date:
        query += " AND DATE(p.tanggal) >= %s"
        params.append(start_date)
    elif end_date:
        query += " AND DATE(p.tanggal) <= %s"
        params.append(end_date)

    if customer and customer != "Semua":
        query += " AND c.nama = %s"
        params.append(customer)

    if barang and barang != "Semua":
        query += " AND b.nama = %s"
        params.append(barang)

    if no_nota:
        query += " AND p.no_nota = %s"
        params.append(no_nota)

    if id_penjualan:
        query += " AND p.id = %s"
        params.append(id_penjualan)

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

# Fungsi baru untuk mengambil list no_nota unik
def get_all_no_nota(start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT no_nota FROM penjualan WHERE 1=1"
    params = []
    
    if start_date and end_date:
        query += " AND DATE(tanggal) BETWEEN %s AND %s"
        params.extend([start_date, end_date])
        
    query += " ORDER BY tanggal DESC, no_nota DESC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df['no_nota'].tolist()

# FUNGSI BARU UNTUK MENGAMBIL DICTIONARY (Display Text -> ID Penjualan)
def get_list_nota_untuk_print():
    conn = get_connection()
    query = """
        SELECT p.id, p.no_nota, p.tanggal, c.nama as nama_customer
        FROM penjualan p
        LEFT JOIN customer c ON p.id_customer = c.id
        WHERE 1=1
    """
    params = []
        
    query += " ORDER BY p.tanggal DESC, p.no_nota DESC"
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    
    if df.empty:
        return {}
        
    # Buat format tampilan: "PJ-001 | 02 Feb 2025 | Toko A"
    df['tanggal_str'] = pd.to_datetime(df['tanggal']).dt.strftime('%d %b %Y')
    df['display'] = df['no_nota'] + " | " + df['tanggal_str'] + " | " + df['nama_customer'].fillna('-')
    
    # Kembalikan sebagai dictionary { 'display_text' : id_penjualan }
    return dict(zip(df['display'], df['id']))










# ================================================
# DATA PEMBELIAN
# ================================================

# Cek apakah sudah ada pembelian dengan no_nota, tanggal, dan supplier yang sama
def get_existing_pembelian(no_nota, tanggal, id_supplier):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT id, total 
        FROM pembelian 
        WHERE no_nota = %s AND tanggal = %s AND id_supplier = %s
        LIMIT 1
    """
    cursor.execute(query, (str(no_nota), tanggal, int(id_supplier)))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if result:
        return {"id": result[0], "total": float(result[1])}
    return None

# Insert data pembelian
def insert_pembelian(df, default_top=None):
    conn = get_connection()
    cursor = conn.cursor()
    success_count = 0
    errors = []

    try:
        conn.start_transaction()

        pembelian_cache = {}
        
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
            nama_supplier = row.get('Nama Supplier')

            if pd.isna(no_nota) or pd.isna(tanggal):
                raise Exception(f"Baris {index + 2}: No nota atau tanggal kosong")

            id_supplier = None
            if not pd.isna(nama_supplier):
                id_supplier = get_supplier_id(nama_supplier)
                if not id_supplier:
                    raise Exception(f"Baris {index + 2}: Customer '{nama_supplier}' tidak ditemukan")
                
            # TOP → prioritas DataFrame → fallback ke default
            top = row.get("TOP") if "TOP" in df.columns and pd.notna(row.get("TOP")) else default_top
            if pd.isna(top) or top is None:
                # Ambil default dari customer
                cursor.execute("SELECT top FROM customer WHERE id = %s", (id_supplier,))
                cust_top = cursor.fetchone()
                top = cust_top[0] if cust_top else 0

            # Ambil tipe (Barang/Ongkir)
            tipe = row.get("Tipe", "Barang") # Default BARANG jika tidak ada

            # ======================
            # CEK DATABASE DULU (UNTUK INPUT MANUAL)
            # ======================
            if no_nota not in pembelian_cache:
                # Cek apakah transaksi sudah ada di database
                cursor.execute("""
                    SELECT id, total 
                    FROM pembelian 
                    WHERE no_nota = %s AND tanggal = %s AND id_supplier = %s
                    LIMIT 1
                """, (str(no_nota), tanggal, id_supplier))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Transaksi sudah ada di database, gunakan yang ada
                    pembelian_cache[no_nota] = {
                        "id": existing[0],
                        "total": float(existing[1])
                    }
                else:
                    # Transaksi belum ada, buat baru
                    query_pembelian = """
                    INSERT INTO pembelian (no_nota, tanggal, id_supplier, total, top, tipe)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(
                        query_pembelian,
                        (
                            str(no_nota),
                            tanggal,
                            id_supplier,
                            0,          # total diupdate belakangan
                            top,
                            tipe
                        )
                    )
                    id_pembelian = cursor.lastrowid
                    pembelian_cache[no_nota] = {
                        "id": id_pembelian,
                        "total": 0
                    }

            # Ambil id_pembelian dari cache
            id_pembelian = pembelian_cache[no_nota]["id"]

            # ======================
            # DETAIL PEMBELIAN
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
                FROM pembelian_detail 
                WHERE id_pembelian = %s AND id_barang = %s
                LIMIT 1
            """, (id_pembelian, id_barang))
            
            existing_detail = cursor.fetchone()
            
            if existing_detail:
                # Barang sudah ada, UPDATE kuantitas dan subtotal
                detail_id = existing_detail[0]
                old_kuantitas = existing_detail[1]
                old_subtotal = float(existing_detail[2])
                
                new_kuantitas = old_kuantitas + kuantitas
                new_subtotal = old_subtotal + subtotal
                
                query_update = """
                UPDATE pembelian_detail
                SET kuantitas = %s, subtotal = %s
                WHERE id = %s
                """
                cursor.execute(query_update, (new_kuantitas, new_subtotal, detail_id))
                
                # Update total pembelian (tambah selisihnya aja)
                pembelian_cache[no_nota]["total"] += subtotal
                
            else:
                # Barang belum ada, INSERT baru
                query_detail = """
                INSERT INTO pembelian_detail
                (id_pembelian, id_barang, kuantitas, harga_satuan, subtotal)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(
                    query_detail,
                    (id_pembelian, id_barang, kuantitas, harga_satuan, subtotal)
                )
                
                pembelian_cache[no_nota]["total"] += subtotal

            success_count += 1

        # ======================
        # UPDATE TOTAL PEMBELIAN & CREATE PIUTANG
        # ======================
        for no_nota, data in pembelian_cache.items():
            # Update total pembelian
            cursor.execute(
                "UPDATE pembelian SET total = %s WHERE id = %s",
                (data["total"], data["id"])
            )
            
            # Ambil data lengkap pembelian untuk create hutang
            cursor.execute("""
                SELECT tanggal, id_supplier, total, top 
                FROM pembelian 
                WHERE id = %s
            """, (data["id"],))
            
            pembelian_data = cursor.fetchone()
            
            if pembelian_data:
                tanggal_pembelian = pembelian_data[0]
                id_cust = pembelian_data[1]
                total_pembelian = float(pembelian_data[2])
                top_value = pembelian_data[3]
                
                # Jika TOP > 0, buat hutang
                if top_value and int(top_value) > 0:
                    # Hitung due_date
                    due_date = tanggal_pembelian + timedelta(days=int(top_value))
                    
                    # Cek apakah hutang sudah ada
                    cursor.execute("""
                        SELECT id FROM hutang 
                        WHERE id_pembelian = %s
                    """, (data["id"],))
                    
                    if not cursor.fetchone():
                        # Insert hutang baru
                        cursor.execute("""
                            INSERT INTO hutang 
                            (id_pembelian, no_nota, tanggal, due_date, id_supplier, 
                             total, terbayar, sisa, status, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, 'BELUM_LUNAS', CURDATE(), CURDATE())
                        """, (
                            data["id"],
                            no_nota,
                            tanggal_pembelian,
                            due_date,
                            id_cust,
                            total_pembelian,
                            total_pembelian  # sisa = total
                        ))

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
def get_pembelian_dates():
    conn = get_connection()
    query = """
        SELECT DISTINCT DATE(tanggal) AS tanggal
        FROM pembelian
        ORDER BY tanggal DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df['tanggal'].tolist()

# Ambil data pembelian
def get_data_pembelian(start_date=None, end_date=None, supplier=None, barang=None):
    conn = get_connection()

    query = """
        SELECT
            p.id,
            p.no_nota,
            p.tanggal,
            s.nama AS nama_supplier,
            b.nama AS nama_barang,
            b.satuan AS satuan,
            pd.kuantitas,
            pd.harga_satuan,
            pd.subtotal,
            p.total AS total_nota,
            p.top AS top
        FROM pembelian p
        JOIN pembelian_detail pd ON p.id = pd.id_pembelian
        JOIN barang b ON pd.id_barang = b.id
        LEFT JOIN supplier s ON p.id_supplier = s.id
        WHERE 1=1
    """

    params = []

    if start_date and end_date:
        query += " AND DATE(p.tanggal) BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    elif start_date:
        query += " AND DATE(p.tanggal) >= %s"
        params.append(start_date)
    elif end_date:
        query += " AND DATE(p.tanggal) <= %s"
        params.append(end_date)

    if supplier and supplier != "Semua":
        query += " AND s.nama = %s"
        params.append(supplier)

    if barang and barang != "Semua":
        query += " AND b.nama = %s"
        params.append(barang)

    query += " ORDER BY p.tanggal DESC, p.no_nota DESC"

    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# Hapus pembelian
def delete_pembelian(id_pembelian):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM pembelian_detail WHERE id_pembelian = %s",
            (int(id_pembelian),)
        )
        cursor.execute(
            "DELETE FROM pembelian WHERE id = %s",
            (int(id_pembelian),)
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










# ================================================
# MODUL PEMBAYARAN & ANALISIS (FIXED STRUCTURE)
# ================================================

def get_outstanding_invoices(jenis, id_partner=None):
    """
    Mengambil daftar invoice yang belum lunas (sisa > 0)
    beserta nama customer/supplier-nya.
    """
    conn = get_connection()
    
    # Tentukan tabel target
    table = "piutang" if jenis == "piutang" else "hutang"
    col_partner_id = "id_customer" if jenis == "piutang" else "id_supplier"
    table_partner = "customer" if jenis == "piutang" else "supplier"
    
    # Query dengan JOIN untuk ambil nama partner
    query = f"""
        SELECT 
            t.id, 
            t.no_nota, 
            t.total, 
            t.terbayar, 
            t.sisa, 
            t.due_date, 
            p.nama as partner_name
        FROM {table} t
        JOIN {table_partner} p ON t.{col_partner_id} = p.id
        WHERE t.sisa > 0
    """
    params = []
    
    if id_partner:
        query += f" AND t.{col_partner_id} = %s"
        params.append(id_partner)
        
    query += " ORDER BY t.due_date ASC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def get_history_pembayaran(jenis, start_date=None, end_date=None):
    """
    Mengambil riwayat pembayaran.
    Perbaikan: Menyesuaikan nama kolom dengan struktur_db.sql
    """
    conn = get_connection()
    table_bayar = "pembayaran_piutang" if jenis == "piutang" else "pembayaran_hutang"
    table_parent = "piutang" if jenis == "piutang" else "hutang"
    col_ref = "id_piutang" if jenis == "piutang" else "id_hutang"
    table_partner = "customer" if jenis == "piutang" else "supplier"
    col_partner_id = "id_customer" if jenis == "piutang" else "id_supplier"
    
    # Perubahan Query: 
    # - pb.no_invoice AS no_pembayaran (karena DB pakai nama no_invoice)
    # - pb.jumlah AS jumlah_bayar
    # - Hapus pb.metode_bayar (karena tidak ada di DB)
    query = f"""
        SELECT 
            pb.id,
            pb.no_invoice as no_pembayaran, 
            pb.tanggal_bayar,
            p.no_nota as no_invoice_tagihan,
            part.nama as partner,
            pb.jumlah as jumlah_bayar,
            pb.keterangan
        FROM {table_bayar} pb
        JOIN {table_parent} p ON pb.{col_ref} = p.id
        JOIN {table_partner} part ON p.{col_partner_id} = part.id
        WHERE 1=1
    """
    params = []
    
    if start_date and end_date:
        query += " AND pb.tanggal_bayar BETWEEN %s AND %s"
        params.append(start_date)
        params.append(end_date)
        
    query += " ORDER BY pb.tanggal_bayar DESC, pb.id DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def delete_pembayaran(jenis, id_pembayaran):
    """
    Menghapus data pembayaran dan MENGEMBALIKAN saldo invoice.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        conn.start_transaction()
        
        table_bayar = "pembayaran_piutang" if jenis == "piutang" else "pembayaran_hutang"
        table_parent = "piutang" if jenis == "piutang" else "hutang"
        col_ref = "id_piutang" if jenis == "piutang" else "id_hutang"
        
        # 1. Ambil info pembayaran sebelum dihapus
        # Perubahan: jumlah_bayar -> jumlah
        cursor.execute(f"SELECT {col_ref}, jumlah FROM {table_bayar} WHERE id = %s", (id_pembayaran,))
        row = cursor.fetchone()
        
        if not row:
            raise Exception("Data pembayaran tidak ditemukan")
            
        id_ref, jumlah = row
        
        # 2. Hapus Pembayaran
        cursor.execute(f"DELETE FROM {table_bayar} WHERE id = %s", (id_pembayaran,))
        
        # 3. Revert Saldo Parent
        q_revert = f"""
            UPDATE {table_parent}
            SET terbayar = terbayar - %s,
                sisa = sisa + %s,
                status = 'BELUM_LUNAS'
            WHERE id = %s
        """
        cursor.execute(q_revert, (jumlah, jumlah, id_ref))
        
        conn.commit()
        return True, "Pembayaran berhasil dihapus dan saldo dikembalikan"
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def get_analisis_summary(jenis):
    """
    Mengambil data ringkasan untuk Dashboard.
    """
    conn = get_connection()
    table = "piutang" if jenis == "piutang" else "hutang"
    
    q_summary = f"""
        SELECT 
            COUNT(*) as total_inv,
            COALESCE(SUM(total), 0) as total_nominal,
            COALESCE(SUM(sisa), 0) as sisa_outstanding
        FROM {table}
        WHERE sisa > 0
    """
    
    # Overdue logic
    q_overdue = f"""
        SELECT COUNT(*) as count, COALESCE(SUM(sisa), 0) as nominal 
        FROM {table} 
        WHERE status = 'OVERDUE' OR (sisa > 0 AND due_date < CURDATE())
    """
    
    summary = pd.read_sql(q_summary, conn).iloc[0]
    overdue = pd.read_sql(q_overdue, conn).iloc[0]
    
    conn.close()
    return summary, overdue

# ================================================
# AUTO-CREATE PIUTANG DARI PENJUALAN
# ================================================

def create_piutang_from_penjualan(id_penjualan, no_nota, tanggal, id_customer, total, top):
    """
    Membuat record piutang otomatis dari transaksi penjualan.
    Dipanggil otomatis saat insert_penjualan jika TOP > 0.
    
    Args:
        id_penjualan: ID dari tabel penjualan
        no_nota: Nomor nota penjualan
        tanggal: Tanggal transaksi
        id_customer: ID customer
        total: Total nilai penjualan
        top: Term of Payment dalam hari
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Hitung due_date berdasarkan TOP
        due_date = tanggal + timedelta(days=int(top))
        
        # Cek apakah piutang sudah ada (untuk prevent duplikasi)
        cursor.execute("""
            SELECT id FROM piutang 
            WHERE id_penjualan = %s
            LIMIT 1
        """, (id_penjualan,))
        
        existing = cursor.fetchone()
        
        if not existing:
            # Insert piutang baru
            query = """
                INSERT INTO piutang 
                (id_penjualan, no_nota, tanggal, due_date, id_customer, total, terbayar, sisa, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, 'BELUM_LUNAS', CURDATE(), CURDATE())
            """
            cursor.execute(query, (
                id_penjualan, 
                no_nota, 
                tanggal, 
                due_date, 
                id_customer, 
                total, 
                total  # sisa = total pada awalnya
            ))
            
            conn.commit()
            return True, "Piutang berhasil dibuat"
        else:
            return True, "Piutang sudah ada"
            
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

# ================================================
# INSERT PEMBAYARAN PIUTANG (SESUAI STRUKTUR DB)
# ================================================

def insert_pembayaran_piutang(id_piutang, no_invoice, tanggal_bayar, jumlah, keterangan):
    """
    Insert pembayaran piutang baru sesuai struktur database.
    PERBAIKAN: SELALU INSERT, TIDAK PERNAH UPDATE.
    Jika ada pembayaran di tanggal yang sama, tetap insert sebagai record terpisah.
    
    Args:
        id_piutang: ID dari tabel piutang (bukan id_penjualan)
        no_invoice: Nomor invoice pembayaran
        tanggal_bayar: Tanggal pembayaran dilakukan
        jumlah: Jumlah yang dibayarkan
        keterangan: Catatan/keterangan pembayaran
    
    Returns:
        Tuple (success: bool, message: str)
    
    Called by: input_pelunasan_piutang.py (Tab Input Manual)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        conn.start_transaction()
        
        # created_at otomatis ambil tanggal hari ini
        created_at = datetime.now().strftime('%Y-%m-%d')
        
        # PENTING: Tidak ada pengecekan existing data
        # Langsung INSERT sebagai record baru
        
        # 1. Insert ke tabel pembayaran_piutang (SELALU INSERT BARU)
        query_insert = """
            INSERT INTO pembayaran_piutang 
            (id_piutang, no_invoice, tanggal_bayar, jumlah, keterangan, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query_insert, (
            int(id_piutang),
            no_invoice,
            tanggal_bayar,
            float(jumlah),
            keterangan if keterangan else None,
            created_at
        ))
        
        # Ambil ID pembayaran yang baru di-insert
        id_pembayaran_baru = cursor.lastrowid
        
        # 2. Update saldo di tabel piutang (akumulatif)
        query_update = """
            UPDATE piutang
            SET terbayar = terbayar + %s,
                sisa = sisa - %s,
                status = CASE 
                    WHEN (sisa - %s) <= 0 THEN 'LUNAS'
                    WHEN (sisa - %s) > 0 AND due_date < CURDATE() THEN 'OVERDUE'
                    ELSE 'BELUM_LUNAS'
                END,
                updated_at = CURDATE()
            WHERE id = %s
        """
        
        cursor.execute(query_update, (
            float(jumlah),  # terbayar + jumlah
            float(jumlah),  # sisa - jumlah
            float(jumlah),  # untuk pengecekan status LUNAS
            float(jumlah),  # untuk pengecekan status OVERDUE
            int(id_piutang)
        ))
        
        # Cek apakah update berhasil
        if cursor.rowcount == 0:
            raise Exception("Data piutang tidak ditemukan atau sudah lunas")
        
        conn.commit()
        
        return True, f"Pembayaran #{id_pembayaran_baru} sebesar Rp {jumlah:,.0f} berhasil disimpan"
        
    except Exception as e:
        conn.rollback()
        return False, f"Gagal menyimpan pembayaran: {str(e)}"
        
    finally:
        cursor.close()
        conn.close()

def insert_pembayaran_hutang(id_hutang, no_invoice, tanggal_bayar, jumlah, keterangan):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        conn.start_transaction()
        
        # created_at otomatis ambil tanggal hari ini
        created_at = datetime.now().strftime('%Y-%m-%d')
        
        # PENTING: Tidak ada pengecekan existing data
        # Langsung INSERT sebagai record baru
        
        # 1. Insert ke tabel pembayaran_hutang (SELALU INSERT BARU)
        query_insert = """
            INSERT INTO pembayaran_hutang
            (id_hutang, no_invoice, tanggal_bayar, jumlah, keterangan, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query_insert, (
            int(id_hutang),
            no_invoice,
            tanggal_bayar,
            float(jumlah),
            keterangan if keterangan else None,
            created_at
        ))
        
        # Ambil ID pembayaran yang baru di-insert
        id_pembayaran_baru = cursor.lastrowid
        
        # 2. Update saldo di tabel piutang (akumulatif)
        query_update = """
            UPDATE hutang
            SET terbayar = terbayar + %s,
                sisa = sisa - %s,
                status = CASE 
                    WHEN (sisa - %s) <= 0 THEN 'LUNAS'
                    WHEN (sisa - %s) > 0 AND due_date < CURDATE() THEN 'OVERDUE'
                    ELSE 'BELUM_LUNAS'
                END,
                updated_at = CURDATE()
            WHERE id = %s
        """
        
        cursor.execute(query_update, (
            float(jumlah),  # terbayar + jumlah
            float(jumlah),  # sisa - jumlah
            float(jumlah),  # untuk pengecekan status LUNAS
            float(jumlah),  # untuk pengecekan status OVERDUE
            int(id_hutang)
        ))
        
        # Cek apakah update berhasil
        if cursor.rowcount == 0:
            raise Exception("Data hutang tidak ditemukan atau sudah lunas")
        
        conn.commit()
        
        return True, f"Pembayaran #{id_pembayaran_baru} sebesar Rp {jumlah:,.0f} berhasil disimpan"
        
    except Exception as e:
        conn.rollback()
        return False, f"Gagal menyimpan pembayaran: {str(e)}"
        
    finally:
        cursor.close()
        conn.close()


import mysql.connector
import pandas as pd
import streamlit as st # Diperlukan untuk decorator cache

# ... (Kode get_connection yang sudah ada sebelumnya biarkan saja) ...

# ================================================
# MODUL GROSS PROFIT & ANALISIS
# ================================================

@st.cache_data(ttl=300)
def get_pembelian_data(start_date=None, end_date=None):
    """Mengambil data pembelian detail"""
    conn = get_connection()
    query = """
    SELECT 
        pd.id,
        p.tanggal,
        p.no_nota,
        pd.id_barang,
        b.nama as nama_barang,
        pd.kuantitas,
        pd.harga_satuan,
        pd.subtotal,
        p.tipe
    FROM pembelian_detail pd
    JOIN pembelian p ON pd.id_pembelian = p.id
    JOIN barang b ON pd.id_barang = b.id
    """
    
    if start_date and end_date:
        query += f" WHERE p.tanggal BETWEEN '{start_date}' AND '{end_date}'"
    
    query += " ORDER BY p.tanggal, pd.id"
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def get_penjualan_data(start_date=None, end_date=None):
    """Mengambil data penjualan detail"""
    conn = get_connection()
    query = """
    SELECT 
        pd.id,
        p.tanggal,
        p.no_nota,
        pd.id_barang,
        b.nama as nama_barang,
        pd.kuantitas,
        pd.harga_satuan,
        pd.subtotal
    FROM penjualan_detail pd
    JOIN penjualan p ON pd.id_penjualan = p.id
    JOIN barang b ON pd.id_barang = b.id
    """
    
    if start_date and end_date:
        query += f" WHERE p.tanggal BETWEEN '{start_date}' AND '{end_date}'"
    
    query += " ORDER BY p.tanggal, pd.id"
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=300)
def get_barang_list_simple():
    """Mengambil list nama barang saja untuk filter"""
    conn = get_connection()
    query = "SELECT id, nama FROM barang ORDER BY nama"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def calculate_gross_profit_fifo(pembelian_df, penjualan_df):
    """
    Menghitung gross profit menggunakan metode FIFO
    
    PERBAIKAN:
    - Ongkir dikaitkan dengan barang berdasarkan (tanggal, id_barang)
    - HPP = (Harga Barang + Ongkir Spesifik) / Qty
    """
    results = []
    
    # STEP 1: Mapping ongkir ke barang berdasarkan tanggal + id_barang
    ongkir_map = {}  # Key: (tanggal, id_barang) -> Value: total_ongkir
    
    # Ambil semua baris ongkir
    ongkir_rows = pembelian_df[pembelian_df['tipe'] == 'Ongkir']
    
    for _, ongkir_row in ongkir_rows.iterrows():
        key = (ongkir_row['tanggal'], ongkir_row['id_barang'])
        ongkir_map[key] = float(ongkir_row['subtotal'])
    
    # STEP 2: Proses setiap barang
    barang_ids = penjualan_df['id_barang'].unique()
    
    for barang_id in barang_ids:
        # Filter pembelian dan penjualan untuk barang ini (HANYA TIPE BARANG)
        pembelian_barang = pembelian_df[
            (pembelian_df['id_barang'] == barang_id) & 
            (pembelian_df['tipe'] == 'Barang')
        ].copy()
        
        penjualan_barang = penjualan_df[penjualan_df['id_barang'] == barang_id].copy()
        
        if pembelian_barang.empty or penjualan_barang.empty:
            continue
        
        # STEP 3: Hitung HPP per unit (termasuk ongkir spesifik)
        pembelian_processed = []
        
        for idx, row in pembelian_barang.iterrows():
            tanggal = row['tanggal']
            qty = float(row['kuantitas'])
            harga_barang = float(row['subtotal'])
            
            # Cari ongkir spesifik untuk barang ini di tanggal yang sama
            key = (tanggal, barang_id)
            if key in ongkir_map:
                ongkir_total = ongkir_map[key]
            else:
                ongkir_total = 0
            
            # Total cost = harga barang + ongkir
            total_cost = harga_barang + ongkir_total
            unit_cost = total_cost / qty if qty > 0 else 0
            
            pembelian_processed.append({
                'tanggal': tanggal,
                'no_nota': row['no_nota'],
                'kuantitas': qty,
                'harga_per_unit': unit_cost,
                'total_cost': total_cost,
                'kuantitas_sisa': qty
            })
        
        # STEP 4: FIFO calculation
        total_penjualan = 0
        total_hpp = 0
        purchase_queue = pembelian_processed.copy()
        
        for _, penjualan in penjualan_barang.iterrows():
            qty_terjual = float(penjualan['kuantitas'])
            harga_jual = float(penjualan['harga_satuan'])
            
            total_penjualan += qty_terjual * harga_jual
            
            # Alokasi HPP menggunakan FIFO
            qty_remaining = qty_terjual
            
            while qty_remaining > 0 and purchase_queue:
                oldest_purchase = purchase_queue[0]
                
                if oldest_purchase['kuantitas_sisa'] >= qty_remaining:
                    # Pembelian ini cukup untuk memenuhi penjualan
                    hpp = qty_remaining * oldest_purchase['harga_per_unit']
                    total_hpp += hpp
                    oldest_purchase['kuantitas_sisa'] -= qty_remaining
                    qty_remaining = 0
                    
                    if oldest_purchase['kuantitas_sisa'] == 0:
                        purchase_queue.pop(0)
                else:
                    # Pembelian ini tidak cukup, ambil semua dan lanjut ke pembelian berikutnya
                    hpp = oldest_purchase['kuantitas_sisa'] * oldest_purchase['harga_per_unit']
                    total_hpp += hpp
                    qty_remaining -= oldest_purchase['kuantitas_sisa']
                    purchase_queue.pop(0)
        
        gross_profit = total_penjualan - total_hpp
        margin = (gross_profit / total_penjualan * 100) if total_penjualan > 0 else 0
        
        results.append({
            'id_barang': barang_id,
            'nama_barang': penjualan_barang.iloc[0]['nama_barang'],
            'total_penjualan': total_penjualan,
            'total_hpp': total_hpp,
            'gross_profit': gross_profit,
            'margin_persen': margin,
            'qty_terjual': penjualan_barang['kuantitas'].sum()
        })
    
    return pd.DataFrame(results)




# ================================================
# 2. FUNGSI GENERATE KARTU STOK FIFO (NEW)
# ================================================

def generate_kartu_stok_fifo(barang_id, pembelian_df, penjualan_df):
    """
    Generate kartu stok FIFO untuk 1 barang tertentu
    Menampilkan setiap transaksi penjualan dengan:
    - Qty terjual
    - Harga jual per pcs
    - HPP per pcs (FIFO)
    - Gross Profit per transaksi
    
    Args:
        barang_id: ID barang yang ingin dilihat
        pembelian_df: DataFrame pembelian (sudah termasuk perhitungan ongkir)
        penjualan_df: DataFrame penjualan
    
    Returns:
        DataFrame dengan kolom: tanggal, no_nota, qty, harga_jual, hpp_avg, subtotal, 
                                total_hpp, gross_profit, margin_persen, hpp_breakdown
    """
    
    # Filter data untuk barang ini
    pembelian_barang = pembelian_df[
        (pembelian_df['id_barang'] == barang_id) & 
        (pembelian_df['tipe'] == 'Barang')
    ].copy().sort_values('tanggal')
    
    penjualan_barang = penjualan_df[
        penjualan_df['id_barang'] == barang_id
    ].copy().sort_values('tanggal')
    
    if pembelian_barang.empty or penjualan_barang.empty:
        return pd.DataFrame()
    
    # STEP 1: Mapping ongkir untuk perhitungan HPP
    ongkir_map = {}
    ongkir_rows = pembelian_df[
        (pembelian_df['id_barang'] == barang_id) & 
        (pembelian_df['tipe'] == 'Ongkir')
    ]
    
    for _, ongkir_row in ongkir_rows.iterrows():
        key = (ongkir_row['tanggal'], ongkir_row['id_barang'])
        ongkir_map[key] = float(ongkir_row['subtotal'])
    
    # STEP 2: Hitung HPP per unit untuk setiap pembelian (termasuk ongkir)
    purchase_queue = []
    
    for _, row in pembelian_barang.iterrows():
        tanggal = row['tanggal']
        qty = float(row['kuantitas'])
        harga_barang = float(row['subtotal'])
        
        # Cari ongkir spesifik
        key = (tanggal, barang_id)
        ongkir_total = ongkir_map.get(key, 0)
        
        # Total cost = harga barang + ongkir
        total_cost = harga_barang + ongkir_total
        unit_cost = total_cost / qty if qty > 0 else 0
        
        purchase_queue.append({
            'tanggal': tanggal,
            'no_nota': row['no_nota'],
            'kuantitas': qty,
            'harga_per_unit': unit_cost,
            'kuantitas_sisa': qty
        })
    
    # STEP 3: Proses setiap transaksi penjualan dengan FIFO
    kartu_stok = []
    
    for _, penjualan in penjualan_barang.iterrows():
        tanggal_jual = penjualan['tanggal']
        no_nota = penjualan['no_nota']
        qty_terjual = float(penjualan['kuantitas'])
        harga_jual = float(penjualan['harga_satuan'])
        subtotal_jual = float(penjualan['subtotal'])
        
        # Alokasi HPP menggunakan FIFO
        qty_remaining = qty_terjual
        total_hpp_transaksi = 0
        hpp_details = []  # Untuk tracking dari mana HPP diambil
        
        # Buat copy queue untuk transaksi ini
        temp_queue = [p.copy() for p in purchase_queue]
        
        while qty_remaining > 0 and temp_queue:
            oldest_purchase = temp_queue[0]
            
            if oldest_purchase['kuantitas_sisa'] >= qty_remaining:
                # Pembelian ini cukup untuk memenuhi penjualan
                hpp = qty_remaining * oldest_purchase['harga_per_unit']
                total_hpp_transaksi += hpp
                
                hpp_details.append({
                    'nota_beli': oldest_purchase['no_nota'],
                    'qty': qty_remaining,
                    'hpp_per_unit': oldest_purchase['harga_per_unit']
                })
                
                oldest_purchase['kuantitas_sisa'] -= qty_remaining
                qty_remaining = 0
                
                if oldest_purchase['kuantitas_sisa'] == 0:
                    temp_queue.pop(0)
            else:
                # Pembelian ini tidak cukup, ambil semua
                hpp = oldest_purchase['kuantitas_sisa'] * oldest_purchase['harga_per_unit']
                total_hpp_transaksi += hpp
                
                hpp_details.append({
                    'nota_beli': oldest_purchase['no_nota'],
                    'qty': oldest_purchase['kuantitas_sisa'],
                    'hpp_per_unit': oldest_purchase['harga_per_unit']
                })
                
                qty_remaining -= oldest_purchase['kuantitas_sisa']
                temp_queue.pop(0)
        
        # Update purchase_queue asli dengan yang sudah dipakai
        purchase_queue = temp_queue
        
        # Hitung gross profit untuk transaksi ini
        gross_profit = subtotal_jual - total_hpp_transaksi
        margin_persen = (gross_profit / subtotal_jual * 100) if subtotal_jual > 0 else 0
        
        # HPP rata-rata per unit untuk transaksi ini
        hpp_avg_per_unit = total_hpp_transaksi / qty_terjual if qty_terjual > 0 else 0
        
        # Format HPP details untuk tooltip/info
        hpp_breakdown = " + ".join([
            f"{d['qty']:.0f} pcs @ Rp {d['hpp_per_unit']:,.0f} ({d['nota_beli']})"
            for d in hpp_details
        ])
        
        kartu_stok.append({
            'tanggal': tanggal_jual,
            'no_nota': no_nota,
            'qty': qty_terjual,
            'harga_jual': harga_jual,
            'hpp_avg': hpp_avg_per_unit,
            'subtotal': subtotal_jual,
            'total_hpp': total_hpp_transaksi,
            'gross_profit': gross_profit,
            'margin_persen': margin_persen,
            'hpp_breakdown': hpp_breakdown  # Detail dari mana HPP diambil
        })
    
    return pd.DataFrame(kartu_stok)







# ================================================
# DATA KARTU STOK
# ================================================

def get_stok_awal_barang(id_barang, start_date):
    """Menghitung stok sebelum tanggal mulai (Start Date)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT COALESCE(SUM(masuk) - SUM(keluar), 0) as stok_awal
        FROM (
            -- Barang Masuk dari Pembelian
            SELECT pd.kuantitas as masuk, 0 as keluar
            FROM pembelian_detail pd
            JOIN pembelian p ON pd.id_pembelian = p.id
            WHERE pd.id_barang = %s AND p.tipe = 'Barang' AND p.tanggal < %s
            
            UNION ALL
            
            -- Barang Keluar dari Penjualan
            SELECT 0 as masuk, pjd.kuantitas as keluar
            FROM penjualan_detail pjd
            JOIN penjualan pj ON pjd.id_penjualan = pj.id
            WHERE pjd.id_barang = %s AND pj.tanggal < %s
        ) as riwayat_awal
    """
    
    cursor.execute(query, (id_barang, start_date, id_barang, start_date))
    result = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return float(result[0]) if result else 0.0

def get_mutasi_harian(id_barang, start_date, end_date):
    """Mengambil riwayat masuk keluar per hari dalam rentang tanggal tertentu"""
    conn = get_connection()
    
    query = """
        SELECT 
            tanggal,
            SUM(masuk) as total_masuk,
            SUM(keluar) as total_keluar
        FROM (
            -- Barang Masuk dari Pembelian
            SELECT p.tanggal, pd.kuantitas as masuk, 0 as keluar
            FROM pembelian_detail pd
            JOIN pembelian p ON pd.id_pembelian = p.id
            WHERE pd.id_barang = %s AND p.tipe = 'Barang' AND p.tanggal BETWEEN %s AND %s
            
            UNION ALL
            
            -- Barang Keluar dari Penjualan
            SELECT pj.tanggal, 0 as masuk, pjd.kuantitas as keluar
            FROM penjualan_detail pjd
            JOIN penjualan pj ON pjd.id_penjualan = pj.id
            WHERE pjd.id_barang = %s AND pj.tanggal BETWEEN %s AND %s
        ) as mutasi
        GROUP BY tanggal
        ORDER BY tanggal ASC
    """
    
    df = pd.read_sql(query, conn, params=(id_barang, start_date, end_date, id_barang, start_date, end_date))
    conn.close()
    return df



# ================================================
# DATA BIAYA TAMBAHAN
# ================================================

def insert_biaya_tambahan(nama, tanggal, jumlah):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            INSERT INTO biaya_tambahan (nama, tanggal, jumlah) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(query, (nama, tanggal, float(jumlah)))
        conn.commit()
        return True, "Biaya tambahan berhasil disimpan"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

def get_all_biaya_tambahan(start_date=None, end_date=None):
    conn = get_connection()
    query = "SELECT id, nama, tanggal, jumlah FROM biaya_tambahan"
    params = []
    
    if start_date and end_date:
        query += " WHERE tanggal BETWEEN %s AND %s"
        params.extend([start_date, end_date])
        
    query += " ORDER BY tanggal DESC, id DESC"
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def delete_biaya_tambahan(id_biaya):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM biaya_tambahan WHERE id = %s", (int(id_biaya),))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()