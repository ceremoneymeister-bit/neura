#!/root/Antigravity/.venv/bin/python3
"""Index all capsule vector databases.

Usage:
  python3 scripts/index-all-capsules.py          # incremental
  python3 scripts/index-all-capsules.py --full    # full reindex
"""
import sys
import time

sys.path.insert(0, "/opt/neura-v2")

from neura.core.vectordb import index_all_capsules

if __name__ == "__main__":
    full = "--full" in sys.argv
    mode = "FULL" if full else "INCREMENTAL"
    print(f"\n{'='*60}")
    print(f"  Capsule Vector Indexing — {mode}")
    print(f"{'='*60}\n")

    start = time.time()
    results = index_all_capsules(full=full)

    print(f"\n{'='*60}")
    print(f"  Results:")
    print(f"{'='*60}")

    total_files = 0
    total_chunks = 0
    for r in results:
        if "error" in r:
            print(f"  ❌ {r['capsule_id']}: {r['error']}")
        else:
            print(f"  ✅ {r['capsule_id']}: {r['files_indexed']} files, {r['total_chunks']} chunks")
            total_files += r.get("total_files", 0)
            total_chunks += r.get("total_chunks", 0)

    elapsed = time.time() - start
    print(f"\n  Total: {total_files} files, {total_chunks} chunks")
    print(f"  Time: {elapsed:.1f}s")
    print()
