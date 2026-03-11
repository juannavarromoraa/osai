import os
import time
import requests
import xml.etree.ElementTree as ET
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pandas as pd

# Configuration
GROBID_URL = "http://localhost:8070/api/processFulltextDocument"
INPUT_DIR = "papers"
OUTPUT_DIR = "outputs"
TEI_DIR = os.path.join("data", "tei")

# Ensure output directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEI_DIR, exist_ok=True)


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
    abstract_text = " ".join(
        [" ".join(node.itertext()).strip() for node in abstract_nodes if "".join(node.itertext()).strip()]
    )

    # Figures
    figures = root.findall(".//tei:figure", ns)
    figure_count = len(figures)

    # Links
    links = []

    for link_node in root.findall(".//tei:ptr[@target]", ns):
        target = link_node.get("target")
        if target:
            links.append(target.strip())

    for ref_node in root.findall(".//tei:ref[@type='url']", ns):
        target = ref_node.get("target")
        text = "".join(ref_node.itertext()).strip() if ref_node.text or list(ref_node) else ""
        if target:
            links.append(target.strip())
        elif text:
            links.append(text)

    # Deduplicate while preserving order
    seen = set()
    unique_links = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    return abstract_text, figure_count, unique_links


def main():
    all_abstracts = ""
    stats = []
    all_links = {}

    if not os.path.exists(INPUT_DIR):
        print(f"Input directory not found: {INPUT_DIR}")
        return

    pdf_files = sorted([f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")])

    print(f"Processing {len(pdf_files)} papers...")

    for pdf in pdf_files:
        print(f"--- Analyzing: {pdf} ---")
        path = os.path.join(INPUT_DIR, pdf)
        xml_result = process_paper(path)

        if xml_result:
            tei_path = save_tei(xml_result, pdf)
            print(f"Saved TEI: {tei_path}")

            abstract, fig_count, links = extract_data(xml_result)
            all_abstracts += " " + abstract
            stats.append({"paper": pdf, "figures": fig_count})
            all_links[pdf] = links
        else:
            print(f"Skipping {pdf} due to extraction failure.")

    # Task 1: Word Cloud
    if all_abstracts.strip():
        wordcloud = WordCloud(
            width=800,
            height=400,
            background_color="white"
        ).generate(all_abstracts)

        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.title("Keyword Cloud from Abstracts")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "wordcloud.png"))
        plt.close()
        print("Generated: outputs/wordcloud.png")

    # Task 2: Figures Visualization
    df = pd.DataFrame(stats)
    if not df.empty:
        plt.figure(figsize=(12, 6))
        plt.bar(df["paper"], df["figures"])
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Number of Figures")
        plt.title("Figures per Article")
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "figures_chart.png"))
        plt.close()
        print("Generated: outputs/figures_chart.png")

        df.to_csv(os.path.join(OUTPUT_DIR, "figures_per_paper.csv"), index=False)
        print("Generated: outputs/figures_per_paper.csv")

    # Task 3: Links List
    with open(os.path.join(OUTPUT_DIR, "links_found.txt"), "w", encoding="utf-8") as f:
        for paper, links in all_links.items():
            f.write(f"Paper: {paper}\n")
            if links:
                for link in links:
                    f.write(f"  - {link}\n")
            else:
                f.write("  - No links found.\n")
            f.write("-" * 20 + "\n")

    print("Generated: outputs/links_found.txt")


if __name__ == "__main__":
    main()