import streamlit as st
import pandas as pd
import sqlite3
from st_aggrid import AgGrid, GridOptionsBuilder
from datetime import datetime

# Function to load the mapping file from Google Drive
def load_mapping(url):
    mapping_df = pd.read_csv(url, dtype={'Original_SKU': str, 'Mapped_SKU': str})
    return mapping_df

# Function to process the uploaded file
def process_file(file, mapping_df):
    df = pd.read_excel(file, skiprows=7)
    df['SKU_prefix'] = df['SKU'].astype(str).str[:5]
    df = df.merge(mapping_df, how='left', left_on='SKU_prefix', right_on='Original_SKU')
    df = df[df['Exclude'] != 'Yes']
    df['Mapped_SKU'] = df['Mapped_SKU'].fillna(df['SKU_prefix'])
    grouped_df = df.groupby('Mapped_SKU', as_index=False)['Anzahl'].sum()
    return grouped_df

# Function to create a connection to the SQLite database
def get_connection():
    conn = sqlite3.connect('inventory.db')
    return conn

# Function to create or update the inventory table
def create_or_update_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            stock INTEGER,
            ordered_quantity INTEGER,
            arrival_date TEXT
        )
    ''')
    c.execute("PRAGMA table_info(inventory)")
    columns = [info[1] for info in c.fetchall()]
    if 'ordered_quantity' not in columns:
        c.execute("ALTER TABLE inventory ADD COLUMN ordered_quantity INTEGER")
    if 'arrival_date' not in columns:
        c.execute("ALTER TABLE inventory ADD COLUMN arrival_date TEXT")
    conn.commit()
    conn.close()

# Function to update inventory in the database
def update_inventory(sku, stock, ordered_quantity, arrival_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO inventory (sku, stock, ordered_quantity, arrival_date)
        VALUES (?, ?, ?, ?)
    ''', (sku, stock, ordered_quantity, arrival_date))
    conn.commit()
    conn.close()

# Function to load inventory from the database
def load_inventory():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT sku, stock, ordered_quantity, arrival_date FROM inventory')
    data = c.fetchall()
    conn.close()
    inventory_df = pd.DataFrame(data, columns=['SKU', 'Stock', 'Ordered_Quantity', 'Arrival_Date'])
    return inventory_df

# URL of the mapping file on Google Drive
mapping_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFPFGMjeiiONwFjegJjsGRPDjtkW8bHRfqJX92a4P9k7yGsYjHGKuvpA1QNNrAI4eugweXxaDSeSwv/pub?output=csv"

st.title("File Uploader and Data Processor")

uploaded_file = st.file_uploader("Upload a file", type=["xlsx"])

create_or_update_table()

if uploaded_file is not None:
    mapping_df = load_mapping(mapping_url)
    processed_data = process_file(uploaded_file, mapping_df)
    
    st.write("Processed Data:")
    st.dataframe(processed_data)
    
    # Define categories
    fluessigduenger_skus = ['80522', '80523', '80524', '80525', '80528']
    kruemelgranulat_skus = ['80526', '80527']
    
    # Calculate sums for each category
    fluessigduenger_sum = processed_data[processed_data['Mapped_SKU'].isin(fluessigduenger_skus)]['Anzahl'].sum()
    kruemelgranulat_sum = processed_data[processed_data['Mapped_SKU'].isin(kruemelgranulat_skus)]['Anzahl'].sum()
    
    st.write(f"Total for Liquid Fertilizer (80522, 80523, 80524, 80525, 80528): {fluessigduenger_sum}")
    st.write(f"Total for Granular Fertilizer (80526, 80527): {kruemelgranulat_sum}")
    
    st.write("Current Inventory:")
    try:
        inventory_df = load_inventory()
    except Exception as e:
        st.error(f"Error loading inventory: {e}")
        inventory_df = pd.DataFrame(columns=['SKU', 'Stock', 'Ordered_Quantity', 'Arrival_Date'])
    
    # Ensure all SKUs from processed_data are included
    all_skus_df = pd.DataFrame({'SKU': processed_data['Mapped_SKU']}).drop_duplicates()
    inventory_df = all_skus_df.merge(inventory_df, how='left', on='SKU')
    
    # Merge inventory data with processed data
    merged_df = processed_data.merge(inventory_df, how='left', left_on='Mapped_SKU', right_on='SKU')
    
    # Calculate usage and stock details
    merged_df['Verbrauch_30_Tage'] = merged_df['Anzahl']
    merged_df['Stock'] = merged_df['Stock'].fillna(0)
    merged_df['Ordered_Quantity'] = merged_df['Ordered_Quantity'].fillna(0)
    merged_df['Arrival_Date'] = pd.to_datetime(merged_df['Arrival_Date'], errors='coerce')
    
    current_date = datetime.now()
    merged_df['Verbrauch_pro_Tag'] = merged_df['Verbrauch_30_Tage'] / 30
    merged_df['Verbrauch_bis_Ankunft'] = (merged_df['Arrival_Date'] - current_date).dt.days * merged_df['Verbrauch_pro_Tag']
    merged_df['Verbrauch_bis_Ankunft'] = merged_df['Verbrauch_bis_Ankunft'].apply(lambda x: max(x, 0))
    merged_df['Bestand_bei_Ankunft'] = merged_df.apply(lambda row: row['Stock'] + row['Ordered_Quantity'] - row['Verbrauch_bis_Ankunft'] if pd.notnull(row['Arrival_Date']) and row['Arrival_Date'] > current_date else row['Stock'], axis=1)
    merged_df['Reichweite_in_Tagen'] = merged_df.apply(lambda row: round(row['Bestand_bei_Ankunft'] / row['Verbrauch_pro_Tag'], 0) if row['Verbrauch_pro_Tag'] > 0 else 0, axis=1)
    
    # Create editable inventory table
    gb = GridOptionsBuilder.from_dataframe(merged_df)
    gb.configure_pagination()
    gb.configure_side_bar()
    gb.configure_default_column(editable=True)
    grid_options = gb.build()
    
    grid_response = AgGrid(
        merged_df,
        gridOptions=grid_options,
        update_mode='MODEL_CHANGED',
        editable=True
    )
    
    updated_df = grid_response['data']
    
    if st.button("Save Inventory"):
        for index, row in updated_df.iterrows():
            # Ensure Arrival_Date is properly handled
            arrival_date_str = None
            if isinstance(row['Arrival_Date'], pd.Timestamp):
                if pd.notnull(row['Arrival_Date']):
                    arrival_date_str = row['Arrival_Date'].strftime('%Y-%m-%d')
            
            # Debugging prints to verify values
            print(f"Updating SKU: {row['Mapped_SKU']} - Stock: {row['Stock']} - Ordered Quantity: {row['Ordered_Quantity']} - Arrival Date: {arrival_date_str}")
            
            update_inventory(row['Mapped_SKU'], row['Stock'], row['Ordered_Quantity'], arrival_date_str)
        
        st.success("Inventory saved!")
    
    st.write("Saved Inventory and Range:")
    st.dataframe(merged_df[['Mapped_SKU', 'Stock', 'Ordered_Quantity', 'Arrival_Date', 'Reichweite_in_Tagen']])
