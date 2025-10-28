#!/usr/bin/env python3

import argparse
import pandas as pd
import json
from jinja2 import Environment, FileSystemLoader

def load_data(file_path):
    # Leggi il CSV
    return pd.read_csv(file_path)


def create_html_page(df, output_file):
    # Filtra solo le righe con dati validi (consumo_settimanale non nullo)
    df = df[df['consumo_settimanale'].notna()].copy()

    # Prepara i dati per anno
    anni_disponibili = sorted(df['anno'].unique())
    print(f"📊 Anni disponibili: {', '.join(map(str, anni_disponibili))}")

    # Crea un dizionario con i dati per anno
    dati_per_anno = {}
    for anno in anni_disponibili:
        df_anno = df[df['anno'] == anno]
        dati_per_anno[str(anno)] = {
            'settimane': df_anno['settimana'].tolist(),
            'date': df_anno['data_centro'].tolist(),
            'consumo_giornaliero': df_anno['consumo_giornaliero'].round(2).tolist(),
            'consumo_settimanale': df_anno['consumo_settimanale'].round(2).tolist(),
            'giorni_coperti': df_anno['giorni_coperti'].tolist()
        }

    # Template HTML da file
    # Crea l'ambiente Jinja2 indicando dove trovare i template
    env = Environment(loader=FileSystemLoader("templates"))

    # Dati da passare al template
    context = {
        "dati_json": json.dumps(dati_per_anno, indent=2)
    }

    # Carica il template
    template = env.get_template("html_template.j2")
    # Renderizza il template con i dati
    output = template.render(context)

    # Salva il file HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)


def main():
    """Funzione principale"""
    # Configurazione argomenti da riga di comando
    parser = argparse.ArgumentParser(
        description='Crea una pagina HTML interattiva per visualizzare i consumi elettrici settimanali.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '-i', '--input',
        default='bollette_hera_riepilogo_processato.csv',
        help='Nome del file CSV con i dati (default: bollette_hera_riepilogo_processato.csv)'
    )
    parser.add_argument(
        '-o', '--html-output',
        default='bollette_hera_riepilogo_interattivo.html',
        help='Nome del file di output (default: bollette_hera_riepilogo_processato.html)'
    )
    
    args = parser.parse_args()
    csv_file = args.input

    try:
        # Carica i dati
        df = load_data(csv_file)

        # Crea la pagina HTML
        create_html_page(df, args.html_output)
        print(f"✅ File HTML generato con successo: {args.html_output}")

    except Exception as e:
        print(f"❌ Errore durante l'elaborazione: {e}")

if __name__ == "__main__":
    main()
    