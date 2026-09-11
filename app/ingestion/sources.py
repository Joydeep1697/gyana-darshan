"""Registry for conservative public-source ingestion targets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IngestionSource:
    key: str
    label: str
    url: str
    robots_url: str
    evidence_dir: Path
    corpus_jsonl: Path | None = None


SOURCES: dict[str, IngestionSource] = {
    "bns": IngestionSource(
        key="bns",
        label="Bharatiya Nyaya Sanhita, 2023",
        url="https://www.indiacode.nic.in/indiacode/handle/123456789/20062?col=123456789%2F1362&view_type=search",
        robots_url="https://www.indiacode.nic.in/robots.txt",
        evidence_dir=Path("corpus_integrity") / "bns",
        corpus_jsonl=Path("corpus_integrity") / "bns_2023_corpus.jsonl",
    ),
    "bnss": IngestionSource(
        key="bnss",
        label="Bharatiya Nagarik Suraksha Sanhita, 2023",
        url="https://www.indiacode.nic.in/",
        robots_url="https://www.indiacode.nic.in/robots.txt",
        evidence_dir=Path("corpus_integrity") / "bnss",
        corpus_jsonl=Path("corpus_integrity") / "bnss_2023_corpus.jsonl",
    ),
    "bsa": IngestionSource(
        key="bsa",
        label="Bharatiya Sakshya Adhiniyam, 2023",
        url="https://www.indiacode.nic.in/",
        robots_url="https://www.indiacode.nic.in/robots.txt",
        evidence_dir=Path("corpus_integrity") / "bsa",
        corpus_jsonl=Path("corpus_integrity") / "bsa_2023_corpus.jsonl",
    ),
    "egazette": IngestionSource(
        key="egazette",
        label="eGazette",
        url="https://egazette.nic.in/",
        robots_url="https://egazette.nic.in/robots.txt",
        evidence_dir=Path("corpus_integrity") / "egazette",
    ),
    "prs": IngestionSource(
        key="prs",
        label="PRS India",
        url="https://prsindia.org/",
        robots_url="https://prsindia.org/robots.txt",
        evidence_dir=Path("corpus_integrity") / "prs",
    ),
}

