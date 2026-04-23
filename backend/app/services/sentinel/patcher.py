"""
Sentinel Patcher - Safe Patch Application

Applies safe patches automatically or queues unsafe ones for human review.
Never touches .py files. Never calls any LLM.

SAFE AUTO-APPLY targets (the ONLY files this class may write to automatically):
  1. backend/app/prompts/*.txt - prompt text files only
  2. backend/app/data/sentinel/sentinel_config.json - sentinel config only

EVERYTHING ELSE goes to pending_patches/ for human review.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PatchResult:
    """Represents the result of a patch application."""
    
    def __init__(
        self,
        patch_id: str,
        applied: bool,
        target_file: str,
        change_summary: str,
        requires_human_review: bool
    ):
        self.patch_id = patch_id
        self.applied = applied
        self.target_file = target_file
        self.change_summary = change_summary
        self.requires_human_review = requires_human_review
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "applied": self.applied,
            "target_file": self.target_file,
            "change_summary": self.change_summary,
            "requires_human_review": self.requires_human_review,
            "timestamp": self.timestamp,
        }


from app.config import DATA_DIR, PROMPTS_DIR, SENTINEL_DIR


class SentinelPatcher:
    """Applies safe patches or queues for review."""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self.prompts_dir = PROMPTS_DIR
        self.sentinel_dir = SENTINEL_DIR
        self.pending_dir = self.sentinel_dir / "pending_patches"
        
        # Ensure directories exist
        self.sentinel_dir.mkdir(parents=True, exist_ok=True)
        self.pending_dir.mkdir(parents=True, exist_ok=True)
    
    def apply(self, diagnosis) -> PatchResult:
        """
        Apply a diagnosis as a patch.
        
        Args:
            diagnosis: SentinelDiagnosis object
            
        Returns:
            PatchResult indicating what happened
        """
        patch_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Check if safe to auto-apply
        if diagnosis.safe_to_auto_apply and diagnosis.fix_type == "prompt":
            result = self._apply_prompt_patch(patch_id, diagnosis, timestamp)
        elif diagnosis.safe_to_auto_apply and diagnosis.fix_type == "config":
            result = self._apply_config_patch(patch_id, diagnosis, timestamp)
        else:
            # Queue for human review
            result = self._queue_for_review(patch_id, diagnosis, timestamp)
        
        # Save to patch history
        self._save_patch_history(result)
        
        return result
    
    def approve_pending(self, patch_id: str) -> Optional[PatchResult]:
        """
        Approve and apply a pending patch.
        
        Args:
            patch_id: ID of pending patch
            
        Returns:
            PatchResult or None if not found
        """
        pending_file = self.pending_dir / f"{patch_id}.patch.json"
        
        if not pending_file.exists():
            logger.warning(f"Pending patch not found: {patch_id}")
            return None
        
        try:
            # Load pending patch
            with open(pending_file, 'r') as f:
                patch_data = json.load(f)
            
            diagnosis_data = patch_data.get("diagnosis", {})
            fix_type = diagnosis_data.get("fix_type", "logic")
            
            # Refuse to auto-apply logic or dependency changes even with approval
            if fix_type in ("logic", "dependency"):
                result = PatchResult(
                    patch_id=patch_id,
                    applied=False,
                    target_file=f"pending_patches/{patch_id}.patch.json",
                    change_summary="Cannot auto-apply logic changes even with approval. Manual code change required.",
                    requires_human_review=True
                )
                self._save_patch_history(result)
                return result
            
            # Create a mock diagnosis object for re-application
            class MockDiagnosis:
                def __init__(self, data):
                    self.diagnosis_id = data.get("diagnosis_id")
                    self.alert_id = data.get("alert_id")
                    self.root_cause = data.get("root_cause")
                    self.fix_type = data.get("fix_type")
                    self.safe_to_auto_apply = True  # Force to true for approval
                    self.proposed_fix = data.get("proposed_fix")
                    self.confidence = data.get("confidence")
                    self.reasoning = data.get("reasoning")
                    self.component = patch_data.get("component", "unknown")
            
            diagnosis = MockDiagnosis(diagnosis_data)
            
            # Re-run apply logic with safe_to_auto_apply forced to True
            if fix_type == "prompt":
                result = self._apply_prompt_patch(patch_id, diagnosis, datetime.utcnow().isoformat())
            elif fix_type == "config":
                result = self._apply_config_patch(patch_id, diagnosis, datetime.utcnow().isoformat())
            else:
                result = PatchResult(
                    patch_id=patch_id,
                    applied=False,
                    target_file=f"pending_patches/{patch_id}.patch.json",
                    change_summary=f"Cannot auto-apply {fix_type} changes",
                    requires_human_review=True
                )
            
            # Delete pending file if applied
            if result.applied:
                pending_file.unlink()
            
            self._save_patch_history(result)
            return result
        
        except Exception as e:
            logger.error(f"Failed to approve pending patch {patch_id}: {e}")
            return None
    
    def reject_pending(self, patch_id: str) -> bool:
        """
        Reject a pending patch.
        
        Args:
            patch_id: ID of pending patch
            
        Returns:
            True if rejected, False if not found
        """
        pending_file = self.pending_dir / f"{patch_id}.patch.json"
        
        if not pending_file.exists():
            logger.warning(f"Pending patch not found: {patch_id}")
            return False
        
        try:
            # Record rejection in history
            result = PatchResult(
                patch_id=patch_id,
                applied=False,
                target_file=f"pending_patches/{patch_id}.patch.json",
                change_summary="Rejected by user",
                requires_human_review=False
            )
            self._save_patch_history(result)
            
            # Delete pending file
            pending_file.unlink()
            
            logger.info(f"Rejected pending patch: {patch_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to reject pending patch {patch_id}: {e}")
            return False
    
    def _apply_prompt_patch(self, patch_id: str, diagnosis, timestamp: str) -> PatchResult:
        """Apply a prompt patch."""
        try:
            # Find matching prompt file based on component name
            component = getattr(diagnosis, 'component', diagnosis.alert_id)
            matched_file = self._find_prompt_file(component)
            
            if matched_file is None:
                # No matching prompt file found - queue for review
                return self._queue_for_review(patch_id, diagnosis, timestamp)
            
            # Read current content
            with open(matched_file, 'r') as f:
                current_content = f.read()
            
            # Append sentinel guidance
            patch_comment = f"\n\n# [Sentinel patch {patch_id} at {timestamp}]\n"
            patch_comment += f"# Issue: {diagnosis.root_cause}\n"
            patch_comment += f"# Fix applied: {diagnosis.proposed_fix}\n"
            
            new_content = current_content + patch_comment
            
            # Write back
            with open(matched_file, 'w') as f:
                f.write(new_content)
            
            logger.info(f"Applied prompt patch to {matched_file}")
            
            return PatchResult(
                patch_id=patch_id,
                applied=True,
                target_file=str(matched_file),
                change_summary=f"Appended sentinel guidance to prompt: {diagnosis.proposed_fix[:100]}",
                requires_human_review=False
            )
        
        except Exception as e:
            logger.error(f"Failed to apply prompt patch: {e}")
            return self._queue_for_review(patch_id, diagnosis, timestamp)
    
    def _apply_config_patch(self, patch_id: str, diagnosis, timestamp: str) -> PatchResult:
        """Apply a config patch."""
        try:
            config_file = self.sentinel_dir / "sentinel_config.json"
            
            # Load existing config
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Add patch
            config[f"patch_{patch_id}"] = diagnosis.proposed_fix
            
            # Write back
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Applied config patch: {patch_id}")
            
            return PatchResult(
                patch_id=patch_id,
                applied=True,
                target_file="data/sentinel/sentinel_config.json",
                change_summary=f"Config patch: {diagnosis.proposed_fix[:100]}",
                requires_human_review=False
            )
        
        except Exception as e:
            logger.error(f"Failed to apply config patch: {e}")
            return self._queue_for_review(patch_id, diagnosis, timestamp)
    
    def _queue_for_review(self, patch_id: str, diagnosis, timestamp: str) -> PatchResult:
        """Queue a patch for human review."""
        try:
            pending_file = self.pending_dir / f"{patch_id}.patch.json"
            
            patch_data = {
                "patch_id": patch_id,
                "timestamp": timestamp,
                "diagnosis": diagnosis.to_dict() if hasattr(diagnosis, 'to_dict') else diagnosis,
                "component": getattr(diagnosis, 'component', 'unknown'),
            }
            
            with open(pending_file, 'w') as f:
                json.dump(patch_data, f, indent=2)
            
            logger.info(f"Queued patch for review: {patch_id}")
            
            return PatchResult(
                patch_id=patch_id,
                applied=False,
                target_file=f"pending_patches/{patch_id}.patch.json",
                change_summary=f"Queued for review: {diagnosis.root_cause[:100]}",
                requires_human_review=True
            )
        
        except Exception as e:
            logger.error(f"Failed to queue patch for review: {e}")
            return PatchResult(
                patch_id=patch_id,
                applied=False,
                target_file="error",
                change_summary=f"Failed to queue: {str(e)}",
                requires_human_review=True
            )
    
    def _find_prompt_file(self, component: str) -> Optional[Path]:
        """Find a prompt file matching the component name."""
        if not self.prompts_dir.exists():
            return None
        
        component_lower = component.lower()
        
        # Try exact match first
        for prompt_file in self.prompts_dir.glob("*.txt"):
            if component_lower in prompt_file.stem.lower():
                return prompt_file
        
        # Try fuzzy match
        for prompt_file in self.prompts_dir.glob("*.txt"):
            stem_lower = prompt_file.stem.lower()
            if any(word in stem_lower for word in component_lower.split()):
                return prompt_file
        
        return None
    
    def _save_patch_history(self, result: PatchResult):
        """Save patch result to history."""
        try:
            history_file = self.sentinel_dir / "patch_history.json"
            
            # Load existing history
            if history_file.exists():
                with open(history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Append new result
            history.append(result.to_dict())
            
            # Keep only last 200 entries
            if len(history) > 200:
                history = history[-200:]
            
            # Save back
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save patch history: {e}")
