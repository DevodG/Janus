"""
Sentinel Diagnostician - Issue Diagnosis using LLM

Takes a SentinelAlert, asks the existing free LLM to diagnose it,
returns a structured SentinelDiagnosis.

CRITICAL: Uses ONLY call_model() from app.agents._model for all LLM calls.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

# MANDATORY IMPORT - use this and only this for LLM calls
from app.agents._model import call_model

logger = logging.getLogger(__name__)


class SentinelDiagnosis:
    """Represents a diagnosis of a system alert."""
    
    def __init__(
        self,
        alert_id: str,
        root_cause: str,
        fix_type: str,
        safe_to_auto_apply: bool,
        proposed_fix: str,
        confidence: float,
        reasoning: str
    ):
        self.diagnosis_id = str(uuid.uuid4())
        self.alert_id = alert_id
        self.root_cause = root_cause
        self.fix_type = fix_type
        self.safe_to_auto_apply = safe_to_auto_apply
        self.proposed_fix = proposed_fix
        self.confidence = confidence
        self.reasoning = reasoning
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "alert_id": self.alert_id,
            "root_cause": self.root_cause,
            "fix_type": self.fix_type,
            "safe_to_auto_apply": self.safe_to_auto_apply,
            "proposed_fix": self.proposed_fix,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }


class SentinelDiagnostician:
    """Diagnoses system alerts using LLM."""
    
    def diagnose(self, alert) -> SentinelDiagnosis:
        """
        Diagnose a system alert using the free LLM.
        
        Args:
            alert: SentinelAlert object to diagnose
            
        Returns:
            SentinelDiagnosis with root cause and proposed fix
        """
        system_prompt = """You are a system diagnostician for an AI orchestration platform called MiroOrg. Your job is to analyze system alerts and propose safe fixes.

You MUST respond with ONLY valid JSON. No markdown. No code fences. No explanation text before or after. Just the raw JSON object.

The JSON must have exactly these fields:
{
  "root_cause": "string describing what caused this issue",
  "fix_type": "one of: config | prompt | logic | dependency | data",
  "safe_to_auto_apply": false,
  "proposed_fix": "string describing the specific fix to apply",
  "confidence": 0.0,
  "reasoning": "string explaining your diagnosis"
}

IMPORTANT RULES for safe_to_auto_apply:
- Set true ONLY if fix_type is "prompt" (editing a .txt prompt file) or "config" (changing a JSON config value)
- Set false for fix_type "logic" (Python code changes)
- Set false for fix_type "dependency" (package changes)
- Set false for fix_type "data" (data migrations)
- When in doubt: set false. Human review is always safer.
- NEVER suggest auto-applying changes to .py files.

Set confidence between 0.0 and 1.0 based on how certain you are."""

        layer_names = {
            1: "Core Platform",
            2: "Agents",
            3: "Domain Packs",
            4: "Simulation",
            5: "Knowledge Evolution",
            6: "Sentinel"
        }
        
        prompt = f"""Analyze this system alert and diagnose the root cause:

Alert ID: {alert.alert_id}
Layer: {alert.layer} ({layer_names.get(alert.layer, 'Unknown')})
Component: {alert.component}
Issue Type: {alert.issue_type}
Severity: {alert.severity}
Evidence: {alert.raw_evidence}

What is the most likely root cause and what is the safest fix?
Remember: respond with ONLY the JSON object, nothing else."""

        try:
            # Call the existing free LLM
            raw_response = call_model(
                prompt=prompt,
                mode="chat",
                system_prompt=system_prompt
            )
            
            # Parse response
            diagnosis_data = self._parse_llm_response(raw_response)
            
            if diagnosis_data is None:
                # Parse failed - return fallback diagnosis
                return SentinelDiagnosis(
                    alert_id=alert.alert_id,
                    root_cause="Could not parse LLM response",
                    fix_type="logic",
                    safe_to_auto_apply=False,
                    proposed_fix="Manual investigation required",
                    confidence=0.0,
                    reasoning=f"JSON parse failed. Raw response: {raw_response[:200]}"
                )
            
            # Create diagnosis from parsed data
            return SentinelDiagnosis(
                alert_id=alert.alert_id,
                root_cause=diagnosis_data.get("root_cause", "Unknown"),
                fix_type=diagnosis_data.get("fix_type", "logic"),
                safe_to_auto_apply=diagnosis_data.get("safe_to_auto_apply", False),
                proposed_fix=diagnosis_data.get("proposed_fix", "No fix proposed"),
                confidence=float(diagnosis_data.get("confidence", 0.0)),
                reasoning=diagnosis_data.get("reasoning", "No reasoning provided")
            )
        
        except Exception as e:
            logger.warning(f"Diagnosis failed for alert {alert.alert_id}: {e}")
            
            # Return fallback diagnosis
            return SentinelDiagnosis(
                alert_id=alert.alert_id,
                root_cause=f"Diagnosis error: {str(e)}",
                fix_type="logic",
                safe_to_auto_apply=False,
                proposed_fix="Manual investigation required",
                confidence=0.0,
                reasoning=f"Exception during diagnosis: {str(e)}"
            )
    
    def _parse_llm_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse LLM response, handling markdown and other formatting.
        
        Args:
            raw_response: Raw string from LLM
            
        Returns:
            Parsed dict or None if parse failed
        """
        try:
            # Strip markdown code fences if present
            cleaned = raw_response.strip()
            
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Validate required fields
            required_fields = ["root_cause", "fix_type", "safe_to_auto_apply", "proposed_fix", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data:
                    logger.warning(f"Missing required field in LLM response: {field}")
                    return None
            
            # Validate fix_type
            valid_fix_types = ["config", "prompt", "logic", "dependency", "data"]
            if data["fix_type"] not in valid_fix_types:
                logger.warning(f"Invalid fix_type: {data['fix_type']}")
                data["fix_type"] = "logic"
            
            # Validate confidence
            try:
                data["confidence"] = float(data["confidence"])
                data["confidence"] = max(0.0, min(1.0, data["confidence"]))
            except:
                data["confidence"] = 0.0
            
            return data
        
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected parse error: {e}")
            return None
