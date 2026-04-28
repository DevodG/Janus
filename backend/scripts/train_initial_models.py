#!/usr/bin/env python
"""
Train initial models from Kaggle datasets.
"""

import asyncio
import sys
import os
import logging

# Add backend and app to path
sys.path.append(os.path.join(os.getcwd(), "backend"))
sys.path.append(os.path.join(os.getcwd(), "backend", "app"))

from app.services.model_training_scheduler import ModelTrainingScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger("TRAIN")

async def main():
    logger.info("Starting initial model training...")
    
    # Ensure data dirs exist
    from app.config import ensure_data_dirs
    ensure_data_dirs()
    
    scheduler = ModelTrainingScheduler()
    
    domains = ["finance", "tech", "healthcare"]
    results = await scheduler.train_all_domains(domains)
    
    print("\n" + "="*50)
    print("TRAINING RESULTS")
    print("="*50)
    for domain, meta in results.items():
        if "error" in meta:
            print(f"✗ {domain}: FAILED - {meta['error']}")
        else:
            print(f"✓ {domain}: SUCCESS - {meta.get('selected_pairs', 0)} pairs, {meta.get('size_kb', 0):.1f} KB")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
