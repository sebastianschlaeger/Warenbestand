import streamlit as st
import pandas as pd
import re

# Preise für etikettierte Ware (special SKUs removed)
ETIKETTIERTE_PREISE = {
    '80522': 3.10, '80523': 2.45, '80524': 2.55, '80525': 2.70, '80526': 2.55, 
    '80527': 2.65, '80528': 2.85, '80537': 2.31, '80538': 2.21, '80539': 2.6, 
    '80534': 2.85, '80536': 2.45, '8000': 3.4
}

# Preise für unetikettierte Ware (special SKUs added)
UNETIKETTIERTE_PREISE = {
    '80522': 2.20, '80523': 1.55, '80524': 1.65, '80525': 1.80, '80526': 1.65, 
    '80527': 1.75, '80528': 1.95, '1001': 117, '1002': 117, '1003': 117, '1004': 117, 
    '1005': 26.78, '2001': 74.4, '2002': 87.6, '3001': 0.38, '3002': 0.21, '3003': 0.22, 
    '3004': 0.47, '3005': 0.48, '3006': 0.99, '3007': 0.5, '3008': 1.05, '80537': 1.41, 
    '80538': 1.31, '80539': 1.7, '80534': 1.95, '80536': 1.55,
    '80510': 6.50, '80513': 2.95, '80511': 3.55, '80533': 13.50, '10520': 4.21, '10695': 2.42
}

# Mengen pro Palette
PALETTEN_MENGEN = {
    '80510': 72, '80513': 600, '80511': 144, '80522': 576, '80523': 576,
    '80524': 576, '80525': 576, '80526': 600, '80527': 600, '80528': 576,
    '80533': 100, '10520': 100, '10695': 100, '3001': 2720, '3002': 2040,
    '3003': 2720, '3004': 1360, '3005': 2000, '3006': 200, '3007': 2040,
    '3008': 400, '80537': 576, '80538': 576, '80539': 576, '80534': 576, '80536': 576
}

# Einheiten pro Karton für spezielle SKUs
EINHEITEN_PRO_KARTON = {
    '80522': 12, '80523': 12, '80524': 12, '80525': 12,
    '80526': 15, '80527': 15, '80528': 12, '80537': 12, '80538': 12, '80539': 12, '80534': 12, '80536': 12
}

# SKUs to exclude for etikettierte Ware
EXCLUDE_SKUS = {'80511', '80513', '80510', '80533', '10695', '10520'}

def extract_sku(value):
    text = str(value)
    match = re.search(r'\d+', text)
    if match:
        return match.group()
    return None

def berechne_menge(einzeln, paletten, sku):
    einzeln = float(einzeln) if pd.notna(einzeln) else 0
    paletten = float(paletten) if pd.notna(paletten) else 0
    
    if sku in PALETTEN_MENGEN:
        return paletten * PALETTEN_MENGEN[sku] + einzeln
    return einzeln

def process_etikettierte_ware(df):
    errors = []
    # Ignore the first three rows (since data starts from row 4)
    df = df.iloc[3:]
    df = df.reset_index(drop=True)
    
    df['SKU'] = df.iloc[:, 1].apply(extract_sku)
    df['Menge'] = pd.to_numeric(df.iloc[:, 2], errors='coerce')
    
    # Check for missing SKUs or quantities
    missing_data = df[df['SKU'].isna() | df['Menge'].isna()]
    if not missing_data.empty:
        for _, row in missing_data.iterrows():
            errors.append(f"Zeile {row.name + 4}: Fehlende SKU oder Menge")  # Add 4 to account for original Excel row number
    
    # Filter out excluded SKUs
    excluded_skus = df[df['SKU'].isin(EXCLUDE_SKUS)]
    if not excluded_skus.empty:
        for _, row in excluded_skus.iterrows():
            errors.append(f"SKU {row['SKU']} wurde ausgeschlossen (in EXCLUDE_SKUS)")
    df = df[~df['SKU'].isin(EXCLUDE_SKUS)]
    
    df = df.dropna(subset=['SKU', 'Menge'])
    inventory_summary = df.groupby('SKU')['Menge'].sum().reset_index()
    
    # Check for missing prices
    inventory_summary['Preis'] = inventory_summary['SKU'].map(ETIKETTIERTE_PREISE)
    missing_prices = inventory_summary[inventory_summary['Preis'].isna()]
    if not missing_prices.empty:
        for _, row in missing_prices.iterrows():
            errors.append(f"Fehlender Preis für SKU: {row['SKU']}")
    
    inventory_summary['Gesamtwert'] = inventory_summary['Menge'] * inventory_summary['Preis']
    inventory_summary = inventory_summary.dropna(subset=['Preis'])
    
    return inventory_summary, errors

