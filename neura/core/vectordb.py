"""Per-capsule vector search — isolated semantic index for each capsule.

Each capsule gets its own ChromaDB collection with only its own files indexed.
Global vsearch (port 7820) is for Claude Code / admin only.

Architecture:
  homes/<name>/  →  collection "capsule_<name>"  →  search by user prompt
  shared/        →  collection "shared_knowledge" →  available to all capsules

Features:
  - Semantic chunking: splits by markdown headers/paragraphs, not fixed size
  - Cross-encoder reranking: two-pass search (vector recall → rerank precision)
  - e5-large embeddings with query/passage prefixes
  - Priority boost for SKILL.md/CLAUDE.md

Thread-safe: chromadb PersistentClient handles locking.
"""
import hashlib
import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

VECTOR_DB_ROOT = Path("/opt/neura-v2/data/vectordb")
MODEL_NAME = "intfloat/multilingual-e5-large"
RERANKER_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

# Semantic chunking params
CHUNK_TARGET = 800       # target chunk size (chars) — e5-large handles longer text well
CHUNK_MAX = 1200         # hard max before forced split
CHUNK_MIN = 80           # minimum chunk size (skip tiny fragments)
CHUNK_OVERLAP_LINES = 2  # overlap N lines between chunks for continuity

MAX_CHUNKS_PER_FILE = 25
MAX_FILE_SIZE = 150_000  # 150KB

# Reranker params
RERANK_CANDIDATES = 15   # fetch this many from vector search
VECTOR_WEIGHT = 0.35     # weight for vector score in combined ranking
RERANK_WEIGHT = 0.65     # weight for reranker score in combined ranking

# Priority files get more chunks indexed and boosted relevance
PRIORITY_FILENAMES = {"SKILL.md", "CLAUDE.md", "SYSTEM.md", "README.md"}
PRIORITY_EXTENSIONS = {".yaml", ".yml"}  # capsule configs

INDEX_EXTENSIONS = {
    ".md", ".txt", ".yaml", ".yml", ".json", ".py",
    ".js", ".ts", ".jsx", ".tsx", ".css", ".html",
    ".csv",  # tabular data (CRM, stacks, analytics)
}

SKIP_DIRS = {
    "node_modules", "__pycache__", ".git", ".cache", "dist",
    "site-packages", ".mypy_cache", ".pytest_cache",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "sessions.json", ".DS_Store",
}

SKIP_PATH_CONTAINS = {
    "/node_modules/", "/__pycache__/", "/.claude/projects/",
    "/legacy-capsule/", "/plugins/marketplaces/",
}

# e5 models require "query: " / "passage: " prefixes for best results
_IS_E5_MODEL = "e5" in MODEL_NAME.lower()

# Singleton model caches — loaded once, shared across all capsule indexes
_model = None
_model_loading = False
_reranker = None
_reranker_loading = False

# Cache open collections to avoid reopening ChromaDB on every request
_collection_cache: dict[str, object] = {}

# Regex for markdown headers
_HEADER_RE = re.compile(r'^(#{1,4})\s+', re.MULTILINE)


def _get_model():
    """Lazy-load the embedding model (shared singleton)."""
    global _model, _model_loading
    if _model is not None:
        return _model
    if _model_loading:
        return None  # another thread is loading, skip this request
    _model_loading = True
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Model loaded (dim={_model.get_sentence_embedding_dimension()})")
        return _model
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None
    finally:
        _model_loading = False


def _get_reranker():
    """Lazy-load the cross-encoder reranker (shared singleton)."""
    global _reranker, _reranker_loading
    if _reranker is not None:
        return _reranker
    if _reranker_loading:
        return None
    _reranker_loading = True
    try:
        from sentence_transformers import CrossEncoder
        logger.info(f"Loading reranker: {RERANKER_NAME}")
        _reranker = CrossEncoder(RERANKER_NAME)
        logger.info("Reranker loaded")
        return _reranker
    except Exception as e:
        logger.error(f"Failed to load reranker: {e}")
        return None
    finally:
        _reranker_loading = False


