from scripts.paperanalyst import extract_data, clean_url


SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
  <text>
    <front>
      <abstract>
        <p>This paper studies language models for scientific document analysis.</p>
        <p>We evaluate extraction quality on open-access papers.</p>
      </abstract>
    </front>
    <body>
      <figure>
        <head>Figure 1</head>
      </figure>
      <figure>
        <head>Figure 2</head>
      </figure>
      <p>
        Related resources are available at
        <ref type="url" target="https://example.org/project">project page</ref>
        and
        <ptr target="https://github.com/example/repo" />
      </p>
      <p>
        Broken reference:
        <ref type="url">1/2024.emnlp-main</ref>
      </p>
      <p>
        Truncated reference:
        <ref type="url">https://samim.io/dl/Predicting%20</ref>
      </p>
    </body>
  </text>
</TEI>
"""


def test_extract_data_returns_abstract():
    abstract, figure_count, links = extract_data(SAMPLE_XML)

    assert "language models" in abstract
    assert "open-access papers" in abstract
    assert isinstance(abstract, str)
    assert len(abstract) > 20


def test_extract_data_counts_figures():
    abstract, figure_count, links = extract_data(SAMPLE_XML)

    assert figure_count == 2


def test_extract_data_filters_and_extracts_links():
    abstract, figure_count, links = extract_data(SAMPLE_XML)

    assert "https://example.org/project" in links
    assert "https://github.com/example/repo" in links
    assert "1/2024.emnlp-main" not in links
    assert "https://samim.io/dl/Predicting%20" not in links


def test_clean_url_accepts_valid_urls():
    assert clean_url("https://example.com") == "https://example.com"
    assert clean_url(" http://example.com/test ") == "http://example.com/test"


def test_clean_url_rejects_invalid_or_broken_urls():
    assert clean_url("") is None
    assert clean_url("not_a_url") is None
    assert clean_url("1/2024.emnlp-main") is None
    assert clean_url("https://x.co") is not None
    assert clean_url("https://samim.io/dl/Predicting%20") is None