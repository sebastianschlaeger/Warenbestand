import streamlit as st
import pandas as pd

def load_mapping(url):
    mapping_df = pd.read_csv(url, dtype={'Original_SKU': str, 'Mapped_SKU': str})
    return mapping_df

def process_file(file, mapping_df):
    df = pd.read_excel(file, skiprows=7)
    df['SKU_prefix'] = df['SKU'].astype(str).str[:5]
    df = df.merge(mapping_df, how='left', left_on='SKU_prefix', right_on='Original_SKU')
    df['Mapped_SKU'] = df['Mapped_SKU'].fillna(df['SKU_prefix'])
    df = df[df['Exclude'] != 'Yes']
    grouped_df = df.groupby('Mapped_SKU', as_index=False)['Anzahl'].sum()
    grouped_df['Anzahl'] = grouped_df['Anzahl'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
    return grouped_df

mapping_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRFPFGMjeiiONwFjegJjsGRPDjtkW8bHRfqJX92a4P9k7yGsYjHGKuvpA1QNNrAI4eugweXxaDSeSwv/pub?output=csv"

st.title("Datei-Uploader und Datenverarbeiter")

uploaded_file = st.file_uploader("Laden Sie eine Datei hoch", type=["xlsx"])

if uploaded_file is not None:
    mapping_df = load_mapping(mapping_url)
    processed_data = process_file(uploaded_file, mapping_df)
    
    st.write("Verarbeitete Daten:")
    st.dataframe(processed_data)

    fluessigduenger_skus = ['80522', '80523', '80524', '80525', '80528']
    kruemelgranulat_skus = ['80526', '80527']
    
    fluessigduenger_sum = processed_data[processed_data['Mapped_SKU'].isin(fluessigduenger_skus)]['Anzahl'].str.replace('.', '').astype(float).sum()
    kruemelgranulat_sum = processed_data[processed_data['Mapped_SKU'].isin(kruemelgranulat_skus)]['Anzahl'].str.replace('.', '').astype(float).sum()
    
    fluessigduenger_sum_formatted = f"{fluessigduenger_sum:,.0f}".replace(',', '.')
    kruemelgranulat_sum_formatted = f"{kruemelgranulat_sum:,.0f}".replace(',', '.')
    
    st.write(f"Gesamtsumme für Flüssigdünger (80522, 80523, 80524, 80525, 80528): {fluessigduenger_sum_formatted}")
    st.write(f"Gesamtsumme für Krümelgranulat (80526, 80527): {kruemelgranulat_sum_formatted}")