def _source_prefix(source: str) -> str:
    """Generate a context prefix from file path for better embedding quality.

    "skills/excel-xlsx/SKILL.md" → "Файл: skills/excel-xlsx/SKILL.md (скилл excel-xlsx)"
    "CLAUDE.md" → "Файл: CLAUDE.md (правила агента)"
    """
    parts = [f"Файл: {source}"]

    path = Path(source)
    name = path.name.lower()

    if "skill" in str(source).lower():
        skill_dir = path.parent.name if path.parent.name != "." else path.stem
        parts.append(f"(скилл {skill_dir})")
    elif name in ("claude.md", "system.md"):
        parts.append("(правила агента)")
    elif name.endswith(".yaml") or name.endswith(".yml"):
        parts.append("(конфигурация)")
    elif "diary" in str(source).lower():
        parts.append("(дневник)")
    elif "memory" in str(source).lower():
        parts.append("(память)")
    elif "knowledge" in str(source).lower():
        parts.append("(база знаний)")
    elif "employee" in str(source).lower():
        parts.append("(досье сотрудника)")

    return " ".join(parts) + "\n"


# ── Semantic Chunking ──────────────────────────────────────────────────


def _split_by_headers(text: str) -> list[dict]:
    """Split markdown text by headers into semantic sections.

    Returns list of {header, body, level} where level is header depth (1-4).
    Non-markdown files get a single section.
    """
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        # No headers — return whole text as one section
        return [{"header": "", "body": text.strip(), "level": 0}]

    sections = []

    # Text before first header
    pre = text[:matches[0].start()].strip()
    if pre:
        sections.append({"header": "", "body": pre, "level": 0})

    for i, m in enumerate(matches):
        level = len(m.group(1))  # number of #
        header_line = text[m.start():text.index("\n", m.start())] if "\n" in text[m.start():] else text[m.start():]
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()

        # Include header text in body for context
        sections.append({
            "header": header_line.lstrip("#").strip(),
            "body": body,
            "level": level,
        })

    return sections


def _split_section_into_chunks(body: str, target: int = CHUNK_TARGET, maximum: int = CHUNK_MAX) -> list[str]:
    """Split a section body into chunks, respecting paragraph boundaries.

    Strategy:
    1. Split by double newlines (paragraphs)
    2. Accumulate paragraphs until target size
    3. If a single paragraph exceeds max, split by sentences
    4. Add overlap lines between chunks
    """
    if len(body) <= target:
        return [body] if len(body) >= CHUNK_MIN else []

    paragraphs = re.split(r'\n\s*\n', body)
    chunks = []
    current = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # If single paragraph exceeds max, split by sentences
        if len(para) > maximum:
            # Flush current
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0

            # Split long paragraph by sentences
            sentences = re.split(r'(?<=[.!?。])\s+', para)
            sent_chunk = []
            sent_len = 0
            for sent in sentences:
                if sent_len + len(sent) > target and sent_chunk:
                    chunks.append(" ".join(sent_chunk))
                    # Keep last sentence as overlap
                    sent_chunk = sent_chunk[-1:] if sent_chunk else []
                    sent_len = sum(len(s) for s in sent_chunk)
                sent_chunk.append(sent)
                sent_len += len(sent)
            if sent_chunk:
                chunks.append(" ".join(sent_chunk))
            continue

        if current_len + len(para) > target and current:
            chunks.append("\n\n".join(current))
            # Keep last paragraph as overlap
            overlap = current[-CHUNK_OVERLAP_LINES:]
            current = overlap
            current_len = sum(len(p) for p in current)

        current.append(para)
        current_len += len(para)

    if current:
        chunk_text = "\n\n".join(current)
        if len(chunk_text) >= CHUNK_MIN:
            chunks.append(chunk_text)

    return chunks


def _chunk_text(text: str, source: str) -> list[dict]:
    """Semantic chunking: split by headers → paragraphs → size limit.

    Each chunk gets a source prefix and section header for context.
    """
    prefix = _source_prefix(source)
    sections = _split_by_headers(text)
    chunks = []

    for section in sections:
        header = section["header"]
        body = section["body"]
        if not body or len(body) < CHUNK_MIN:
            continue

        sub_chunks = _split_section_into_chunks(body)

        for sub in sub_chunks:
            # Prepend header to chunk for context
            if header:
                chunk_text = f"{prefix}## {header}\n{sub}"
            else:
                chunk_text = f"{prefix}{sub}"

            chunks.append({
                "text": chunk_text,
                "source": source,
                "chunk_index": len(chunks),
                "section": header or "(intro)",
            })

    # Priority files get full indexing, others are limited
    fname = Path(source).name
    max_chunks = MAX_CHUNKS_PER_FILE * 2 if fname in PRIORITY_FILENAMES else MAX_CHUNKS_PER_FILE
    return chunks[:max_chunks]


# ── File Collection ────────────────────────────────────────────────────


