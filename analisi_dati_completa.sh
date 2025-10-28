#!/bin/bash

FOLDER="${1:-./francesco-electricity}"

echo "Selected folder: ${FOLDER}"

./step1_analizza_bollette_hera.py ${FOLDER} \
    --output-csv ${FOLDER}/bollette_hera_riepilogo.csv

./step2_interpolazione.py \
    --input ${FOLDER}/bollette_hera_riepilogo.csv \
    --output-csv ${FOLDER}/bollette_hera_riepilogo_processato.csv

./step3_crea_pagina_html.py \
    --input ${FOLDER}/bollette_hera_riepilogo_processato.csv \
    --output-html ${FOLDER}/bollette_hera_riepilogo_interattivo.html
