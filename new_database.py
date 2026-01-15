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

# Input data barang ke database
def insert_barang(nama_barang, model_prediksi="Mean", p=None, d=None, q=None):
    conn = get_connection()
    cursor = conn.cursor()

    success_count = 0
    error_count = 0
    errors = []

    for idx, row in df.iterrows():
        nama_barang = row["Nama"]

        try:
            # Skip kosong
            if not nama_barang or str(nama_barang).strip() == "":
                raise ValueError("Nama barang kosong")

            # Cek duplikasi
            cursor.execute(
                "SELECT id FROM barang WHERE nama = %s",
                (nama_barang,)
            )
            if cursor.fetchone():
                raise ValueError(f"Barang '{nama_barang}' sudah ada")

            # Insert
            cursor.execute(
                """
                INSERT INTO barang (nama, model_prediksi, p, d, q)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (nama_barang, model_prediksi, p, d, q)
            )
            success_count += 1

        except Exception as e:
            error_count += 1
            errors.append(f"Baris {idx + 1}: {str(e)}")

    conn.commit()
    cursor.close()
    conn.close()

    return success_count, error_count, errors

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

# Ambil semua data customer tapi bisa pilih kolomnya
def get_all_data_customer(columns="*"):
    conn = get_connection()
    
    if isinstance(columns, list):
        columns = ", ".join(columns)

    query = f"SELECT {columns} FROM customer"
    df = pd.read_sql(query, conn)
    conn.close()
    
    return df
