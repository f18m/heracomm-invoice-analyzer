# heracomm-invoice-analyzer

Household bill analyzer.
Developed for the HERAComm bill format.
Right now it only deals with **electricity** expenses. Natural gas will be added later.

## How to use 

1. Collect all bills you have in a single folder, in PDF format. 
The filenames do not matter and with the first Python script you will be able to do a bulk-rename.
This project only works with PDF files.

2. Run the first step:

```
./step1_invoice_analyzer.py --output-csv <step1out.csv>  <path-to-folder-with-all-bills>
```

This step will produce a CSV file with all important data extracted from PDF files.
Check the CSV file and validate for at least a couple of rows that extracted data is valid.

3. Run second step, interpolation:

```
./step2_interpolate.py --input step1out.csv --output step2out.csv
```

This step will produce another CSV file containign the data from step 1 interpolated so that
consumed energy is presented on a weekly-basis for all years where data is available.
Open the CSV file produced and try to check if it contains meaningful data.
E.g. sum all kWh consumed in a year and check the original PDF bill, the numbers won't be _identical_ but should be _close_ enough.

4. Run third step, data presentation layer:


```
./step3_create_html_page.py --input step2out.csv --output-html page.html
```

Open the HTML page produced and check it renders correctly in your browser.

And that's it :)

