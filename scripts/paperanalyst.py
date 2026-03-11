import os
import re
import time
import requests
import xml.etree.ElementTree as ET
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import pandas as pd

# Configuration
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
INPUT_DIR = "papers"
OUTPUT_DIR = "outputs"
TEI_DIR = os.path.join("data", "tei")
PARSED_DIR = os.path.join("data", "parsed")

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEI_DIR, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)


def process_paper(pdf_path):
    """Send a PDF to Grobid and return the XML response text."""
    for delay in [1, 2, 4, 8, 16]:
        try:
            with open(pdf_path, "rb") as f:
                files = {"input": f}
                response = requests.post(GROBID_URL, files=files, timeout=120)

            if response.status_code == 200 and response.text.strip():
                return response.text

            print(f"Error {response.status_code} for {pdf_path}")

        except Exception as e:
            print(f"Connection failed for {pdf_path}: {e}. Retrying in {delay}s...")
            time.sleep(delay)

    return None


def save_tei(xml_text, pdf_name):
    """Save TEI XML using the same base name as the PDF."""
    base_name = os.path.splitext(pdf_name)[0]
    tei_path = os.path.join(TEI_DIR, f"{base_name}.tei.xml")
    with open(tei_path, "w", encoding="utf-8") as f:
        f.write(xml_text)
    return tei_path


def clean_url(url):
    """Normalize and filter extracted URLs."""
    if not url:
        return None

    url = url.strip()

    # Remove whitespace/newlines inside URL
    url = re.sub(r"\s+", "", url)

    # Only keep plausible URLs
    if not (url.startswith("http://") or url.startswith("https://")):
        return None

    # Filter obvious broken fragments
    if len(url) < 12:
        return None

    # Filter links ending in clearly broken URL-encoded space
    if url.endswith("%20"):
        return None

    return url


def extract_data(xml_text):
    """Parse Grobid XML to find abstract, figure count, and links."""
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"XML parse error: {e}")
        return "", 0, []

    # Abstract
    abstract_nodes = root.findall(".//tei:abstract//tei:p", ns)
    abstract_parts = []
    for node in abstract_nodes:
        text = " ".join(node.itertext()).strip()
        if text:
            abstract_parts.append(text)
    abstract_text = " ".join(abstract_parts)

    # Figures
    figures = root.findall(".//tei:figure", ns)
    figure_count = len(figures)

    # Links
    raw_links = []

    for link_node in root.findall(".//tei:ptr[@target]", ns):
        target = link_node.get("target")
        if target:
            raw_links.append(target)

    for ref_node in root.findall(".//tei:ref[@type='url']", ns):
        target = ref_node.get("target")
        text = " ".join(ref_node.itertext()).strip()

        if target:
            raw_links.append(target)
        elif text:
            raw_links.append(text)

    # Clean + deduplicate while preserving order
    seen = set()
    unique_links = []
    for link in raw_links:
        cleaned = clean_url(link)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique_links.append(cleaned)

    return abstract_text, figure_count, unique_links


def save_tabular_outputs(stats, abstracts_data, links_rows):
    """Save CSV files with parsed results."""
    if stats:
        df_stats = pd.DataFrame(stats)
        df_stats.to_csv(os.path.join(OUTPUT_DIR, "figures_per_paper.csv"), index=False)
        print("Generated: outputs/figures_per_paper.csv")

    if abstracts_data:
        df_abstracts = pd.DataFrame(abstracts_data)
        df_abstracts.to_csv(os.path.join(PARSED_DIR, "abstracts.csv"), index=False)
        print("Generated: data/parsed/abstracts.csv")

    if links_rows:
        df_links = pd.DataFrame(links_rows)
        df_links.to_csv(os.path.join(PARSED_DIR, "links_per_paper.csv"), index=False)
        print("Generated: data/parsed/links_per_paper.csv")


def generate_wordcloud(all_abstracts):
    """Generate word cloud from all abstracts."""
    if not all_abstracts.strip():
        return

    custom_stopwords = STOPWORDS.union({
        "et", "al", "figure", "fig", "table", "tables",
        "section", "sections", "paper", "study", "results",
        "method", "methods", "using", "used"
    })

    wordcloud = WordCloud(
        width=800,
        height=400,
        background_color="white",
        stopwords=custom_stopwords
    ).generate(all_abstracts)

    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title("Keyword Cloud from Abstracts")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "wordcloud.png"))
    plt.close()
    print("Generated: outputs/wordcloud.png")


def generate_figures_chart(stats):
    """Generate bar chart of figures per paper."""
    df = pd.DataFrame(stats)
    if df.empty:
        return

    plt.figure(figsize=(12, 6))
    plt.bar(df["paper"], df["figures"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Number of Figures")
    plt.title("Figures per Article")
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, "figures_chart.png"))
    plt.close()
    print("Generated: outputs/figures_chart.png")


def save_links_txt(all_links):
    """Save human-readable text file with links per paper."""
    output_path = os.path.join(OUTPUT_DIR, "links_found.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for paper, links in all_links.items():
            f.write(f"Paper: {paper}\n")
            if links:
                for link in links:
                    f.write(f"  - {link}\n")
            else:
                f.write("  - No links found.\n")
            f.write("-" * 20 + "\n")
    print("Generated: outputs/links_found.txt")


def main():
    all_abstracts = ""
    stats = []
    all_links = {}
    abstracts_data = []
    links_rows = []

    if not os.path.exists(INPUT_DIR):
        print(f"Input directory not found: {INPUT_DIR}")
        return

    pdf_files = sorted([f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")])

    if not pdf_files:
        print(f"No PDF files found in {INPUT_DIR}")
        return

    print(f"Processing {len(pdf_files)} papers...")

    for pdf in pdf_files:
        print(f"--- Analyzing: {pdf} ---")
        path = os.path.join(INPUT_DIR, pdf)
        xml_result = process_paper(path)

        if not xml_result:
            print(f"Skipping {pdf} due to extraction failure.")
            continue

        tei_path = save_tei(xml_result, pdf)
        print(f"Saved TEI: {tei_path}")

        abstract, fig_count, links = extract_data(xml_result)

        all_abstracts += " " + abstract
        stats.append({"paper": pdf, "figures": fig_count})
        all_links[pdf] = links
        abstracts_data.append({"paper": pdf, "abstract": abstract})

        if links:
            for link in links:
                links_rows.append({"paper": pdf, "link": link})
        else:
            links_rows.append({"paper": pdf, "link": ""})

    generate_wordcloud(all_abstracts)
    generate_figures_chart(stats)
    save_links_txt(all_links)
    save_tabular_outputs(stats, abstracts_data, links_rows)


if __name__ == "__main__":
    main()