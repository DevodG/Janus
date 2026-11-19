"""
HuggingFace dataset pusher for Janus self-improvement.

Pushes curated examples to HF dataset repo for external training.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

HF_DATASET_REPO = os.getenv("HF_DATA_DATASET", "DevodG/janus-traces")
HF_TOKEN = os.getenv("HUGGINGFACE_API_KEY", "")
CURATED_FILE = (
    Path(__file__).parent.parent.parent.parent
    / "data"
    / "curation"
    / "curated_examples.jsonl"
)


class HFDatasetPusher:
    def __init__(self):
        self._api = None

    def _get_api(self):
        if self._api is None and HF_TOKEN:
            try:
                from huggingface_hub import HfApi

                self._api = HfApi(token=HF_TOKEN)
            except ImportError:
                logger.warning("huggingface_hub not installed")
            except Exception as e:
                logger.error(f"Failed to init HF API: {e}")
        return self._api

    def push_curated_dataset(self, limit: int = 500) -> Dict[str, Any]:
        """Push curated examples to HF dataset repo."""
        api = self._get_api()
        if api is None:
            return {"error": "HF API not available"}

        examples = self._read_curated_examples(limit)
        if not examples:
            return {"error": "No curated examples to push"}

        try:
            # Convert to HF dataset format
            dataset_json = {
                "examples": examples,
                "metadata": {
                    "count": len(examples),
                    "pushed_at": self._get_timestamp(),
                    "source": "janus-traces",
                },
            }

            # Push as JSON file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump(dataset_json, f, indent=2)
                temp_path = f.name

            api.upload_file(
                path_or_fileobj=temp_path,
                path_in_repo="curated_examples.json",
                repo_id=HF_DATASET_REPO,
                repo_type="dataset",
            )

            import os as os_mod

            os_mod.unlink(temp_path)

            return {
                "pushed": len(examples),
                "repo": HF_DATASET_REPO,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Failed to push dataset: {e}")
            return {"error": str(e)}

    def _read_curated_examples(self, limit: int) -> List[Dict[str, Any]]:
        """Read curated examples from JSONL file."""
        examples = []
        if not CURATED_FILE.exists():
            return examples

        try:
            with open(CURATED_FILE) as f:
                for line in f:
                    if line.strip():
                        examples.append(json.loads(line))
            return examples[-limit:]
        except Exception as e:
            logger.error(f"Failed to read curated examples: {e}")
            return []

    def _get_timestamp(self) -> str:
        from datetime import datetime

        return datetime.utcnow().isoformat()
