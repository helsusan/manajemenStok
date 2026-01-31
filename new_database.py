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

# Insert data penjualan
def insert_penjualan(df):
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
            id_barang = id_barang[0]

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

            # ======================
            # INSERT PENJUALAN (HEADER)
            # ======================
            if no_nota not in penjualan_cache:
                query_penjualan = """
                INSERT INTO penjualan (no_nota, tanggal, id_customer, total, top, metode_bayar)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    query_penjualan,
                    (
                        str(no_nota),
                        tanggal,
                        id_customer,
                        0,          # total diupdate belakangan
                        None,       # TOP
                        None        # metode_bayar
                    )
                )
                id_penjualan = cursor.lastrowid
                penjualan_cache[no_nota] = {
                    "id": id_penjualan,
                    "total": 0
                }
            else:
                id_penjualan = penjualan_cache[no_nota]["id"]

            # ======================
            # DETAIL
            # ======================
            kuantitas = row.get('Kuantitas')
            harga_satuan = row.get('Harga Satuan') or row.get('Jumlah')

            if pd.isna(kuantitas):
                raise Exception(f"Baris {index + 2}: Kuantitas kosong")

            kuantitas = int(float(kuantitas))
            harga_satuan = float(harga_satuan) if not pd.isna(harga_satuan) else 0
            subtotal = kuantitas * harga_satuan

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
def get_penjualan_data(tanggal=None, customer=None, barang=None):
    conn = get_connection()

    query = """
        SELECT
            p.id,
            p.no_nota,
            p.tanggal,
            c.nama AS nama_customer,
            b.nama AS nama_barang,
            pd.kuantitas,
            pd.subtotal
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

    query += " ORDER BY p.tanggal DESC"

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


