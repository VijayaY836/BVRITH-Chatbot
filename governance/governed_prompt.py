"""
Gov-5: the governed system prompt now lives in app.py itself (GOVERNED_SYSTEM_PROMPT is the
production default in app._answer_with_context) so there's a single source of truth. This
module just re-exports it for governance scripts that need to pass it explicitly as
base_prompt= when re-scanning against it (e.g. to compare against BASE_GROUNDING_PROMPT).
"""
from app import BASE_GROUNDING_PROMPT, GOVERNANCE_ADDENDUM, GOVERNED_SYSTEM_PROMPT

__all__ = ["BASE_GROUNDING_PROMPT", "GOVERNANCE_ADDENDUM", "GOVERNED_SYSTEM_PROMPT"]
