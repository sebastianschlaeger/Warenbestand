import streamlit as st
import pandas as pd
import re

# Vorgegebene Kosten pro SKU
SKU_COSTS = {
    '80510': 6.50,
    '80513': 2.95,
    '80511': 3.55,
    '80522': 3.10,
    '80523': 2.45,
    '80524': 2.55,
    '80525': 2.70,
    '80526': 2.55,
    '80527': 2.65,
    '80528': 2.85,
    '80533': 13.50,
    '10520': 4.21,
    '10695': 2.42
}

def extract_sku(text):
    # Extrahiert die ersten 5 Ziffern nach dem ersten Auftreten von 5 aufeinanderfolgenden Ziffern
    match = re.search(r'\d{5}', text)
    if match:
        return match.group()[:5]
    return None

def main():
    st.title("Inventar-App")
    st.header("Excel-Upload und Inventarauswertung")
    
    uploaded_file = st.file_uploader("Wählen Sie eine Excel-Datei", type="xlsx")
    
    if uploaded_file is not None:
        process_excel_file(uploaded_file)

def process_excel_file(uploaded_file):
    try:
        # Lesen der Excel-Datei
        df = pd.read_excel(uploaded_file)
        st.success("Datei erfolgreich hochgeladen!")
        
        # Extrahieren der SKU aus Spalte D und der Menge aus Spalte G
        df['SKU_5'] = df.iloc[:, 3].apply(extract_sku)  # Spalte D ist Index 3
        df['Menge'] = df.iloc[:, 6]  # Spalte G ist Index 6
        
        # Gruppieren nach SKU und Summieren der Mengen
        inventory_summary = df.groupby('SKU_5')['Menge'].sum().reset_index()
        
        # Berechnung des Gesamtwertes
        inventory_summary['Preis'] = inventory_summary['SKU_5'].map(SKU_COSTS)
        inventory_summary['Gesamtwert'] = inventory_summary['Menge'] * inventory_summary['Preis']
        
        # Entfernen von Zeilen, wo kein Preis gefunden wurde
        inventory_summary = inventory_summary.dropna(subset=['Preis'])
        
        # Anzeigen der Zusammenfassung
        st.subheader("Zusammenfassung des Inventars")
        st.dataframe(inventory_summary)
        
        # Berechnung und Anzeige des Gesamtwertes
        total_value = inventory_summary['Gesamtwert'].sum()
        st.subheader(f"Gesamtwert des Inventars: {total_value:.2f} €")
        
        # Zusätzliche Statistiken
        st.subheader("Zusätzliche Statistiken")
        st.write(f"Anzahl unterschiedlicher SKUs: {len(inventory_summary)}")
        st.write(f"Gesamtanzahl aller Artikel: {inventory_summary['Menge'].sum()}")
        st.write(f"Durchschnittlicher Wert pro Artikel: {(total_value / inventory_summary['Menge'].sum()):.2f} €")
        
        # Visualisierung: Top 5 SKUs nach Gesamtwert
        st.subheader("Top 5 SKUs nach Gesamtwert")
        top_5_skus = inventory_summary.nlargest(5, 'Gesamtwert')
        st.bar_chart(top_5_skus.set_index('SKU_5')['Gesamtwert'])
        
    except Exception as e:
        st.error(f"Fehler beim Verarbeiten der Datei: {e}")

if __name__ == "__main__":
    main()
