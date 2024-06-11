import streamlit as st
import pandas as pd
import requests

# Funktion zum Laden der Zuordnungsdatei von GitHub
def load_mapping(url):
    mapping_df = pd.read_csv(url)
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

# URL der Zuordnungsdatei in Ihrem GitHub-Repository
mapping_url = "https://github.com/sebastianschlaeger/Purgruen-Warenbestand/blob/main/sku_mapping.csv"

# Laden der Zuordnungsdatei
mapping_df = load_mapping(mapping_url)

st.title("Datei-Uploader und Datenverarbeiter")

uploaded_file = st.file_uploader("Laden Sie eine Datei hoch", type=["xlsx"])

if uploaded_file is not None:
    processed_data = process_file(uploaded_file, mapping_df)
    st.write("Verarbeitete Daten:")
    st.dataframe(processed_data)
