import streamlit as st
import pandas as pd
import io

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

def main():
    st.title("Inventar-App")

    # Seitenleiste für die Navigation
    page = st.sidebar.selectbox("Wählen Sie eine Seite", ["SKU-Eingabe", "Excel-Upload"])

    if page == "SKU-Eingabe":
        sku_input()
    elif page == "Excel-Upload":
        excel_upload()

def sku_input():
    st.header("SKU-Eingabe")
    
    # Erstellen oder Laden der Inventardaten
    if 'inventory_data' not in st.session_state:
        st.session_state.inventory_data = pd.DataFrame(columns=['SKU', 'Preis'])

    # Formular für neue Einträge
    with st.form("new_entry"):
        new_sku = st.text_input("SKU (erste 5 Ziffern)")
        submitted = st.form_submit_button("Hinzufügen")
        
        if submitted:
            if len(new_sku) == 5 and new_sku.isdigit():
                if new_sku in SKU_COSTS:
                    price = SKU_COSTS[new_sku]
                    new_data = pd.DataFrame({'SKU': [new_sku], 'Preis': [price]})
                    st.session_state.inventory_data = pd.concat([st.session_state.inventory_data, new_data], ignore_index=True)
                    st.success(f"Eintrag hinzugefügt! SKU: {new_sku}, Preis: {price} €")
                else:
                    st.error(f"SKU {new_sku} nicht in der Preisliste gefunden.")
            else:
                st.error("Bitte geben Sie eine gültige 5-stellige SKU ein.")

    # Anzeige der aktuellen Daten
    st.subheader("Aktuelles Inventar")
    st.dataframe(st.session_state.inventory_data)

    # Berechnung des Gesamtwertes
    total_value = st.session_state.inventory_data['Preis'].sum()
    st.write(f"Gesamtwert des Inventars: {total_value:.2f} €")

def excel_upload():
    st.header("Excel-Upload")
    
    uploaded_file = st.file_uploader("Wählen Sie eine Excel-Datei", type="xlsx")
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            st.success("Datei erfolgreich hochgeladen!")
            
            # Verarbeitung der Daten
            df['SKU_5'] = df['SKU'].astype(str).str[:5]
            inventory_summary = df.groupby('SKU_5')['Menge'].sum().reset_index()
            
            # Berechnung des Gesamtwertes
            inventory_summary['Preis'] = inventory_summary['SKU_5'].map(SKU_COSTS)
            inventory_summary['Gesamtwert'] = inventory_summary['Menge'] * inventory_summary['Preis']
            
            # Entfernen von Zeilen, wo kein Preis gefunden wurde
            inventory_summary = inventory_summary.dropna(subset=['Preis'])
            
            st.subheader("Zusammenfassung des Inventars")
            st.dataframe(inventory_summary)
            
            total_value = inventory_summary['Gesamtwert'].sum()
            st.write(f"Gesamtwert des Inventars: {total_value:.2f} €")
            
        except Exception as e:
            st.error(f"Fehler beim Verarbeiten der Datei: {e}")

if __name__ == "__main__":
    main()
