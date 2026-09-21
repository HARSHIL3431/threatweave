#!/usr/bin/env python3
"""Build the local MITRE ATT&CK RAG index.

Usage (from the repository root):
    python scripts/build_mitre_index.py            # download if needed + build
    python scripts/build_mitre_index.py --force-download
    python scripts/build_mitre_index.py --model sentence-transformers/all-MiniLM-L6-v2

Outputs (under data/mitre, overridable):
    raw/enterprise-attack.json     official MITRE CTI STIX bundle
    processed/techniques.json      normalized techniques (deterministic)
    vectorstore/index.faiss        FAISS IndexFlatIP (normalized embeddings)
    vectorstore/metadata.json      aligned document metadata

The pipeline is deterministic: the same source produces the same documents in
the same order, so the index can be rebuilt reproducibly. No API keys required.
"""
import argparse
import json
import sys
import time
from pathlib import Path

# Allow importing the backend package when run from the repo root.
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))


def download_stix(url: str, dest: Path) -> None:
    """Download the official MITRE ATT&CK enterprise STIX bundle."""
    try:
        import httpx
    except ImportError:
        sys.exit("httpx is required to download MITRE data; install project dependencies first.")

    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading MITRE ATT&CK STIX data from:\n  {url}")
    with httpx.Client(follow_redirects=True, timeout=300.0) as client:
        resp = client.get(url)
        if resp.status_code != 200:
            sys.exit(
                f"FATAL: Failed to download MITRE data (HTTP {resp.status_code}). "
                f"Check network access to {url}."
            )
        dest.write_bytes(resp.content)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"Downloaded {dest.stat().st_size} bytes ({size_mb:.1f} MB) -> {dest}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the MITRE ATT&CK RAG vector index")
    parser.add_argument("--force-download", action="store_true", help="Re-download STIX data even if present")
    parser.add_argument("--raw", type=Path, default=None, help="Path to a local enterprise-attack.json")
    parser.add_argument("--out", type=Path, default=None, help="Output data/mitre directory")
    parser.add_argument("--model", type=str, default=None, help="SentenceTransformer model name")
    parser.add_argument("--include-inactive", action="store_true",
                        help="Index revoked/deprecated techniques too (default: exclude)")
    args = parser.parse_args()

    from app.core.config import settings
    from app.services.embedding_service import EmbeddingService
    from app.services.mitre_data import (
        MitreDataError,
        build_documents,
        parse_stix_bundle,
    )
    from app.services.vector_store import VectorStore

    print("MITRE ATT&CK ingestion started")

    raw_file = args.raw or settings.mitre_stix_file
    if args.raw is None and (args.force_download or not raw_file.exists()):
        download_stix(settings.MITRE_ENTERPRISE_STIX_URL, raw_file)
    if not raw_file.exists():
        sys.exit(
            f"FATAL: MITRE STIX source not found at {raw_file}. "
            f"Run with --force-download or place enterprise-attack.json there."
        )

    print(f"Parsing STIX bundle: {raw_file}")
    with open(raw_file, "r", encoding="utf-8") as f:
        bundle = json.load(f)
    try:
        techniques = parse_stix_bundle(bundle)
    except MitreDataError as e:
        sys.exit(f"FATAL: MITRE data parse error: {e}")

    tech_count = sum(1 for t in techniques if not t.is_subtechnique)
    sub_count = sum(1 for t in techniques if t.is_subtechnique)
    revoked = sum(1 for t in techniques if t.is_revoked)
    deprecated = sum(1 for t in techniques if t.is_deprecated)
    print(f"Techniques loaded: {tech_count}")
    print(f"Sub-techniques loaded: {sub_count}")
    if revoked or deprecated:
        print(f"Revoked techniques excluded from index: {revoked}")
        print(f"Deprecated techniques excluded from index: {deprecated}")

    # Deterministic documents (sorted by technique_id)
    documents = build_documents(techniques, include_inactive=args.include_inactive)
    print(f"Documents created: {len(documents)}")

    # Persist normalized techniques (deterministic ordering)
    processed_dir = settings.mitre_processed_dir
    processed_dir.mkdir(parents=True, exist_ok=True)
    techniques_file = settings.mitre_techniques_file
    ordered = sorted(techniques, key=lambda t: (t.technique_id, t.technique_name))
    with open(techniques_file, "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "technique_id": t.technique_id,
                    "technique_name": t.technique_name,
                    "tactics": t.tactics,
                    "is_subtechnique": t.is_subtechnique,
                    "is_revoked": t.is_revoked,
                    "is_deprecated": t.is_deprecated,
                }
                for t in ordered
            ],
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Normalized techniques saved: {techniques_file}")

    if not documents:
        sys.exit("FATAL: No active techniques to index after normalization.")

    model_name = args.model or settings.RAG_EMBEDDING_MODEL
    print(f"Embedding model: {model_name}")
    embedder = EmbeddingService(model_name=model_name)
    start = time.perf_counter()
    vectors = embedder.embed([doc.text for doc in documents], batch_size=32)
    elapsed = time.perf_counter() - start
    print(f"Embeddings generated: {vectors.shape[0]} x {vectors.shape[1]} in {elapsed:.1f}s")

    index_dir = settings.mitre_vectorstore_dir
    index_dir.mkdir(parents=True, exist_ok=True)

    active_techniques = sum(1 for d in documents if d.type == "technique")
    active_subtechniques = sum(1 for d in documents if d.type == "sub-technique")

    store = VectorStore.create(
        vectors=vectors,
        documents=[doc.to_metadata_dict() for doc in documents],
        index_path=settings.mitre_index_file,
        metadata_path=settings.mitre_index_metadata_file,
        embedding_model=model_name,
        technique_count=active_techniques,
        subtechnique_count=active_subtechniques,
    )
    store.save()

    print(f"Embedding dimension: {vectors.shape[1]}")
    print("FAISS index created")
    print(f"Index saved: {settings.mitre_index_file}")
    print(f"Metadata saved: {settings.mitre_index_metadata_file}")
    print("MITRE ATT&CK ingestion completed successfully")


if __name__ == "__main__":
    main()