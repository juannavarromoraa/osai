import os
import requests
import xml.etree.ElementTree as ET
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pandas as pd
import time

# Configuration
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
INPUT_DIR = "input"
OUTPUT_DIR = "output"

# Ensure output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)


def process_paper(pdf_path):
    """Sends a PDF to Grobid and returns the XML response text."""
    # Exponential backoff retry logic (Best practice from slides)
    for delay in [1, 2, 4, 8, 16]:
        try:
            with open(pdf_path, 'rb') as f:
                files = {'input': f}
                # We use processFulltextDocument to get abstracts, figures, and links
                response = requests.post(GROBID_URL, files=files, timeout=60)
                if response.status_code == 200:
                    return response.text
                else:
                    print(f"Error {response.status_code} for {pdf_path}")
        except Exception as e:
            print(f"Connection failed for {pdf_path}, retrying in {delay}s...")
            time.sleep(delay)
    return None


def extract_data(xml_text):
    """Parses Grobid XML to find abstract, figure count, and links."""
    # The XML uses the TEI namespace
    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    root = ET.fromstring(xml_text)

    # 1. Extract Abstract Text
    abstract_nodes = root.findall(".//tei:abstract//tei:p", ns)
    abstract_text = " ".join([node.text for node in abstract_nodes if node.text])

    # 2. Count Figures
    # Grobid marks figures with <figure> tags
    figures = root.findall(".//tei:figure", ns)
    figure_count = len(figures)

    # 3. Extract Links
    # Links are usually in <ptr target="..."> or <ref type="url">
    links = []
    for link_node in root.findall(".//tei:ptr[@target]", ns):
        links.append(link_node.get('target'))
    for ref_node in root.findall(".//tei:ref[@type='url']", ns):
        links.append(ref_node.get('target') or ref_node.text)

    return abstract_text, figure_count, list(set(links))


def main():
    all_abstracts = ""
    stats = []
    all_links = {}

    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.pdf')]
    print(f"Processing {len(pdf_files)} papers...")

    for pdf in pdf_files:
        print(f"--- Analyzing: {pdf} ---")
        path = os.path.join(INPUT_DIR, pdf)
        xml_result = process_paper(path)

        if xml_result:
            abstract, fig_count, links = extract_data(xml_result)
            all_abstracts += " " + abstract
            stats.append({'paper': pdf, 'figures': fig_count})
            all_links[pdf] = links
        else:
            print(f"Skipping {pdf} due to extraction failure.")

    # --- Task 1: Word Cloud ---
    if all_abstracts.strip():
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(all_abstracts)
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title("Keyword Cloud from Abstracts")
        plt.savefig(os.path.join(OUTPUT_DIR, "wordcloud.png"))
        print("Generated: output/wordcloud.png")

    # --- Task 2: Figures Visualization ---
    df = pd.DataFrame(stats)
    if not df.empty:
        plt.figure(figsize=(12, 6))
        plt.bar(df['paper'], df['figures'], color='skyblue')
        plt.xticks(rotation=45, ha='right')
        plt.ylabel("Number of Figures")
        plt.title("Figures per Article")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "figures_chart.png"))
        print("Generated: output/figures_chart.png")

    # --- Task 3: Links List ---
    with open(os.path.join(OUTPUT_DIR, "links_found.txt"), "w") as f:
        for paper, links in all_links.items():
            f.write(f"Paper: {paper}\n")
            if links:
                for link in links:
                    f.write(f"  - {link}\n")
            else:
                f.write("  - No links found.\n")
            f.write("-" * 20 + "\n")
    print("Generated: output/links_found.txt")


if __name__ == "__main__":
    main()