"""
Persistence Manager for HF Spaces.
Syncs local models and metrics with an HF dataset repo to survive restarts.
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any
from huggingface_hub import HfApi

logger = logging.getLogger(__name__)

class PersistenceManager:
    """Manages syncing of critical data to HF Dataset repository."""
    
    def __init__(self):
        self.repo_id = os.getenv("HF_STORE_REPO")  # e.g., "username/janus-memory"
        self.token = os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN")
        
        from app.config import DATA_DIR
        self.data_dir = Path(DATA_DIR)
        
        # Directories to sync
        self.sync_dirs = [
            "distilled_models",
            "metrics",
            "learning",
            "knowledge",
            "skills"
        ]
        
        self.api = None
        if self.repo_id and self.token:
            try:
                self.api = HfApi(token=self.token)
                logger.info(f"✓ PersistenceManager initialized for repo: {self.repo_id}")
            except Exception as e:
                logger.error(f"Failed to init HF API for persistence: {e}")

    def download_all(self):
        """Download all synced directories from HF on startup."""
        if not self.api:
            logger.warning("Persistence sync skipped: HF_STORE_REPO or HF_TOKEN not set")
            return

        logger.info(f"Pulling persisted data from {self.repo_id}...")
        for folder in self.sync_dirs:
            try:
                local_path = self.data_dir / folder
                local_path.mkdir(parents=True, exist_ok=True)
                
                # Check if folder exists in repo
                files = self.api.list_repo_tree(self.repo_id, path_in_repo=folder, repo_type="dataset")
                if not files:
                    continue

                for file_info in files:
                    if file_info.path.endswith('.json') or file_info.path.endswith('.jsonl'):
                        self.api.hf_hub_download(
                            repo_id=self.repo_id,
                            filename=file_info.path,
                            repo_type="dataset",
                            local_dir=str(self.data_dir),
                            force_download=True
                        )
                logger.info(f"  ✓ Synced {folder}")
            except Exception as e:
                logger.error(f"  ✗ Failed to sync {folder}: {e}")

    def upload_all(self):
        """Upload all synced directories to HF."""
        if not self.api:
            return

        logger.info(f"Pushing data to {self.repo_id}...")
        for folder in self.sync_dirs:
            local_path = self.data_dir / folder
            if not local_path.exists():
                continue

            try:
                self.api.upload_folder(
                    folder_path=str(local_path),
                    path_in_repo=folder,
                    repo_id=self.repo_id,
                    repo_type="dataset",
                    commit_message=f"Sync {folder} from Janus instance"
                )
                logger.info(f"  ✓ Pushed {folder}")
            except Exception as e:
                logger.error(f"  ✗ Failed to push {folder}: {e}")

    def upload_file(self, local_file_path: str, path_in_repo: str):
        """Upload a specific file to the repo."""
        if not self.api:
            return
        
        try:
            self.api.upload_file(
                path_or_fileobj=local_file_path,
                path_in_repo=path_in_repo,
                repo_id=self.repo_id,
                repo_type="dataset"
            )
        except Exception as e:
            logger.error(f"Failed to upload file {local_file_path}: {e}")
