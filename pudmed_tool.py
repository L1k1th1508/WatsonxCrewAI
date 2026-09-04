"""
PubMed search tool for CrewAI.

Replaces the original repo's Serper (generic Google search) tool.
Genomics literature review needs actual PubMed abstracts, not web search
snippets — this hits NCBI's E-utilities directly. No API key required,
though NCBI asks you to stay under 3 requests/sec without one (10/sec if
you set NCBI_API_KEY as an env var).
"""

import os
import time
import xml.etree.ElementTree as ET

import requests
from crewai.tools import tool

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_API_KEY = os.getenv("f8bc5f6a9975ca052beccec9e32227875108")  # optional, raises rate limit


def _rate_limit_params():
    params = {}
    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY
    return params


def _esearch(query: str, max_results: int) -> list[str]:
    """Get a list of PMIDs matching the query."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
        **_rate_limit_params(),
    }
    resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("esearchresult", {}).get("idlist", [])


def _efetch(pmids: list[str]) -> list[dict]:
    """Fetch title/abstract/journal/year/authors for a batch of PMIDs."""
    if not pmids:
        return []
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml",
        **_rate_limit_params(),
    }
    resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    papers = []
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        pmid = pmid_el.text if pmid_el is not None else "unknown"

        title_el = article.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else "No title"

        abstract_parts = article.findall(".//AbstractText")
        abstract = " ".join("".join(a.itertext()).strip() for a in abstract_parts) or "No abstract available."

        journal_el = article.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else "Unknown journal"

        year_el = article.find(".//PubDate/Year")
        year = year_el.text if year_el is not None else article.findtext(".//PubDate/MedlineDate", default="n.d.")

        authors = []
        for author in article.findall(".//AuthorList/Author")[:3]:
            last = author.findtext("LastName", default="")
            init = author.findtext("Initials", default="")
            if last:
                authors.append(f"{last} {init}".strip())
        author_str = ", ".join(authors) + (" et al." if len(article.findall(".//AuthorList/Author")) > 3 else "")

        papers.append(
            {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "year": year,
                "authors": author_str or "Unknown authors",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )
    return papers


@tool("PubMed Literature Search")
def pubmed_search(query: str, max_results: int = 10) -> str:
    """
    Search PubMed for genomics/biomedical research papers on a given topic
    (e.g. a gene, variant, disease, or pathway) and return their titles,
    authors, journal, year, PMID, and abstract text.

    Args:
        query: Search term — supports PubMed query syntax, e.g.
               'BRCA1 AND breast cancer AND variant classification'.
        max_results: Number of papers to retrieve (default 10, keep under 30
                     to avoid overwhelming context / hitting rate limits).
    """
    pmids = _esearch(query, max_results)
    time.sleep(0.34 if not NCBI_API_KEY else 0.1)  # respect NCBI rate limits
    papers = _efetch(pmids)

    if not papers:
        return f"No PubMed results found for query: {query}"

    formatted = []
    for p in papers:
        formatted.append(
            f"PMID: {p['pmid']} | {p['year']} | {p['journal']}\n"
            f"Title: {p['title']}\n"
            f"Authors: {p['authors']}\n"
            f"URL: {p['url']}\n"
            f"Abstract: {p['abstract']}\n"
        )
    return "\n---\n".join(formatted)