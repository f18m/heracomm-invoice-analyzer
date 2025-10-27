#!/usr/bin/env python3

import pandas as pd
import json

# Leggi il CSV
df = pd.read_csv('bollette_hera_riepilogo_processato.csv')

# Filtra solo le righe con dati validi (consumo_settimanale non nullo)
df = df[df['consumo_settimanale'].notna()].copy()

# Prepara i dati per anno
anni_disponibili = sorted(df['anno'].unique())

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

# Template HTML
html_template = '''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analisi Consumi Elettrici</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .controls {
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .control-group label {
            font-weight: 600;
            color: #495057;
            font-size: 1.1em;
        }
        
        .control-group select {
            padding: 12px 20px;
            font-size: 1em;
            border: 2px solid #667eea;
            border-radius: 10px;
            background: white;
            color: #495057;
            cursor: pointer;
            transition: all 0.3s ease;
            min-width: 150px;
        }
        
        .control-group select:hover {
            border-color: #764ba2;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        
        .control-group select:focus {
            outline: none;
            border-color: #764ba2;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .stats {
            padding: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            background: #f8f9fa;
        }
        
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }
        
        .stat-card h3 {
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 5px;
        }
        
        .stat-card .unit {
            color: #718096;
            font-size: 0.9em;
        }
        
        .chart-container {
            padding: 30px;
        }
        
        #chart {
            width: 100%;
            height: 500px;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .stats {
                grid-template-columns: 1fr;
            }
            
            #chart {
                height: 400px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Analisi Consumi Elettrici</h1>
            <p>Visualizzazione interattiva dei consumi settimanali</p>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <label for="anno-select">Seleziona Anno:</label>
                <select id="anno-select">
                    <!-- Opzioni generate dinamicamente -->
                </select>
            </div>
        </div>
        
        <div class="stats" id="stats">
            <!-- Statistiche generate dinamicamente -->
        </div>
        
        <div class="chart-container">
            <div id="chart"></div>
        </div>
    </div>
    
    <script>
        const datiPerAnno = ''' + json.dumps(dati_per_anno, indent=2) + ''';
        
        const annoSelect = document.getElementById('anno-select');
        const statsContainer = document.getElementById('stats');
        
        // Popola la combobox degli anni
        Object.keys(datiPerAnno).sort((a, b) => b - a).forEach(anno => {
            const option = document.createElement('option');
            option.value = anno;
            option.textContent = anno;
            annoSelect.appendChild(option);
        });
        
        function calcolaStatistiche(dati) {
            const consumiSettimanali = dati.consumo_settimanale.filter(c => c > 0);
            const consumiGiornalieri = dati.consumo_giornaliero.filter(c => c > 0);
            
            const totale = consumiSettimanali.reduce((a, b) => a + b, 0);
            const media = totale / consumiSettimanali.length;
            const max = Math.max(...consumiSettimanali);
            const min = Math.min(...consumiSettimanali);
            const mediaGiornaliera = consumiGiornalieri.reduce((a, b) => a + b, 0) / consumiGiornalieri.length;
            
            return {
                totale: totale.toFixed(2),
                media: media.toFixed(2),
                max: max.toFixed(2),
                min: min.toFixed(2),
                mediaGiornaliera: mediaGiornaliera.toFixed(2),
                settimane: consumiSettimanali.length
            };
        }
        
        function aggiornaStatistiche(dati) {
            const stats = calcolaStatistiche(dati);
            
            statsContainer.innerHTML = `
                <div class="stat-card">
                    <h3>Consumo Totale</h3>
                    <div class="value">${stats.totale}</div>
                    <div class="unit">kWh</div>
                </div>
                <div class="stat-card">
                    <h3>Media Settimanale</h3>
                    <div class="value">${stats.media}</div>
                    <div class="unit">kWh/settimana</div>
                </div>
                <div class="stat-card">
                    <h3>Media Giornaliera</h3>
                    <div class="value">${stats.mediaGiornaliera}</div>
                    <div class="unit">kWh/giorno</div>
                </div>
                <div class="stat-card">
                    <h3>Massimo Settimanale</h3>
                    <div class="value">${stats.max}</div>
                    <div class="unit">kWh</div>
                </div>
                <div class="stat-card">
                    <h3>Minimo Settimanale</h3>
                    <div class="value">${stats.min}</div>
                    <div class="unit">kWh</div>
                </div>
                <div class="stat-card">
                    <h3>Settimane con Dati</h3>
                    <div class="value">${stats.settimane}</div>
                    <div class="unit">settimane</div>
                </div>
            `;
        }
        
        function aggiornaGrafico(anno) {
            const dati = datiPerAnno[anno];
            
            const trace1 = {
                x: dati.settimane,
                y: dati.consumo_settimanale,
                type: 'bar',
                name: 'Consumo Settimanale',
                marker: {
                    color: dati.consumo_settimanale,
                    colorscale: 'Viridis',
                    showscale: true,
                    colorbar: {
                        title: 'kWh'
                    }
                },
                text: dati.consumo_settimanale.map(c => c.toFixed(2) + ' kWh'),
                hovertemplate: '<b>Settimana %{x}</b><br>' +
                               'Data: %{customdata}<br>' +
                               'Consumo: %{y:.2f} kWh<br>' +
                               '<extra></extra>',
                customdata: dati.date
            };
            
            const trace2 = {
                x: dati.settimane,
                y: dati.consumo_giornaliero,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Consumo Giornaliero Medio',
                yaxis: 'y2',
                line: {
                    color: '#ff6b6b',
                    width: 3
                },
                marker: {
                    size: 8,
                    color: '#ff6b6b'
                },
                hovertemplate: '<b>Settimana %{x}</b><br>' +
                               'Media giornaliera: %{y:.2f} kWh/giorno<br>' +
                               '<extra></extra>'
            };
            
            const layout = {
                title: {
                    text: `Consumi Elettrici - Anno ${anno}`,
                    font: { size: 24, color: '#2d3748' }
                },
                xaxis: {
                    title: 'Settimana dell\'Anno',
                    gridcolor: '#e2e8f0',
                    tickmode: 'linear',
                    tick0: 1,
                    dtick: 2
                },
                yaxis: {
                    title: 'Consumo Settimanale (kWh)',
                    gridcolor: '#e2e8f0',
                    side: 'left'
                },
                yaxis2: {
                    title: 'Consumo Giornaliero Medio (kWh/giorno)',
                    overlaying: 'y',
                    side: 'right',
                    gridcolor: '#fee',
                    showgrid: false
                },
                hovermode: 'x unified',
                showlegend: true,
                legend: {
                    x: 0.01,
                    y: 0.99,
                    bgcolor: 'rgba(255,255,255,0.8)',
                    bordercolor: '#e2e8f0',
                    borderwidth: 1
                },
                plot_bgcolor: '#f7fafc',
                paper_bgcolor: 'white',
                margin: { t: 60, r: 80, b: 60, l: 80 }
            };
            
            const config = {
                responsive: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            };
            
            Plotly.newPlot('chart', [trace1, trace2], layout, config);
            aggiornaStatistiche(dati);
        }
        
        // Event listener per il cambio anno
        annoSelect.addEventListener('change', (e) => {
            aggiornaGrafico(e.target.value);
        });
        
        // Inizializza con l'anno più recente
        if (Object.keys(datiPerAnno).length > 0) {
            const anniOrdinati = Object.keys(datiPerAnno).sort((a, b) => b - a);
            annoSelect.value = anniOrdinati[0];
            aggiornaGrafico(anniOrdinati[0]);
        }
    </script>
</body>
</html>
'''

# Salva il file HTML
with open('bollette_hera_riepilogo_interattivo.html', 'w', encoding='utf-8') as f:
    f.write(html_template)

print("✅ File HTML generato con successo: consumi_elettrici.html")
print(f"📊 Anni disponibili: {', '.join(map(str, anni_disponibili))}")
