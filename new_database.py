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
def insert_barang(nama_barang, model_prediksi="Mean"):
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
                INSERT INTO barang (nama, model_prediksi)
                VALUES (%s, %s)
                """,
                (nama_barang, "Mean")
            )
            success_count += 1

        except Exception as e:
            error_count += 1
            errors.append(f"Baris {idx + 1}: {str(e)}")

    conn.commit()
    cursor.close()
    conn.close()

    return success_count, error_count, errors












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
