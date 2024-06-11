import streamlit as st
import pandas as pd

def process_file(file):
    # Skip the first 7 rows and read the relevant data into a new dataframe
    df = pd.read_excel(file, skiprows=7)
    
    # Extract the first 5 characters of the SKU
    df['SKU_prefix'] = df['SKU'].astype(str).str[:5]
    
    # Group by the SKU_prefix and sum the Anzahl column
    grouped_df = df.groupby('SKU_prefix', as_index=False)['Anzahl'].sum()
    
    return grouped_df

st.title("Datei-Uploader und Datenverarbeiter")

uploaded_file = st.file_uploader("Laden Sie eine Datei hoch", type=["xlsx"])

if uploaded_file is not None:
    processed_data = process_file(uploaded_file)
    st.write("Verarbeitete Daten:")
    st.dataframe(processed_data)
