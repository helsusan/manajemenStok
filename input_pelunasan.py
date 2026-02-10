import streamlit as st
import pandas as pd
from datetime import datetime
import new_database

st.set_page_config(
    page_title="Pelunasan Hutang & Piutang",
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

st.header("Pelunasan Hutang & Piutang")

tab1, tab2 = st.tabs(["📝 Hutang", "📤 Piutang"])

# ================================================
# TAB 1 : PELUNASAN HUTANG
# ================================================

with tab1:
    st.subheader("➕ Input Pelunasan Hutang")

    customers = new_database.get_all_data_customer(["id", "nama"])
    cust_opts = {"-- Pilih Customer --": None}
    if not customers.empty:
        cust_opts.update(dict(zip(customers['nama'], customers['id'])))
        
    sel_cust = st.selectbox("Pilih Customer", options=list(cust_opts.keys()))
    
    if sel_cust != "-- Pilih Customer --":
        cust_id = cust_opts[sel_cust]
        # Query piutang active customer ini
        df = new_database.get_filtered_piutang(
            datetime(2000,1,1), datetime(2099,12,31), 
            cust_id, "BELUM_LUNAS"
        )
        
        if not df.empty:
            st.subheader(f"Tagihan: {sel_cust}")
            for idx, row in df.iterrows():
                with st.expander(f"{row['no_invoice']} | Sisa: {format_currency(row['sisa_piutang'])}"):
                    new_database.render_payment_form('piutang', row)
        else:
            st.success("Tidak ada tagihan belum lunas.")

# ================================================
# TAB 2 : PELUNASAN PIUTANG
# ================================================

with tab2:
    st.subheader("➕ Input Pelunasan Piutang")

    suppliers = new_database.get_all_data_supplier(["id", "nama"])
    supp_opts = {"-- Pilih Supplier --": None}
    if not suppliers.empty:
        supp_opts.update(dict(zip(suppliers['nama'], suppliers['id'])))
        
    sel_supp = st.selectbox("Pilih Supplier", options=list(supp_opts.keys()))
    
    if sel_supp != "-- Pilih Supplier --":
        supp_id = supp_opts[sel_supp]
        df = new_database.get_filtered_hutang(
            datetime(2000,1,1), datetime(2099,12,31), 
            supp_id, "BELUM_LUNAS"
        )
        
        if not df.empty:
            st.subheader(f"Tagihan: {sel_supp}")
            for idx, row in df.iterrows():
                with st.expander(f"{row['no_invoice']} | Sisa: {format_currency(row['sisa_hutang'])}"):
                    new_database.render_payment_form('hutang', row)
        else:
            st.success("Tidak ada hutang belum lunas.")