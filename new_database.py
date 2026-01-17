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

def check_pricelist_exists(id_customer, id_barang):
    """
    Check if pricelist combination already exists
    Returns True if exists, False otherwise
    """
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

def upsert_customer_pricelist(id_customer, id_barang, harga):
    """
    Insert or Update customer pricelist
    If combination exists, update the price and timestamp
    If not, insert new record
    """
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

def update_customer_pricelist(id_pricelist, harga):
    """Update specific pricelist by ID"""
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

def get_customer_with_pricelist():
    """
    Get all customers with their pricelist
    Returns DataFrame with columns: id_customer, customer, id_pricelist, barang, harga, updated_at
    """
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