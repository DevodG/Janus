"""
Prompt evolution through A/B testing and versioning.

Creates prompt variants, tests them, and promotes better versions.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid

logger = logging.getLogger(__name__)


class PromptOptimizer:
    """Manages prompt evolution and A/B testing."""
    
    def __init__(self, data_dir: str, model_fn):
        self.data_dir = Path(data_dir) / "prompt_versions"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_fn = model_fn
    
    async def create_prompt_variant(self, prompt_name: str, current_prompt: str, goal: str) -> Dict[str, Any]:
        """
        Create a new prompt variant using LLM.
        
        Args:
            prompt_name: Name of the prompt (e.g., "research", "verifier")
            current_prompt: Current prompt text
            goal: Optimization goal (e.g., "improve clarity", "reduce tokens")
            
        Returns:
            Prompt variant with metadata
        """
        logger.info(f"Creating prompt variant for {prompt_name} with goal: {goal}")
        
        optimization_prompt = f"""You are a prompt engineering expert. Improve the following prompt based on this goal: {goal}

Current prompt:
{current_prompt}

Create an improved version that:
1. Maintains the same core functionality
2. {goal}
3. Is clear and actionable

Improved prompt:"""
        
        try:
            improved_prompt = await self.model_fn(optimization_prompt, max_tokens=2000)
            
            variant = {
                "id": str(uuid.uuid4()),
                "prompt_name": prompt_name,
                "version": self._get_next_version(prompt_name),
                "prompt_text": improved_prompt,
                "goal": goal,
                "status": "testing",
                "created_at": datetime.utcnow().isoformat(),
                "test_count": 0,
                "win_count": 0,
                "win_rate": 0.0,
            }
            
            self._save_variant(variant)
            logger.info(f"Created prompt variant: {variant['id']} (v{variant['version']})")
            
            return variant
        
        except Exception as e:
            logger.error(f"Failed to create prompt variant: {e}")
            raise
    
    async def test_prompt_variant(self, variant_id: str, test_input: str, expected_quality: str) -> Dict[str, Any]:
        """
        Test a prompt variant with sample input.
        
        Args:
            variant_id: Variant ID
            test_input: Test input
            expected_quality: Expected quality criteria
            
        Returns:
            Test results
        """
        variant = self._load_variant(variant_id)
        if not variant:
            raise ValueError(f"Variant not found: {variant_id}")
        
        logger.info(f"Testing prompt variant: {variant_id}")
        
        try:
            # Run the prompt with test input
            test_prompt = variant["prompt_text"].replace("{input}", test_input)
            output = await self.model_fn(test_prompt, max_tokens=1000)
            
            # Evaluate quality
            quality_score = await self._evaluate_quality(output, expected_quality)
            
            # Update variant stats
            variant["test_count"] += 1
            if quality_score >= 0.7:  # Consider it a "win" if quality >= 70%
                variant["win_count"] += 1
            variant["win_rate"] = variant["win_count"] / variant["test_count"]
            
            self._save_variant(variant)
            
            return {
                "variant_id": variant_id,
                "quality_score": quality_score,
                "output": output,
                "win_rate": variant["win_rate"],
            }
        
        except Exception as e:
            logger.error(f"Failed to test prompt variant: {e}")
            raise
    
    def compare_prompts(self, variant_id_a: str, variant_id_b: str) -> Dict[str, Any]:
        """
        Compare two prompt variants.
        
        Args:
            variant_id_a: First variant ID
            variant_id_b: Second variant ID
            
        Returns:
            Comparison results
        """
        variant_a = self._load_variant(variant_id_a)
        variant_b = self._load_variant(variant_id_b)
        
        if not variant_a or not variant_b:
            raise ValueError("One or both variants not found")
        
        return {
            "variant_a": {
                "id": variant_a["id"],
                "version": variant_a["version"],
                "win_rate": variant_a["win_rate"],
                "test_count": variant_a["test_count"],
            },
            "variant_b": {
                "id": variant_b["id"],
                "version": variant_b["version"],
                "win_rate": variant_b["win_rate"],
                "test_count": variant_b["test_count"],
            },
            "winner": variant_a["id"] if variant_a["win_rate"] > variant_b["win_rate"] else variant_b["id"],
        }
    
    def promote_prompt(self, variant_id: str, min_tests: int = 10, min_win_rate: float = 0.7) -> bool:
        """
        Promote a prompt variant to production.
        
        Args:
            variant_id: Variant ID
            min_tests: Minimum number of tests required
            min_win_rate: Minimum win rate required
            
        Returns:
            True if promoted, False otherwise
        """
        variant = self._load_variant(variant_id)
        if not variant:
            raise ValueError(f"Variant not found: {variant_id}")
        
        # Validate promotion criteria
        if variant["test_count"] < min_tests:
            logger.warning(f"Variant {variant_id} has insufficient tests: {variant['test_count']} < {min_tests}")
            return False
        
        if variant["win_rate"] < min_win_rate:
            logger.warning(f"Variant {variant_id} has insufficient win rate: {variant['win_rate']} < {min_win_rate}")
            return False
        
        # Archive current production version
        current_production = self._get_production_variant(variant["prompt_name"])
        if current_production:
            current_production["status"] = "archived"
            current_production["archived_at"] = datetime.utcnow().isoformat()
            self._save_variant(current_production)
        
        # Promote variant
        variant["status"] = "production"
        variant["promoted_at"] = datetime.utcnow().isoformat()
        self._save_variant(variant)
        
        logger.info(f"Promoted prompt variant {variant_id} to production")
        return True
    
    def archive_prompt(self, variant_id: str):
        """Archive a prompt variant."""
        variant = self._load_variant(variant_id)
        if not variant:
            raise ValueError(f"Variant not found: {variant_id}")
        
        variant["status"] = "archived"
        variant["archived_at"] = datetime.utcnow().isoformat()
        self._save_variant(variant)
        
        logger.info(f"Archived prompt variant: {variant_id}")
    
    def list_versions(self, prompt_name: str) -> List[Dict[str, Any]]:
        """List all versions of a prompt."""
        versions = []
        
        for file_path in self.data_dir.glob(f"{prompt_name}_*.json"):
            try:
                with open(file_path, 'r') as f:
                    variant = json.load(f)
                versions.append(variant)
            except Exception as e:
                logger.error(f"Failed to read variant {file_path}: {e}")
        
        # Sort by version descending
        versions.sort(key=lambda x: x.get("version", 0), reverse=True)
        return versions
    
    def _save_variant(self, variant: Dict[str, Any]):
        """Save a prompt variant to disk."""
        file_path = self.data_dir / f"{variant['prompt_name']}_{variant['id']}.json"
        with open(file_path, 'w') as f:
            json.dump(variant, f, indent=2)
    
    def _load_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Load a prompt variant from disk."""
        for file_path in self.data_dir.glob(f"*_{variant_id}.json"):
            with open(file_path, 'r') as f:
                return json.load(f)
        return None
    
    def _get_production_variant(self, prompt_name: str) -> Optional[Dict[str, Any]]:
        """Get the current production variant for a prompt."""
        for file_path in self.data_dir.glob(f"{prompt_name}_*.json"):
            try:
                with open(file_path, 'r') as f:
                    variant = json.load(f)
                if variant.get("status") == "production":
                    return variant
            except Exception as e:
                logger.error(f"Failed to read variant {file_path}: {e}")
        return None
    
    def _get_next_version(self, prompt_name: str) -> int:
        """Get the next version number for a prompt."""
        versions = self.list_versions(prompt_name)
        if not versions:
            return 1
        return max(v.get("version", 0) for v in versions) + 1
    
    async def _evaluate_quality(self, output: str, expected_quality: str) -> float:
        """Evaluate output quality using LLM."""
        eval_prompt = f"""Evaluate the quality of this output based on the criteria: {expected_quality}

Output:
{output}

Rate the quality from 0.0 to 1.0, where:
- 0.0 = Completely fails criteria
- 0.5 = Partially meets criteria
- 1.0 = Fully meets criteria

Provide only the numeric score:"""
        
        try:
            score_text = await self.model_fn(eval_prompt, max_tokens=10)
            score = float(score_text.strip())
            return max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except Exception as e:
            logger.error(f"Failed to evaluate quality: {e}")
            return 0.5  # Default to neutral score
