"""
Skill distillation from repeated patterns in case execution.

Detects patterns in successful cases and distills them into reusable skills.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from collections import Counter

logger = logging.getLogger(__name__)


class SkillDistiller:
    """Distills skills from execution patterns."""
    
    def __init__(self, data_dir: str, model_fn):
        self.data_dir = Path(data_dir) / "skills"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.model_fn = model_fn
    
    def detect_skill_candidates(self, cases: List[Dict[str, Any]], min_frequency: int = 3) -> List[Dict[str, Any]]:
        """
        Detect skill candidates from case patterns.
        
        Args:
            cases: List of case records
            min_frequency: Minimum frequency for a pattern to be considered
            
        Returns:
            List of skill candidates
        """
        logger.info(f"Detecting skill candidates from {len(cases)} cases")
        
        # Extract patterns
        domain_patterns = Counter()
        source_patterns = Counter()
        agent_patterns = Counter()
        
        for case in cases:
            route = case.get("route", {})
            domain = route.get("domain_pack") or route.get("domain")
            if domain:
                domain_patterns[domain] += 1
            
            # Extract sources from research output
            raw_outputs = case.get("outputs", {})
            if isinstance(raw_outputs, list):
                outputs = {
                    output.get("agent"): output.get("details", {})
                    for output in raw_outputs
                    if isinstance(output, dict) and output.get("agent")
                }
            elif isinstance(raw_outputs, dict):
                outputs = raw_outputs
            else:
                outputs = {}

            research_output = outputs.get("research", {})
            sources = research_output.get("sources", [])
            for source in sources:
                source_patterns[source] += 1
            
            # Extract agent sequence
            agent_sequence = tuple(outputs.keys())
            agent_patterns[agent_sequence] += 1
        
        # Find frequent patterns
        candidates = []
        
        for domain, count in domain_patterns.items():
            if count >= min_frequency:
                candidates.append({
                    "type": "domain_expertise",
                    "domain": domain,
                    "frequency": count,
                    "confidence": count / len(cases),
                })
        
        for source, count in source_patterns.items():
            if count >= min_frequency:
                candidates.append({
                    "type": "preferred_source",
                    "source": source,
                    "frequency": count,
                    "confidence": count / len(cases),
                })
        
        for agent_seq, count in agent_patterns.items():
            if count >= min_frequency:
                candidates.append({
                    "type": "agent_workflow",
                    "agents": list(agent_seq),
                    "frequency": count,
                    "confidence": count / len(cases),
                })
        
        logger.info(f"Detected {len(candidates)} skill candidates")
        return candidates
    
    async def distill_skill(self, candidate: Dict[str, Any], example_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Distill a skill from a candidate pattern.
        
        Args:
            candidate: Skill candidate
            example_cases: Example cases demonstrating the pattern
            
        Returns:
            Distilled skill
        """
        logger.info(f"Distilling skill from candidate: {candidate['type']}")
        
        # Generate skill description using LLM
        examples_text = "\n\n".join([
            f"Case {i+1}:\nInput: {case.get('user_input', '')}\nOutput: {case.get('final_answer', '')}"
            for i, case in enumerate(example_cases[:3])
        ])
        
        distill_prompt = f"""Analyze these successful cases and create a reusable skill description.

Pattern type: {candidate['type']}
Pattern details: {json.dumps(candidate, indent=2)}

Example cases:
{examples_text}

Create a skill that includes:
1. A clear name
2. Trigger patterns (when to use this skill)
3. Recommended agents
4. Preferred sources
5. Expected outcomes

Skill (JSON format):"""
        
        try:
            skill_text = await self.model_fn(distill_prompt, max_tokens=1000)
            
            # Parse skill (basic fallback if LLM doesn't return valid JSON)
            try:
                skill = json.loads(skill_text)
            except json.JSONDecodeError:
                skill = {
                    "name": f"{candidate['type']}_skill",
                    "description": skill_text,
                    "trigger_patterns": [],
                    "recommended_agents": [],
                    "preferred_sources": [],
                }
            
            # Add metadata
            skill["id"] = f"{candidate['type']}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            skill["type"] = candidate["type"]
            skill["frequency"] = candidate["frequency"]
            skill["confidence"] = candidate["confidence"]
            skill["created_at"] = datetime.utcnow().isoformat()
            skill["usage_count"] = 0
            skill["success_count"] = 0
            skill["success_rate"] = 0.0
            
            self._save_skill(skill)
            logger.info(f"Distilled skill: {skill['id']}")
            
            return skill
        
        except Exception as e:
            logger.error(f"Failed to distill skill: {e}")
            raise
    
    async def test_skill(self, skill_id: str, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a skill with a test case.
        
        Args:
            skill_id: Skill ID
            test_case: Test case
            
        Returns:
            Test results
        """
        skill = self._load_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        logger.info(f"Testing skill: {skill_id}")
        
        # Check if skill triggers match test case
        triggers_match = self._check_triggers(skill, test_case)
        
        return {
            "skill_id": skill_id,
            "triggers_match": triggers_match,
            "test_case_id": test_case.get("case_id"),
        }
    
    def apply_skill(self, skill_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a skill to a context.
        
        Args:
            skill_id: Skill ID
            context: Execution context
            
        Returns:
            Skill application results
        """
        skill = self._load_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")
        
        logger.info(f"Applying skill: {skill_id}")
        
        # Update usage stats
        skill["usage_count"] += 1
        self._save_skill(skill)
        
        return {
            "skill_id": skill_id,
            "recommended_agents": skill.get("recommended_agents", []),
            "preferred_sources": skill.get("preferred_sources", []),
            "expected_outcomes": skill.get("expected_outcomes", []),
        }
    
    def record_skill_outcome(self, skill_id: str, success: bool):
        """Record the outcome of a skill application."""
        skill = self._load_skill(skill_id)
        if not skill:
            return
        
        if success:
            skill["success_count"] += 1
        
        if skill["usage_count"] > 0:
            skill["success_rate"] = skill["success_count"] / skill["usage_count"]
        
        self._save_skill(skill)
        logger.info(f"Recorded skill outcome: {skill_id} (success={success})")
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """List all skills."""
        skills = []
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    skill = json.load(f)
                skills.append(skill)
            except Exception as e:
                logger.error(f"Failed to read skill {file_path}: {e}")
        
        # Sort by success rate descending
        skills.sort(key=lambda x: x.get("success_rate", 0), reverse=True)
        return skills
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by ID."""
        return self._load_skill(skill_id)
    
    def _save_skill(self, skill: Dict[str, Any]):
        """Save a skill to disk."""
        file_path = self.data_dir / f"{skill['id']}.json"
        with open(file_path, 'w') as f:
            json.dump(skill, f, indent=2)
    
    def _load_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Load a skill from disk."""
        file_path = self.data_dir / f"{skill_id}.json"
        if not file_path.exists():
            return None
        
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _check_triggers(self, skill: Dict[str, Any], test_case: Dict[str, Any]) -> bool:
        """Check if skill triggers match a test case."""
        trigger_patterns = skill.get("trigger_patterns", [])
        if not trigger_patterns:
            return True  # No triggers means always applicable
        
        user_input = test_case.get("user_input", "").lower()
        
        for pattern in trigger_patterns:
            if pattern.lower() in user_input:
                return True
        
        return False
