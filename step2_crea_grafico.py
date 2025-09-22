#!/usr/bin/env python3

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from datetime import datetime, timedelta
import argparse
import warnings
warnings.filterwarnings('ignore')

def load_and_process_data(csv_file):
    """Carica e processa i dati dal file CSV"""
    df = pd.read_csv(csv_file)
    
    # Converte le date in formato datetime
    df['Periodo Inizio'] = pd.to_datetime(df['Periodo Inizio'])
    df['Periodo Fine'] = pd.to_datetime(df['Periodo Fine'])
    
    # Calcola il punto medio del periodo
    df['Data Media'] = df['Periodo Inizio'] + (df['Periodo Fine'] - df['Periodo Inizio']) / 2
    
    # Calcola i giorni del periodo
    df['Giorni Periodo'] = (df['Periodo Fine'] - df['Periodo Inizio']).dt.days + 1
    
    # Calcola il consumo medio giornaliero
    df['Consumo Giornaliero'] = df['Consumo Totale (kWh)'] / df['Giorni Periodo']
    
    return df

def get_week_dates(year):
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

def distribute_uniform_consumption(df, year):
    """Distribuisce uniformemente i consumi dei periodi nelle settimane corrispondenti"""
    # Filtra i dati per periodi che intersecano l'anno specificato
    # Include periodi che:
    # - iniziano nell'anno specificato, oppure
    # - finiscono nell'anno specificato, oppure
    # - iniziano prima e finiscono dopo (attraversano tutto l'anno)
    year_start = datetime(year, 1, 1)
    year_end = datetime(year, 12, 31)
    
    year_data = df[
        (df['Periodo Inizio'] <= year_end) & 
        (df['Periodo Fine'] >= year_start)
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
        periodo_start = periodo['Periodo Inizio']
        periodo_end = periodo['Periodo Fine']
        consumo_giornaliero = periodo['Consumo Giornaliero']
        
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
            avg_daily = 0
            weekly_consumption = 0
            
            # Cerca le settimane più vicine con dati
            neighbor_values = []
            for offset in range(1, 27):  # Cerca fino a 26 settimane prima/dopo
                for direction in [-1, 1]:
                    neighbor_week = week_num + (offset * direction)
                    if 1 <= neighbor_week <= 52 and neighbor_week in weekly_results:
                        neighbor_data = weekly_results[neighbor_week]
                        if neighbor_data['giorni_totali_coperti'] > 0:
                            neighbor_avg = neighbor_data['consumo_totale_settimana'] / neighbor_data['giorni_totali_coperti']
                            neighbor_values.append(neighbor_avg)
                            break
                if len(neighbor_values) >= 2:  # Usa al massimo 2 vicini
                    break
            
            if neighbor_values:
                avg_daily = np.mean(neighbor_values)
                weekly_consumption = avg_daily * 7
        
        results.append({
            'settimana': week_num,
            'data_centro': data['data_centro'],
            'consumo_giornaliero': max(0, avg_daily),
            'consumo_settimanale': max(0, weekly_consumption),
            'giorni_coperti': data['giorni_totali_coperti'],
            'num_periodi': len(data['periodi_che_intersecano'])
        })
    
    return pd.DataFrame(results)

def create_interactive_plot(df, csv_file):
    """Crea il grafico interattivo con selezione dell'anno"""
    
    # Ottieni gli anni disponibili nei dati
    years = sorted(df['Periodo Inizio'].dt.year.unique())
    
    # Crea subplot con assi y secondari
    fig = make_subplots(
        rows=1, cols=1,
        specs=[[{"secondary_y": True}]]
    )
    
    # Crea le tracce per ogni anno
    traces_weekly = []
    traces_daily = []
    
    for year in years:
        weekly_data = distribute_uniform_consumption(df, year)
        
        if weekly_data is not None:
            # Traccia consumo settimanale
            trace_weekly = go.Scatter(
                x=weekly_data['settimana'],
                y=weekly_data['consumo_settimanale'],
                mode='lines+markers',
                name=f'Consumo Settimanale {year}',
                visible=(year == years[0]),  # Solo il primo anno visibile inizialmente
                line=dict(width=3),
                marker=dict(size=8),
                customdata=weekly_data[['giorni_coperti', 'num_periodi']],
                hovertemplate=
                    f'<b>Anno {year}</b><br>' +
                    'Settimana: %{x}<br>' +
                    'Consumo Settimanale: %{y:.1f} kWh<br>' +
                    'Giorni con dati: %{customdata[0]}/7<br>' +
                    'Periodi intersecanti: %{customdata[1]}<br>' +
                    '<extra></extra>'
            )
            
            # Traccia consumo giornaliero medio
            trace_daily = go.Scatter(
                x=weekly_data['settimana'],
                y=weekly_data['consumo_giornaliero'],
                mode='lines+markers',
                name=f'Consumo Giornaliero Medio {year}',
                visible=(year == years[0]),
                line=dict(width=2, dash='dash'),
                marker=dict(size=6),
                yaxis='y2',
                customdata=weekly_data[['giorni_coperti', 'num_periodi']],
                hovertemplate=
                    f'<b>Anno {year}</b><br>' +
                    'Settimana: %{x}<br>' +
                    'Consumo Giornaliero: %{y:.1f} kWh/giorno<br>' +
                    'Giorni con dati: %{customdata[0]}/7<br>' +
                    'Periodi intersecanti: %{customdata[1]}<br>' +
                    '<extra></extra>'
            )
            
            traces_weekly.append(trace_weekly)
            traces_daily.append(trace_daily)
    
    # Aggiungi tutte le tracce
    for trace in traces_weekly:
        fig.add_trace(trace, secondary_y=False)
    
    for trace in traces_daily:
        fig.add_trace(trace, secondary_y=True)
    
    # Crea i bottoni per selezionare l'anno
    buttons = []
    for i, year in enumerate(years):
        visibility = [False] * len(traces_weekly) * 2
        visibility[i] = True  # Traccia settimanale
        visibility[len(traces_weekly) + i] = True  # Traccia giornaliera
        
        buttons.append(
            dict(
                label=str(year),
                method="update",
                args=[{"visible": visibility},
                     {"title": f"Consumi Elettrici - Anno {year} (Distribuzione Uniforme)"}]
            )
        )
    
    # Configura il layout
    fig.update_layout(
        title=f"Consumi Elettrici - Anno {years[0]} (Distribuzione Uniforme)",
        xaxis_title="Settimana dell'Anno",
        updatemenus=[
            dict(
                type="dropdown",
                direction="down",
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.15,
                yanchor="top",
                buttons=buttons
            )
        ],
        annotations=[
            dict(
                text="Seleziona Anno:",
                showarrow=False,
                x=0.02,
                y=1.18,
                xref="paper",
                yref="paper",
                align="left",
                font=dict(size=14)
            )
        ],
        height=600,
        showlegend=True,
        legend=dict(x=0.7, y=1.15, orientation="h"),
        hovermode='x unified'
    )
    
    # Configura gli assi
    fig.update_xaxes(
        range=[0, 53],
        dtick=4,
        title_text="Settimana dell'Anno"
    )
    
    fig.update_yaxes(
        title_text="<b>Consumo Settimanale (kWh)</b>",
        secondary_y=False,
        showgrid=True
    )
    
    fig.update_yaxes(
        title_text="<b>Consumo Giornaliero Medio (kWh/giorno)</b>",
        secondary_y=True,
        showgrid=False
    )
    
    return fig

def main():
    """Funzione principale"""
    # Configurazione argomenti da riga di comando
    parser = argparse.ArgumentParser(
        description='Analizza i consumi elettrici e crea grafici settimanali interattivi',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python script.py                          # Usa file default 'consumi_elettrici.csv'
  python script.py -f consumi.csv          # Specifica file CSV personalizzato
  python script.py --no-open               # Non apre automaticamente il browser
        """
    )
    
    parser.add_argument(
        '-f', '--file',
        default='bollette_hera_riepilogo.csv',
        help='Nome del file CSV con i dati (default: bollette_hera_riepilogo.csv)'
    )
    
    parser.add_argument(
        '-o', '--output',
        default='bollette_hera_riepilogo_interattivo.html',
        help='Nome del file di output (default: bollette_hera_riepilogo_interattivo.html)'
    )
    
    parser.add_argument(
        '--no-open',
        action='store_true',
        help='Non aprire automaticamente il browser'
    )
    
    args = parser.parse_args()
    csv_file = args.file
    
    try:
        print("Caricamento dati...")
        df = load_and_process_data(csv_file)
        print(f"Dati caricati: {len(df)} record dal {df['Periodo Inizio'].min().strftime('%Y-%m-%d')} al {df['Periodo Fine'].max().strftime('%Y-%m-%d')}")
        
        print("\nModalità: DISTRIBUZIONE UNIFORME")
        print("- I consumi vengono distribuiti uniformemente all'interno di ogni periodo")
        print("- Le settimane che intersecano più periodi sommano i contributi proporzionali")
        print("- I periodi che attraversano più anni vengono divisi correttamente")
        print("- Le settimane senza dati usano la media delle settimane vicine")
        
        print("\nCreazione grafico interattivo...")
        fig = create_interactive_plot(df, csv_file)

        print(f"Salvataggio grafico come '{args.output}'...")
        pyo.plot(fig, filename=args.output, auto_open=not args.no_open)

        if not args.no_open:
            print("Grafico aperto nel browser...")
        
        # Stampa statistiche di base
        print("\n" + "="*50)
        print("STATISTICHE GENERALI")
        print("="*50)
        print(f"Consumo totale medio giornaliero: {df['Consumo Giornaliero'].mean():.2f} kWh/giorno")
        print(f"Consumo totale massimo giornaliero: {df['Consumo Giornaliero'].max():.2f} kWh/giorno")
        print(f"Consumo totale minimo giornaliero: {df['Consumo Giornaliero'].min():.2f} kWh/giorno")
        
        # Statistiche per anno
        df['Anno'] = df['Periodo Inizio'].dt.year
        yearly_stats = df.groupby('Anno').agg({
            'Consumo Giornaliero': ['mean', 'std'],
            'Consumo Totale (kWh)': 'sum',
            'Giorni Periodo': 'sum'
        }).round(2)
        
        print("\nSTATISTICHE PER ANNO")
        print("-" * 50)
        for year in yearly_stats.index:
            mean_daily = yearly_stats.loc[year, ('Consumo Giornaliero', 'mean')]
            std_daily = yearly_stats.loc[year, ('Consumo Giornaliero', 'std')]
            total_yearly = yearly_stats.loc[year, ('Consumo Totale (kWh)', 'sum')]
            total_days = yearly_stats.loc[year, ('Giorni Periodo', 'sum')]
            print(f"Anno {year}: Media {mean_daily:.2f} ± {std_daily:.2f} kWh/giorno")
            print(f"          Totale: {total_yearly:.1f} kWh in {total_days} giorni coperti")
        
        # Informazioni sui periodi di fatturazione
        print("\nINFORMAZIONI PERIODI DI FATTURAZIONE")
        print("-" * 50)
        for year in sorted(df['Anno'].unique()):
            year_data = df[df['Anno'] == year]
            num_periods = len(year_data)
            avg_period_length = year_data['Giorni Periodo'].mean()
            coverage = (year_data['Giorni Periodo'].sum() / 365.25) * 100
            print(f"Anno {year}: {num_periods} periodi, durata media {avg_period_length:.1f} giorni, copertura {coverage:.1f}%")
        
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