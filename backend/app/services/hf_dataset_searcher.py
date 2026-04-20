"""
Hugging Face Dataset Searcher for Janus.

Searches HF Hub for datasets relevant to identified knowledge gaps.
Uses the `datasets` library with streaming to avoid full downloads.
"""

import logging
import time
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# High-quality instruction-tuning datasets to prioritize
CURATED_DATASETS = [
    {
        "name": "HuggingFaceH4/instruction-dataset",
        "description": "High-quality instruction-tuning dataset",
        "size": "~250k examples",
        "topics": ["general", "instruction", "reasoning"],
    },
    {
        "name": "Open-Orca/OpenOrca",
        "description": "Large-scale reasoning dataset",
        "size": "~4M examples",
        "topics": ["reasoning", "analysis", "general"],
    },
    {
        "name": "teknium/OpenHermes-2.5",
        "description": "General knowledge and reasoning",
        "size": "~1M examples",
        "topics": ["general", "knowledge", "reasoning"],
    },
    {
        "name": "allenai/science_qa",
        "description": "Scientific reasoning questions",
        "size": "~21k examples",
        "topics": ["science", "physics", "chemistry", "biology"],
    },
    {
        "name": "financial_phrasebank",
        "description": "Financial sentiment analysis",
        "size": "~4k examples",
        "topics": ["finance", "sentiment", "analysis"],
    },
    {
        "name": "truthful_qa",
        "description": "Truthful question answering",
        "size": "~800 examples",
        "topics": ["truthfulness", "factual", "reasoning"],
    },
]


class HFDatasetSearcher:
    """
    Searches Hugging Face Hub for datasets relevant to knowledge gaps.
    Uses streaming to avoid full downloads.
    """

    def __init__(self):
        self._datasets_available = None
        self._last_check = 0

    def _check_datasets_available(self) -> bool:
        """Check if the datasets library is available."""
        if self._datasets_available is not None:
            return self._datasets_available

        try:
            import datasets

            self._datasets_available = True
            logger.info("datasets library available")
            return True
        except ImportError:
            logger.warning("datasets library not installed")
            self._datasets_available = False
            return False

    def search_for_gap(self, gap_topic: str, max_results: int = 5) -> List[Dict]:
        """
        Search for datasets relevant to a knowledge gap.

        Args:
            gap_topic: The topic of the knowledge gap
            max_results: Maximum number of datasets to return

        Returns:
            List of dataset info dicts with relevance scores
        """
        if not self._check_datasets_available():
            return self._fallback_search(gap_topic, max_results)

        try:
            from huggingface_hub import HfApi

            api = HfApi()
            datasets = api.list_datasets(
                search=gap_topic,
                limit=max_results,
                sort="downloads",
            )

            results = []
            for ds in datasets:
                # Score based on downloads (proxy for quality)
                downloads = getattr(ds, "downloads", 0) or 0
                score = min(downloads / 10000, 1.0)  # Normalize to 0-1

                results.append(
                    {
                        "name": ds.id,
                        "description": getattr(ds, "card_data", {})
                        .get("dataset_info", {})
                        .get("description", "")[:200]
                        if hasattr(ds, "card_data") and ds.card_data
                        else "",
                        "downloads": downloads,
                        "size": getattr(ds, "size_categories", []) or [],
                        "relevance_score": round(score, 2),
                        "topics": [gap_topic],
                        "streaming_available": True,
                    }
                )

            # Boost curated datasets if they match
            for result in results:
                for curated in CURATED_DATASETS:
                    if curated["name"] == result["name"]:
                        result["curated"] = True
                        result["relevance_score"] = min(
                            result["relevance_score"] + 0.2, 1.0
                        )
                        break

            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            logger.info(f"Found {len(results)} datasets for '{gap_topic}'")
            return results[:max_results]

        except Exception as e:
            logger.error(f"HF dataset search failed for '{gap_topic}': {e}")
            return self._fallback_search(gap_topic, max_results)

    def _fallback_search(self, gap_topic: str, max_results: int) -> List[Dict]:
        """Fallback search using curated dataset list."""
        results = []
        for ds in CURATED_DATASETS:
            if any(topic in gap_topic.lower() for topic in ds["topics"]):
                results.append(
                    {
                        **ds,
                        "relevance_score": 0.7,
                        "curated": True,
                        "streaming_available": True,
                    }
                )

        # Also add general datasets
        if not results:
            for ds in CURATED_DATASETS[:3]:
                results.append(
                    {
                        **ds,
                        "relevance_score": 0.5,
                        "curated": True,
                        "streaming_available": True,
                    }
                )

        return results[:max_results]

    def get_curated_datasets(self) -> List[Dict]:
        """Get list of curated high-quality datasets."""
        return CURATED_DATASETS.copy()

    def stream_dataset_sample(
        self, dataset_name: str, max_samples: int = 100, split: str = "train"
    ) -> List[Dict]:
        """
        Get dataset info via HF Hub API (lightweight, no datasets library needed).
        Returns dataset metadata and sample info instead of full data.
        """
        try:
            from huggingface_hub import HfApi, hf_hub_download
            import json

            api = HfApi()

            # Get dataset info
            ds_info = api.dataset_info(dataset_name)

            # Try to get a small sample from the dataset card or README
            sample_data = {
                "dataset_name": dataset_name,
                "description": getattr(ds_info, "card_data", {})
                .get("dataset_info", {})
                .get("description", "")
                if hasattr(ds_info, "card_data") and ds_info.card_data
                else "",
                "tags": getattr(ds_info, "tags", []) or [],
                "downloads": getattr(ds_info, "downloads", 0) or 0,
            }

            try:
                readme = api.hf_hub_download(
                    repo_id=dataset_name,
                    filename="README.md",
                    repo_type="dataset",
                )
                with open(readme) as f:
                    content = f.read()[:1000]
                    sample_data["readme_preview"] = content
            except Exception:
                pass

        except Exception as e:
            logger.warning(f"Failed to get basic dataset info for {dataset_name}: {e}")
            sample_data = {"dataset_name": dataset_name}

        try:
            from datasets import load_dataset

            # Try to load the dataset using the library
            ds = load_dataset(dataset_name, split=split, streaming=True)
            samples = [sample_data] # first element is dataset metadata


            for i, item in enumerate(ds):
                if i >= max_samples:
                    break
                samples.append(dict(item))

            logger.info(f"Streamed {len(samples)} samples from {dataset_name}")
            return samples

        except Exception as e:
            logger.error(f"Failed to stream {dataset_name}: {e}")
            return []


hf_dataset_searcher = HFDatasetSearcher()
