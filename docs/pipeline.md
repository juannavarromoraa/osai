# Pipeline Description

The pipeline processes scientific papers using the **GROBID full-text parsing API**.

## Workflow

The analysis pipeline performs the following steps:

1. Input PDF papers are stored in the `papers/` directory.
2. Each paper is sent to the GROBID API.
3. GROBID converts the PDF into **TEI XML** format.
4. The TEI XML is parsed to extract:
   - abstract text
   - number of figures
   - external links
5. Results are aggregated and exported as datasets and visualisations.

## Generated Outputs

The pipeline generates the following outputs:

- `outputs/wordcloud.png`
- `outputs/figures_chart.png`
- `outputs/figures_per_paper.csv`
- `outputs/links_found.txt`

Intermediate datasets are stored in:
