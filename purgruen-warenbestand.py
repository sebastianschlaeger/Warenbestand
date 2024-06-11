import streamlit as st
import pandas as pd
import sqlite3
from st_aggrid import AgGrid, GridOptionsBuilder
from datetime import datetime

# Funktion zum Laden der Zuordnungsdatei von Google Drive
def load_mapping(file_path):
    mapping_df = pd.read_csv(file_path, dtype={'Original_SKU': str, 'Mapped_SKU': str})
    return mapping_df

# Funktion zum Verarbeiten der hochgeladenen Datei
def process_file(file, mapping_df):
    # Skip the first 7 rows and read the relevant data into a new dataframe
    df = pd.read_excel(file, skiprows=7)
    
    # Extract the first 5 characters of the SKU
    df['SKU_prefix'] = df['SKU'].astype(str).str[:5]
    
    # Apply the mapping
    df = df.merge(mapping_df, how='left', left_on='SKU_prefix', right_on='Original_SKU')
    
    # Handle exclusions
    df = df[df['Exclude'] != 'Yes']
    
    # Replace SKU_prefix with Mapped_SKU where applicable
    df['Mapped_SKU'] = df['Mapped_SKU'].fillna(df['SKU_prefix'])
    
    # Group by the Mapped_SKU and sum the Anzahl column
    grouped_df = df.groupby('Mapped_SKU', as_index=False)['Anzahl'].sum()
    
    return grouped_df

# Funktion zum Erstellen einer Verbindung zur SQLite-Datenbank
def get_connection():
    conn = sqlite3.connect('inventory.db')
    return conn

# Funktion zum Erstellen oder Aktualisieren der Tabelle für den Warenbestand
def create_or_update_table():
    conn = get_connection()
    c = conn.cursor()
    # Erstellen der Tabelle, falls sie nicht existiert
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT PRIMARY KEY,
            stock INTEGER,
            ordered_quantity INTEGER,
            arrival_date TEXT
        )
    ''')
    # Überprüfen und Hinzufügen fehlender Spalten
    c.execute("PRAGMA table_info(inventory)")
    columns = [info[1] for info in c.fetchall()]
    if 'ordered_quantity' not in columns:
        c.execute("ALTER TABLE inventory ADD COLUMN ordered_quantity INTEGER")
    if 'arrival_date' not in columns:
        c.execute("ALTER TABLE inventory ADD COLUMN arrival_date TEXT")
    conn.commit()
    conn.close()

# Funktion zum Speichern oder Aktualisieren des Warenbestands in der Datenbank
def update_inventory(sku, stock, ordered_quantity, arrival_date):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO inventory (sku, stock, ordered_quantity, arrival_date)
        VALUES (?, ?, ?, ?)
    ''', (sku, stock, ordered_quantity, arrival_date))
    conn.commit()
    conn.close()

# Funktion zum Laden des Warenbestands aus der Datenbank
def load_inventory():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT sku, stock, ordered_quantity, arrival_date FROM inventory')
    data = c.fetchall()
    conn.close()
    inventory_df = pd.DataFrame(data, columns=['SKU', 'Stock', 'Ordered_Quantity', 'Arrival_Date'])
    return inventory_df

# Datei-Pfade
mapping_file_path = '/mnt/data/sku_mapping - Tabellenblatt1.csv'
sales_file_path = '/mnt/data/salesbyarticle (54).xlsx'

st.title("Datei-Uploader und Datenverarbeiter")

uploaded_file = st.file_uploader("Laden Sie eine Datei hoch", type=["xlsx"])

create_or_update_table()

if uploaded_file is not None:
    mapping_df = load_mapping(mapping_file_path)
    processed_data = process_file(uploaded_file, mapping_df)
    
    st.write("Verarbeitete Daten:")
    st.dataframe(processed_data)
    
    # Flüssigdünger und Krümelgranulat Kategorien
    fluessigduenger_skus = ['80522', '80523', '80524', '80525', '80528']
    kruemelgranulat_skus = ['80526', '80527']
    
    # Berechnung der Summen für jede Kategorie
    fluessigduenger_sum = processed_data[processed_data['Mapped_SKU'].isin(fluessigduenger_skus)]['Anzahl'].sum()
    kruemelgranulat_sum = processed_data[processed_data['Mapped_SKU'].isin(kruemelgranulat_skus)]['Anzahl'].sum()
    
    st.write(f"Gesamtsumme für Flüssigdünger (80522, 80523, 80524, 80525, 80528): {fluessigduenger_sum}")
    st.write(f"Gesamtsumme für Krümelgranulat (80526, 80527): {kruemelgranulat_sum}")
    
    st.write("Aktueller Warenbestand:")

    try:
        inventory_df = load_inventory()
    except Exception as e:
        st.error(f"Fehler beim Laden des Warenbestands: {e}")
        inventory_df = pd.DataFrame(columns=['SKU', 'Stock', 'Ordered_Quantity', 'Arrival_Date'])
    
    # Zusammenführen der Bestandsdaten mit den verarbeiteten Daten
    merged_df = processed_data.merge(inventory_df, how='left', left_on='Mapped_SKU', right_on='SKU')
    
    # Berechnung der Reichweite in Tagen
    merged_df['Verbrauch_30_Tage'] = merged_df['Anzahl']
    merged_df['Stock'] = merged_df['Stock'].fillna(0)
    merged_df['Ordered_Quantity'] = merged_df['Ordered_Quantity'].fillna(0)
    merged_df['Arrival_Date'] = pd.to_datetime(merged_df['Arrival_Date'], errors='coerce')
    
    # Berücksichtigung der bestellten Menge für die Berechnung der Reichweite
    current_date = datetime.now()
    merged_df['Verbrauch_pro_Tag'] = merged_df['Verbrauch_30_Tage'] / 30
    merged_df['Verbrauch_bis_Ankunft'] = (merged_df['Arrival_Date'] - current_date).dt.days * merged_df['Verbrauch_pro_Tag']
    merged_df['Verbrauch_bis_Ankunft'] = merged_df['Verbrauch_bis_Ankunft'].apply(lambda x: max(x, 0))  # Negative Werte auf 0 setzen
    merged_df['Bestand_bei_Ankunft'] = merged_df.apply(lambda row: row['Stock'] + row['Ordered_Quantity'] - row['Verbrauch_bis_Ankunft'] if pd.notnull(row['Arrival_Date']) and row['Arrival_Date'] > current_date else row['Stock'], axis=1)
    merged_df['Reichweite_in_Tagen'] = merged_df.apply(lambda row: round(row['Bestand_bei_Ankunft'] / row['Verbrauch_pro_Tag'], 0) if row['Verbrauch_pro_Tag'] > 0 else 0, axis=1)
    
    # Erstellen der Tabelle zur Bearbeitung der Bestandsdaten
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
    
    if st.button("Bestände speichern"):
        for index, row in updated_df.iterrows():
            update_inventory(row['Mapped_SKU'], row['Stock'], row['Ordered_Quantity'], row['Arrival_Date'].strftime('%Y-%m-%d
