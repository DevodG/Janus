"""
Scheduled model training and persistence sync.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import List, Dict

from app.services.kaggle_integration import KaggleIntegration
from app.services.distillation_engine import KnowledgeDistiller
from app.services.curation.persistence_manager import PersistenceManager

logger = logging.getLogger(__name__)

class ModelTrainingScheduler:
    """Manages continuous model training and HF sync."""
    
    def __init__(self):
        self.kaggle = KaggleIntegration()
        self.distiller = KnowledgeDistiller()
        self.persistence = PersistenceManager()
        self.is_training = False

    async def train_all_domains(self, domains: List[str] = ["finance", "tech", "healthcare"]):
        """Discover, download, distill, and sync models for all domains."""
        if self.is_training:
            logger.warning("Training already in progress, skipping.")
            return

        self.is_training = True
        results = {}
        
        try:
            for domain in domains:
                logger.info(f"--- Starting Training Loop for {domain} ---")
                
                # 1. Discover
                datasets = self.kaggle.discover_datasets_for_domain(domain, max_results=2)
                if not datasets:
                    logger.warning(f"No datasets found for {domain}")
                    continue
                
                # 2. Download and Distill
                best_ds = datasets[0]
                try:
                    ds_path = self.kaggle.download_dataset(best_ds['name'])
                    metadata = self.distiller.distill_dataset_to_model(
                        ds_path, 
                        domain, 
                        f"{domain}_model_{datetime.now().strftime('%Y%m%d')}"
                    )
                    results[domain] = metadata
                except Exception as e:
                    logger.error(f"Failed to process {domain}: {e}")
                    results[domain] = {"error": str(e)}

            # 3. Sync to HF
            logger.info("Syncing new models to Hugging Face...")
            self.persistence.upload_all()
            
        finally:
            self.is_training = False
            
        return results

    async def start_schedule(self, interval_hours: int = 168):
        """Background loop for weekly training."""
        logger.info(f"Model training schedule started (every {interval_hours} hours)")
        while True:
            # Wait for interval
            await asyncio.sleep(interval_hours * 3600)
            
            try:
                await self.train_all_domains()
            except Exception as e:
                logger.error(f"Scheduled training failed: {e}")
