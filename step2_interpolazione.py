#!/usr/bin/env python3

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import warnings

def load_and_process_data(csv_file: str):
    """Carica e processa i dati dal file CSV"""
    df = pd.read_csv(csv_file)
    
    # Converte le date in formato datetime
    df['periodo_inizio'] = pd.to_datetime(df['periodo_inizio'])
    df['periodo_fine'] = pd.to_datetime(df['periodo_fine'])
    print(f"Dati caricati: {len(df)} record dal {df['periodo_inizio'].min().strftime('%Y-%m-%d')} al {df['periodo_fine'].max().strftime('%Y-%m-%d')}")
    
    # Calcola il punto medio del periodo
    df['data_media'] = df['periodo_inizio'] + (df['periodo_fine'] - df['periodo_inizio']) / 2
    
    # Calcola i giorni del periodo
    df['giorni_periodo'] = (df['periodo_fine'] - df['periodo_inizio']).dt.days + 1
    
    # Calcola il consumo medio giornaliero
    df['consumo_giornaliero_kwh'] = df['consumo_totale_kwh'] / df['giorni_periodo']
    
    # Informazioni sui periodi di fatturazione
    print("\nINFORMAZIONI PERIODI DI FATTURAZIONE")
    print("-" * 50)
    df['Anno'] = df['periodo_inizio'].dt.year
    for year in sorted(df['Anno'].unique()):
        year_data = df[df['Anno'] == year]
        num_periods = len(year_data)
        avg_period_length = year_data['giorni_periodo'].mean()
        coverage = (year_data['giorni_periodo'].sum() / 365.25) * 100
        print(f"Anno {year}: {num_periods} periodi, durata media {avg_period_length:.1f} giorni, copertura {coverage:.1f}%")

    return df

def get_week_dates(year: int):
    """Restituisce le date di inizio e fine per ogni settimana dell'anno"""
    weeks = []
    
    # Trova il primo lunedì dell'anno
    first_day = datetime(year, 1, 1)
    days_ahead = 0 - first_day.weekday()  # Lunedì è 0
    if days_ahead <= 0:
        days_ahead += 7
    first_monday = first_day + timedelta(days=days_ahead)
    
    # Se il primo gennaio è già un lunedì o è nella prima settimana
    if first_day.weekday() < 4:  # Se è da lunedì a giovedì
        first_monday = first_day - timedelta(days=first_day.weekday())
    
    current_monday = first_monday
    week_num = 1
    
    while current_monday.year <= year and week_num <= 52:
        week_end = current_monday + timedelta(days=6)
        
        # Assicurati che la settimana non vada oltre l'anno
        if week_end.year > year:
            week_end = datetime(year, 12, 31)
        
        weeks.append({
            'settimana': week_num,
            'inizio': current_monday,
            'fine': week_end,
            'centro': current_monday + timedelta(days=3)
        })
        
        current_monday += timedelta(days=7)
        week_num += 1
        
        # Ferma se la nuova settimana inizierebbe nell'anno successivo
        if current_monday.year > year:
            break
    
    return weeks

