"""
persistent_store.py — HF Spaces-aware persistent storage

THE PROBLEM:
  HF Spaces has an ephemeral filesystem. Every time the Space sleeps and wakes,
  or is restarted, ALL files in data/ are deleted. This means:
  - All case memory is lost
  - All cached responses are lost
  - All learned skills are lost
  - All simulation history is lost

THE SOLUTION:
  Use HF Datasets as a key-value store. It's free, persistent across restarts,
  and works with your existing HF_TOKEN secret.

  Fallback: if HF_TOKEN is not set (local dev), uses local JSON files as before.

USAGE:
  from app.services.persistent_store import store

  # Save
  store.set("cases:abc123", {"query": "...", "answer": "..."})

  # Load
  case = store.get("cases:abc123")

  # List all keys with prefix
  keys = store.list_prefix("cases:")
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

HF_TOKEN    = os.getenv("HF_TOKEN", "")
HF_REPO_ID  = os.getenv("HF_STORE_REPO", "")   # e.g. "DevodG/janus-memory"
IS_HF_SPACE = os.getenv("SPACE_ID", "") != ""   # HF injects SPACE_ID automatically

# Local fallback path
try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


class _LocalStore:
    """Local JSON file store — for development."""

    def __init__(self):
        self._base = pathlib.Path(DATA_DIR)
        self._lock = threading.RLock()

    def _path(self, key: str) -> pathlib.Path:
        # key like "cases:abc123" → data/cases/abc123.json
        parts = key.split(":", 1)
        if len(parts) == 2:
            folder, name = parts
        else:
            folder, name = "misc", parts[0]
        p = self._base / folder
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{name}.json"

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            p = self._path(key)
            if not p.exists():
                return None
            try:
                return json.loads(p.read_text())
            except Exception:
                return None

    def set(self, key: str, value: Any) -> bool:
        with self._lock:
            try:
                p = self._path(key)
                p.write_text(json.dumps(value, indent=2, default=str))
                return True
            except Exception as e:
                logger.warning("LocalStore.set(%s) failed: %s", key, e)
                return False

    def delete(self, key: str) -> bool:
        with self._lock:
            p = self._path(key)
            if p.exists():
                p.unlink()
                return True
            return False

    def list_prefix(self, prefix: str) -> list[str]:
        with self._lock:
            parts = prefix.rstrip(":").split(":", 1)
            folder = parts[0]
            folder_path = self._base / folder
            if not folder_path.exists():
                return []
            return [
                f"{folder}:{f.stem}"
                for f in folder_path.glob("*.json")
            ]


class _HFDatasetStore:
    """
    Persistent store backed by a private HF Dataset repo.

    Each key is stored as a file in the dataset repo:
      cases/abc123.json
      skills/pattern_xyz.json
      memory/index.json
      etc.

    Writes are batched and committed every 60s to avoid rate limits.
    Reads always check local cache first.
    """

    def __init__(self):
        from huggingface_hub import HfApi
        self._api      = HfApi(token=HF_TOKEN)
        self._repo     = HF_REPO_ID
        self._cache: dict[str, Any] = {}
        self._dirty: dict[str, Any] = {}   # pending writes
        self._lock     = threading.RLock()
        self._last_commit = 0.0
        self._commit_interval = 60         # seconds

        # Ensure repo exists
        try:
            self._api.repo_info(repo_id=self._repo, repo_type="dataset")
        except Exception:
            logger.info("Creating HF dataset repo: %s", self._repo)
            try:
                self._api.create_repo(repo_id=self._repo, repo_type="dataset", private=True)
            except Exception as e:
                logger.error("Could not create HF dataset repo: %s", e)

        # Background commit thread
        t = threading.Thread(target=self._commit_loop, daemon=True)
        t.start()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._dirty:
                return self._dirty[key]
            if key in self._cache:
                return self._cache[key]
        # Fetch from HF
        try:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(
                repo_id=self._repo,
                filename=self._key_to_filename(key),
                repo_type="dataset",
                token=HF_TOKEN,
            )
            data = json.loads(pathlib.Path(path).read_text())
            with self._lock:
                self._cache[key] = data
            return data
        except Exception:
            return None

    def set(self, key: str, value: Any) -> bool:
        with self._lock:
            self._dirty[key] = value
            self._cache[key] = value
        return True

    def delete(self, key: str) -> bool:
        with self._lock:
            self._dirty.pop(key, None)
            self._cache.pop(key, None)
        try:
            self._api.delete_file(
                path_in_repo=self._key_to_filename(key),
                repo_id=self._repo,
                repo_type="dataset",
            )
            return True
        except Exception:
            return False

    def list_prefix(self, prefix: str) -> list[str]:
        try:
            files = self._api.list_repo_files(repo_id=self._repo, repo_type="dataset")
            folder = prefix.rstrip(":").replace(":", "/")
            return [
                self._filename_to_key(f)
                for f in files
                if f.startswith(folder + "/")
            ]
        except Exception:
            return []

    def flush(self):
        """Force-commit all pending writes now."""
        self._commit_dirty()

    def _commit_loop(self):
        while True:
            time.sleep(self._commit_interval)
            self._commit_dirty()

    def _commit_dirty(self):
        with self._lock:
            if not self._dirty:
                return
            batch = dict(self._dirty)
            self._dirty.clear()

        import tempfile
        ops = []
        tmp_files = []
        try:
            for key, value in batch.items():
                f = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                )
                json.dump(value, f, indent=2, default=str)
                f.close()
                tmp_files.append(f.name)
                ops.append({
                    "path_in_repo": self._key_to_filename(key),
                    "path_or_fileobj": f.name,
                })

            self._api.upload_folder(
                repo_id=self._repo,
                repo_type="dataset",
                folder_path=None,  # type: ignore
                path_in_repo="",
                # use individual file uploads instead
            )
            # Simpler: upload each file
            for op in ops:
                self._api.upload_file(
                    repo_id=self._repo,
                    repo_type="dataset",
                    path_in_repo=op["path_in_repo"],
                    path_or_fileobj=op["path_or_fileobj"],
                    token=HF_TOKEN,
                )
            logger.info("PersistentStore: committed %d keys to HF", len(batch))
        except Exception as e:
            logger.error("PersistentStore: commit failed: %s", e)
            # Re-queue failed writes
            with self._lock:
                for key, value in batch.items():
                    if key not in self._dirty:
                        self._dirty[key] = value
        finally:
            for f in tmp_files:
                try:
                    os.unlink(f)
                except Exception:
                    pass

    @staticmethod
    def _key_to_filename(key: str) -> str:
        """cases:abc123 → cases/abc123.json"""
        return key.replace(":", "/") + ".json"

    @staticmethod
    def _filename_to_key(filename: str) -> str:
        """cases/abc123.json → cases:abc123"""
        return filename.replace("/", ":").removesuffix(".json")


def _build_store():
    """Pick the right backend based on environment."""
    if IS_HF_SPACE and HF_TOKEN and HF_REPO_ID:
        logger.info("PersistentStore: using HF Datasets backend (repo: %s)", HF_REPO_ID)
        try:
            return _HFDatasetStore()
        except ImportError:
            logger.warning("huggingface_hub not installed — falling back to local store")
    if IS_HF_SPACE and not HF_REPO_ID:
        logger.warning(
            "PersistentStore: running on HF Space but HF_STORE_REPO is not set! "
            "All data will be lost on restart. Set HF_STORE_REPO=YourUsername/janus-memory "
            "in Space Secrets."
        )
    return _LocalStore()


# Module-level singleton
store = _build_store()
