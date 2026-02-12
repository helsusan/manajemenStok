import streamlit as st

pages = {
    "Kelola Data": [
        st.Page("input_data_barang.py", title="Data Barang"),
        st.Page("input_data_customer.py", title="Data Customer"),
        st.Page("input_data_supplier.py", title="Data Supplier"),
        st.Page("input_data_penjualan.py", title="Data Penjualan"),
        st.Page("input_data_pembelian.py", title="Data Pembelian"),
        st.Page("input_pelunasan_piutang.py", title="Data Piutang"),
        st.Page("input_pelunasan_hutang.py", title="Data Hutang"),
    ],
    "Dashboard": [
        st.Page("rekapan.py", title="Rekapan Hutang & Piutang"),
        st.Page("gross_profit.py", title="Gross Profit"),
    ],
}

pg = st.navigation(pages)
pg.run()