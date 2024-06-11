import streamlit as st
import pandas as pd

# Funktion zum Laden der Zuordnungsdatei von Google Drive
def load_mapping(url):
    mapping_df = pd.read_csv(url, dtype={'Original_SKU': str, 'Mapped_SKU': str})
    return mapping_df

# Funktion zum Verarbeiten der hochgeladenen Datei
def process_file_fixed(sales_df, mapping_df):
    # Apply the mapping using the full SKU instead of SKU_prefix
    merged_df = sales_df.merge(mapping_df, how='left', left_on='SKU', right_on='Original_SKU')
    
    # Handle exclusions
    merged_df = merged_df[merged_df['Exclude'] != 'Yes']
    
    # Replace SKU with Mapped_SKU where applicable
    merged_df['Mapped_SKU'] = merged_df['Mapped_SKU'].fillna(merged_df['SKU'])
    
    # Group by the Mapped_SKU and sum the Anzahl column
    grouped_df = merged_df.groupby('Mapped_SKU', as_index=False)['Anzahl'].sum()
    
    # Format the 'Anzahl' column with a point as the thousand separator
    grouped_df['Anzahl'] = grouped_df['Anzahl'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
    
    return grouped_df

# URL der Zuordnungsdatei in Google Drive
mapping_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFPFGMjeiiONwFjegJjsGRPDjtkW8bHRfqJX92a4P9k7yGsYjHGKuvpA1QNNrAI4eugweXxaDSeSwv/pub?output=csv"

st.title("Datei-Uploader und Datenverarbeiter")

uploaded_file = st.file_uploader("Laden Sie eine Datei hoch", type=["xlsx"])

if uploaded_file is not None:
    mapping_df = load_mapping(mapping_url)
    sales_df = pd.read_excel(uploaded_file, skiprows=7)
    processed_data_fixed = process_file_fixed(sales_df, mapping_df)
    
    st.write("Verarbeitete Daten:")
    st.dataframe(processed_data_fixed)
    
    # Flüssigdünger und Krümelgranulat Kategorien
    fluessigduenger_skus = ['80522', '80523', '80524', '80525', '80528']
    kruemelgranulat_skus = ['80526', '80527']
    
    # Berechnung der Summen für jede Kategorie
    fluessigduenger_sum_fixed = processed_data_fixed[processed_data_fixed['Mapped_SKU'].isin(fluessigduenger_skus)]['Anzahl'].str.replace('.', '').astype(float).sum()
    kruemelgranulat_sum_fixed = processed_data_fixed[processed_data_fixed['Mapped_SKU'].isin(kruemelgranulat_skus)]['Anzahl'].str.replace('.', '').astype(float).sum()
    
    # Formatieren der Summen mit Punkt als Tausendertrennzeichen
    fluessigduenger_sum_formatted_fixed = f"{fluessigduenger_sum_fixed:,.0f}".replace(',', '.')
    kruemelgranulat_sum_formatted_fixed = f"{kruemelgranulat_sum_fixed:,.0f}".replace(',', '.')
    
    st.write(f"Gesamtsumme für Flüssigdünger (80522, 80523, 80524, 80525, 80528): {fluessigduenger_sum_formatted_fixed}")
    st.write(f"Gesamtsumme für Krümelgranulat (80526, 80527): {kruemelgranulat_sum_formatted_fixed}")
