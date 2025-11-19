import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import os
import json
import plotly.express as px
import plotly.graph_objects as go

# Database setup
DB_PATH = "tissue_culture.db"

def init_db():
    """Initialize the database with all required tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Orders table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            cultivar TEXT NOT NULL,
            num_plants INTEGER NOT NULL,
            plant_size TEXT NOT NULL,
            order_date DATE NOT NULL,
            delivery_quantity INTEGER,
            is_recurring INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            completion_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    c.execute("PRAGMA table_info(orders)")
    columns = [column[1] for column in c.fetchall()]
    if 'completed' not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN completed INTEGER DEFAULT 0")
    if 'completion_date' not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN completion_date DATE")
    if 'delivery_quantity' not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN delivery_quantity INTEGER")
    if 'is_recurring' not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN is_recurring INTEGER DEFAULT 0")
    
    # Explant batches table (initiation)
    c.execute('''
        CREATE TABLE IF NOT EXISTS explant_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            batch_name TEXT NOT NULL,
            num_explants INTEGER NOT NULL,
            explant_type TEXT NOT NULL,
            media_type TEXT NOT NULL,
            hormones TEXT,
            additional_elements TEXT,
            initiation_date DATE NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    c.execute("PRAGMA table_info(explant_batches)")
    columns = [column[1] for column in c.fetchall()]
    if 'hormones' not in columns:
        c.execute("ALTER TABLE explant_batches ADD COLUMN hormones TEXT")
    if 'additional_elements' not in columns:
        c.execute("ALTER TABLE explant_batches ADD COLUMN additional_elements TEXT")
    
    # Infection records table
    c.execute('''
        CREATE TABLE IF NOT EXISTS infection_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            num_infected INTEGER NOT NULL,
            infection_type TEXT NOT NULL,
            identification_date DATE NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES explant_batches(id)
        )
    ''')
    
    # Transfer records table
    c.execute('''
        CREATE TABLE IF NOT EXISTS transfer_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            parent_transfer_id INTEGER,
            transfer_date DATE NOT NULL,
            explants_in INTEGER NOT NULL,
            explants_out INTEGER NOT NULL,
            new_media TEXT NOT NULL,
            hormones TEXT,
            additional_elements TEXT,
            multiplication_occurred INTEGER NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES explant_batches(id),
            FOREIGN KEY (parent_transfer_id) REFERENCES transfer_records(id)
        )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    c.execute("PRAGMA table_info(transfer_records)")
    columns = [column[1] for column in c.fetchall()]
    if 'hormones' not in columns:
        c.execute("ALTER TABLE transfer_records ADD COLUMN hormones TEXT")
    if 'additional_elements' not in columns:
        c.execute("ALTER TABLE transfer_records ADD COLUMN additional_elements TEXT")
    
    # Rooting records table
    c.execute('''
        CREATE TABLE IF NOT EXISTS rooting_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transfer_id INTEGER,
            batch_id INTEGER NOT NULL,
            num_placed INTEGER NOT NULL,
            placement_date DATE NOT NULL,
            num_rooted INTEGER,
            rooting_date DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transfer_id) REFERENCES transfer_records(id),
            FOREIGN KEY (batch_id) REFERENCES explant_batches(id)
        )
    ''')
    
    # Delivery records table
    c.execute('''
        CREATE TABLE IF NOT EXISTS delivery_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            batch_id INTEGER,
            num_delivered INTEGER NOT NULL,
            delivery_date DATE NOT NULL,
            delivery_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (batch_id) REFERENCES explant_batches(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_connection():
    """Get database connection."""
    return sqlite3.connect(DB_PATH)

# Helper functions for database operations
def add_order(client_name, cultivar, num_plants, plant_size, order_date, delivery_quantity, is_recurring, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (client_name, cultivar, num_plants, plant_size, order_date, delivery_quantity, is_recurring, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (client_name, cultivar, num_plants, plant_size, str(order_date), delivery_quantity, 1 if is_recurring else 0, notes))
    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id

def get_orders():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM orders ORDER BY order_date DESC", conn)
    conn.close()
    return df

def update_order(order_id, client_name, cultivar, num_plants, plant_size, order_date, delivery_quantity, is_recurring, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE orders 
        SET client_name = ?, cultivar = ?, num_plants = ?, plant_size = ?, order_date = ?, delivery_quantity = ?, is_recurring = ?, notes = ?
        WHERE id = ?
    ''', (client_name, cultivar, num_plants, plant_size, str(order_date), delivery_quantity, 1 if is_recurring else 0, notes, order_id))
    conn.commit()
    conn.close()

def delete_order(order_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()

def add_explant_batch(order_id, batch_name, num_explants, explant_type, media_type, hormones, additional_elements, initiation_date, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO explant_batches (order_id, batch_name, num_explants, explant_type, media_type, hormones, additional_elements, initiation_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (order_id, batch_name, num_explants, explant_type, media_type, hormones, additional_elements, initiation_date, notes))
    conn.commit()
    batch_id = c.lastrowid
    conn.close()
    return batch_id

def get_explant_batches(order_id=None):
    conn = get_connection()
    if order_id:
        df = pd.read_sql_query(
            "SELECT * FROM explant_batches WHERE order_id = ? ORDER BY initiation_date DESC",
            conn, params=(order_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM explant_batches ORDER BY initiation_date DESC", conn)
    conn.close()
    return df

def update_explant_batch(batch_id, order_id, batch_name, num_explants, explant_type, media_type, hormones, additional_elements, initiation_date, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE explant_batches 
        SET order_id = ?, batch_name = ?, num_explants = ?, explant_type = ?, media_type = ?, 
            hormones = ?, additional_elements = ?, initiation_date = ?, notes = ?
        WHERE id = ?
    ''', (order_id, batch_name, num_explants, explant_type, media_type, hormones, additional_elements, initiation_date, notes, batch_id))
    conn.commit()
    conn.close()

def delete_explant_batch(batch_id):
    conn = get_connection()
    c = conn.cursor()
    # Delete related records first (cascading)
    c.execute("DELETE FROM infection_records WHERE batch_id = ?", (batch_id,))
    c.execute("DELETE FROM transfer_records WHERE batch_id = ?", (batch_id,))
    c.execute("DELETE FROM rooting_records WHERE batch_id = ?", (batch_id,))
    c.execute("DELETE FROM explant_batches WHERE id = ?", (batch_id,))
    conn.commit()
    conn.close()

def add_infection_record(batch_id, num_infected, infection_type, identification_date, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO infection_records (batch_id, num_infected, infection_type, identification_date, notes)
        VALUES (?, ?, ?, ?, ?)
    ''', (batch_id, num_infected, infection_type, identification_date, notes))
    conn.commit()
    record_id = c.lastrowid
    conn.close()
    return record_id

def get_infection_records(batch_id=None):
    conn = get_connection()
    if batch_id:
        df = pd.read_sql_query(
            "SELECT * FROM infection_records WHERE batch_id = ? ORDER BY identification_date DESC",
            conn, params=(batch_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM infection_records ORDER BY identification_date DESC", conn)
    conn.close()
    return df

def get_total_infections_for_batch(batch_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(num_infected), 0) FROM infection_records WHERE batch_id = ?", (batch_id,))
    total = c.fetchone()[0]
    conn.close()
    return total

def update_infection_record(record_id, batch_id, num_infected, infection_type, identification_date, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE infection_records 
        SET batch_id = ?, num_infected = ?, infection_type = ?, identification_date = ?, notes = ?
        WHERE id = ?
    ''', (batch_id, num_infected, infection_type, identification_date, notes, record_id))
    conn.commit()
    conn.close()

def delete_infection_record(record_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM infection_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def add_transfer_record(batch_id, parent_transfer_id, transfer_date, explants_in, explants_out, new_media, hormones, additional_elements, multiplication_occurred, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO transfer_records (batch_id, parent_transfer_id, transfer_date, explants_in, explants_out, new_media, hormones, additional_elements, multiplication_occurred, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (batch_id, parent_transfer_id, transfer_date, explants_in, explants_out, new_media, hormones, additional_elements, multiplication_occurred, notes))
    conn.commit()
    transfer_id = c.lastrowid
    conn.close()
    return transfer_id

def get_transfer_records(batch_id=None):
    conn = get_connection()
    if batch_id:
        df = pd.read_sql_query(
            "SELECT * FROM transfer_records WHERE batch_id = ? ORDER BY transfer_date DESC",
            conn, params=(batch_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM transfer_records ORDER BY transfer_date DESC", conn)
    conn.close()
    return df

def update_transfer_record(transfer_id, batch_id, parent_transfer_id, transfer_date, explants_in, explants_out, new_media, hormones, additional_elements, multiplication_occurred, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE transfer_records 
        SET batch_id = ?, parent_transfer_id = ?, transfer_date = ?, explants_in = ?, explants_out = ?, 
            new_media = ?, hormones = ?, additional_elements = ?, multiplication_occurred = ?, notes = ?
        WHERE id = ?
    ''', (batch_id, parent_transfer_id, transfer_date, explants_in, explants_out, new_media, hormones, additional_elements, multiplication_occurred, notes, transfer_id))
    conn.commit()
    conn.close()

def delete_transfer_record(transfer_id):
    conn = get_connection()
    c = conn.cursor()
    # Delete related rooting records first
    c.execute("DELETE FROM rooting_records WHERE transfer_id = ?", (transfer_id,))
    c.execute("DELETE FROM transfer_records WHERE id = ?", (transfer_id,))
    conn.commit()
    conn.close()

def add_rooting_record(transfer_id, batch_id, num_placed, placement_date, num_rooted, rooting_date, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO rooting_records (transfer_id, batch_id, num_placed, placement_date, num_rooted, rooting_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (transfer_id, batch_id, num_placed, str(placement_date), num_rooted, str(rooting_date) if rooting_date else None, notes))
    conn.commit()
    record_id = c.lastrowid
    conn.close()
    return record_id

def update_rooting_record(record_id, num_rooted, rooting_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE rooting_records 
        SET num_rooted = ?, rooting_date = ?
        WHERE id = ?
    ''', (num_rooted, str(rooting_date) if rooting_date else None, record_id))
    conn.commit()
    conn.close()

def update_rooting_record_full(record_id, transfer_id, batch_id, num_placed, placement_date, num_rooted, rooting_date, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE rooting_records 
        SET transfer_id = ?, batch_id = ?, num_placed = ?, placement_date = ?, num_rooted = ?, rooting_date = ?, notes = ?
        WHERE id = ?
    ''', (transfer_id, batch_id, num_placed, str(placement_date), num_rooted, str(rooting_date) if rooting_date else None, notes, record_id))
    conn.commit()
    conn.close()

def delete_rooting_record(record_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM rooting_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def get_rooting_records(batch_id=None, transfer_id=None):
    conn = get_connection()
    if batch_id:
        df = pd.read_sql_query(
            "SELECT * FROM rooting_records WHERE batch_id = ? ORDER BY placement_date DESC",
            conn, params=(batch_id,)
        )
    elif transfer_id:
        df = pd.read_sql_query(
            "SELECT * FROM rooting_records WHERE transfer_id = ? ORDER BY placement_date DESC",
            conn, params=(transfer_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM rooting_records ORDER BY placement_date DESC", conn)
    conn.close()
    return df

def add_delivery_record(order_id, batch_id, num_delivered, delivery_date, delivery_method, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO delivery_records (order_id, batch_id, num_delivered, delivery_date, delivery_method, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (order_id, batch_id, num_delivered, str(delivery_date), delivery_method, notes))
    conn.commit()
    record_id = c.lastrowid
    conn.close()
    return record_id

def update_delivery_record(record_id, order_id, batch_id, num_delivered, delivery_date, delivery_method, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE delivery_records 
        SET order_id = ?, batch_id = ?, num_delivered = ?, delivery_date = ?, delivery_method = ?, notes = ?
        WHERE id = ?
    ''', (order_id, batch_id, num_delivered, str(delivery_date), delivery_method, notes, record_id))
    conn.commit()
    conn.close()

def delete_delivery_record(record_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM delivery_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def get_delivery_records(order_id=None, batch_id=None):
    conn = get_connection()
    if order_id:
        df = pd.read_sql_query(
            "SELECT * FROM delivery_records WHERE order_id = ? ORDER BY delivery_date DESC",
            conn, params=(order_id,)
        )
    elif batch_id:
        df = pd.read_sql_query(
            "SELECT * FROM delivery_records WHERE batch_id = ? ORDER BY delivery_date DESC",
            conn, params=(batch_id,)
        )
    else:
        df = pd.read_sql_query("SELECT * FROM delivery_records ORDER BY delivery_date DESC", conn)
    conn.close()
    return df

def mark_order_completed(order_id, completion_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE orders 
        SET completed = 1, completion_date = ?
        WHERE id = ?
    ''', (str(completion_date), order_id))
    conn.commit()
    conn.close()

def mark_order_incomplete(order_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE orders 
        SET completed = 0, completion_date = NULL
        WHERE id = ?
    ''', (order_id,))
    conn.commit()
    conn.close()

def get_batch_summary(batch_id):
    """Get a summary of the batch including infections and transfers."""
    conn = get_connection()
    c = conn.cursor()
    
    # Get batch info
    c.execute("SELECT * FROM explant_batches WHERE id = ?", (batch_id,))
    batch = c.fetchone()
    
    if not batch:
        conn.close()
        return None
    
    # Get total infections
    c.execute("SELECT COALESCE(SUM(num_infected), 0) FROM infection_records WHERE batch_id = ?", (batch_id,))
    total_infected = c.fetchone()[0]
    
    # Get latest transfer count
    c.execute("""
        SELECT COALESCE(SUM(explants_out), 0) 
        FROM transfer_records 
        WHERE batch_id = ?
    """, (batch_id,))
    total_transferred = c.fetchone()[0]
    
    conn.close()
    
    return {
        'batch': batch,
        'total_infected': total_infected,
        'total_transferred': total_transferred,
        'healthy': batch[3] - total_infected  # num_explants - total_infected
    }

# Initialize database
init_db()

# Streamlit app
st.set_page_config(
    page_title="Tissue Culture Tracker",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Tissue Culture Explant Tracker")

# Sidebar navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["Dashboard", "Order Management", "Explant Initiation", "Infection Tracking", "Transfer Management", "Rooting Tracking", "Delivery", "Timeline", "Statistics", "Archive"]
)

# Dashboard
if page == "Dashboard":
    st.header("Dashboard Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Get summary statistics
    conn = get_connection()
    
    total_orders = pd.read_sql_query("SELECT COUNT(*) as count FROM orders", conn).iloc[0]['count']
    total_batches = pd.read_sql_query("SELECT COUNT(*) as count FROM explant_batches", conn).iloc[0]['count']
    total_explants = pd.read_sql_query("SELECT COALESCE(SUM(num_explants), 0) as total FROM explant_batches", conn).iloc[0]['total']
    total_infections = pd.read_sql_query("SELECT COALESCE(SUM(num_infected), 0) as total FROM infection_records", conn).iloc[0]['total']
    
    conn.close()
    
    with col1:
        st.metric("Total Orders", total_orders)
    with col2:
        st.metric("Explant Batches", total_batches)
    with col3:
        st.metric("Total Explants", int(total_explants))
    with col4:
        infection_rate = (total_infections / total_explants * 100) if total_explants > 0 else 0
        st.metric("Infection Rate", f"{infection_rate:.1f}%")
    
    st.divider()
    
    # Recent activity
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Orders")
        orders = get_orders()
        if not orders.empty:
            st.dataframe(
                orders[['client_name', 'cultivar', 'num_plants', 'order_date']].head(5),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No orders yet")
    
    with col2:
        st.subheader("Recent Explant Batches")
        batches = get_explant_batches()
        if not batches.empty:
            st.dataframe(
                batches[['batch_name', 'num_explants', 'explant_type', 'initiation_date']].head(5),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No batches yet")

# Order Management
elif page == "Order Management":
    st.header("Order Management")
    
    # Initialize session state for edit mode
    if 'edit_order_id' not in st.session_state:
        st.session_state.edit_order_id = None
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add New Order", "View Orders", "Edit/Delete Orders", "Mark Complete"])
    
    with tab1:
        st.subheader("Add New Order")
        
        with st.form("new_order_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                client_name = st.text_input("Client Name*")
                cultivar = st.text_input("Cultivar*")
                num_plants = st.number_input("Number of Plants*", min_value=1, value=1)
                delivery_quantity = st.number_input("Delivery Quantity (Tissue Culture Plants)*", min_value=0, value=0, help="Number of tissue culture plants the client wants delivered")
            
            with col2:
                plant_size = st.selectbox(
                    "Plant Size*",
                    ["In Vitro Shoots", "Clones", "Teens", "Other"]
                )
                order_date = st.date_input("Order Date*", value=date.today())
                is_recurring = st.checkbox("Recurring Order", value=False, help="Check if this is a recurring delivery order")
                notes = st.text_area("Notes")
            
            submitted = st.form_submit_button("Add Order")
            
            if submitted:
                if client_name and cultivar:
                    order_id = add_order(client_name, cultivar, num_plants, plant_size, str(order_date), delivery_quantity, is_recurring, notes)
                    st.success(f"Order #{order_id} added successfully!")
                else:
                    st.error("Please fill in all required fields")
    
    with tab2:
        st.subheader("All Orders")
        orders = get_orders()
        
        if not orders.empty:
            # Add filter options
            client_filter = st.selectbox(
                "Filter by Client",
                ["All"] + orders['client_name'].unique().tolist()
            )
            
            if client_filter != "All":
                orders = orders[orders['client_name'] == client_filter]
            
            # Format the display to show recurring status
            display_orders = orders.copy()
            if 'is_recurring' in display_orders.columns:
                display_orders['Recurring'] = display_orders['is_recurring'].apply(lambda x: 'Yes' if x == 1 else 'No')
            
            display_cols = ['id', 'client_name', 'cultivar', 'num_plants', 'delivery_quantity', 'Recurring', 'plant_size', 'order_date', 'completed', 'completion_date', 'notes']
            available_cols = [col for col in display_cols if col in display_orders.columns]
            st.dataframe(display_orders[available_cols], use_container_width=True, hide_index=True)
            
            # Export option
            csv = orders.to_csv(index=False)
            st.download_button(
                "Download Orders CSV",
                csv,
                "orders.csv",
                "text/csv"
            )
        else:
            st.info("No orders found")
    
    with tab3:
        st.subheader("Edit or Delete Orders")
        orders = get_orders()
        
        if not orders.empty:
            # Order selection
            order_options = {f"Order #{row['id']} - {row['client_name']} ({row['cultivar']})": row['id'] 
                           for _, row in orders.iterrows()}
            selected_order = st.selectbox("Select Order to Edit/Delete", list(order_options.keys()))
            order_id = order_options[selected_order]
            
            selected_order_data = orders[orders['id'] == order_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Edit Order**")
                with st.form("edit_order_form"):
                    edit_client_name = st.text_input("Client Name*", value=selected_order_data['client_name'])
                    edit_cultivar = st.text_input("Cultivar*", value=selected_order_data['cultivar'])
                    edit_num_plants = st.number_input("Number of Plants*", min_value=1, value=int(selected_order_data['num_plants']))
                    edit_delivery_quantity = st.number_input("Delivery Quantity (Tissue Culture Plants)*", min_value=0, 
                                                              value=int(selected_order_data.get('delivery_quantity', 0)) if pd.notna(selected_order_data.get('delivery_quantity')) else 0,
                                                              help="Number of tissue culture plants the client wants delivered")
                    edit_plant_size = st.selectbox(
                        "Plant Size*",
                        ["In Vitro Shoots", "Clones", "Teens", "Other"],
                        index=["In Vitro Shoots", "Clones", "Teens", "Other"].index(selected_order_data['plant_size']) if selected_order_data['plant_size'] in ["In Vitro Shoots", "Clones", "Teens", "Other"] else 0
                    )
                    edit_order_date = st.date_input("Order Date*", value=pd.to_datetime(selected_order_data['order_date']).date())
                    edit_is_recurring = st.checkbox("Recurring Order", 
                                                   value=bool(selected_order_data.get('is_recurring', 0)) if pd.notna(selected_order_data.get('is_recurring')) else False,
                                                   help="Check if this is a recurring delivery order")
                    edit_notes = st.text_area("Notes", value=selected_order_data['notes'] if pd.notna(selected_order_data['notes']) else "")
                    
                    edit_submitted = st.form_submit_button("Update Order")
                    
                    if edit_submitted:
                        if edit_client_name and edit_cultivar:
                            update_order(order_id, edit_client_name, edit_cultivar, edit_num_plants, edit_plant_size, str(edit_order_date), edit_delivery_quantity, edit_is_recurring, edit_notes)
                            st.success(f"Order #{order_id} updated successfully!")
                            st.rerun()
                        else:
                            st.error("Please fill in all required fields")
            
            with col2:
                st.write("**Delete Order**")
                st.warning("⚠️ Deleting an order will NOT delete associated batches. This action cannot be undone.")
                
                if st.button("Delete Order", type="primary", use_container_width=True):
                    delete_order(order_id)
                    st.success(f"Order #{order_id} deleted successfully!")
                    st.rerun()
        else:
            st.info("No orders found")
    
    with tab4:
        st.subheader("Mark Order as Complete")
        orders = get_orders()
        
        # Filter to show only incomplete orders
        incomplete_orders = orders[orders.get('completed', 0) == 0] if 'completed' in orders.columns else orders
        
        if not incomplete_orders.empty:
            order_options = {f"Order #{row['id']} - {row['client_name']} ({row['cultivar']})": row['id'] 
                           for _, row in incomplete_orders.iterrows()}
            selected_order = st.selectbox("Select Order to Mark Complete", list(order_options.keys()))
            order_id = order_options[selected_order]
            
            selected_order_data = orders[orders['id'] == order_id].iloc[0]
            
            with st.form("complete_order_form"):
                st.write(f"**Order Details:**")
                st.write(f"- Client: {selected_order_data['client_name']}")
                st.write(f"- Cultivar: {selected_order_data['cultivar']}")
                st.write(f"- Number of Plants: {selected_order_data['num_plants']}")
                delivery_qty = selected_order_data.get('delivery_quantity', 0) if pd.notna(selected_order_data.get('delivery_quantity')) else 0
                is_recurring_val = bool(selected_order_data.get('is_recurring', 0)) if pd.notna(selected_order_data.get('is_recurring')) else False
                st.write(f"- Delivery Quantity: {delivery_qty} tissue culture plants")
                st.write(f"- Recurring Order: {'Yes' if is_recurring_val else 'No'}")
                
                completion_date = st.date_input("Completion Date*", value=date.today())
                
                submitted = st.form_submit_button("Mark Order as Complete")
                
                if submitted:
                    mark_order_completed(order_id, completion_date)
                    st.success(f"Order #{order_id} marked as complete!")
                    st.rerun()
        else:
            st.info("No incomplete orders found")
        
        # Show completed orders
        st.subheader("Completed Orders")
        completed_orders = orders[orders.get('completed', 0) == 1] if 'completed' in orders.columns else pd.DataFrame()
        
        if not completed_orders.empty:
            # Format the display to show recurring status
            display_orders = completed_orders.copy()
            if 'is_recurring' in display_orders.columns:
                display_orders['Recurring'] = display_orders['is_recurring'].apply(lambda x: 'Yes' if x == 1 else 'No')
            
            display_cols = ['id', 'client_name', 'cultivar', 'num_plants', 'delivery_quantity', 'Recurring', 'plant_size', 'order_date', 'completion_date', 'notes']
            available_cols = [col for col in display_cols if col in display_orders.columns]
            st.dataframe(display_orders[available_cols], use_container_width=True, hide_index=True)
            
            # Option to mark as incomplete
            st.subheader("Mark Order as Incomplete")
            completed_order_options = {f"Order #{row['id']} - {row['client_name']} ({row['cultivar']})": row['id'] 
                                      for _, row in completed_orders.iterrows()}
            if completed_order_options:
                selected_completed = st.selectbox("Select Completed Order", list(completed_order_options.keys()))
                completed_order_id = completed_order_options[selected_completed]
                
                if st.button("Mark as Incomplete", type="primary"):
                    mark_order_incomplete(completed_order_id)
                    st.success(f"Order #{completed_order_id} marked as incomplete!")
                    st.rerun()
        else:
            st.info("No completed orders found")

# Explant Initiation
elif page == "Explant Initiation":
    st.header("Explant Initiation")
    
    tab1, tab2, tab3 = st.tabs(["Initiate New Batch", "View Batches", "Edit/Delete Batches"])
    
    with tab1:
        st.subheader("Initiate New Explant Batch")
        
        # Get orders for dropdown
        orders = get_orders()
        
        with st.form("new_batch_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                if not orders.empty:
                    order_options = {f"Order #{row['id']} - {row['client_name']} ({row['cultivar']})": row['id'] 
                                   for _, row in orders.iterrows()}
                    selected_order = st.selectbox("Link to Order (optional)", ["None"] + list(order_options.keys()))
                    order_id = order_options.get(selected_order) if selected_order != "None" else None
                else:
                    st.info("No orders available")
                    order_id = None
                
                batch_name = st.text_input("Batch Name/ID*")
                num_explants = st.number_input("Number of Explants*", min_value=1, value=1)
            
            with col2:
                explant_type = st.selectbox(
                    "Explant Type*",
                    ["Node", "Microshoot", "Meristem", "Other"]
                )
                media_type = st.selectbox(
                    "Media Type*",
                    ["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"]
                )
                initiation_date = st.date_input("Initiation Date*", value=date.today())
            
            st.subheader("Media Additives")
            col3, col4 = st.columns(2)
            
            with col3:
                hormones = st.text_area("Hormones and Concentrations", placeholder="e.g., BAP 2.0 mg/L, IBA 0.5 mg/L")
            
            with col4:
                additional_elements = st.text_area("Additional Elements and Concentrations", placeholder="e.g., Activated charcoal 0.5 g/L, Sucrose 30 g/L")
            
            notes = st.text_area("Notes")
            
            submitted = st.form_submit_button("Initiate Batch")
            
            if submitted:
                if batch_name and media_type:
                    batch_id = add_explant_batch(
                        order_id, batch_name, num_explants, explant_type,
                        media_type, hormones or None, additional_elements or None, str(initiation_date), notes
                    )
                    st.success(f"Batch '{batch_name}' (ID: {batch_id}) initiated successfully!")
                else:
                    st.error("Please fill in all required fields")
    
    with tab2:
        st.subheader("All Explant Batches")
        batches = get_explant_batches()
        
        if not batches.empty:
            # Add filter
            explant_filter = st.selectbox(
                "Filter by Explant Type",
                ["All"] + batches['explant_type'].unique().tolist()
            )
            
            if explant_filter != "All":
                batches = batches[batches['explant_type'] == explant_filter]
            
            st.dataframe(batches, use_container_width=True, hide_index=True)
        else:
            st.info("No batches found")
    
    with tab3:
        st.subheader("Edit or Delete Batches")
        batches = get_explant_batches()
        orders = get_orders()
        
        if not batches.empty:
            # Batch selection
            batch_options = {f"Batch #{row['id']} - {row['batch_name']}": row['id'] 
                           for _, row in batches.iterrows()}
            selected_batch = st.selectbox("Select Batch to Edit/Delete", list(batch_options.keys()))
            batch_id = batch_options[selected_batch]
            
            selected_batch_data = batches[batches['id'] == batch_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Edit Batch**")
                with st.form("edit_batch_form"):
                    # Order selection
                    if not orders.empty:
                        order_options = {f"Order #{row['id']} - {row['client_name']} ({row['cultivar']})": row['id'] 
                                       for _, row in orders.iterrows()}
                        current_order_id = selected_batch_data.get('order_id')
                        if pd.notna(current_order_id):
                            current_order = orders[orders['id'] == int(current_order_id)]
                            if not current_order.empty:
                                current_order_key = f"Order #{current_order.iloc[0]['id']} - {current_order.iloc[0]['client_name']} ({current_order.iloc[0]['cultivar']})"
                                default_order = current_order_key if current_order_key in order_options else "None"
                            else:
                                default_order = "None"
                        else:
                            default_order = "None"
                        selected_order = st.selectbox("Link to Order (optional)", ["None"] + list(order_options.keys()), 
                                                     index=(["None"] + list(order_options.keys())).index(default_order) if default_order in (["None"] + list(order_options.keys())) else 0)
                        edit_order_id = order_options.get(selected_order) if selected_order != "None" else None
                    else:
                        st.info("No orders available")
                        edit_order_id = None
                    
                    edit_batch_name = st.text_input("Batch Name/ID*", value=selected_batch_data['batch_name'])
                    edit_num_explants = st.number_input("Number of Explants*", min_value=1, value=int(selected_batch_data['num_explants']))
                    edit_explant_type = st.selectbox(
                        "Explant Type*",
                        ["Node", "Microshoot", "Meristem", "Other"],
                        index=["Node", "Microshoot", "Meristem", "Other"].index(selected_batch_data['explant_type']) if selected_batch_data['explant_type'] in ["Node", "Microshoot", "Meristem", "Other"] else 0
                    )
                    edit_media_type = st.selectbox(
                        "Media Type*",
                        ["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"],
                        index=["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"].index(selected_batch_data['media_type']) if selected_batch_data['media_type'] in ["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"] else 0
                    )
                    edit_initiation_date = st.date_input("Initiation Date*", value=pd.to_datetime(selected_batch_data['initiation_date']).date())
                    
                    st.subheader("Media Additives")
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        edit_hormones = st.text_area("Hormones and Concentrations", 
                                                     value=selected_batch_data.get('hormones', '') if pd.notna(selected_batch_data.get('hormones')) else "")
                    
                    with col4:
                        edit_additional_elements = st.text_area("Additional Elements and Concentrations",
                                                               value=selected_batch_data.get('additional_elements', '') if pd.notna(selected_batch_data.get('additional_elements')) else "")
                    
                    edit_notes = st.text_area("Notes", value=selected_batch_data['notes'] if pd.notna(selected_batch_data['notes']) else "")
                    
                    edit_submitted = st.form_submit_button("Update Batch")
                    
                    if edit_submitted:
                        if edit_batch_name and edit_media_type:
                            update_explant_batch(batch_id, edit_order_id, edit_batch_name, edit_num_explants, edit_explant_type,
                                               edit_media_type, edit_hormones or None, edit_additional_elements or None,
                                               str(edit_initiation_date), edit_notes)
                            st.success(f"Batch #{batch_id} updated successfully!")
                            st.rerun()
                        else:
                            st.error("Please fill in all required fields")
            
            with col2:
                st.write("**Delete Batch**")
                st.warning("⚠️ Deleting a batch will also delete all associated infection records, transfer records, and rooting records. This action cannot be undone.")
                
                if st.button("Delete Batch", type="primary", use_container_width=True):
                    delete_explant_batch(batch_id)
                    st.success(f"Batch #{batch_id} deleted successfully!")
                    st.rerun()
        else:
            st.info("No batches found")

# Infection Tracking
elif page == "Infection Tracking":
    st.header("Infection Tracking")
    
    tab1, tab2, tab3 = st.tabs(["Record Infection", "View Infection Records", "Edit/Delete Records"])
    
    with tab1:
        st.subheader("Record Infection")
        
        batches = get_explant_batches()
        
        if not batches.empty:
            with st.form("infection_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    batch_options = {f"{row['batch_name']} (ID: {row['id']}) - {row['num_explants']} explants": row['id'] 
                                   for _, row in batches.iterrows()}
                    selected_batch = st.selectbox("Select Batch*", list(batch_options.keys()))
                    batch_id = batch_options[selected_batch]
                    
                    # Show current infection count
                    total_infected = get_total_infections_for_batch(batch_id)
                    batch_info = batches[batches['id'] == batch_id].iloc[0]
                    remaining = batch_info['num_explants'] - total_infected
                    
                    st.info(f"Previously infected: {total_infected} | Remaining healthy: {remaining}")
                    
                    num_infected = st.number_input(
                        "Number Infected*",
                        min_value=1,
                        max_value=remaining if remaining > 0 else 1,
                        value=1
                    )
                
                with col2:
                    infection_type = st.selectbox(
                        "Infection Type*",
                        ["Bacterial", "Fungal", "Viral", "Mixed", "Unknown", "Other"]
                    )
                    identification_date = st.date_input("Date Identified*", value=date.today())
                    notes = st.text_area("Notes (symptoms, appearance, etc.)")
                
                submitted = st.form_submit_button("Record Infection")
                
                if submitted:
                    if remaining >= num_infected:
                        record_id = add_infection_record(
                            batch_id, num_infected, infection_type,
                            str(identification_date), notes
                        )
                        st.success(f"Infection record #{record_id} added successfully!")
                    else:
                        st.error("Cannot infect more explants than remaining healthy count")
        else:
            st.warning("No batches available. Please initiate a batch first.")
    
    with tab2:
        st.subheader("Infection Records")
        
        # Filter by batch
        batches = get_explant_batches()
        if not batches.empty:
            batch_filter_options = {"All Batches": None}
            batch_filter_options.update({
                f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                for _, row in batches.iterrows()
            })
            selected_filter = st.selectbox("Filter by Batch", list(batch_filter_options.keys()))
            filter_batch_id = batch_filter_options[selected_filter]
            
            infections = get_infection_records(filter_batch_id)
            
            if not infections.empty:
                st.dataframe(infections, use_container_width=True, hide_index=True)
                
                # Summary by infection type
                st.subheader("Summary by Infection Type")
                summary = infections.groupby('infection_type')['num_infected'].sum().reset_index()
                summary.columns = ['Infection Type', 'Total Infected']
                st.dataframe(summary, use_container_width=True, hide_index=True)
            else:
                st.info("No infection records found")
        else:
            st.info("No batches available")
    
    with tab3:
        st.subheader("Edit or Delete Infection Records")
        infections = get_infection_records()
        batches = get_explant_batches()
        
        if not infections.empty:
            # Infection record selection
            infection_options = {f"Record #{row['id']} - Batch {row['batch_id']} ({row['num_infected']} infected on {row['identification_date']})": row['id'] 
                               for _, row in infections.iterrows()}
            selected_infection = st.selectbox("Select Infection Record to Edit/Delete", list(infection_options.keys()))
            record_id = infection_options[selected_infection]
            
            selected_infection_data = infections[infections['id'] == record_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Edit Infection Record**")
                with st.form("edit_infection_form"):
                    batch_options = {f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                                   for _, row in batches.iterrows()}
                    current_batch_id = selected_infection_data['batch_id']
                    current_batch = batches[batches['id'] == current_batch_id]
                    if not current_batch.empty:
                        current_batch_key = f"{current_batch.iloc[0]['batch_name']} (ID: {current_batch.iloc[0]['id']})"
                        default_batch = current_batch_key if current_batch_key in batch_options else list(batch_options.keys())[0]
                    else:
                        default_batch = list(batch_options.keys())[0]
                    
                    edit_batch_id = st.selectbox("Select Batch*", list(batch_options.keys()), 
                                                 index=list(batch_options.keys()).index(default_batch) if default_batch in batch_options else 0)
                    edit_batch_id = batch_options[edit_batch_id]
                    
                    # Get remaining healthy for validation
                    total_infected = get_total_infections_for_batch(edit_batch_id)
                    batch_info = batches[batches['id'] == edit_batch_id].iloc[0]
                    remaining = batch_info['num_explants'] - total_infected + selected_infection_data['num_infected']  # Add back current record's count
                    
                    edit_num_infected = st.number_input("Number Infected*", min_value=1, max_value=remaining if remaining > 0 else 1, 
                                                       value=int(selected_infection_data['num_infected']))
                    edit_infection_type = st.selectbox(
                        "Infection Type*",
                        ["Bacterial", "Fungal", "Viral", "Mixed", "Unknown", "Other"],
                        index=["Bacterial", "Fungal", "Viral", "Mixed", "Unknown", "Other"].index(selected_infection_data['infection_type']) if selected_infection_data['infection_type'] in ["Bacterial", "Fungal", "Viral", "Mixed", "Unknown", "Other"] else 0
                    )
                    edit_identification_date = st.date_input("Date Identified*", value=pd.to_datetime(selected_infection_data['identification_date']).date())
                    edit_notes = st.text_area("Notes", value=selected_infection_data['notes'] if pd.notna(selected_infection_data['notes']) else "")
                    
                    edit_submitted = st.form_submit_button("Update Infection Record")
                    
                    if edit_submitted:
                        if edit_num_infected <= remaining:
                            update_infection_record(record_id, edit_batch_id, edit_num_infected, edit_infection_type, str(edit_identification_date), edit_notes)
                            st.success(f"Infection record #{record_id} updated successfully!")
                            st.rerun()
                        else:
                            st.error("Cannot infect more explants than remaining healthy count")
            
            with col2:
                st.write("**Delete Infection Record**")
                st.warning("⚠️ This action cannot be undone.")
                
                if st.button("Delete Infection Record", type="primary", use_container_width=True):
                    delete_infection_record(record_id)
                    st.success(f"Infection record #{record_id} deleted successfully!")
                    st.rerun()
        else:
            st.info("No infection records found")

# Transfer Management
elif page == "Transfer Management":
    st.header("Transfer Management")
    
    tab1, tab2, tab3 = st.tabs(["Record Transfer", "View Transfers", "Edit/Delete Transfers"])
    
    with tab1:
        st.subheader("Record Transfer to New Media")
        
        batches = get_explant_batches()
        
        if not batches.empty:
            with st.form("transfer_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    batch_options = {f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                                   for _, row in batches.iterrows()}
                    selected_batch = st.selectbox("Select Batch*", list(batch_options.keys()))
                    batch_id = batch_options[selected_batch]
                    
                    # Get batch summary
                    summary = get_batch_summary(batch_id)
                    if summary:
                        st.info(f"Total initiated: {summary['batch'][3]} | Healthy: {summary['healthy']}")
                    
                    # Option to link to previous transfer
                    transfers = get_transfer_records(batch_id)
                    if not transfers.empty:
                        transfer_options = {"New transfer (from original batch)": None}
                        transfer_options.update({
                            f"Transfer #{row['id']} ({row['transfer_date']}) - {row['explants_out']} out": row['id']
                            for _, row in transfers.iterrows()
                        })
                        selected_parent = st.selectbox("Parent Transfer", list(transfer_options.keys()))
                        parent_transfer_id = transfer_options[selected_parent]
                    else:
                        parent_transfer_id = None
                        st.caption("This will be the first transfer for this batch")
                    
                    explants_in = st.number_input("Explants In*", min_value=1, value=1)
                
                with col2:
                    explants_out = st.number_input("Explants Out*", min_value=1, value=1)
                    new_media = st.selectbox(
                        "New Media Type*",
                        ["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"]
                    )
                    transfer_date = st.date_input("Transfer Date*", value=date.today())
                    multiplication_occurred = st.checkbox("Multiplication Occurred")
                
                st.subheader("Media Additives")
                col3, col4 = st.columns(2)
                
                with col3:
                    hormones = st.text_area("Hormones and Concentrations", placeholder="e.g., BAP 2.0 mg/L, IBA 0.5 mg/L")
                
                with col4:
                    additional_elements = st.text_area("Additional Elements and Concentrations", placeholder="e.g., Activated charcoal 0.5 g/L, Sucrose 30 g/L")
                
                notes = st.text_area("Notes")
                
                # Show multiplication ratio
                if explants_in > 0:
                    ratio = explants_out / explants_in
                    st.metric("Multiplication Ratio", f"{ratio:.2f}x")
                
                submitted = st.form_submit_button("Record Transfer")
                
                if submitted:
                    if new_media:
                        transfer_id = add_transfer_record(
                            batch_id, parent_transfer_id, str(transfer_date),
                            explants_in, explants_out, new_media,
                            hormones or None, additional_elements or None,
                            1 if multiplication_occurred else 0, notes
                        )
                        st.success(f"Transfer #{transfer_id} recorded successfully!")
                        st.info(f"In: {explants_in} → Out: {explants_out} (Ratio: {explants_out/explants_in:.2f}x)")
                    else:
                        st.error("Please specify the new media type")
        else:
            st.warning("No batches available. Please initiate a batch first.")
    
    with tab2:
        st.subheader("Transfer Records")
        
        # Filter by batch
        batches = get_explant_batches()
        if not batches.empty:
            batch_filter_options = {"All Batches": None}
            batch_filter_options.update({
                f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                for _, row in batches.iterrows()
            })
            selected_filter = st.selectbox("Filter by Batch", list(batch_filter_options.keys()))
            filter_batch_id = batch_filter_options[selected_filter]
            
            transfers = get_transfer_records(filter_batch_id)
            
            if not transfers.empty:
                # Add multiplication ratio column
                transfers['ratio'] = transfers['explants_out'] / transfers['explants_in']
                transfers['multiplication'] = transfers['multiplication_occurred'].apply(lambda x: "Yes" if x else "No")
                
                display_cols = ['id', 'batch_id', 'transfer_date', 'explants_in', 
                               'explants_out', 'ratio', 'new_media', 'hormones', 'additional_elements', 'multiplication', 'notes']
                st.dataframe(transfers[display_cols], use_container_width=True, hide_index=True)
                
                # Summary statistics
                st.subheader("Transfer Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Transfers", len(transfers))
                with col2:
                    avg_ratio = transfers['ratio'].mean()
                    st.metric("Avg Multiplication Ratio", f"{avg_ratio:.2f}x")
                with col3:
                    total_out = transfers['explants_out'].sum()
                    st.metric("Total Explants Out", int(total_out))
            else:
                st.info("No transfer records found")
        else:
            st.info("No batches available")
    
    with tab3:
        st.subheader("Edit or Delete Transfer Records")
        transfers = get_transfer_records()
        batches = get_explant_batches()
        
        if not transfers.empty:
            # Transfer selection
            transfer_options = {f"Transfer #{row['id']} - Batch {row['batch_id']} ({row['explants_in']} in → {row['explants_out']} out on {row['transfer_date']})": row['id'] 
                              for _, row in transfers.iterrows()}
            selected_transfer = st.selectbox("Select Transfer to Edit/Delete", list(transfer_options.keys()))
            transfer_id = transfer_options[selected_transfer]
            
            selected_transfer_data = transfers[transfers['id'] == transfer_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Edit Transfer**")
                with st.form("edit_transfer_form"):
                    batch_options = {f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                                   for _, row in batches.iterrows()}
                    current_batch_id = selected_transfer_data['batch_id']
                    current_batch = batches[batches['id'] == current_batch_id]
                    if not current_batch.empty:
                        current_batch_key = f"{current_batch.iloc[0]['batch_name']} (ID: {current_batch.iloc[0]['id']})"
                        default_batch = current_batch_key if current_batch_key in batch_options else list(batch_options.keys())[0]
                    else:
                        default_batch = list(batch_options.keys())[0]
                    
                    edit_batch_id = st.selectbox("Select Batch*", list(batch_options.keys()), 
                                                 index=list(batch_options.keys()).index(default_batch) if default_batch in batch_options else 0)
                    edit_batch_id = batch_options[edit_batch_id]
                    
                    # Parent transfer selection
                    batch_transfers = get_transfer_records(edit_batch_id)
                    if not batch_transfers.empty:
                        parent_options = {"New transfer (from original batch)": None}
                        parent_options.update({
                            f"Transfer #{row['id']} ({row['transfer_date']})": row['id']
                            for _, row in batch_transfers.iterrows() if row['id'] != transfer_id
                        })
                        current_parent = selected_transfer_data.get('parent_transfer_id')
                        if pd.notna(current_parent):
                            current_parent_key = f"Transfer #{int(current_parent)}"
                            default_parent = current_parent_key if current_parent_key in parent_options else "New transfer (from original batch)"
                        else:
                            default_parent = "New transfer (from original batch)"
                        edit_parent_transfer_id = st.selectbox("Parent Transfer", list(parent_options.keys()),
                                                               index=list(parent_options.keys()).index(default_parent) if default_parent in parent_options else 0)
                        edit_parent_transfer_id = parent_options[edit_parent_transfer_id]
                    else:
                        edit_parent_transfer_id = None
                    
                    edit_explants_in = st.number_input("Explants In*", min_value=1, value=int(selected_transfer_data['explants_in']))
                    edit_explants_out = st.number_input("Explants Out*", min_value=1, value=int(selected_transfer_data['explants_out']))
                    edit_new_media = st.selectbox(
                        "New Media Type*",
                        ["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"],
                        index=["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"].index(selected_transfer_data['new_media']) if selected_transfer_data['new_media'] in ["50% EECN", "100% EECN", "50% MS", "100% MS", "50% DKW", "100% DKW", "Rooting Media"] else 0
                    )
                    edit_transfer_date = st.date_input("Transfer Date*", value=pd.to_datetime(selected_transfer_data['transfer_date']).date())
                    edit_multiplication_occurred = st.checkbox("Multiplication Occurred", value=bool(selected_transfer_data['multiplication_occurred']))
                    
                    st.subheader("Media Additives")
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        edit_hormones = st.text_area("Hormones and Concentrations",
                                                     value=selected_transfer_data.get('hormones', '') if pd.notna(selected_transfer_data.get('hormones')) else "")
                    
                    with col4:
                        edit_additional_elements = st.text_area("Additional Elements and Concentrations",
                                                               value=selected_transfer_data.get('additional_elements', '') if pd.notna(selected_transfer_data.get('additional_elements')) else "")
                    
                    edit_notes = st.text_area("Notes", value=selected_transfer_data['notes'] if pd.notna(selected_transfer_data['notes']) else "")
                    
                    edit_submitted = st.form_submit_button("Update Transfer")
                    
                    if edit_submitted:
                        if edit_new_media:
                            update_transfer_record(transfer_id, edit_batch_id, edit_parent_transfer_id, str(edit_transfer_date),
                                                  edit_explants_in, edit_explants_out, edit_new_media,
                                                  edit_hormones or None, edit_additional_elements or None,
                                                  1 if edit_multiplication_occurred else 0, edit_notes)
                            st.success(f"Transfer #{transfer_id} updated successfully!")
                            st.rerun()
                        else:
                            st.error("Please specify the new media type")
            
            with col2:
                st.write("**Delete Transfer**")
                st.warning("⚠️ Deleting a transfer will also delete all associated rooting records. This action cannot be undone.")
                
                if st.button("Delete Transfer", type="primary", use_container_width=True):
                    delete_transfer_record(transfer_id)
                    st.success(f"Transfer #{transfer_id} deleted successfully!")
                    st.rerun()
        else:
            st.info("No transfer records found")

# Reports
elif page == "Reports":
    st.header("Reports & Analytics")
    
    tab1, tab2, tab3 = st.tabs(["Batch Summary", "Infection Analysis", "Transfer Analysis"])
    
    with tab1:
        st.subheader("Batch Summary Report")
        
        batches = get_explant_batches()
        
        if not batches.empty:
            # Build comprehensive summary
            summary_data = []
            
            for _, batch in batches.iterrows():
                batch_id = batch['id']
                total_infected = get_total_infections_for_batch(batch_id)
                transfers = get_transfer_records(batch_id)
                
                total_transferred = transfers['explants_out'].sum() if not transfers.empty else 0
                avg_ratio = transfers['explants_out'].sum() / transfers['explants_in'].sum() if not transfers.empty and transfers['explants_in'].sum() > 0 else 0
                
                summary_data.append({
                    'Batch ID': batch_id,
                    'Batch Name': batch['batch_name'],
                    'Initial Count': batch['num_explants'],
                    'Type': batch['explant_type'],
                    'Media': batch['media_type'],
                    'Hormones': batch.get('hormones', '') or '',
                    'Additional Elements': batch.get('additional_elements', '') or '',
                    'Date': batch['initiation_date'],
                    'Infected': total_infected,
                    'Infection %': f"{(total_infected/batch['num_explants']*100):.1f}%" if batch['num_explants'] > 0 else "0%",
                    'Healthy': batch['num_explants'] - total_infected,
                    'Transfers': len(transfers),
                    'Total Out': int(total_transferred),
                    'Avg Ratio': f"{avg_ratio:.2f}x"
                })
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            # Export
            csv = summary_df.to_csv(index=False)
            st.download_button(
                "Download Summary CSV",
                csv,
                "batch_summary.csv",
                "text/csv"
            )
        else:
            st.info("No batches to report on")
    
    with tab2:
        st.subheader("Infection Analysis")
        
        infections = get_infection_records()
        
        if not infections.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Infection by type
                st.write("**Infections by Type**")
                type_summary = infections.groupby('infection_type')['num_infected'].sum().reset_index()
                type_summary.columns = ['Type', 'Count']
                st.bar_chart(type_summary.set_index('Type'))
            
            with col2:
                # Infection timeline
                st.write("**Infection Timeline**")
                timeline = infections.groupby('identification_date')['num_infected'].sum().reset_index()
                timeline.columns = ['Date', 'Infected']
                timeline['Date'] = pd.to_datetime(timeline['Date'])
                timeline = timeline.sort_values('Date')
                st.line_chart(timeline.set_index('Date'))
            
            # Detailed table
            st.write("**Detailed Infection Records**")
            st.dataframe(infections, use_container_width=True, hide_index=True)
        else:
            st.info("No infection records to analyze")
    
    with tab3:
        st.subheader("Transfer Analysis")
        
        transfers = get_transfer_records()
        
        if not transfers.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Multiplication ratios
                st.write("**Multiplication Ratios**")
                transfers['ratio'] = transfers['explants_out'] / transfers['explants_in']
                st.bar_chart(transfers[['id', 'ratio']].set_index('id'))
            
            with col2:
                # Media usage
                st.write("**Media Usage**")
                media_summary = transfers.groupby('new_media')['explants_out'].sum().reset_index()
                media_summary.columns = ['Media', 'Explants Out']
                st.dataframe(media_summary, use_container_width=True, hide_index=True)
            
            # Transfer efficiency
            st.write("**Overall Transfer Efficiency**")
            total_in = transfers['explants_in'].sum()
            total_out = transfers['explants_out'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total In", int(total_in))
            with col2:
                st.metric("Total Out", int(total_out))
            with col3:
                overall_ratio = total_out / total_in if total_in > 0 else 0
                st.metric("Overall Ratio", f"{overall_ratio:.2f}x")
        else:
            st.info("No transfer records to analyze")

# Rooting Tracking
elif page == "Rooting Tracking":
    st.header("Rooting Tracking")
    
    tab1, tab2, tab3 = st.tabs(["Record Rooting", "View Rooting Records", "Edit/Delete Records"])
    
    with tab1:
        st.subheader("Record Plants Placed in Rooting Media")
        
        # Get transfers that used rooting media
        transfers = get_transfer_records()
        rooting_transfers = transfers[transfers['new_media'] == 'Rooting Media'] if not transfers.empty else pd.DataFrame()
        
        if not rooting_transfers.empty:
            # Get batch info for display
            batches = get_explant_batches()
            transfer_options = {}
            for _, transfer in rooting_transfers.iterrows():
                batch_info = batches[batches['id'] == transfer['batch_id']]
                if not batch_info.empty:
                    batch_name = batch_info.iloc[0]['batch_name']
                    transfer_options[f"Transfer #{transfer['id']} - Batch: {batch_name} ({transfer['explants_out']} explants)"] = transfer['id']
            
            selected_transfer = st.selectbox("Select Transfer*", list(transfer_options.keys()))
            transfer_id = transfer_options[selected_transfer]
            selected_transfer_data = rooting_transfers[rooting_transfers['id'] == transfer_id].iloc[0]
            
            # Get existing rooting records for this transfer
            existing_rooting = get_rooting_records(transfer_id=transfer_id)
            if not existing_rooting.empty:
                already_placed = existing_rooting['num_placed'].sum()
                remaining = selected_transfer_data['explants_out'] - already_placed
                st.info(f"Already placed: {already_placed} | Remaining: {remaining}")
            else:
                remaining = selected_transfer_data['explants_out']
            
            with st.form("rooting_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Auto-fill with remaining explants from transfer
                    default_placed = remaining if remaining > 0 else 1
                    num_placed = st.number_input("Number Placed in Rooting Media*", min_value=1, max_value=remaining if remaining > 0 else 1, value=default_placed)
                    # Auto-fill placement date from transfer date
                    transfer_date = pd.to_datetime(selected_transfer_data['transfer_date']).date()
                    placement_date = st.date_input("Placement Date*", value=transfer_date)
                
                with col2:
                    batch_id = int(selected_transfer_data['batch_id'])
                    num_rooted = st.number_input("Number Rooted (optional)", min_value=0, value=0)
                    rooting_date = st.date_input("Rooting Date (optional)", value=None)
                    notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Record Rooting")
                
                if submitted:
                    if num_placed <= remaining:
                        record_id = add_rooting_record(
                            transfer_id, batch_id, num_placed, placement_date,
                            num_rooted if num_rooted > 0 else None,
                            rooting_date, notes
                        )
                        st.success(f"Rooting record #{record_id} added successfully!")
                    else:
                        st.error("Cannot place more explants than available")
        else:
            st.warning("No transfers to rooting media found. Please create a transfer with 'Rooting Media' first.")
    
    with tab2:
        st.subheader("Rooting Records")
        
        # Filter by batch
        batches = get_explant_batches()
        if not batches.empty:
            batch_filter_options = {"All Batches": None}
            batch_filter_options.update({
                f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                for _, row in batches.iterrows()
            })
            selected_filter = st.selectbox("Filter by Batch", list(batch_filter_options.keys()))
            filter_batch_id = batch_filter_options[selected_filter]
            
            rooting_records = get_rooting_records(filter_batch_id)
            
            if not rooting_records.empty:
                # Add rooting rate column
                rooting_records['rooting_rate'] = (rooting_records['num_rooted'] / rooting_records['num_placed'] * 100).round(1)
                rooting_records['rooting_rate'] = rooting_records['rooting_rate'].fillna(0)
                rooting_records['status'] = rooting_records.apply(
                    lambda x: "Rooted" if pd.notna(x['num_rooted']) and x['num_rooted'] > 0 else "In Progress",
                    axis=1
                )
                
                display_cols = ['id', 'batch_id', 'transfer_id', 'num_placed', 'placement_date', 
                               'num_rooted', 'rooting_date', 'rooting_rate', 'status', 'notes']
                st.dataframe(rooting_records[display_cols], use_container_width=True, hide_index=True)
                
                # Summary statistics
                st.subheader("Rooting Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_placed = rooting_records['num_placed'].sum()
                    st.metric("Total Placed", int(total_placed))
                with col2:
                    total_rooted = rooting_records['num_rooted'].sum() if 'num_rooted' in rooting_records.columns else 0
                    st.metric("Total Rooted", int(total_rooted) if pd.notna(total_rooted) else 0)
                with col3:
                    overall_rate = (total_rooted / total_placed * 100) if total_placed > 0 and pd.notna(total_rooted) else 0
                    st.metric("Overall Rooting Rate", f"{overall_rate:.1f}%")
                with col4:
                    in_progress = total_placed - (total_rooted if pd.notna(total_rooted) else 0)
                    st.metric("In Progress", int(in_progress))
                
                # Update rooting records
                st.subheader("Update Rooting Status")
                with st.form("update_rooting_form"):
                    record_options = {f"Record #{row['id']} - {row['num_placed']} placed on {row['placement_date']}": row['id']
                                     for _, row in rooting_records.iterrows()}
                    selected_record = st.selectbox("Select Record to Update", list(record_options.keys()))
                    record_id = record_options[selected_record]
                    
                    selected_record_data = rooting_records[rooting_records['id'] == record_id].iloc[0]
                    max_rooted = selected_record_data['num_placed']
                    
                    new_num_rooted = st.number_input("Number Rooted*", min_value=0, max_value=max_rooted, 
                                                    value=int(selected_record_data['num_rooted']) if pd.notna(selected_record_data['num_rooted']) else 0)
                    new_rooting_date = st.date_input("Rooting Date*", 
                                                    value=pd.to_datetime(selected_record_data['rooting_date']).date() if pd.notna(selected_record_data['rooting_date']) else date.today())
                    
                    update_submitted = st.form_submit_button("Update Rooting Status")
                    
                    if update_submitted:
                        update_rooting_record(record_id, new_num_rooted, new_rooting_date)
                        st.success(f"Rooting record #{record_id} updated successfully!")
                        st.rerun()
            else:
                st.info("No rooting records found")
        else:
            st.info("No batches available")
    
    with tab3:
        st.subheader("Edit or Delete Rooting Records")
        rooting_records = get_rooting_records()
        batches = get_explant_batches()
        transfers = get_transfer_records()
        
        if not rooting_records.empty:
            # Rooting record selection
            record_options = {f"Record #{row['id']} - Batch {row['batch_id']} ({row['num_placed']} placed on {row['placement_date']})": row['id'] 
                            for _, row in rooting_records.iterrows()}
            selected_record = st.selectbox("Select Rooting Record to Edit/Delete", list(record_options.keys()))
            record_id = record_options[selected_record]
            
            selected_record_data = rooting_records[rooting_records['id'] == record_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Edit Rooting Record**")
                with st.form("edit_rooting_form"):
                    # Transfer selection
                    rooting_transfers = transfers[transfers['new_media'] == 'Rooting Media'] if not transfers.empty else pd.DataFrame()
                    if not rooting_transfers.empty:
                        transfer_options = {f"Transfer #{row['id']} - Batch {row['batch_id']}": row['id'] 
                                          for _, row in rooting_transfers.iterrows()}
                        current_transfer_id = selected_record_data.get('transfer_id')
                        if pd.notna(current_transfer_id):
                            current_transfer_key = f"Transfer #{int(current_transfer_id)}"
                            default_transfer = current_transfer_key if current_transfer_key in transfer_options else list(transfer_options.keys())[0]
                        else:
                            default_transfer = list(transfer_options.keys())[0]
                        edit_transfer_id = st.selectbox("Select Transfer*", list(transfer_options.keys()),
                                                        index=list(transfer_options.keys()).index(default_transfer) if default_transfer in transfer_options else 0)
                        edit_transfer_id = transfer_options[edit_transfer_id]
                    else:
                        edit_transfer_id = None
                        st.info("No transfers to rooting media available")
                    
                    # Batch selection
                    batch_options = {f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                                   for _, row in batches.iterrows()}
                    current_batch_id = selected_record_data['batch_id']
                    current_batch = batches[batches['id'] == current_batch_id]
                    if not current_batch.empty:
                        current_batch_key = f"{current_batch.iloc[0]['batch_name']} (ID: {current_batch.iloc[0]['id']})"
                        default_batch = current_batch_key if current_batch_key in batch_options else list(batch_options.keys())[0]
                    else:
                        default_batch = list(batch_options.keys())[0]
                    
                    edit_batch_id = st.selectbox("Select Batch*", list(batch_options.keys()), 
                                                 index=list(batch_options.keys()).index(default_batch) if default_batch in batch_options else 0)
                    edit_batch_id = batch_options[edit_batch_id]
                    
                    edit_num_placed = st.number_input("Number Placed*", min_value=1, value=int(selected_record_data['num_placed']))
                    edit_placement_date = st.date_input("Placement Date*", value=pd.to_datetime(selected_record_data['placement_date']).date())
                    edit_num_rooted = st.number_input("Number Rooted (optional)", min_value=0, max_value=edit_num_placed,
                                                      value=int(selected_record_data['num_rooted']) if pd.notna(selected_record_data['num_rooted']) else 0)
                    edit_rooting_date = st.date_input("Rooting Date (optional)", 
                                                      value=pd.to_datetime(selected_record_data['rooting_date']).date() if pd.notna(selected_record_data['rooting_date']) else None)
                    edit_notes = st.text_area("Notes", value=selected_record_data['notes'] if pd.notna(selected_record_data['notes']) else "")
                    
                    edit_submitted = st.form_submit_button("Update Rooting Record")
                    
                    if edit_submitted:
                        update_rooting_record_full(record_id, edit_transfer_id, edit_batch_id, edit_num_placed, edit_placement_date,
                                                   edit_num_rooted if edit_num_rooted > 0 else None, edit_rooting_date, edit_notes)
                        st.success(f"Rooting record #{record_id} updated successfully!")
                        st.rerun()
            
            with col2:
                st.write("**Delete Rooting Record**")
                st.warning("⚠️ This action cannot be undone.")
                
                if st.button("Delete Rooting Record", type="primary", use_container_width=True):
                    delete_rooting_record(record_id)
                    st.success(f"Rooting record #{record_id} deleted successfully!")
                    st.rerun()
        else:
            st.info("No rooting records found")

# Delivery
elif page == "Delivery":
    st.header("Delivery Tracking")
    
    tab1, tab2, tab3 = st.tabs(["Record Delivery", "View Delivery Records", "Edit/Delete Records"])
    
    with tab1:
        st.subheader("Record Delivery")
        
        # Get orders and batches
        orders = get_orders()
        batches = get_explant_batches()
        
        if not orders.empty:
            with st.form("delivery_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Order selection
                    order_options = {f"Order #{row['id']} - {row['client_name']} ({row['cultivar']})": row['id'] 
                                    for _, row in orders.iterrows()}
                    selected_order = st.selectbox("Select Order*", list(order_options.keys()))
                    order_id = order_options[selected_order]
                    
                    # Batch selection (batches linked to this order)
                    order_batches = batches[batches['order_id'] == order_id] if not batches.empty else pd.DataFrame()
                    if not order_batches.empty:
                        batch_options = {f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                                        for _, row in order_batches.iterrows()}
                        batch_options["None"] = None
                        selected_batch = st.selectbox("Select Batch (optional)", list(batch_options.keys()))
                        batch_id = batch_options[selected_batch]
                    else:
                        batch_id = None
                        st.info("No batches found for this order")
                    
                    num_delivered = st.number_input("Number Delivered*", min_value=1, value=1)
                    delivery_date = st.date_input("Delivery Date*", value=date.today())
                
                with col2:
                    delivery_method = st.text_input("Delivery Method (e.g., Shipping, Pickup, etc.)")
                    notes = st.text_area("Notes")
                
                submitted = st.form_submit_button("Record Delivery")
                
                if submitted:
                    record_id = add_delivery_record(
                        order_id, batch_id, num_delivered, delivery_date, delivery_method, notes
                    )
                    st.success(f"Delivery record #{record_id} added successfully!")
                    st.rerun()
        else:
            st.warning("No orders found. Please create an order first.")
    
    with tab2:
        st.subheader("Delivery Records")
        delivery_records = get_delivery_records()
        
        if not delivery_records.empty:
            # Merge with orders and batches for display
            delivery_display = delivery_records.merge(
                orders, left_on='order_id', right_on='id', how='left', suffixes=('', '_order')
            )
            delivery_display = delivery_display.merge(
                batches, left_on='batch_id', right_on='id', how='left', suffixes=('', '_batch')
            )
            
            display_cols = ['id', 'order_id', 'client_name', 'cultivar', 'batch_name', 
                          'num_delivered', 'delivery_date', 'delivery_method', 'notes']
            available_cols = [col for col in display_cols if col in delivery_display.columns]
            st.dataframe(delivery_display[available_cols], use_container_width=True, hide_index=True)
            
            # Summary
            st.subheader("Delivery Summary")
            col1, col2 = st.columns(2)
            with col1:
                total_delivered = delivery_records['num_delivered'].sum()
                st.metric("Total Plants Delivered", total_delivered)
            with col2:
                total_deliveries = len(delivery_records)
                st.metric("Total Delivery Records", total_deliveries)
        else:
            st.info("No delivery records found")
    
    with tab3:
        st.subheader("Edit or Delete Delivery Records")
        delivery_records = get_delivery_records()
        
        if not delivery_records.empty:
            # Delivery record selection
            delivery_options = {}
            orders = get_orders()
            batches = get_explant_batches()
            
            for _, delivery in delivery_records.iterrows():
                order_info = orders[orders['id'] == delivery['order_id']]
                batch_info = batches[batches['id'] == delivery['batch_id']] if pd.notna(delivery['batch_id']) else pd.DataFrame()
                
                order_str = f"Order #{delivery['order_id']}"
                if not order_info.empty:
                    order_str += f" - {order_info.iloc[0]['client_name']}"
                
                batch_str = ""
                if not batch_info.empty:
                    batch_str = f" - Batch: {batch_info.iloc[0]['batch_name']}"
                
                delivery_options[f"Delivery #{delivery['id']} - {order_str}{batch_str} ({delivery['num_delivered']} plants)"] = delivery['id']
            
            selected_delivery = st.selectbox("Select Delivery Record to Edit/Delete", list(delivery_options.keys()))
            record_id = delivery_options[selected_delivery]
            
            selected_record_data = delivery_records[delivery_records['id'] == record_id].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Edit Delivery Record**")
                with st.form("edit_delivery_form"):
                    # Order selection
                    order_options = {f"Order #{row['id']} - {row['client_name']} ({row['cultivar']})": row['id'] 
                                    for _, row in orders.iterrows()}
                    current_order_id = selected_record_data['order_id']
                    current_order_key = f"Order #{current_order_id}"
                    for key in order_options.keys():
                        if key.startswith(current_order_key):
                            current_order_key = key
                            break
                    default_order = current_order_key if current_order_key in order_options else list(order_options.keys())[0]
                    
                    edit_order_id = st.selectbox("Select Order*", list(order_options.keys()),
                                                 index=list(order_options.keys()).index(default_order) if default_order in order_options else 0)
                    edit_order_id = order_options[edit_order_id]
                    
                    # Batch selection
                    order_batches = batches[batches['order_id'] == edit_order_id] if not batches.empty else pd.DataFrame()
                    if not order_batches.empty:
                        batch_options = {f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                                        for _, row in order_batches.iterrows()}
                        batch_options["None"] = None
                        current_batch_id = selected_record_data.get('batch_id')
                        if pd.notna(current_batch_id):
                            current_batch = batches[batches['id'] == current_batch_id]
                            if not current_batch.empty:
                                current_batch_key = f"{current_batch.iloc[0]['batch_name']} (ID: {current_batch.iloc[0]['id']})"
                                default_batch = current_batch_key if current_batch_key in batch_options else "None"
                            else:
                                default_batch = "None"
                        else:
                            default_batch = "None"
                        
                        edit_batch_id = st.selectbox("Select Batch (optional)", list(batch_options.keys()),
                                                     index=list(batch_options.keys()).index(default_batch) if default_batch in batch_options else 0)
                        edit_batch_id = batch_options[edit_batch_id]
                    else:
                        edit_batch_id = None
                        st.info("No batches found for this order")
                    
                    edit_num_delivered = st.number_input("Number Delivered*", min_value=1, value=int(selected_record_data['num_delivered']))
                    edit_delivery_date = st.date_input("Delivery Date*", value=pd.to_datetime(selected_record_data['delivery_date']).date())
                    edit_delivery_method = st.text_input("Delivery Method", value=selected_record_data.get('delivery_method', '') if pd.notna(selected_record_data.get('delivery_method')) else "")
                    edit_notes = st.text_area("Notes", value=selected_record_data.get('notes', '') if pd.notna(selected_record_data.get('notes')) else "")
                    
                    edit_submitted = st.form_submit_button("Update Delivery Record")
                    
                    if edit_submitted:
                        update_delivery_record(record_id, edit_order_id, edit_batch_id, edit_num_delivered, edit_delivery_date, edit_delivery_method, edit_notes)
                        st.success(f"Delivery record #{record_id} updated successfully!")
                        st.rerun()
            
            with col2:
                st.write("**Delete Delivery Record**")
                st.warning("⚠️ This action cannot be undone.")
                
                if st.button("Delete Delivery Record", type="primary", use_container_width=True):
                    delete_delivery_record(record_id)
                    st.success(f"Delivery record #{record_id} deleted successfully!")
                    st.rerun()
        else:
            st.info("No delivery records found")

# Timeline
elif page == "Timeline":
    st.header("Complete Timeline View")
    
    tab1, tab2 = st.tabs(["Gantt Chart by Cultivar", "Batch Timeline"])
    
    with tab1:
        st.subheader("Gantt Chart - Cultivar Timeline")
        
        # Get all data
        orders = get_orders()
        batches = get_explant_batches()
        transfers = get_transfer_records()
        rooting_records = get_rooting_records()
        delivery_records = get_delivery_records()
        
        if not batches.empty and not orders.empty:
            # Merge batches with orders to get cultivar info
            batches_with_orders = batches.merge(orders, left_on='order_id', right_on='id', how='left', suffixes=('', '_order'))
            batches_with_orders = batches_with_orders[batches_with_orders['cultivar'].notna()]
            
            if not batches_with_orders.empty:
                # Get unique cultivars
                all_cultivars = batches_with_orders['cultivar'].unique().tolist()
                
                # Cultivar selection
                selected_cultivars = st.multiselect(
                    "Select Cultivars (leave empty for all)",
                    all_cultivars,
                    default=all_cultivars
                )
                
                if not selected_cultivars:
                    selected_cultivars = all_cultivars
                
                # Filter batches by selected cultivars
                filtered_batches = batches_with_orders[batches_with_orders['cultivar'].isin(selected_cultivars)]
                
                # Convert rooting_records batch_id to numeric once before the loop
                if not rooting_records.empty:
                    rooting_records = rooting_records.copy()
                    rooting_records['batch_id'] = pd.to_numeric(rooting_records['batch_id'], errors='coerce')
                
                # Build Gantt chart data
                gantt_data = []
                
                for _, batch in filtered_batches.iterrows():
                    cultivar = batch['cultivar']
                    batch_id = int(batch['id'])
                    
                    # Order received
                    order_date = pd.to_datetime(batch['order_date'])
                    
                    # Initiation
                    init_date = pd.to_datetime(batch['initiation_date'])
                    
                    # Get transfers for this batch
                    batch_transfers = transfers[transfers['batch_id'] == batch_id] if not transfers.empty else pd.DataFrame()
                    
                    # Get rooting records for this batch
                    batch_rooting = rooting_records[rooting_records['batch_id'] == batch_id] if not rooting_records.empty else pd.DataFrame()
                    
                    # Get delivery records for this batch
                    batch_deliveries = delivery_records[delivery_records['batch_id'] == batch_id] if not delivery_records.empty else pd.DataFrame()
                    
                    # Get order completion date
                    order_id = batch.get('order_id')
                    order_completion = None
                    if pd.notna(order_id):
                        order_row = orders[orders['id'] == int(order_id)]
                        if not order_row.empty and order_row.iloc[0].get('completed', 0) == 1:
                            completion_date = order_row.iloc[0].get('completion_date')
                            if pd.notna(completion_date):
                                order_completion = pd.to_datetime(completion_date)
                    
                    # Order received - single day marker
                    gantt_data.append({
                        'Cultivar': cultivar,
                        'Task': 'Order Received',
                        'Start': order_date,
                        'Finish': order_date + pd.Timedelta(days=1),
                        'Duration': 1
                    })
                    
                    # Passive time: Order to Initiation
                    if init_date > order_date + pd.Timedelta(days=1):
                        gantt_data.append({
                            'Cultivar': cultivar,
                            'Task': 'Passive Time',
                            'Start': order_date + pd.Timedelta(days=1),
                            'Finish': init_date,
                            'Duration': (init_date - (order_date + pd.Timedelta(days=1))).days
                        })
                    
                    # Initiation - single day marker
                    init_end = init_date + pd.Timedelta(days=1)
                    gantt_data.append({
                        'Cultivar': cultivar,
                        'Task': 'Explant Initiation',
                        'Start': init_date,
                        'Finish': init_end,
                        'Duration': 1
                    })
                    
                    # Initiation to First Transfer
                    if not batch_transfers.empty:
                        first_transfer = batch_transfers.sort_values('transfer_date').iloc[0]
                        first_transfer_date = pd.to_datetime(first_transfer['transfer_date'])
                        
                        # Passive time: Initiation to First Transfer
                        if first_transfer_date > init_end:
                            gantt_data.append({
                                'Cultivar': cultivar,
                                'Task': 'Passive Time',
                                'Start': init_end,
                                'Finish': first_transfer_date,
                                'Duration': (first_transfer_date - init_end).days
                            })
                        
                        # Show each individual transfer as a separate task
                        sorted_transfers = batch_transfers.sort_values('transfer_date')
                        prev_date = init_end  # Start from day after initiation
                        
                        for idx, transfer in sorted_transfers.iterrows():
                            transfer_date = pd.to_datetime(transfer['transfer_date'])
                            media_type = transfer['new_media']
                            explants_in = int(transfer['explants_in'])
                            explants_out = int(transfer['explants_out'])
                            multiplication = "Yes" if transfer['multiplication_occurred'] else "No"
                            
                            # Add passive time between previous event and this transfer
                            if transfer_date > prev_date + pd.Timedelta(days=1):
                                gantt_data.append({
                                    'Cultivar': cultivar,
                                    'Task': 'Passive Time',
                                    'Start': prev_date,
                                    'Finish': transfer_date,
                                    'Duration': (transfer_date - prev_date).days
                                })
                            
                            # Each transfer is shown as a point in time (1 day duration to make it visible)
                            gantt_data.append({
                                'Cultivar': cultivar,
                                'Task': f"Transfer #{transfer['id']}: {media_type} ({explants_in}→{explants_out}, Mult: {multiplication})",
                                'Start': transfer_date,
                                'Finish': transfer_date + pd.Timedelta(days=1),
                                'Duration': 1
                            })
                            
                            prev_date = transfer_date + pd.Timedelta(days=1)
                        
                        # Show rooting media placement dates
                        if not batch_rooting.empty:
                            sorted_rooting = batch_rooting.sort_values('placement_date')
                            for idx, rooting in sorted_rooting.iterrows():
                                placement_date = pd.to_datetime(rooting['placement_date'])
                                num_placed = int(rooting['num_placed'])
                                
                                # Add passive time if there's a gap before placement
                                if placement_date > prev_date + pd.Timedelta(days=1):
                                    gantt_data.append({
                                        'Cultivar': cultivar,
                                        'Task': 'Passive Time',
                                        'Start': prev_date,
                                        'Finish': placement_date,
                                        'Duration': (placement_date - prev_date).days
                                    })
                                
                                # Rooting placement as a point in time
                                gantt_data.append({
                                    'Cultivar': cultivar,
                                    'Task': f"Rooting Placement: {num_placed} placed",
                                    'Start': placement_date,
                                    'Finish': placement_date + pd.Timedelta(days=1),
                                    'Duration': 1
                                })
                                
                                prev_date = placement_date + pd.Timedelta(days=1)
                                
                                # Rooting completion date if available
                                if pd.notna(rooting['rooting_date']):
                                    rooting_date = pd.to_datetime(rooting['rooting_date'])
                                    num_rooted = int(rooting['num_rooted']) if pd.notna(rooting['num_rooted']) else 0
                                    
                                    # Add passive time if there's a gap before completion
                                    if rooting_date > prev_date + pd.Timedelta(days=1):
                                        gantt_data.append({
                                            'Cultivar': cultivar,
                                            'Task': 'Passive Time',
                                            'Start': prev_date,
                                            'Finish': rooting_date,
                                            'Duration': (rooting_date - prev_date).days
                                        })
                                    
                                    # Show rooting completion as a point in time
                                    gantt_data.append({
                                        'Cultivar': cultivar,
                                        'Task': f"Rooting Complete: {num_rooted} rooted",
                                        'Start': rooting_date,
                                        'Finish': rooting_date + pd.Timedelta(days=1),
                                        'Duration': 1
                                    })
                                    
                                    prev_date = rooting_date + pd.Timedelta(days=1)
                    
                    # Add delivery events
                    if not batch_deliveries.empty:
                        sorted_deliveries = batch_deliveries.sort_values('delivery_date')
                        for idx, delivery in sorted_deliveries.iterrows():
                            delivery_date = pd.to_datetime(delivery['delivery_date'])
                            num_delivered = int(delivery['num_delivered'])
                            
                            # Add passive time if there's a gap before delivery
                            if delivery_date > prev_date + pd.Timedelta(days=1):
                                gantt_data.append({
                                    'Cultivar': cultivar,
                                    'Task': 'Passive Time',
                                    'Start': prev_date,
                                    'Finish': delivery_date,
                                    'Duration': (delivery_date - prev_date).days
                                })
                            
                            # Delivery as a point in time
                            gantt_data.append({
                                'Cultivar': cultivar,
                                'Task': f"Delivery: {num_delivered} delivered",
                                'Start': delivery_date,
                                'Finish': delivery_date + pd.Timedelta(days=1),
                                'Duration': 1
                            })
                            
                            prev_date = delivery_date + pd.Timedelta(days=1)
                    
                    # Add order completion event
                    if order_completion is not None:
                        # Add passive time if there's a gap before completion
                        if order_completion > prev_date + pd.Timedelta(days=1):
                            gantt_data.append({
                                'Cultivar': cultivar,
                                'Task': 'Passive Time',
                                'Start': prev_date,
                                'Finish': order_completion,
                                'Duration': (order_completion - prev_date).days
                            })
                        
                        # Order completion as a point in time
                        gantt_data.append({
                            'Cultivar': cultivar,
                            'Task': 'Order Completed',
                            'Start': order_completion,
                            'Finish': order_completion + pd.Timedelta(days=1),
                            'Duration': 1
                        })
                else:
                    # No transfers yet, show passive time from initiation to today
                    today = pd.to_datetime(date.today())
                    if today > init_date + pd.Timedelta(days=1):
                        gantt_data.append({
                            'Cultivar': cultivar,
                            'Task': 'Passive Time',
                            'Start': init_date + pd.Timedelta(days=1),
                            'Finish': today,
                            'Duration': (today - init_date - pd.Timedelta(days=1)).days
                        })
                
                if gantt_data:
                    gantt_df = pd.DataFrame(gantt_data)
                    
                    # Create Gantt chart
                    fig = px.timeline(
                        gantt_df,
                        x_start='Start',
                        x_end='Finish',
                        y='Cultivar',
                        color='Task',
                        title='Cultivar Timeline - Gantt Chart',
                        labels={'Start': 'Start Date', 'Finish': 'End Date', 'Cultivar': 'Cultivar'},
                        hover_data=['Duration']
                    )
                    
                    fig.update_yaxes(autorange="reversed")
                    fig.update_layout(
                        height=max(400, len(selected_cultivars) * 50),
                        xaxis_title="Date",
                        yaxis_title="Cultivar",
                        showlegend=True
                    )
                    
                    # Configure for high-resolution PNG downloads
                    config = {
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'timeline_chart',
                            'height': None,  # Use chart height
                            'width': None,   # Use chart width
                            'scale': 3       # 3x scale for high resolution (default is 1)
                        }
                    }
                    
                    st.plotly_chart(fig, use_container_width=True, config=config)
                    
                    # Summary table
                    st.subheader("Summary by Cultivar")
                    summary_data = []
                    for cultivar in selected_cultivars:
                        cultivar_data = gantt_df[gantt_df['Cultivar'] == cultivar]
                        if not cultivar_data.empty:
                            total_days = cultivar_data['Duration'].sum()
                            summary_data.append({
                                'Cultivar': cultivar,
                                'Total Days': int(total_days),
                                'Stages': len(cultivar_data),
                                'Current Stage': cultivar_data.iloc[-1]['Task'] if not cultivar_data.empty else 'N/A'
                            })
                    
                    if summary_data:
                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No timeline data available for selected cultivars")
            else:
                st.info("No batches linked to orders with cultivar information")
        else:
            st.info("No data available for Gantt chart")
    
    with tab2:
        st.subheader("Batch Timeline (Detailed View)")
        
        batches = get_explant_batches()
        
        if not batches.empty:
            # Filter by batch
            batch_options = {f"{row['batch_name']} (ID: {row['id']})": row['id'] 
                            for _, row in batches.iterrows()}
            selected_batch = st.selectbox("Select Batch", list(batch_options.keys()))
            batch_id = batch_options[selected_batch]
            
            batch_info = batches[batches['id'] == batch_id].iloc[0]
            
            # Get order info if linked
            order_info = None
            if pd.notna(batch_info.get('order_id')):
                orders = get_orders()
                order_info = orders[orders['id'] == batch_info['order_id']].iloc[0] if not orders.empty else None
            
            # Get all related data
            infections = get_infection_records(batch_id)
            transfers = get_transfer_records(batch_id)
            rooting_records = get_rooting_records(batch_id)
            
            # Display timeline
            st.subheader(f"Timeline for Batch: {batch_info['batch_name']}")
            
            timeline_items = []
            
            # Order receipt (if linked)
            if order_info is not None:
                timeline_items.append({
                    'date': pd.to_datetime(order_info['order_date']),
                    'event': 'Order Received',
                    'details': f"Client: {order_info['client_name']}, Cultivar: {order_info['cultivar']}, {order_info['num_plants']} plants"
                })
            
            # Initiation
            timeline_items.append({
                'date': pd.to_datetime(batch_info['initiation_date']),
                'event': 'Explant Initiation',
                'details': f"{batch_info['num_explants']} explants, Type: {batch_info['explant_type']}, Media: {batch_info['media_type']}"
            })
            
            # Infections
            for _, infection in infections.iterrows():
                timeline_items.append({
                    'date': pd.to_datetime(infection['identification_date']),
                    'event': 'Infection Identified',
                    'details': f"{infection['num_infected']} explants, Type: {infection['infection_type']}"
                })
            
            # Transfers
            for _, transfer in transfers.iterrows():
                timeline_items.append({
                    'date': pd.to_datetime(transfer['transfer_date']),
                    'event': 'Transfer',
                    'details': f"{transfer['explants_in']} in → {transfer['explants_out']} out, Media: {transfer['new_media']}, Multiplication: {'Yes' if transfer['multiplication_occurred'] else 'No'}"
                })
            
            # Rooting
            for _, rooting in rooting_records.iterrows():
                timeline_items.append({
                    'date': pd.to_datetime(rooting['placement_date']),
                    'event': 'Placed in Rooting Media',
                    'details': f"{rooting['num_placed']} explants placed"
                })
                if pd.notna(rooting['rooting_date']):
                    timeline_items.append({
                        'date': pd.to_datetime(rooting['rooting_date']),
                        'event': 'Rooting Completed',
                        'details': f"{rooting['num_rooted']} explants rooted ({rooting['num_rooted']/rooting['num_placed']*100:.1f}%)"
                    })
            
            # Deliveries
            delivery_records = get_delivery_records()
            batch_deliveries = delivery_records[delivery_records['batch_id'] == batch_id] if not delivery_records.empty else pd.DataFrame()
            for _, delivery in batch_deliveries.iterrows():
                timeline_items.append({
                    'date': pd.to_datetime(delivery['delivery_date']),
                    'event': 'Delivery',
                    'details': f"{delivery['num_delivered']} plants delivered" + (f" ({delivery['delivery_method']})" if pd.notna(delivery.get('delivery_method')) else "")
                })
            
            # Order completion
            if order_info is not None:
                if order_info.get('completed', 0) == 1 and pd.notna(order_info.get('completion_date')):
                    timeline_items.append({
                        'date': pd.to_datetime(order_info['completion_date']),
                        'event': 'Order Completed',
                        'details': f"Order marked as complete"
                    })
            
            # Sort by date
            timeline_df = pd.DataFrame(timeline_items)
            if not timeline_df.empty:
                timeline_df = timeline_df.sort_values('date')
                timeline_df['date'] = timeline_df['date'].dt.strftime('%Y-%m-%d')
                
                st.dataframe(timeline_df, use_container_width=True, hide_index=True)
            else:
                st.info("No timeline data available")
        else:
            st.info("No batches available")

# Statistics
elif page == "Statistics":
    st.header("Statistics & Analytics")
    
    # Toggle to include/exclude archived orders
    include_archived = st.checkbox("Include Archived Orders", value=False)
    
    tab1, tab2 = st.tabs(["Global Statistics", "Per-Cultivar Statistics"])
    
    with tab1:
        st.subheader("Global Statistics")
        
        conn = get_connection()
        
        # Get all data
        orders = get_orders()
        batches = get_explant_batches()
        infections = get_infection_records()
        transfers = get_transfer_records()
        rooting_records = get_rooting_records()
        
        # Filter out archived orders if toggle is off
        if not include_archived:
            if 'completed' in orders.columns:
                active_order_ids = orders[orders.get('completed', 0) == 0]['id'].tolist()
                # Filter batches to only those linked to active orders
                if not batches.empty:
                    batches = batches[batches['order_id'].isin(active_order_ids) | batches['order_id'].isna()]
                # Filter infections, transfers, and rooting records based on active batches
                if not batches.empty:
                    active_batch_ids = batches['id'].tolist()
                    if not infections.empty:
                        infections = infections[infections['batch_id'].isin(active_batch_ids)]
                    if not transfers.empty:
                        transfers = transfers[transfers['batch_id'].isin(active_batch_ids)]
                    if not rooting_records.empty:
                        rooting_records = rooting_records[rooting_records['batch_id'].isin(active_batch_ids)]
        
        if not batches.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            # Rooting rate
            total_placed = rooting_records['num_placed'].sum() if not rooting_records.empty else 0
            # Handle NaN values in num_rooted before summing
            if not rooting_records.empty and 'num_rooted' in rooting_records.columns:
                total_rooted = rooting_records['num_rooted'].fillna(0).sum()
            else:
                total_rooted = 0
            rooting_rate = (total_rooted / total_placed * 100) if total_placed > 0 else 0
            
            with col1:
                st.metric("Global Rooting Rate", f"{rooting_rate:.1f}%")
            
            # Infection rate
            total_explants = batches['num_explants'].sum()
            total_infected = infections['num_infected'].sum() if not infections.empty else 0
            infection_rate = (total_infected / total_explants * 100) if total_explants > 0 else 0
            
            with col2:
                st.metric("Global Infection Rate", f"{infection_rate:.1f}%")
            
            # Average time calculations
            if not batches.empty and not transfers.empty:
                # Calculate average time from initiation to first transfer
                batch_transfer_times = []
                for _, batch in batches.iterrows():
                    batch_transfers = transfers[transfers['batch_id'] == batch['id']]
                    if not batch_transfers.empty:
                        first_transfer = batch_transfers.sort_values('transfer_date').iloc[0]
                        init_date = pd.to_datetime(batch['initiation_date'])
                        transfer_date = pd.to_datetime(first_transfer['transfer_date'])
                        days = (transfer_date - init_date).days
                        if days >= 0:
                            batch_transfer_times.append(days)
                
                avg_init_to_transfer = sum(batch_transfer_times) / len(batch_transfer_times) if batch_transfer_times else 0
                
                with col3:
                    st.metric("Avg Days: Initiation to First Transfer", f"{avg_init_to_transfer:.1f}")
                
                # Calculate average time in rooting
                if not rooting_records.empty:
                    rooting_times = []
                    for _, record in rooting_records.iterrows():
                        if pd.notna(record['rooting_date']) and pd.notna(record['placement_date']):
                            placement = pd.to_datetime(record['placement_date'])
                            rooting = pd.to_datetime(record['rooting_date'])
                            days = (rooting - placement).days
                            if days >= 0:
                                rooting_times.append(days)
                    
                    avg_rooting_time = sum(rooting_times) / len(rooting_times) if rooting_times else 0
                    
                    with col4:
                        st.metric("Avg Days in Rooting Media", f"{avg_rooting_time:.1f}")
                else:
                    with col4:
                        st.metric("Avg Days in Rooting Media", "N/A")
            else:
                with col3:
                    st.metric("Avg Days: Initiation to First Transfer", "N/A")
                with col4:
                    st.metric("Avg Days in Rooting Media", "N/A")
            
            st.divider()
            
            # Total Explants Over Time
            st.subheader("Total Explants Over Time")
            if not batches.empty:
                # Get all events that affect explant count
                events = []
                
                # Batch initiations (add explants)
                for _, batch in batches.iterrows():
                    events.append({
                        'date': pd.to_datetime(batch['initiation_date']),
                        'change': int(batch['num_explants']),
                        'type': 'initiation'
                    })
                
                # Infections (subtract explants)
                if not infections.empty:
                    for _, infection in infections.iterrows():
                        events.append({
                            'date': pd.to_datetime(infection['identification_date']),
                            'change': -int(infection['num_infected']),
                            'type': 'infection'
                        })
                
                # Transfers (net change: explants_out - explants_in)
                if not transfers.empty:
                    for _, transfer in transfers.iterrows():
                        net_change = int(transfer['explants_out']) - int(transfer['explants_in'])
                        events.append({
                            'date': pd.to_datetime(transfer['transfer_date']),
                            'change': net_change,
                            'type': 'transfer'
                        })
                
                if events:
                    # Sort events by date
                    events_df = pd.DataFrame(events)
                    events_df = events_df.sort_values('date')
                    
                    # Calculate cumulative total
                    events_df['cumulative_total'] = events_df['change'].cumsum()
                    
                    # Group by date (in case multiple events on same day)
                    daily_changes = events_df.groupby(events_df['date'].dt.date).agg({
                        'change': 'sum',
                        'cumulative_total': 'last'
                    }).reset_index()
                    daily_changes.columns = ['Date', 'Daily Change', 'Cumulative Total']
                    daily_changes['Date'] = pd.to_datetime(daily_changes['Date'])
                    daily_changes = daily_changes.sort_values('Date')
                    
                    # Recalculate cumulative after grouping
                    daily_changes['Cumulative Total'] = daily_changes['Daily Change'].cumsum()
                    
                    # Create continuous timeline
                    date_range = pd.date_range(
                        start=daily_changes['Date'].min(),
                        end=pd.to_datetime(date.today()),
                        freq='D'
                    )
                    
                    continuous_timeline = pd.DataFrame({'Date': date_range})
                    continuous_timeline = continuous_timeline.merge(
                        daily_changes[['Date', 'Cumulative Total']],
                        on='Date',
                        how='left'
                    )
                    continuous_timeline['Cumulative Total'] = continuous_timeline['Cumulative Total'].ffill().fillna(0)
                    continuous_timeline = continuous_timeline.set_index('Date')
                    
                    st.line_chart(continuous_timeline['Cumulative Total'])
                else:
                    st.info("No event data available")
            
            st.divider()
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Rooting Rate Over Time**")
                if not rooting_records.empty and 'rooting_date' in rooting_records.columns:
                    rooting_timeline = rooting_records[pd.notna(rooting_records['rooting_date'])].copy()
                    if not rooting_timeline.empty:
                        rooting_timeline['rooting_date'] = pd.to_datetime(rooting_timeline['rooting_date'])
                        daily_rooting = rooting_timeline.groupby(rooting_timeline['rooting_date'].dt.date).agg({
                            'num_rooted': 'sum',
                            'num_placed': 'sum'
                        }).reset_index()
                        daily_rooting['rate'] = (daily_rooting['num_rooted'] / daily_rooting['num_placed'] * 100).round(1)
                        daily_rooting['rooting_date'] = pd.to_datetime(daily_rooting['rooting_date'])
                        daily_rooting = daily_rooting.sort_values('rooting_date')
                        
                        # Calculate cumulative totals for rate calculation
                        daily_rooting['cumulative_rooted'] = daily_rooting['num_rooted'].cumsum()
                        daily_rooting['cumulative_placed'] = daily_rooting['num_placed'].cumsum()
                        daily_rooting['cumulative_rate'] = (daily_rooting['cumulative_rooted'] / daily_rooting['cumulative_placed'] * 100).round(1)
                        
                        # Create continuous timeline
                        date_range = pd.date_range(
                            start=daily_rooting['rooting_date'].min(),
                            end=pd.to_datetime(date.today()),
                            freq='D'
                        )
                        
                        continuous_timeline = pd.DataFrame({'Date': date_range})
                        continuous_timeline = continuous_timeline.merge(
                            daily_rooting[['rooting_date', 'cumulative_rate']],
                            left_on='Date',
                            right_on='rooting_date',
                            how='left'
                        )
                        continuous_timeline['cumulative_rate'] = continuous_timeline['cumulative_rate'].ffill()
                        continuous_timeline = continuous_timeline.set_index('Date')
                        
                        st.line_chart(continuous_timeline['cumulative_rate'])
                    else:
                        st.info("No rooting completion data")
                else:
                    st.info("No rooting data available")
            
            with col2:
                st.write("**Infection Rate Over Time**")
                if not infections.empty:
                    infection_timeline = infections.copy()
                    infection_timeline['identification_date'] = pd.to_datetime(infection_timeline['identification_date'])
                    daily_infections = infection_timeline.groupby(infection_timeline['identification_date'].dt.date).agg({
                        'num_infected': 'sum'
                    }).reset_index()
                    daily_infections['identification_date'] = pd.to_datetime(daily_infections['identification_date'])
                    daily_infections = daily_infections.sort_values('identification_date')
                    
                    # Calculate cumulative infection rate
                    # Get total explants initiated up to each date
                    batches_sorted = batches.copy()
                    batches_sorted['initiation_date'] = pd.to_datetime(batches_sorted['initiation_date'])
                    batches_sorted = batches_sorted.sort_values('initiation_date')
                    
                    daily_infections['cumulative_infected'] = daily_infections['num_infected'].cumsum()
                    
                    # Calculate total explants initiated by each infection date
                    infection_rates = []
                    for _, inf_row in daily_infections.iterrows():
                        inf_date = inf_row['identification_date']
                        total_initiated = batches_sorted[batches_sorted['initiation_date'] <= inf_date]['num_explants'].sum()
                        if total_initiated > 0:
                            rate = (inf_row['cumulative_infected'] / total_initiated * 100)
                            infection_rates.append({
                                'Date': inf_date,
                                'Infection Rate': rate
                            })
                    
                    if infection_rates:
                        rates_df = pd.DataFrame(infection_rates)
                        
                        # Create continuous timeline
                        date_range = pd.date_range(
                            start=rates_df['Date'].min(),
                            end=pd.to_datetime(date.today()),
                            freq='D'
                        )
                        
                        continuous_timeline = pd.DataFrame({'Date': date_range})
                        continuous_timeline = continuous_timeline.merge(
                            rates_df,
                            on='Date',
                            how='left'
                        )
                        continuous_timeline['Infection Rate'] = continuous_timeline['Infection Rate'].ffill()
                        continuous_timeline = continuous_timeline.set_index('Date')
                        
                        st.line_chart(continuous_timeline['Infection Rate'])
                    else:
                        st.info("No infection rate data available")
                else:
                    st.info("No infection data available")
        else:
            st.info("No data available for statistics")
        
        conn.close()
    
    with tab2:
        st.subheader("Per-Cultivar Statistics")
        
        orders = get_orders()
        batches = get_explant_batches()
        infections = get_infection_records()
        transfers = get_transfer_records()
        rooting_records = get_rooting_records()
        
        # Filter out archived orders if toggle is off
        if not include_archived:
            if 'completed' in orders.columns:
                active_order_ids = orders[orders.get('completed', 0) == 0]['id'].tolist()
                # Filter batches to only those linked to active orders
                if not batches.empty:
                    batches = batches[batches['order_id'].isin(active_order_ids) | batches['order_id'].isna()]
                # Filter infections, transfers, and rooting records based on active batches
                if not batches.empty:
                    active_batch_ids = batches['id'].tolist()
                    if not infections.empty:
                        infections = infections[infections['batch_id'].isin(active_batch_ids)]
                    if not transfers.empty:
                        transfers = transfers[transfers['batch_id'].isin(active_batch_ids)]
                    if not rooting_records.empty:
                        rooting_records = rooting_records[rooting_records['batch_id'].isin(active_batch_ids)]
        
        if not orders.empty and not batches.empty:
            # Merge orders and batches to get cultivar info
            batches_with_orders = batches.merge(orders, left_on='order_id', right_on='id', how='left', suffixes=('', '_order'))
            
            if not batches_with_orders.empty:
                cultivar_stats = []
                
                for cultivar in batches_with_orders['cultivar'].dropna().unique():
                    cultivar_batches = batches_with_orders[batches_with_orders['cultivar'] == cultivar]
                    cultivar_batch_ids = cultivar_batches['id'].tolist()
                    
                    # Get data for this cultivar
                    cultivar_infections = infections[infections['batch_id'].isin(cultivar_batch_ids)] if not infections.empty else pd.DataFrame()
                    cultivar_transfers = transfers[transfers['batch_id'].isin(cultivar_batch_ids)] if not transfers.empty else pd.DataFrame()
                    cultivar_rooting = rooting_records[rooting_records['batch_id'].isin(cultivar_batch_ids)] if not rooting_records.empty else pd.DataFrame()
                    
                    # Calculate statistics
                    total_explants = cultivar_batches['num_explants'].sum()
                    total_infected = cultivar_infections['num_infected'].sum() if not cultivar_infections.empty else 0
                    infection_rate = (total_infected / total_explants * 100) if total_explants > 0 else 0
                    
                    total_placed = cultivar_rooting['num_placed'].sum() if not cultivar_rooting.empty else 0
                    # Handle NaN values in num_rooted before summing
                    if not cultivar_rooting.empty and 'num_rooted' in cultivar_rooting.columns:
                        total_rooted = cultivar_rooting['num_rooted'].fillna(0).sum()
                    else:
                        total_rooted = 0
                    rooting_rate = (total_rooted / total_placed * 100) if total_placed > 0 else 0
                    
                    # Average time in rooting
                    avg_rooting_time = 0
                    if not cultivar_rooting.empty:
                        rooting_times = []
                        for _, record in cultivar_rooting.iterrows():
                            if pd.notna(record['rooting_date']) and pd.notna(record['placement_date']):
                                placement = pd.to_datetime(record['placement_date'])
                                rooting = pd.to_datetime(record['rooting_date'])
                                days = (rooting - placement).days
                                if days >= 0:
                                    rooting_times.append(days)
                        avg_rooting_time = sum(rooting_times) / len(rooting_times) if rooting_times else 0
                    
                    cultivar_stats.append({
                        'Cultivar': cultivar,
                        'Total Explants': int(total_explants),
                        'Infection Rate (%)': f"{infection_rate:.1f}",
                        'Total Placed in Rooting': int(total_placed),
                        'Total Rooted': int(total_rooted) if pd.notna(total_rooted) else 0,
                        'Rooting Rate (%)': f"{rooting_rate:.1f}",
                        'Avg Days in Rooting': f"{avg_rooting_time:.1f}" if avg_rooting_time > 0 else "N/A"
                    })
                
                stats_df = pd.DataFrame(cultivar_stats)
                st.dataframe(stats_df, use_container_width=True, hide_index=True)
                
                # Total Explants Over Time by Cultivar
                st.subheader("Total Explants Over Time by Cultivar")
                if not batches_with_orders.empty:
                    # Prepare data for multi-line chart
                    all_dates = []
                    cultivar_chart_data = {}
                    
                    for cultivar in batches_with_orders['cultivar'].dropna().unique():
                        cultivar_batches = batches_with_orders[batches_with_orders['cultivar'] == cultivar]
                        cultivar_batch_ids = cultivar_batches['id'].tolist()
                        
                        # Get cultivar-specific data
                        cultivar_infections = infections[infections['batch_id'].isin(cultivar_batch_ids)] if not infections.empty else pd.DataFrame()
                        cultivar_transfers = transfers[transfers['batch_id'].isin(cultivar_batch_ids)] if not transfers.empty else pd.DataFrame()
                        
                        # Get all events that affect explant count for this cultivar
                        events = []
                        
                        # Batch initiations
                        for _, batch in cultivar_batches.iterrows():
                            events.append({
                                'date': pd.to_datetime(batch['initiation_date']),
                                'change': int(batch['num_explants']),
                                'type': 'initiation'
                            })
                        
                        # Infections
                        if not cultivar_infections.empty:
                            for _, infection in cultivar_infections.iterrows():
                                events.append({
                                    'date': pd.to_datetime(infection['identification_date']),
                                    'change': -int(infection['num_infected']),
                                    'type': 'infection'
                                })
                        
                        # Transfers (net change)
                        if not cultivar_transfers.empty:
                            for _, transfer in cultivar_transfers.iterrows():
                                net_change = int(transfer['explants_out']) - int(transfer['explants_in'])
                                events.append({
                                    'date': pd.to_datetime(transfer['transfer_date']),
                                    'change': net_change,
                                    'type': 'transfer'
                                })
                        
                        if events:
                            events_df = pd.DataFrame(events)
                            events_df = events_df.sort_values('date')
                            events_df['cumulative_total'] = events_df['change'].cumsum()
                            
                            # Group by date
                            daily_changes = events_df.groupby(events_df['date'].dt.date).agg({
                                'change': 'sum',
                                'cumulative_total': 'last'
                            }).reset_index()
                            daily_changes.columns = ['Date', 'Daily Change', 'Cumulative Total']
                            daily_changes['Date'] = pd.to_datetime(daily_changes['Date'])
                            daily_changes = daily_changes.sort_values('Date')
                            daily_changes['Cumulative Total'] = daily_changes['Daily Change'].cumsum()
                            
                            cultivar_chart_data[cultivar] = daily_changes[['Date', 'Cumulative Total']]
                            all_dates.extend(daily_changes['Date'].tolist())
                    
                    if cultivar_chart_data and all_dates:
                        # Create continuous date range
                        date_range = pd.date_range(
                            start=min(all_dates),
                            end=pd.to_datetime(date.today()),
                            freq='D'
                        )
                        
                        chart_data = pd.DataFrame({'Date': date_range})
                        
                        # Add each cultivar's data
                        for cultivar_name, cultivar_data in cultivar_chart_data.items():
                            # Merge this cultivar's data
                            merged = chart_data.merge(
                                cultivar_data,
                                on='Date',
                                how='left'
                            )
                            # Forward fill and rename
                            merged['Cumulative Total'] = merged['Cumulative Total'].ffill().fillna(0)
                            chart_data[cultivar_name] = merged['Cumulative Total']
                        
                        # Set Date as index
                        chart_data = chart_data.set_index('Date')
                        st.line_chart(chart_data)
                    else:
                        st.info("No date data available")
            else:
                st.info("No batches linked to orders")
        else:
            st.info("No data available")

# Archive
elif page == "Archive":
    st.header("Archive - Completed Orders")
    
    orders = get_orders()
    completed_orders = orders[orders.get('completed', 0) == 1] if 'completed' in orders.columns else pd.DataFrame()
    
    if not completed_orders.empty:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            client_filter = st.selectbox(
                "Filter by Client",
                ["All"] + completed_orders['client_name'].unique().tolist()
            )
        with col2:
            cultivar_filter = st.selectbox(
                "Filter by Cultivar",
                ["All"] + completed_orders['cultivar'].unique().tolist()
            )
        
        filtered_orders = completed_orders.copy()
        if client_filter != "All":
            filtered_orders = filtered_orders[filtered_orders['client_name'] == client_filter]
        if cultivar_filter != "All":
            filtered_orders = filtered_orders[filtered_orders['cultivar'] == cultivar_filter]
        
        # Format the display to show recurring status
        display_orders = filtered_orders.copy()
        if 'is_recurring' in display_orders.columns:
            display_orders['Recurring'] = display_orders['is_recurring'].apply(lambda x: 'Yes' if x == 1 else 'No')
        
        # Display orders
        display_cols = ['id', 'client_name', 'cultivar', 'num_plants', 'delivery_quantity', 'Recurring', 'plant_size', 'order_date', 'completion_date', 'notes']
        available_cols = [col for col in display_cols if col in display_orders.columns]
        st.dataframe(display_orders[available_cols], use_container_width=True, hide_index=True)
        
        # Summary statistics
        st.subheader("Archive Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Completed Orders", len(completed_orders))
        with col2:
            total_plants = completed_orders['num_plants'].sum()
            st.metric("Total Plants Ordered", total_plants)
        with col3:
            if 'completion_date' in completed_orders.columns:
                avg_completion_days = None
                for _, order in completed_orders.iterrows():
                    if pd.notna(order.get('completion_date')) and pd.notna(order.get('order_date')):
                        order_date = pd.to_datetime(order['order_date'])
                        completion_date = pd.to_datetime(order['completion_date'])
                        days = (completion_date - order_date).days
                        if avg_completion_days is None:
                            avg_completion_days = days
                        else:
                            avg_completion_days = (avg_completion_days + days) / 2
                if avg_completion_days:
                    st.metric("Average Days to Complete", f"{avg_completion_days:.1f}")
                else:
                    st.metric("Average Days to Complete", "N/A")
            else:
                st.metric("Average Days to Complete", "N/A")
        
        # Get delivery records for completed orders
        delivery_records = get_delivery_records()
        if not delivery_records.empty:
            st.subheader("Delivery Records for Completed Orders")
            completed_order_ids = completed_orders['id'].tolist()
            completed_deliveries = delivery_records[delivery_records['order_id'].isin(completed_order_ids)]
            
            if not completed_deliveries.empty:
                # Merge with orders for display
                delivery_display = completed_deliveries.merge(
                    completed_orders, left_on='order_id', right_on='id', how='left', suffixes=('', '_order')
                )
                display_cols = ['id', 'order_id', 'client_name', 'cultivar', 'num_delivered', 'delivery_date', 'delivery_method', 'notes']
                available_cols = [col for col in display_cols if col in delivery_display.columns]
                st.dataframe(delivery_display[available_cols], use_container_width=True, hide_index=True)
                
                total_delivered = completed_deliveries['num_delivered'].sum()
                st.metric("Total Plants Delivered (Completed Orders)", total_delivered)
            else:
                st.info("No delivery records found for completed orders")
        
        # Export option
        csv = filtered_orders.to_csv(index=False)
        st.download_button(
            "Download Archive CSV",
            csv,
            "archive.csv",
            "text/csv"
        )
    else:
        st.info("No completed orders in archive")

# Footer
st.sidebar.divider()
st.sidebar.caption("Tissue Culture Tracker v1.0")
st.sidebar.caption(f"Database: {DB_PATH}")
