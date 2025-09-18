#!/usr/bin/env python3

import zipfile
import os
import re
import fitz  # PyMuPDF
import pandas as pd
import openpyxl
from openpyxl.chart import LineChart, Reference
import argparse
import sys
from datetime import datetime, timedelta

def estrai_dati_bolletta(pdf_path):
    """Estrae i dati richiesti da una singola bolletta PDF Hera"""
    with fitz.open(pdf_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()

    # Nome file
    nome_file = os.path.basename(pdf_path)

    # Periodo (inizio e fine)
    periodo_match = re.search(r"Periodo: dal (\d{2}\.\d{2}\.\d{4}) al (\d{2}\.\d{2}\.\d{4})", text)
    if periodo_match:
        periodo_inizio = periodo_match.group(1)
        periodo_fine = periodo_match.group(2)
    else:
        periodo_inizio = periodo_fine = None

    # Consumi per fasce e totale
    consumi_match = re.search(
        r"Consumo fatturato.*?([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*kWh", text, re.DOTALL
    )
    if consumi_match:
        consumo_f1 = float(consumi_match.group(1).replace(",", "."))
        consumo_f23 = float(consumi_match.group(2).replace(",", "."))
        consumo_tot = float(consumi_match.group(3).replace(",", "."))
    else:
        consumo_f1 = consumo_f23 = consumo_tot = None

    # Totale energia elettrica (escludendo gas e altri servizi)
    elettricita_match = re.search(r"Totale bolletta/contratto\s+([\d,]+)", text)
    if elettricita_match:
        totale_elettricita = float(elettricita_match.group(1).replace(",", "."))
    else:
        totale_elettricita = None

    return {
        "File": nome_file,
        "Periodo Inizio": periodo_inizio,
        "Periodo Fine": periodo_fine,
        "Consumo F1 (kWh)": consumo_f1,
        "Consumo F2+F3 (kWh)": consumo_f23,
        "Consumo Totale (kWh)": consumo_tot,
        "Totale Energia (€)": totale_elettricita,
    }


def aggiungi_grafici(excel_path):
    """Aggiunge grafici di consumi e costi all'Excel"""
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active

    # Creiamo una colonna con i periodi come etichette (Periodo Inizio - Periodo Fine)
    for i in range(2, ws.max_row + 1):
        periodo = f"{ws.cell(row=i, column=2).value} - {ws.cell(row=i, column=3).value}"
        ws.cell(row=i, column=8, value=periodo)

    cats = Reference(ws, min_col=8, min_row=2, max_row=ws.max_row)

    # === Grafico Consumi ===
    chart_consumi = LineChart()
    chart_consumi.title = "Andamento Consumi"
    chart_consumi.y_axis.title = "kWh"
    chart_consumi.x_axis.title = "Periodo"

    data_consumi = Reference(ws, min_col=6, min_row=1, max_row=ws.max_row)  # Consumo Totale
    chart_consumi.add_data(data_consumi, titles_from_data=True)
    chart_consumi.set_categories(cats)

    ws.add_chart(chart_consumi, "J2")

    # === Grafico Costi ===
    chart_costi = LineChart()
    chart_costi.title = "Andamento Costi Energia"
    chart_costi.y_axis.title = "Euro"
    chart_costi.x_axis.title = "Periodo"

    data_costi = Reference(ws, min_col=7, min_row=1, max_row=ws.max_row)  # Totale Energia
    chart_costi.add_data(data_costi, titles_from_data=True)
    chart_costi.set_categories(cats)

    ws.add_chart(chart_costi, "J20")

    wb.save(excel_path)
    print(f"📊 Grafici aggiunti a {excel_path}")

def controlla_copertura(df):
    """Verifica se ci sono buchi temporali tra le bollette"""
    # Conversione delle date
    df["Periodo Inizio"] = pd.to_datetime(df["Periodo Inizio"], format="%d.%m.%Y")
    df["Periodo Fine"] = pd.to_datetime(df["Periodo Fine"], format="%d.%m.%Y")

    # Ordinamento cronologico
    df = df.sort_values("Periodo Inizio").reset_index(drop=True)

    gaps = []
    for i in range(1, len(df)):
        prev_end = df.loc[i-1, "Periodo Fine"]
        curr_start = df.loc[i, "Periodo Inizio"]

        if curr_start > prev_end + timedelta(days=1):
            gaps.append((prev_end + timedelta(days=1), curr_start - timedelta(days=1)))

    return gaps

def main():
    parser = argparse.ArgumentParser(description="Estrai dati dalle bollette Hera e crea un Excel riepilogativo con grafici.")
    parser.add_argument("input_path", help="Percorso di un file ZIP di bollette o di una cartella contenente PDF")
    parser.add_argument("-o", "--output", default="bollette_hera_riepilogo.xlsx", help="Nome del file Excel di output")

    args = parser.parse_args()

    input_path = args.input_path
    output_excel = args.output

    # Se è uno ZIP -> estraiamo i file
    if zipfile.is_zipfile(input_path):
        extract_dir = "bollette_pdf"
        with zipfile.ZipFile(input_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        pdf_dir = extract_dir
    elif os.path.isdir(input_path):
        pdf_dir = input_path
    else:
        print("❌ Errore: devi fornire uno ZIP valido o una cartella contenente PDF.")
        sys.exit(1)

    # Elaborazione dei PDF
    dati_bollette = []
    for filename in sorted(os.listdir(pdf_dir)):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(pdf_dir, filename)
            dati = estrai_dati_bolletta(pdf_path)
            dati_bollette.append(dati)

    if not dati_bollette:
        print("❌ Nessun PDF trovato.")
        sys.exit(1)

    # Creazione DataFrame e salvataggio Excel
    df = pd.DataFrame(dati_bollette)
    df.to_excel(output_excel, index=False)
    print(f"✅ File Excel creato: {output_excel}")
    
    
    buchi = controlla_copertura(df)
    if buchi:
        print("⚠️ Trovati periodi non coperti:")
        for inizio, fine in buchi:
            print(f"   - dal {inizio.date()} al {fine.date()}")
    else:
        print("✅ Nessun buco temporale: le bollette coprono l’intero periodo senza interruzioni.")
        
        
    # Aggiunta grafici
    aggiungi_grafici(output_excel)


if __name__ == "__main__":
    main()

