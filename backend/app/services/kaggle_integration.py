"""
Kaggle dataset discovery and management.
"""

import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class KaggleIntegration:
    """Manages Kaggle dataset discovery and integration."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        # Default to backend/app/data/kaggle
        if cache_dir is None:
            from app.config import DATA_DIR
            self.cache_dir = str(Path(DATA_DIR) / "kaggle")
        else:
            self.cache_dir = cache_dir
            
        self.api = None
        self.authenticated = False
        
        # Create cache dir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize API
        self._init_api()

    def _init_api(self):
        """Initialize Kaggle API with credentials."""
        try:
            # Check for KAGGLE_CONFIG env var (HF Spaces Secret)
            kaggle_config = os.getenv("KAGGLE_CONFIG")
            if kaggle_config:
                kaggle_path = Path.home() / ".kaggle"
                kaggle_path.mkdir(exist_ok=True)
                config_file = kaggle_path / "kaggle.json"
                if not config_file.exists():
                    config_file.write_text(kaggle_config)
                    config_file.chmod(0o600)
                    logger.info("✓ Kaggle config created from env var")

            from kaggle.api.kaggle_api_extended import KaggleApi
            self.api = KaggleApi()
            self.api.authenticate()
            self.authenticated = True
            logger.info("✓ Kaggle API authenticated")
        except Exception as e:
            self.authenticated = False
            logger.warning(f"⚠ Kaggle API not authenticated: {e}")

    def discover_datasets_for_domain(self, domain: str, max_results: int = 5) -> List[Dict]:
        """Discover Kaggle datasets relevant to a domain."""
        if not self.authenticated or not self.api:
            logger.warning("Kaggle API not available, using hardcoded high-quality fallbacks")
            return self._get_fallback_datasets(domain)
        
        query_map = {
            "finance": ["financial qa", "stock market sentiment", "finance analysis"],
            "tech": ["technical interview qa", "system design interview", "machine learning research"],
            "healthcare": ["medical qa", "disease symptoms", "healthcare analysis"],
            "insurance": ["insurance faq", "actuarial science", "insurance risk"],
        }
        
        queries = query_map.get(domain, [domain])
        datasets = []
        
        for query in queries:
            try:
                results = self.api.dataset_list(
                    search=query,
                    sort_by="votes",
                    max_size=500 * 1024 * 1024,  # 500MB max for faster distillation
                    page=1
                )
                
                for d in results:
                    datasets.append({
                        "name": str(d.ref),
                        "title": str(d.title),
                        "size_mb": getattr(d, "total_bytes", 0) / (1024 * 1024),
                        "download_count": int(getattr(d, "download_count", 0)),
                        "last_updated": str(getattr(d, "last_updated", "")),
                        "usability_score": float(getattr(d, "usability_rating", 0))
                    })
                    if len(datasets) >= max_results:
                        break
            except Exception as e:
                logger.warning(f"Error discovering {query}: {e}")
        
        return datasets[:max_results]

    def download_dataset(self, dataset_ref: str) -> str:
        """Download dataset from Kaggle."""
        if not self.authenticated or not self.api:
            raise ValueError("Kaggle API not authenticated")
        
        # Use a safe folder name
        safe_name = dataset_ref.replace("/", "_")
        download_path = os.path.join(self.cache_dir, safe_name)
        os.makedirs(download_path, exist_ok=True)
        
        try:
            self.api.dataset_download_files(
                dataset_ref,
                path=download_path,
                unzip=True
            )
            logger.info(f"✓ Downloaded {dataset_ref} to {download_path}")
            return download_path
        except Exception as e:
            logger.error(f"Failed to download {dataset_ref}: {e}")
            raise

    def _get_fallback_datasets(self, domain: str) -> List[Dict]:
        """Default high-quality datasets for each domain."""
        fallbacks = {
            "finance": [
                {"name": "borismarjanovic/price-volume-data-for-all-us-stocks-etfs", "title": "Huge Stock Market Dataset"},
                {"name": "omermetinn/values-of-top-nasdaq-companies", "title": "Nasdaq Top Companies"}
            ],
            "tech": [
                {"name": "arnabchaman/popular-tech-stacks-of-2023", "title": "Popular Tech Stacks"},
                {"name": "lokeshparab/amazon-products-dataset", "title": "Amazon Products"}
            ],
            "healthcare": [
                {"name": "prasad22/healthcare-dataset", "title": "Healthcare Dataset"},
                {"name": "tanishqdublish/medical-costs-dataset", "title": "Medical Costs"}
            ]
        }
        return fallbacks.get(domain, [])