def process_unetikettierte_ware(df):
    errors = []
    # Filter rows where column B (index 1) has an article number
    df = df[df.iloc[:, 1].notna()]
    
    # Convert SKU to string and remove decimal places
    df['SKU'] = df.iloc[:, 1].astype(str).apply(lambda x: x.split('.')[0])
    df['Einzeln'] = pd.to_numeric(df.iloc[:, 3], errors='coerce')
    df['Paletten'] = pd.to_numeric(df.iloc[:, 4], errors='coerce')
    
    # Check for missing or invalid data
    missing_data = df[df['SKU'].isna() | (df['Einzeln'].isna() & df['Paletten'].isna())]
    if not missing_data.empty:
        for _, row in missing_data.iterrows():
            errors.append(f"Zeile {row.name + 2}: Fehlende SKU oder ungültige Mengenangaben")
    
    df['Menge'] = df.apply(lambda row: berechne_menge(row['Einzeln'], row['Paletten'], row['SKU']), axis=1)
    df = df.dropna(subset=['SKU', 'Menge'])
    
    inventory_summary = df.groupby('SKU')['Menge'].sum().reset_index()
    
    # Check for missing prices
    inventory_summary['Preis'] = inventory_summary['SKU'].map(UNETIKETTIERTE_PREISE)
    missing_prices = inventory_summary[inventory_summary['Preis'].isna()]
    if not missing_prices.empty:
        for _, row in missing_prices.iterrows():
            errors.append(f"Fehlender Preis für SKU: {row['SKU']}")
    
    inventory_summary['Gesamtwert'] = inventory_summary['Menge'] * inventory_summary['Preis']
    inventory_summary = inventory_summary.dropna(subset=['Preis'])
    
    # Check for SKUs in PALETTEN_MENGEN that are not in the data
    unused_skus = set(PALETTEN_MENGEN.keys()) - set(inventory_summary['SKU'])
    for sku in unused_skus:
        errors.append(f"SKU {sku} ist in PALETTEN_MENGEN vorhanden, aber nicht in den Daten")
    
    return inventory_summary, errors

def main():
    st.title("Inventar-App")
    st.header("Excel-Upload und Inventarauswertung")
    
    ware_typ = st.radio("Wählen Sie den Warentyp:", ("Etikettierte Ware", "Unetikettierte Ware"))
    
    uploaded_file = st.file_uploader("Wählen Sie eine Excel-Datei", type="xlsx")
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success("Datei erfolgreich hochgeladen!")
            
            if ware_typ == "Etikettierte Ware":
                inventory_summary, errors = process_etikettierte_ware(df)
            else:
                inventory_summary, errors = process_unetikettierte_ware(df)
            
            if errors:
                st.subheader("Fehler und Warnungen")
                for error in errors:
                    st.warning(error)
            
            st.subheader("Zusammenfassung des Inventars")
            st.dataframe(inventory_summary)
            
            total_value = inventory_summary['Gesamtwert'].sum()
            st.subheader(f"Gesamtwert des Inventars: {total_value:.2f} €")
            
            st.subheader("Zusätzliche Statistiken")
            st.write(f"Anzahl unterschiedlicher SKUs: {len(inventory_summary)}")
            st.write(f"Gesamtanzahl aller Artikel: {inventory_summary['Menge'].sum():.0f}")
            avg_value = total_value / inventory_summary['Menge'].sum() if inventory_summary['Menge'].sum() > 0 else 0
            st.write(f"Durchschnittlicher Wert pro Artikel: {avg_value:.2f} €")
            
            st.subheader("Top 5 SKUs nach Gesamtwert")
            top_5_skus = inventory_summary.nlargest(5, 'Gesamtwert')
            st.bar_chart(top_5_skus.set_index('SKU')['Gesamtwert'])
            
        except Exception as e:
            st.error(f"Fehler beim Verarbeiten der Datei: {str(e)}")
            st.write("Bitte überprüfen Sie das Format Ihrer Excel-Datei und stellen Sie sicher, dass die Spalten die erwarteten Daten enthalten.")

    # Hinzugefügte Testzeile
    st.write("Das ist ein Test")

if __name__ == "__main__":
    main()