def distribute_uniform_consumption(df, year: int):
    """Distribuisce uniformemente i consumi dei periodi nelle settimane corrispondenti"""
    # Filtra i dati per periodi che intersecano l'anno specificato
    # Include periodi che:
    # - iniziano nell'anno specificato, oppure
    # - finiscono nell'anno specificato, oppure
    # - iniziano prima e finiscono dopo (attraversano tutto l'anno)
    year_start = datetime(year, 1, 1)
    year_end = datetime(year, 12, 31)
    
    year_data = df[
        (df['periodo_inizio'] <= year_end) & 
        (df['periodo_fine'] >= year_start)
    ].copy()
    
    if len(year_data) == 0:
        return None
    
    # Ottieni le settimane per l'anno
    weeks = get_week_dates(year)
    
    # Inizializza i risultati
    weekly_results = {}
    for week in weeks:
        weekly_results[week['settimana']] = {
            'settimana': week['settimana'],
            'data_centro': week['centro'],
            'consumo_totale_settimana': 0,
            'giorni_totali_coperti': 0,
            'periodi_che_intersecano': []
        }
    
    # Per ogni periodo, distribuisce il consumo nelle settimane che interseca
    for _, periodo in year_data.iterrows():
        periodo_start = periodo['periodo_inizio']
        periodo_end = periodo['periodo_fine']
        consumo_giornaliero = periodo['consumo_giornaliero_kwh']
        
        # Limita il periodo all'anno corrente per il calcolo
        periodo_start_year = max(periodo_start, year_start)
        periodo_end_year = min(periodo_end, year_end)
        
        # Se il periodo non interseca effettivamente l'anno, salta
        if periodo_start_year > periodo_end_year:
            continue
        
        # Trova tutte le settimane che intersecano questo periodo (limitato all'anno)
        for week in weeks:
            week_start = week['inizio']
            week_end = week['fine']
            
            # Calcola l'intersezione tra periodo (limitato all'anno) e settimana
            intersection_start = max(periodo_start_year, week_start)
            intersection_end = min(periodo_end_year, week_end)
            
            if intersection_start <= intersection_end:
                # Calcola i giorni di intersezione
                giorni_intersezione = (intersection_end - intersection_start).days + 1
                
                # Aggiungi il consumo di questi giorni alla settimana
                consumo_settimana = consumo_giornaliero * giorni_intersezione
                
                weekly_results[week['settimana']]['consumo_totale_settimana'] += consumo_settimana
                weekly_results[week['settimana']]['giorni_totali_coperti'] += giorni_intersezione
                weekly_results[week['settimana']]['periodi_che_intersecano'].append({
                    'periodo_id': periodo.name,
                    'periodo_start': periodo_start.strftime('%Y-%m-%d'),
                    'periodo_end': periodo_end.strftime('%Y-%m-%d'),
                    'giorni': giorni_intersezione,
                    'consumo': consumo_settimana
                })
    
    # Calcola i consumi finali per ogni settimana
    results = []
    for week_num, data in weekly_results.items():
        if data['giorni_totali_coperti'] > 0:
            # Il consumo totale della settimana è la somma dei consumi dei giorni coperti
            weekly_consumption = data['consumo_totale_settimana']
            
            # Il consumo medio giornaliero è calcolato sui giorni effettivamente coperti
            avg_daily = weekly_consumption / data['giorni_totali_coperti']
            
            # Se la settimana non è completamente coperta (meno di 7 giorni),
            # estrapola il consumo per tutta la settimana
            if data['giorni_totali_coperti'] < 7:
                weekly_consumption = avg_daily * 7
        else:
            # Se non ci sono dati per questa settimana, usa la media delle settimane vicine
            avg_daily = None
            weekly_consumption = None
            
            # # Cerca le settimane più vicine con dati
            # neighbor_values = []
            # for offset in range(1, 27):  # Cerca fino a 26 settimane prima/dopo
            #     for direction in [-1, 1]:
            #         neighbor_week = week_num + (offset * direction)
            #         if 1 <= neighbor_week <= 52 and neighbor_week in weekly_results:
            #             neighbor_data = weekly_results[neighbor_week]
            #             if neighbor_data['giorni_totali_coperti'] > 0:
            #                 neighbor_avg = neighbor_data['consumo_totale_settimana'] / neighbor_data['giorni_totali_coperti']
            #                 neighbor_values.append(neighbor_avg)
            #                 break
            #     if len(neighbor_values) >= 2:  # Usa al massimo 2 vicini
            #         break
            
            # if neighbor_values:
            #     avg_daily = np.mean(neighbor_values)
            #     weekly_consumption = avg_daily * 7
        
        results.append({
            'anno': year,
            'settimana': week_num,
            'data_centro': data['data_centro'],
            'consumo_giornaliero': avg_daily,
            'consumo_settimanale': weekly_consumption,
            'giorni_coperti': data['giorni_totali_coperti'],
            'num_periodi': len(data['periodi_che_intersecano'])
        })
    
    return pd.DataFrame(results)

def process_all_years(df: pd.DataFrame):
    """Processa i dati anno per anno"""
    
    # Ottieni gli anni disponibili nei dati
    years = sorted(df['periodo_inizio'].dt.year.unique())

    # Crea le tracce per ogni anno
    results = []
    for year in years:
        weekly_data = distribute_uniform_consumption(df, year)
        if weekly_data is not None:
            results.append(weekly_data)
    #return pd.DataFrame(results)
    return pd.concat(results, ignore_index=True)

