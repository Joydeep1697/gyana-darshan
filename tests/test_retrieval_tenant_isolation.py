from pathlib import Path

from retrieval.search import search


def test_retrieval_search_never_crosses_tenant_roots(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus_integrity" / "bns" / "section_103.md"
    corpus.parent.mkdir(parents=True)
    corpus.write_text(
        "---\nsource_url: https://example.test/bns103\nfetched_at: 2026-09-12T00:00:00+00:00\nprovenance_verified: false\n---\n# BNS Section 103\nMurder text.",
        encoding="utf-8",
    )
    vault = tmp_path / "app" / "storage" / "vault"
    (vault / "personal-a").mkdir(parents=True)
    (vault / "personal-b").mkdir(parents=True)
    (vault / "default_tenant").mkdir(parents=True)
    (vault / "personal-a" / "owned.md").write_text("tenant alpha contract retrieval", encoding="utf-8")
    (vault / "personal-b" / "secret.md").write_text("cross tenant secretxyz", encoding="utf-8")
    (vault / "default_tenant" / "default.md").write_text("default tenant secretxyz", encoding="utf-8")

    import retrieval.indexer as indexer
    import retrieval.search as search_module

    monkeypatch.setattr(indexer, "ROOT", tmp_path)
    monkeypatch.setattr(indexer, "CORPUS_BNS", corpus)
    monkeypatch.setattr(indexer, "VAULT_ROOT", vault)
    monkeypatch.setattr(indexer, "INDEX_ROOT", tmp_path / "app" / "storage" / "retrieval_index")
    monkeypatch.setattr(search_module, "load_tenant_index", indexer.load_tenant_index)

    visible = search("tenant alpha", "personal-a", top_k=10)
    hidden = search("secretxyz", "personal-a", top_k=10)

    assert any(result["file_path"].endswith("owned.md") for result in visible)
    assert not hidden
