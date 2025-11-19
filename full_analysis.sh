#!/bin/bash

FOLDER="${1:-./francesco-electricity}"

echo "Selected folder: ${FOLDER}"

./step1_invoice_analyzer.py ${FOLDER} \
    --output-csv ${FOLDER}/bollette_hera_riepilogo.csv

./step2_interpolate.py \
    --input ${FOLDER}/bollette_hera_riepilogo.csv \
    --output-csv ${FOLDER}/bollette_hera_riepilogo_processato.csv

./step3_create_html_page.py \
    --input ${FOLDER}/bollette_hera_riepilogo_processato.csv \
    --output-html ${FOLDER}/bollette_hera_riepilogo_interattivo.html
