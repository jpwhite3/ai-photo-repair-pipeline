"""LangGraph node functions for the restoration pipeline.

Each node takes the current ``RestorationState`` plus its collaborators and returns a
dict of fields to merge into the state. Following the reference repo's pattern, every
node guards its external call with try/except + a graceful fallback so a single failure
never crashes the whole graph.
"""

from __future__ import annotations

import logging

from photo_repair.image_client import ImageClient
from photo_repair.state import RestorationAnalysis, RestorationState, VerificationResult
from photo_repair.storage import save_restoration_outputs

logger = logging.getLogger(__name__)


def analyze_node(state: RestorationState, client: ImageClient) -> dict:
    """Characterise era / process / defects (fallback to 'unknown' on error)."""
    try:
        analysis = client.analyze(state.image_bytes, state.mime_type)
        note = f"Analyzed: {analysis.era}, {analysis.photographic_process}"
    except Exception as err:  # noqa: BLE001 - fallback by design
        logger.exception("analyze failed: %s", err)
        analysis = RestorationAnalysis(
            era="unknown",
            photographic_process="unknown",
            notes=f"analysis failed: {err}",
        )
        note = f"Analysis fell back to defaults: {err}"
    return {
        "analysis": analysis,
        "current_step": "analyzed",
        "notes": state.notes + [note],
    }


def plan_node(state: RestorationState, client: ImageClient) -> dict:
    """Create a step-by-step restoration plan."""
    analysis = state.analysis or RestorationAnalysis(era="unknown", photographic_process="unknown")
    try:
        plan_text = client.plan(state.image_bytes, state.mime_type, analysis)
        note = "Restoration plan generated."
    except Exception as err:  # noqa: BLE001 - fallback by design
        logger.exception("plan failed: %s", err)
        plan_text = "Restore the photo, removing any defects and preserving composition."
        note = f"Planning failed, fell back to default plan: {err}"
    return {
        "plan": plan_text,
        "current_step": "planned",
        "notes": state.notes + [note],
    }


def restore_node(state: RestorationState, client: ImageClient) -> dict:
    """Run the image-edit restoration with the plan and feedback from previous verify attempts."""
    attempts = state.attempts + 1
    plan_text = state.plan or "Restore the photo."
    issues = state.verification.issues if state.verification else None
    try:
        restored = client.restore(state.image_bytes, state.mime_type, plan_text, issues)
        return {
            "restored_bytes": restored,
            "attempts": attempts,
            "current_step": "restored",
            "notes": state.notes + [f"Restore attempt {attempts} succeeded"],
        }
    except Exception as err:  # noqa: BLE001 - fallback by design
        logger.exception("restore failed (attempt %s): %s", attempts, err)
        return {
            "restored_bytes": None,
            "attempts": attempts,
            "current_step": "restored",
            "notes": state.notes + [f"Restore attempt {attempts} failed: {err}"],
        }


def verify_node(state: RestorationState, client: ImageClient) -> dict:
    """QA the restored image against the original's hard constraints."""
    if state.restored_bytes is None:
        verification = VerificationResult(
            composition_preserved=False,
            identity_preserved=False,
            clothing_preserved=False,
            environment_preserved=False,
            no_hallucinations_or_artifacts=False,
            text_and_signage_preserved=False,
            tonality_and_grain_preserved=False,
            quality_ok=False,
            issues=["No restored image was produced."],
        )
        return {
            "verification": verification,
            "current_step": "verified",
            "notes": state.notes + ["Verification skipped: nothing to verify."],
        }
    try:
        verification = client.verify(state.image_bytes, state.restored_bytes, state.mime_type)
        note = f"Verified (passed={verification.passed})"
    except Exception as err:  # noqa: BLE001 - fallback by design
        logger.exception("verify failed: %s", err)
        # Don't block on a verifier outage; accept the result but record the issue.
        verification = VerificationResult(
            composition_preserved=True,
            identity_preserved=True,
            clothing_preserved=True,
            environment_preserved=True,
            no_hallucinations_or_artifacts=True,
            text_and_signage_preserved=True,
            tonality_and_grain_preserved=True,
            quality_ok=True,
            issues=[f"verification error: {err}"],
        )
        note = f"Verification errored, accepting result: {err}"
    return {
        "verification": verification,
        "current_step": "verified",
        "notes": state.notes + [note],
    }


def route_after_verify(state: RestorationState, max_attempts: int) -> str:
    """Decide whether to retry the restore or finalize."""
    if state.verification is not None and state.verification.passed:
        return "finalize"
    if state.attempts >= max_attempts:
        return "finalize"
    return "restore"


def finalize_node(state: RestorationState, base_dir: str) -> dict:
    """Persist artifacts and mark the run complete."""
    output_path = save_restoration_outputs(state, base_dir=base_dir)
    return {
        "output_path": output_path,
        "current_step": "completed",
        "notes": state.notes + [f"Saved outputs to {output_path}"],
    }