def _collect_files(directory: Path) -> list[Path]:
    """Collect indexable files from a directory."""
    files = []
    if not directory.exists():
        return files

    for root, dirs, filenames in os.walk(directory, followlinks=True):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in filenames:
            if fname in SKIP_FILES:
                continue
            fpath = Path(root) / fname
            if any(skip in str(fpath) for skip in SKIP_PATH_CONTAINS):
                continue
            if fpath.suffix not in INDEX_EXTENSIONS:
                continue
            try:
                size = fpath.stat().st_size
                if size < 50 or size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue
            files.append(fpath)
    return files


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ── CapsuleVectorDB ───────────────────────────────────────────────────


class CapsuleVectorDB:
    """Per-capsule vector index — isolated search over capsule's own files."""

    def __init__(self, capsule_id: str, home_path: str):
        self._capsule_id = capsule_id
        self._home = Path(home_path)
        self._collection_name = f"capsule_{capsule_id}"
        self._db_path = VECTOR_DB_ROOT / capsule_id
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._meta_path = self._db_path / "meta.json"
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            if self._collection_name in _collection_cache:
                self._collection = _collection_cache[self._collection_name]
            else:
                import chromadb
                client = chromadb.PersistentClient(path=str(self._db_path))
                self._collection = client.get_or_create_collection(
                    name=self._collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                _collection_cache[self._collection_name] = self._collection
        return self._collection

    def _reset_collection_cache(self):
        """Clear cached collection (e.g. after reindex or dimension mismatch)."""
        _collection_cache.pop(self._collection_name, None)
        self._collection = None

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Two-pass search: vector recall (top-N) → cross-encoder rerank (top-K).

        Pass 1: Fetch RERANK_CANDIDATES results via cosine similarity
        Pass 2: Rerank with cross-encoder for precise relevance
        Fallback: If reranker unavailable, uses vector scores only

        Returns list of {source, text, score, rerank_score}.
        """
        model = _get_model()
        if model is None:
            return []

        collection = self._get_collection()
        if collection.count() == 0:
            return []

        # ── Pass 1: Vector recall ──
        try:
            q = f"query: {query}" if _IS_E5_MODEL else query
            embedding = model.encode([q]).tolist()
            n_candidates = min(RERANK_CANDIDATES, collection.count())
            results = collection.query(
                query_embeddings=embedding,
                n_results=n_candidates,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            err_str = str(e)
            if "dimension" in err_str.lower():
                logger.warning(f"Dimension mismatch for {self._capsule_id}, reindexing...")
                self._reset_collection_cache()
                try:
                    self.index(full=True)
                    # Retry search after reindex
                    collection = self._get_collection()
                    if collection.count() == 0:
                        return []
                    results = collection.query(
                        query_embeddings=embedding,
                        n_results=min(RERANK_CANDIDATES, collection.count()),
                        include=["documents", "metadatas", "distances"],
                    )
                except Exception as e2:
                    logger.error(f"Reindex+retry failed for {self._capsule_id}: {e2}")
                    return []
            else:
                logger.warning(f"Vector search error for {self._capsule_id}: {e}")
                return []

        # Build candidate list
        candidates = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            vector_score = round(1 - dist, 4)
            if vector_score < 0.2:  # very low threshold for recall pass
                continue
            candidates.append({
                "source": meta.get("source", ""),
                "text": doc,
                "vector_score": vector_score,
                "section": meta.get("section", ""),
            })

        if not candidates:
            return []

        # ── Pass 2: Cross-encoder rerank ──
        reranker = _get_reranker()
        if reranker is not None:
            try:
                pairs = []
                for c in candidates:
                    # Strip "Файл: ..." prefix for cleaner reranking
                    clean_text = c["text"]
                    if clean_text.startswith("Файл:"):
                        newline_idx = clean_text.find("\n")
                        if newline_idx > 0:
                            clean_text = clean_text[newline_idx + 1:]
                    pairs.append((query, clean_text[:500]))  # limit text length for speed

                rerank_scores = reranker.predict(pairs).tolist()

                # Normalize rerank scores to 0-1 via min-max within batch
                rr_min = min(rerank_scores)
                rr_max = max(rerank_scores)
                rr_range = rr_max - rr_min if rr_max > rr_min else 1.0

                for c, rs in zip(candidates, rerank_scores):
                    c["rerank_score"] = round(rs, 3)
                    c["rerank_norm"] = (rs - rr_min) / rr_range  # 0-1 normalized

                # Combined score: vector (semantic match) + reranker (precision)
                for c in candidates:
                    combined = (
                        VECTOR_WEIGHT * c["vector_score"] +
                        RERANK_WEIGHT * c["rerank_norm"]
                    )
                    c["combined_score"] = round(combined, 4)

                candidates.sort(key=lambda x: x["combined_score"], reverse=True)

            except Exception as e:
                logger.warning(f"Reranker error for {self._capsule_id}: {e}")
                for c in candidates:
                    c["combined_score"] = c["vector_score"]
                candidates.sort(key=lambda x: x["combined_score"], reverse=True)
        else:
            for c in candidates:
                c["combined_score"] = c["vector_score"]
            candidates.sort(key=lambda x: x["combined_score"], reverse=True)

        # ── Build output ──
        output = []
        for c in candidates[:top_k]:
            score = c["combined_score"]

            # Priority boost for important files
            fname = Path(c["source"]).name
            if fname in PRIORITY_FILENAMES:
                score = min(score + 0.05, 1.0)

            if score < 0.3:
                continue

            output.append({
                "source": c["source"],
                "text": c["text"],
                "score": round(score, 3),
                "vector_score": c["vector_score"],
                "rerank_score": c.get("rerank_score"),
            })

        return output

    def index(self, full: bool = False) -> dict:
        """Index all files in capsule home with semantic chunking. Returns stats."""
        import json
        import chromadb

        model = _get_model()
        client = chromadb.PersistentClient(path=str(self._db_path))

        if full:
            try:
                client.delete_collection(self._collection_name)
            except Exception:
                pass

        collection = client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._collection = collection

        # Load previous metadata
        prev_meta = {}
        if not full and self._meta_path.exists():
            try:
                prev_meta = json.loads(self._meta_path.read_text())
            except Exception:
                pass

        files = _collect_files(self._home)

        # Also index shared knowledge if it exists
        shared_dir = Path("/opt/neura-v2/shared")
        if shared_dir.exists():
            files.extend(_collect_files(shared_dir))

        new_meta = {}
        added = 0
        skipped = 0

        for fpath in files:
            try:
                rel = str(fpath.relative_to(self._home)) if str(fpath).startswith(str(self._home)) else f"shared/{fpath.name}"
            except ValueError:
                rel = str(fpath.name)

            try:
                fhash = _file_hash(fpath)
            except Exception:
                continue

            if not full and prev_meta.get(rel) == fhash:
                new_meta[rel] = fhash
                skipped += 1
                continue

            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if not text.strip() or len(text) < 20:
                continue

            # Remove old chunks
            try:
                existing = collection.get(where={"source": rel})
                if existing["ids"]:
                    collection.delete(ids=existing["ids"])
            except Exception:
                pass

            chunks = _chunk_text(text, rel)
            if not chunks:
                continue

            texts = [c["text"] for c in chunks]
            encode_texts = [f"passage: {t}" for t in texts] if _IS_E5_MODEL else texts
            embeddings = model.encode(encode_texts, show_progress_bar=False).tolist()
            ids = [f"{rel}::chunk_{c['chunk_index']}" for c in chunks]
            metadatas = [{
                "source": c["source"],
                "chunk_index": c["chunk_index"],
                "section": c.get("section", ""),
            } for c in chunks]

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            new_meta[rel] = fhash
            added += 1

        # Save metadata
        self._meta_path.write_text(json.dumps(new_meta, indent=2))

        stats = {
            "capsule_id": self._capsule_id,
            "files_indexed": added,
            "files_skipped": skipped,
            "total_files": len(new_meta),
            "total_chunks": collection.count(),
        }
        logger.info(f"Vector index for {self._capsule_id}: {stats}")
        return stats


# ── Convenience functions ──────────────────────────────────────────────


def search_capsule(capsule_id: str, home_path: str, query: str, top_k: int = 5) -> list[dict]:
    """Convenience function — search capsule's vector index."""
    vdb = CapsuleVectorDB(capsule_id, home_path)
    return vdb.search(query, top_k)


def index_capsule(capsule_id: str, home_path: str, full: bool = False) -> dict:
    """Convenience function — index a capsule."""
    vdb = CapsuleVectorDB(capsule_id, home_path)
    return vdb.index(full=full)


def index_all_capsules(full: bool = False) -> list[dict]:
    """Index all capsules found in homes directory."""
    homes_dir = Path("/opt/neura-v2/homes")
    results = []

    for home in sorted(homes_dir.iterdir()):
        if not home.is_dir():
            continue
        capsule_id = home.name
        try:
            stats = index_capsule(capsule_id, str(home), full=full)
            results.append(stats)
        except Exception as e:
            logger.error(f"Failed to index {capsule_id}: {e}")
            results.append({"capsule_id": capsule_id, "error": str(e)})

    return results
