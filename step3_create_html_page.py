#!/usr/bin/env python3

import argparse
import pandas as pd
import json
import calendar
from jinja2 import Environment, FileSystemLoader

def load_data(file_path):
    # Leggi il CSV
    # header atteso:
    #    anno,settimana,periodo_inizio,periodo_fine,consumo_giornaliero_kwh,consumo_settimanale_kwh,
    #    costo_materia_energia_settimana_eur,costo_totale_settimana_eur,giorni_coperti,num_periodi
    return pd.read_csv(file_path)


def create_html_page(df, output_file):
    # Filtra solo le righe con dati validi (consumo_settimanale non nullo)
    df = df[df['consumo_settimanale_kwh'].notna()].copy()

    # Prepara i dati per anno
    anni_disponibili = sorted(df['anno'].unique())
    print(f"📊 Anni disponibili: {', '.join(map(str, anni_disponibili))}")

    # Crea un dizionario con i dati per anno
    dati_per_anno = {}
    for anno in anni_disponibili:
        df_anno = df[df['anno'] == anno]
        dati_per_anno[str(anno)] = {
            'settimane': df_anno['settimana'].tolist(),
            'date': df_anno['periodo_inizio'].tolist(),
            'consumo_giornaliero_kwh': df_anno['consumo_giornaliero_kwh'].round(2).tolist(),
            'consumo_settimanale_kwh': df_anno['consumo_settimanale_kwh'].round(2).tolist(),
            'costo_materia_energia_settimana_eur': df_anno['costo_materia_energia_settimana_eur'].round(2).tolist(),
            'costo_totale_settimana_eur': df_anno['costo_totale_settimana_eur'].round(2).tolist(),
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


def create_yearly_html_page(df, output_file):
    """Crea una pagina HTML con un grafico annuale a doppio asse Y."""
    df_valid = df[
        df['consumo_settimanale_kwh'].notna() &
        df['costo_totale_settimana_eur'].notna() &
        df['giorni_coperti'].notna()
    ].copy()

    yearly = (
        df_valid.groupby('anno', as_index=False)
        .agg({
            'costo_totale_settimana_eur': 'sum',
            'consumo_settimanale_kwh': 'sum',
            'giorni_coperti': 'sum'
        })
        .sort_values('anno')
    )

    yearly['giorni_anno'] = yearly['anno'].apply(lambda y: 366 if calendar.isleap(int(y)) else 365)
    yearly['copertura_percento'] = (yearly['giorni_coperti'] / yearly['giorni_anno']) * 100

    # Include solo anni con copertura > 90%
    yearly = yearly[yearly['copertura_percento'] > 90].copy()

    yearly_data = {
        'anni': yearly['anno'].astype(int).tolist(),
        'costi_totali_eur': yearly['costo_totale_settimana_eur'].round(2).tolist(),
        'consumi_totali_kwh': yearly['consumo_settimanale_kwh'].round(2).tolist(),
        'copertura_percento': yearly['copertura_percento'].round(1).tolist(),
    }

    env = Environment(loader=FileSystemLoader("templates"))
    context = {
        "yearly_json": json.dumps(yearly_data, indent=2)
    }

    template = env.get_template("html_yearly_template.j2")
    output = template.render(context)

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
        '-o', '--output-html',
        default='bollette_hera_riepilogo_interattivo.html',
        help='Nome del file di output (default: bollette_hera_riepilogo_processato.html)'
    )
    parser.add_argument(
        '--output-yearly-html',
        default='bollette_hera_riepilogo_annuale.html',
        help='Nome del file HTML annuale (default: bollette_hera_riepilogo_annuale.html)'
    )
    
    args = parser.parse_args()
    csv_file = args.input

    try:
        # Carica i dati
        df = load_data(csv_file)

        # Crea la pagina HTML
        create_html_page(df, args.output_html)
        print(f"✅ File HTML generato con successo: {args.output_html}")

        # Crea la pagina HTML annuale con doppio asse Y
        create_yearly_html_page(df, args.output_yearly_html)
        print(f"✅ File HTML annuale generato con successo: {args.output_yearly_html}")

    except Exception as e:
        print(f"❌ Errore durante l'elaborazione: {e}")

if __name__ == "__main__":
    main()
    