#!/root/Antigravity/.venv/bin/python3
"""Index all capsule vector databases.

Usage:
  python3 scripts/index-all-capsules.py          # incremental
  python3 scripts/index-all-capsules.py --full    # full reindex
"""
import sys
import os
import time
import fcntl
import signal
import shutil
from pathlib import Path

# Force HuggingFace Hub into offline mode BEFORE any HF imports.
# The embedding model (intfloat/multilingual-e5-large) is fully cached locally
# and does not need network access to run. When HF Hub is in online mode, it
# checks for file updates / missing files on every model load, which has been
# observed to hang indefinitely in futex waits (10.04 incident: 727% CPU,
# 3.4 GB RAM, 179+ min hang). Offline mode skips all network checks and uses
# the local snapshot directly.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")

sys.path.insert(0, "/opt/neura-v2")

LOCK_FILE = "/tmp/index-all-capsules.lock"
# Self-destruct 20s before cron's `timeout 1800` fires SIGTERM.
# Legitimate full runs have historically taken ~29 min on 08.04 — this gives
# just enough headroom while still guaranteeing a hard exit if the process
# is stuck in native code that ignores cron's SIGTERM.
TIMEOUT_SEC = 1780  # 29m 40s

def _timeout_handler(signum, frame):
    # Hard exit — sys.exit can be swallowed by native C code (PyTorch/transformers).
    # Clean up lock file here since os._exit skips atexit handlers.
    sys.stderr.write(f"\n  ⚠️ TIMEOUT: indexing exceeded {TIMEOUT_SEC}s limit, aborting hard.\n")
    sys.stderr.flush()
    try:
        os.unlink(LOCK_FILE)
    except OSError:
        pass
    os._exit(124)

def _clear_poisoned_hf_cache():
    """Clear HuggingFace Hub .no_exist sentinel dirs that cause infinite lock waits.

    Problem: when a model file is missing in the local snapshot, HF Hub writes
    zero-byte sentinel files to .no_exist/<snapshot_id>/<filename>. On next
    model.encode() call, HF acquires a lock waiting for the file to be
    downloaded — but there is nothing to trigger the download, so the process
    hangs forever in native code that ignores signals.
    """
    for model_name in ("models--intfloat--multilingual-e5-large",
                       "models--cross-encoder--mmarco-mMiniLMv2-L12-H384-v1"):
        sentinel = Path(f"/root/.cache/huggingface/hub/{model_name}/.no_exist")
        if sentinel.exists():
            print(f"  ⚠️ Clearing poisoned HF Hub cache: {sentinel}")
            shutil.rmtree(sentinel, ignore_errors=True)

_clear_poisoned_hf_cache()

from neura.core.vectordb import index_all_capsules

if __name__ == "__main__":
    # Prevent concurrent runs
    lock_fd = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("  ⚠️ Another index-all-capsules.py is already running, exiting.")
        sys.exit(0)

    # Set timeout
    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(TIMEOUT_SEC)

    lock_fd.write(str(os.getpid()))
    lock_fd.flush()

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

    # Cleanup
    signal.alarm(0)
    fcntl.flock(lock_fd, fcntl.LOCK_UN)
    lock_fd.close()
    try:
        os.unlink(LOCK_FILE)
    except OSError:
        pass
