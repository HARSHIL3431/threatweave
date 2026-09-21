"""Strict validation of LLM outputs before they reach the API client.

The raw LLM output is treated as untrusted. Before acceptance it must:
  1. Parse as a single JSON object.
  2. Contain all required fields with correct types.
  3. Use non-empty strings where required.
  4. Use confidence values from the allowed enum: low | medium | high.
  5. Reference ONLY technique IDs supplied by the RAG context.
  6. Match the RAG-supplied technique name for every referenced ID.
  7. Yield an empty potential_attack_context when no RAG context exists.

Any violation raises LLMValidationErrorException with structured details. The
output is never silently accepted and never corrupts the detection result.
"""
import json
from typing import Any, Dict, List, Mapping

from app.core.exceptions import LLMValidationErrorException
from app.schemas.llm import LLMExplanationOutput, PotentialAttackContext

_REQUIRED_FIELDS = {
    "summary": "str",
    "anomaly_assessment": "str",
    "observed_indicators": "list",
    "potential_attack_context": "list",
    "recommended_actions": "list",
    "limitations": "list",
}
_ALLOWED_CONFIDENCE = {"low", "medium", "high"}


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def validate_llm_output(
    raw: str,
    allowed_technique_ids: Mapping[str, str],
) -> LLMExplanationOutput:
    """Validate raw LLM JSON against the schema and RAG grounding constraints.

    allowed_technique_ids maps technique_id -> technique_name as returned by RAG.
    """
    errors: Dict[str, Any] = {}

    try:
        parsed = json.loads(_strip_code_fences(raw))
    except (json.JSONDecodeError, TypeError) as exc:
        raise LLMValidationErrorException(
            "LLM output is not valid JSON",
            details={"field": "root", "problem": str(exc)},
        ) from exc

    if not isinstance(parsed, dict):
        raise LLMValidationErrorException(
            "LLM output must be a single JSON object",
            details={"field": "root", "problem": "top-level value is not an object"},
        )

    missing = [f for f in _REQUIRED_FIELDS if f not in parsed]
    if missing:
        errors["missing_fields"] = missing

    for field, expected in _REQUIRED_FIELDS.items():
        if field in parsed and not _type_ok(parsed[field], expected):
            errors.setdefault("wrong_type", {})[field] = expected

    if "summary" in parsed and isinstance(parsed["summary"], str) and not parsed["summary"].strip():
        errors.setdefault("empty_strings", []).append("summary")
    if "anomaly_assessment" in parsed and isinstance(parsed["anomaly_assessment"], str) and not parsed["anomaly_assessment"].strip():
        errors.setdefault("empty_strings", []).append("anomaly_assessment")
    for list_field in ("observed_indicators", "recommended_actions", "limitations"):
        if list_field in parsed and isinstance(parsed[list_field], list):
            _validate_string_list(parsed[list_field], list_field, errors)

    _validate_technique_context(
        parsed.get("potential_attack_context") if isinstance(parsed.get("potential_attack_context"), list) else None,
        allowed_technique_ids,
        errors,
    )

    if errors:
        raise LLMValidationErrorException(
            "LLM output failed validation",
            details=errors,
        )

    return LLMExplanationOutput(
        summary=parsed["summary"].strip(),
        anomaly_assessment=parsed["anomaly_assessment"].strip(),
        observed_indicators=[i.strip() for i in parsed["observed_indicators"]],
        potential_attack_context=[
            PotentialAttackContext(
                technique_id=entry["technique_id"].strip(),
                technique_name=entry["technique_name"].strip(),
                confidence=entry["confidence"].strip().lower(),
                reason=entry["reason"].strip(),
            )
            for entry in parsed["potential_attack_context"]
        ],
        recommended_actions=[a.strip() for a in parsed["recommended_actions"]],
        limitations=[l_.strip() for l_ in parsed["limitations"]],
    )


def _type_ok(value: Any, expected: str) -> bool:
    if expected == "str":
        return isinstance(value, str)
    return isinstance(value, list)


def _validate_string_list(values: List[Any], field: str, errors: Dict[str, Any]) -> None:
    bad = [i for i, v in enumerate(values) if not isinstance(v, str) or not v.strip()]
    if bad:
        errors.setdefault("non_string_list_items", {})[field] = bad


def _validate_technique_context(
    entries: Any,
    allowed: Mapping[str, str],
    errors: Dict[str, Any],
) -> None:
    if entries is None:
        errors.setdefault("wrong_type", {})["potential_attack_context"] = "list"
        return

    if not allowed and entries:
        errors.setdefault("ungrounded_techniques", []).append(
            "potential_attack_context must be [] when no RAG context is supplied"
        )
        return

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.setdefault("non_object_entries", []).append(idx)
            continue

        tid = entry.get("technique_id")
        tname = entry.get("technique_name")
        confidence = entry.get("confidence")
        reason = entry.get("reason")

        if not isinstance(tid, str) or not tid.strip():
            errors.setdefault("invalid_technique_entries", []).append(
                {"index": idx, "problem": "technique_id missing or not a string"}
            )
        else:
            tid = tid.strip()
            if tid not in allowed:
                errors.setdefault("ungrounded_techniques", []).append(
                    {"index": idx, "technique_id": tid, "problem": "not supplied by RAG context"}
                )
            elif not isinstance(tname, str) or tname.strip() != allowed[tid]:
                errors.setdefault("technique_name_mismatch", []).append(
                    {
                        "index": idx,
                        "technique_id": tid,
                        "expected_name": allowed.get(tid),
                        "got_name": tname,
                    }
                )

        if not isinstance(confidence, str) or confidence.strip().lower() not in _ALLOWED_CONFIDENCE:
            errors.setdefault("invalid_confidence", []).append(
                {"index": idx, "confidence": confidence, "allowed": sorted(_ALLOWED_CONFIDENCE)}
            )

        if not isinstance(reason, str) or not reason.strip():
            errors.setdefault("empty_reason", []).append(idx)
        else:
            for name in "technique_id", "technique_name", "confidence":
                if isinstance(entry.get(name), str):
                    entry[name] = entry[name].strip()
            entry["confidence"] = entry["confidence"].strip().lower()