def generate_summary(interp_df: pd.DataFrame):

    # Statistiche per settimana
    weekly_stats_all_years = interp_df.groupby('settimana').agg({
        'consumo_giornaliero': ['mean', 'std'],
        'consumo_settimanale': ['mean', 'std'],
        'giorni_coperti': 'mean'
    }).round(2)
    
    print("\nSTATISTICHE PER SETTIMANA")
    print("-" * 50)
    for week in weekly_stats_all_years.index:
        mean_daily = weekly_stats_all_years.loc[week, ('consumo_giornaliero', 'mean')]
        std_daily = weekly_stats_all_years.loc[week, ('consumo_giornaliero', 'std')]
        mean_weekly = weekly_stats_all_years.loc[week, ('consumo_settimanale', 'mean')]
        std_weekly = weekly_stats_all_years.loc[week, ('consumo_settimanale', 'std')]
        #total_yearly = weekly_stats_all_years.loc[year, ('Consumo Totale (kWh)', 'sum')]
        #total_days = weekly_stats_all_years.loc[year, ('giorni_periodo', 'sum')]
        print(f"Settimana {week}: Media {mean_daily:.2f} ± {std_daily:.2f} kWh/giorno; Media {mean_weekly:.2f} ± {std_weekly:.2f} kWh/settimana")
        #print(f"          Totale: {total_yearly:.1f} kWh in {total_days} giorni coperti")
    
    # Statistiche per anno
    yearly_stats = interp_df.groupby('anno').agg({
        'consumo_giornaliero': ['sum'],
        'consumo_settimanale': ['sum'],
        'giorni_coperti': 'sum'
    }).round(2)
    
    print("\nSTATISTICHE PER ANNO")
    print("-" * 50)
    for year in yearly_stats.index:
        # this is not accurate because not for all weeks we have full-week coverage, 7 days long:
        #consumo_totale1 = yearly_stats.loc[year, ('consumo_giornaliero', 'sum')] * 7

        consumo_totale2 = yearly_stats.loc[year, ('consumo_settimanale', 'sum')]
        giorni_coperti = yearly_stats.loc[year, ('giorni_coperti', 'sum')]
        print(f"Anno {year}: Consumo totale: {consumo_totale2:.2f} kWh [copertura: {giorni_coperti}gg]")

    print(yearly_stats.to_html(index=False))

def main():
    """Funzione principale"""
    # Configurazione argomenti da riga di comando
    parser = argparse.ArgumentParser(
        description='Analizza i consumi elettrici e crea una interpolazione settimanale uniforme',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '-i', '--input',
        default='bollette_hera_riepilogo.csv',
        help='Nome del file CSV con i dati (default: bollette_hera_riepilogo.csv)'
    )
    parser.add_argument(
        '-o', '--csv-output',
        default='bollette_hera_riepilogo_processato.csv',
        help='Nome del file di output (default: bollette_hera_riepilogo_processato.csv)'
    )
    
    args = parser.parse_args()
    csv_file = args.input

    try:
        print("Caricamento dati da '{}'...".format(csv_file))
        df = load_and_process_data(csv_file)
        
        print("\nProcessamento dati...")
        print("\nModalità: DISTRIBUZIONE UNIFORME")
        print("- I consumi vengono distribuiti uniformemente all'interno di ogni periodo")
        print("- Le settimane che intersecano più periodi sommano i contributi proporzionali")
        print("- I periodi che attraversano più anni vengono divisi correttamente")
        print("- Le settimane senza dati usano la media delle settimane vicine")
        interp_df = process_all_years(df)
        
        # save to disk as CSV the dataframe
        interp_df.to_csv(args.csv_output, index=False)
        print(f"✅ File CSV creato: {args.csv_output}")

        # stats
        generate_summary(interp_df)

        print("\n" + "="*50)
        print("COMPLETATO CON SUCCESSO!")
        print("="*50)
        
    except FileNotFoundError:
        print(f"ERRORE: File '{csv_file}' non trovato.")
        print("Assicurati che il file CSV sia nella directory corrente.")
        print("Usa l'opzione -f per specificare un percorso diverso.")
    except Exception as e:
        print(f"ERRORE durante l'esecuzione: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()