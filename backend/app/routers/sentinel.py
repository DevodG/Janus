"""
Sentinel Router - API Endpoints

Provides REST API for sentinel monitoring and control.
"""

import logging
import os
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.sentinel.sentinel_engine import SentinelEngine
from app.services.sentinel.patcher import SentinelPatcher
from app.services.sentinel.capability_tracker import CapabilityTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sentinel", tags=["sentinel"])

# Initialize services
engine = SentinelEngine()
patcher = SentinelPatcher()
tracker = CapabilityTracker()


# ── Request/Response Models ───────────────────────────────────────────────────

class PatchApprovalRequest(BaseModel):
    """Request to approve a pending patch."""
    pass


class PatchRejectionRequest(BaseModel):
    """Request to reject a pending patch."""
    pass


# ── Helper Functions ──────────────────────────────────────────────────────────

def _disabled_response():
    """Return response when sentinel is disabled."""
    return {
        "sentinel_enabled": False,
        "message": "Sentinel layer is disabled. Set SENTINEL_ENABLED=true to enable."
    }


def _check_enabled():
    """Check if sentinel is enabled, raise HTTPException if not."""
    if not os.getenv("SENTINEL_ENABLED", "true").lower() == "true":
        raise HTTPException(status_code=503, detail="Sentinel layer is disabled")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
def get_status():
    """
    Get current sentinel status.
    
    Returns:
        Status dict with health metrics
    """
    if not os.getenv("SENTINEL_ENABLED", "true").lower() == "true":
        return _disabled_response()
    
    try:
        return engine.get_status()
    except Exception as e:
        logger.error(f"Failed to get sentinel status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get sentinel status")


@router.get("/alerts")
def get_alerts(limit: int = 50):
    """
    Get recent alerts.
    
    Args:
        limit: Maximum number of alerts to return
        
    Returns:
        List of recent alerts
    """
    _check_enabled()
    
    try:
        from pathlib import Path
        import json
        
        sentinel_dir = Path("backend/app/data/sentinel")
        alert_file = sentinel_dir / "alert_history.json"
        
        if not alert_file.exists():
            return []
        
        with open(alert_file, 'r') as f:
            alerts = json.load(f)
        
        # Return most recent alerts
        return alerts[-limit:] if len(alerts) > limit else alerts
    
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get alerts")


@router.get("/patches")
def get_patches(limit: int = 50):
    """
    Get recent patches.
    
    Args:
        limit: Maximum number of patches to return
        
    Returns:
        List of recent patches
    """
    _check_enabled()
    
    try:
        from pathlib import Path
        import json
        
        sentinel_dir = Path("backend/app/data/sentinel")
        patch_file = sentinel_dir / "patch_history.json"
        
        if not patch_file.exists():
            return []
        
        with open(patch_file, 'r') as f:
            patches = json.load(f)
        
        # Return most recent patches
        return patches[-limit:] if len(patches) > limit else patches
    
    except Exception as e:
        logger.error(f"Failed to get patches: {e}")
        raise HTTPException(status_code=500, detail="Failed to get patches")


@router.get("/patches/pending")
def get_pending_patches():
    """
    Get pending patches awaiting human review.
    
    Returns:
        List of pending patches
    """
    _check_enabled()
    
    try:
        from pathlib import Path
        import json
        
        sentinel_dir = Path("backend/app/data/sentinel")
        pending_dir = sentinel_dir / "pending_patches"
        
        if not pending_dir.exists():
            return []
        
        pending = []
        
        for patch_file in pending_dir.glob("*.patch.json"):
            try:
                with open(patch_file, 'r') as f:
                    patch_data = json.load(f)
                pending.append(patch_data)
            except Exception as e:
                logger.warning(f"Failed to read pending patch {patch_file}: {e}")
                continue
        
        return pending
    
    except Exception as e:
        logger.error(f"Failed to get pending patches: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pending patches")


@router.post("/patches/{patch_id}/approve")
def approve_patch(patch_id: str, request: PatchApprovalRequest):
    """
    Approve and apply a pending patch.
    
    Args:
        patch_id: ID of pending patch
        request: Approval request (empty body)
        
    Returns:
        PatchResult
    """
    _check_enabled()
    
    try:
        result = patcher.approve_pending(patch_id)
        
        if result is None:
            raise HTTPException(status_code=404, detail="Pending patch not found")
        
        return result.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve patch {patch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve patch")


@router.post("/patches/{patch_id}/reject")
def reject_patch(patch_id: str, request: PatchRejectionRequest):
    """
    Reject a pending patch.
    
    Args:
        patch_id: ID of pending patch
        request: Rejection request (empty body)
        
    Returns:
        Success message
    """
    _check_enabled()
    
    try:
        success = patcher.reject_pending(patch_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Pending patch not found")
        
        return {"rejected": True, "patch_id": patch_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject patch {patch_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject patch")


@router.get("/capability")
def get_capability_trend(days: int = 7):
    """
    Get capability trend over specified days.
    
    Args:
        days: Number of days to look back
        
    Returns:
        List of capability snapshots
    """
    _check_enabled()
    
    try:
        return tracker.trend(days=days)
    
    except Exception as e:
        logger.error(f"Failed to get capability trend: {e}")
        raise HTTPException(status_code=500, detail="Failed to get capability trend")


@router.get("/capability/current")
def get_current_capability():
    """
    Get current capability snapshot.
    
    Returns:
        Current capability snapshot
    """
    _check_enabled()
    
    try:
        snapshot = tracker.snapshot()
        return snapshot.to_dict()
    
    except Exception as e:
        logger.error(f"Failed to get current capability: {e}")
        raise HTTPException(status_code=500, detail="Failed to get current capability")


@router.post("/run-now")
def run_cycle_now():
    """
    Trigger a sentinel cycle immediately.
    
    Returns:
        Cycle report
    """
    _check_enabled()
    
    try:
        report = engine.run_cycle()
        return report.dict()
    
    except Exception as e:
        logger.error(f"Failed to run sentinel cycle: {e}")
        raise HTTPException(status_code=500, detail="Failed to run sentinel cycle")


@router.get("/cycle-history")
def get_cycle_history(limit: int = 20):
    """
    Get recent cycle history.
    
    Args:
        limit: Maximum number of cycles to return
        
    Returns:
        List of recent cycle reports
    """
    _check_enabled()
    
    try:
        from pathlib import Path
        import json
        
        sentinel_dir = Path("backend/app/data/sentinel")
        history_file = sentinel_dir / "cycle_history.json"
        
        if not history_file.exists():
            return []
        
        with open(history_file, 'r') as f:
            history = json.load(f)
        
        # Return most recent cycles
        return history[-limit:] if len(history) > limit else history
    
    except Exception as e:
        logger.error(f"Failed to get cycle history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cycle history")
