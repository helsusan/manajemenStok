import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import new_database

st.set_page_config(
    page_title="Rekapan Hutang & Piutang",
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

st.header("Rekapan Hutang & Piutang")

tab1, tab2, tab3 = st.tabs(["Semua", "Hutang", "Piutang"])

# ================================================
# TAB 1 : DASHBOARD HUTANG & PIUTANG
# ================================================

with tab1:
    # st.subheader("📊 Dashboard Piutang & Hutang")

    # --- SUMMARY PIUTANG ---
    st.subheader("📈 Ringkasan Piutang")
    col1, col2, col3, col4 = st.columns(4)
    
    data_piutang = new_database.get_piutang_summary()
    
    if data_piutang is not None:
        with col1: st.metric("Total Invoice", data_piutang['total_invoice'])
        with col2: st.metric("Total Piutang", new_database.format_currency(data_piutang['total_piutang']))
        with col3: st.metric("Sudah Dibayar", new_database.format_currency(data_piutang['total_terbayar']))
        with col4: st.metric("Sisa Piutang", new_database.format_currency(data_piutang['sisa_piutang']))
    
    # Alerts Piutang
    overdue, due_week = new_database.get_overdue_alerts('piutang')
    if overdue and overdue['jml'] > 0:
        st.error(f"⚠️ **{overdue['jml']} invoice PIUTANG OVERDUE** dengan total {new_database.format_currency(overdue['total'])}")
    if due_week and due_week['jml'] > 0:
        st.warning(f"📅 **{due_week['jml']} invoice PIUTANG jatuh tempo minggu ini** dengan total {new_database.format_currency(due_week['total'])}")
    
    st.markdown("---")
    
    # --- SUMMARY HUTANG ---
    st.subheader("📉 Ringkasan Hutang")
    col1, col2, col3, col4 = st.columns(4)
    
    data_hutang = new_database.get_hutang_summary()
    
    if data_hutang is not None:
        with col1: st.metric("Total Invoice", data_hutang['total_invoice'])
        with col2: st.metric("Total Hutang", new_database.format_currency(data_hutang['total_hutang']))
        with col3: st.metric("Sudah Dibayar", new_database.format_currency(data_hutang['total_terbayar']))
        with col4: st.metric("Sisa Hutang", new_database.format_currency(data_hutang['sisa_hutang']))

    # Alerts Hutang
    overdue_h, due_week_h = new_database.get_overdue_alerts('hutang')
    if overdue_h and overdue_h['jml'] > 0:
        st.error(f"⚠️ **{overdue_h['jml']} invoice HUTANG OVERDUE** dengan total {new_database.format_currency(overdue_h['total'])}")
    if due_week_h and due_week_h['jml'] > 0:
        st.warning(f"📅 **{due_week_h['jml']} invoice HUTANG jatuh tempo minggu ini** dengan total {new_database.format_currency(due_week_h['total'])}")

# ================================================
# TAB 2 : REKAPAN PIUTANG
# ================================================

with tab2:
    st.subheader("📋 Rekapan Piutang")

    with st.expander("🔍 Filter Data", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Tanggal Mulai", value=datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Tanggal Akhir", value=datetime.now())
        with col3:
            customers = new_database.get_all_data_customer(["id", "nama"])
            customer_options = {"Semua": 0}
            if not customers.empty:
                customer_options.update(dict(zip(customers['nama'], customers['id'])))
            selected_customer = st.selectbox("Customer", options=list(customer_options.keys()))
        
        col4, col5, col6 = st.columns(3)
        with col4:
            status_filter = st.selectbox("Status", ["Semua", "BELUM_LUNAS", "LUNAS", "OVERDUE"])
        with col5:
            search_invoice = st.text_input("Cari No Invoice")
        with col6:
            st.write("")
            apply_filter = st.button("🔍 Terapkan Filter", use_container_width=True)

    # Get Data
    df = new_database.get_filtered_piutang(
        start_date, end_date, 
        customer_options[selected_customer], 
        status_filter, 
        search_invoice
    )
    
    if not df.empty:
        # Summary small cards
        c1, c2, c3 = st.columns(3)
        c1.info(f"**Total Invoice:** {len(df)}")
        c2.info(f"**Total Piutang:** {new_database.format_currency(df['total_piutang'].sum())}")
        c3.info(f"**Sisa Piutang:** {new_database.format_currency(df['sisa_piutang'].sum())}")
        
        st.markdown("---")
        
        for idx, row in df.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    # Status logic
                    if row['status'] == 'OVERDUE':
                        status_color, status_text = "🔴", f"OVERDUE ({row['hari_overdue']} hari)"
                    elif row['status'] == 'LUNAS':
                        status_color, status_text = "✅", "LUNAS"
                    else:
                        status_color, status_text = "🟡", "BELUM LUNAS"
                    
                    st.markdown(f"### {status_color} {row['no_invoice']} - {row['customer']}")
                    st.write(f"**Tgl:** {row['tanggal_invoice']} | **Jatuh Tempo:** {row['tanggal_jatuh_tempo']}")
                    
                    ca, cb, cc = st.columns(3)
                    ca.metric("Total", new_database.format_currency(row['total_piutang']))
                    cb.metric("Terbayar", new_database.format_currency(row['total_terbayar']))
                    cc.metric("Sisa", new_database.format_currency(row['sisa_piutang']))
                    st.caption(f"Status: {status_text}")

                with col2:
                    st.write("")
                    if st.button("📄 Detail", key=f"det_p_{row['id']}", use_container_width=True):
                        new_database.show_detail_transaksi('piutang', row['id'])
                    
                    if row['status'] != 'LUNAS':
                        if st.button("💰 Bayar", key=f"pay_p_{row['id']}", use_container_width=True):
                            st.session_state[f'bayar_p_{row["id"]}'] = True
                
                # Form Pembayaran Inline
                if st.session_state.get(f'bayar_p_{row["id"]}', False):
                    new_database.render_payment_form('piutang', row)

                st.markdown("---")
    else:
        st.info("Tidak ada data piutang sesuai filter")

# ================================================
# TAB 3 : REKAPAN HUTANG
# ================================================

with tab3:
    st.subheader("📋 Rekapan Hutang")

    with st.expander("🔍 Filter Data", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Tanggal Mulai", value=datetime.now() - timedelta(days=30), key="h_start")
        with col2:
            end_date = st.date_input("Tanggal Akhir", value=datetime.now(), key="h_end")
        with col3:
            suppliers = new_database.get_all_data_supplier(["id", "nama"])
            supplier_options = {"Semua": 0}
            if not suppliers.empty:
                supplier_options.update(dict(zip(suppliers['nama'], suppliers['id'])))
            selected_supplier = st.selectbox("Supplier", options=list(supplier_options.keys()))
        
        col4, col5, col6 = st.columns(3)
        with col4:
            status_filter = st.selectbox("Status", ["Semua", "BELUM_LUNAS", "LUNAS", "OVERDUE"], key="h_status")
        with col5:
            search_invoice = st.text_input("Cari No Invoice", key="h_search")
        with col6:
            st.write("")
            st.button("🔍 Terapkan Filter", use_container_width=True, key="h_btn")

    # Get Data
    df = new_database.get_filtered_hutang(
        start_date, end_date, 
        supplier_options[selected_supplier], 
        status_filter, 
        search_invoice
    )
    
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.info(f"**Total Invoice:** {len(df)}")
        c2.info(f"**Total Hutang:** {new_database.format_currency(df['total_hutang'].sum())}")
        c3.info(f"**Sisa Hutang:** {new_database.format_currency(df['sisa_hutang'].sum())}")
        
        st.markdown("---")
        
        for idx, row in df.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    if row['status'] == 'OVERDUE':
                        status_color, status_text = "🔴", f"OVERDUE ({row['hari_overdue']} hari)"
                    elif row['status'] == 'LUNAS':
                        status_color, status_text = "✅", "LUNAS"
                    else:
                        status_color, status_text = "🟡", "BELUM LUNAS"
                    
                    st.markdown(f"### {status_color} {row['no_invoice']} - {row['supplier']}")
                    st.write(f"**Tgl:** {row['tanggal_invoice']} | **Jatuh Tempo:** {row['tanggal_jatuh_tempo']}")
                    
                    ca, cb, cc = st.columns(3)
                    ca.metric("Total", new_database.format_currency(row['total_hutang']))
                    cb.metric("Terbayar", new_database.format_currency(row['total_terbayar']))
                    cc.metric("Sisa", new_database.format_currency(row['sisa_hutang']))
                    st.caption(f"Status: {status_text}")

                with col2:
                    st.write("")
                    if st.button("📄 Detail", key=f"det_h_{row['id']}", use_container_width=True):
                        new_database.show_detail_transaksi('hutang', row['id'])
                    
                    if row['status'] != 'LUNAS':
                        if st.button("💰 Bayar", key=f"pay_h_{row['id']}", use_container_width=True):
                            st.session_state[f'bayar_h_{row["id"]}'] = True
                
                # Form Pembayaran Inline
                if st.session_state.get(f'bayar_h_{row["id"]}', False):
                    new_database.render_payment_form('hutang', row)

                st.markdown("---")
    else:
        st.info("Tidak ada data hutang sesuai filter")