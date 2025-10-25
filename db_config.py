import mysql.connector
import streamlit as st

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="manajemen_stok"
    )

def run_query(query):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result
