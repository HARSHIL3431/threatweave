"""Strict validation of LLM outputs before they reach the API client.

The raw LLM output is treated as untrusted. Before acceptance it must:
  1. Parse as a single JSON object.
  2. Contain all required fields with correct types.
  3. Use non-empty strings where required.
  4. Use confidence values from the allowed enum: low | medium | high.
  5. Reference ONLY technique IDs supplied by the RAG context.
  6. Match the RAG-supplied technique name for every referenced ID.
  7. Yield an empty potential_attack_context when no RAG context exists.
  8. Mention no ATT&CK ID in free prose that RAG did not supply (no
     smuggling invented IDs through summaries, reasons, or actions;
     obfuscated separators such as "T 9999" are normalized first).
  9. Present no retrieved technique as a confirmed attack: unqualified
     confirmatory language ("confirmed", "definitely", "proof of", ...)
     fails, while a hedge or negation placed before the claim ("not
     confirmed", "possible attack") passes. A hedge word after the claim
     does not neutralize it. Deterministic backstop, not semantic proof.
  10. Assert no specific CVE identifier anywhere in free prose: no CVE data
     exists anywhere in the pipeline, so any CVE-shaped mention (hyphen,
     space, or dash separated) is unsupported.
  11. Present no high-impact remediation (isolate/disable/wipe/delete/block,
     credential resets at scale, offline/suspend/reboot/lock-out and kin)
     without explicit qualification in its own clause (or an explicit
     condition in an adjacent clause), unless the verb occurrence sits
     inside quoted retrieved ATT&CK mitigation text (authoritative STIX
     guidance). Negated and double-quoted mentions are not instructions.

Any violation raises LLMValidationErrorException with structured details. The
output is never silently accepted and never corrupts the detection result.
"""
import json
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

from app.core.exceptions import LLMValidationErrorException
from app.schemas.llm import LLMExplanationOutput, PotentialAttackContext

_TECHNIQUE_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.IGNORECASE)
# Obfuscated separators (G-06): "T 1046", "T-1046" are normalized to canonical
# form before scanning so trivial reformatting cannot evade the ID guard.
# Accepted formats after normalization: Txxxx[.yyy], any case, with zero or
# one separator (space/dash) between T and digits.
_TECHNIQUE_ID_OBFUSCATED_RE = re.compile(
    r"\bT\s*-?\s*(\d{4}(?:\.\d{3})?)\b", re.IGNORECASE
)
# CVE shapes (G-05): ASCII hyphens plus common unicode dashes and bare
# whitespace between all three components. Both numeric groups required so
# generic "CVE database" or year-only prose never matches.
_CVE_RE = re.compile(
    r"\bCVE[\s_\-–—―−]*\d{4}[\s_\-–—―−]*\d{4,}\b", re.IGNORECASE
)
_MITIGATION_REF_RE = re.compile(
    r"mitigation\s*\(per\s+(T\d{4}(?:\.\d{3})?)\s*\):", re.IGNORECASE
)

# High-impact verbs: actions that can interrupt operations, destroy evidence,
# lock out users, or cause irreversible damage. Matched case-insensitively
# with word boundaries; see the remediation-grounding rubric for the full list
# and rationale. G-03 additions (reset-at-scale, offline, suspend, reboot,
# lock-out, deactivate) are deliberately narrow: bare "restart" is routine
# operations and stays unlisted, and "reset" requires a credential/account
# object (a bare "reset the test environment" is out of this rule's scope).
_HIGH_IMPACT_PATTERNS = (
    re.compile(r"\b(isolat\w*|quarantin\w*)\b", re.IGNORECASE),
    re.compile(r"\b(disabl\w*|shut\s?down|power\s?off)\b", re.IGNORECASE),
    re.compile(r"\b(wip\w*|reimag\w*|format|purg\w*)\b", re.IGNORECASE),
    re.compile(r"\b(delet\w*|eras\w*|destroy\w*)\b", re.IGNORECASE),
    re.compile(r"\b(terminat\w*|kill\s+(?:all|the|-9)|revok\w*)\b", re.IGNORECASE),
    re.compile(r"\b(block|disconnect\w*|blackhol\w*|null[\s-]?rout\w*)\b", re.IGNORECASE),
    re.compile(
        r"\breset(?:s|ting)?\s+(?:all\s+|every\s+|each\s+|multiple\s+|bulk\s+)?"
        r"(?:user(?:s['’])?\s+|account\s+|credential\s+|password\s+|login\s+)?"
        r"(?:passwords?|credentials?|accounts?|logins?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\btak(?:e|ing|en)\b.{0,60}?\boffline\b", re.IGNORECASE),
    re.compile(r"\bsuspend\w*\b", re.IGNORECASE),
    re.compile(r"\breboot\w*\b", re.IGNORECASE),
    re.compile(r"\block\s?out\b", re.IGNORECASE),
    re.compile(r"\bdeactivat\w*\b", re.IGNORECASE),
)

# Qualification markers: conditional/verification language that keeps a
# high-impact action proportionate (review step, condition, or hedge).
# G-01: markers only qualify the clause (segment) they appear in; a marker
# elsewhere in the action no longer exempts a separate instruction. A bare
# conditional in an adjacent segment still qualifies (see _CONDITIONAL_MARKERS).
_QUALIFICATION_MARKERS = (
    "consider", "if ", "after ", "once ", "pending", "review", "verif",
    "corroborat", "candidate", "potential", "possible", "may ", "might ",
    "could ", "suspect", "evaluat", "assess", "subject to", "before acting",
    "before proceeding", "prior to",
)

# Markers strong enough to qualify an instruction from an adjacent clause.
# Bare hedges ("review:", "consider ... later", "possible side effects")
# are excluded on purpose: cross-clause qualification requires an explicit
# condition, which genuinely conditions the advice.
_CONDITIONAL_MARKERS = (
    "if ", "once ", "after ", "pending", "subject to", "provided ",
    "when ", "upon ", "before acting", "before proceeding", "prior to",
)

# Negated instructions are prohibitions, not orders: "do not delete the
# logs" must not fail as an unqualified deletion. Checked per verb
# occurrence, same clause, negation before the verb.
_NEGATION_RE = re.compile(
    r"\b(do\s?not|don't|does\s?not|doesn't|never|avoid|without|no)\b",
    re.IGNORECASE,
)

# Double-quoted spans are mentions, not instructions: searching logs for the
# word "delete" must not fail as an unqualified deletion.
_QUOTED_SPAN_RE = re.compile(r'"[^"]*"')

# Clause splitter for scoping markers to the instruction they qualify (G-01).
# Splits on sentence ends, semicolons, colons, and newlines: "Review:
# delete all logs now" is two clauses, so the bare "Review" cannot exempt
# the deletion. Deliberate trade-off documented in _validate_recommended_actions.
_CLAUSE_SPLIT_RE = re.compile(r"[.!?;:\n]+")


# Strong confirmatory claims that must never appear as established fact in an
# explanation: retrieved techniques are candidates, and an anomaly score is not
# proof of an attack. Matching is sentence-scoped and negation/hedge aware so
# honest disclaimers ("not confirmed", "possible attack") still pass.
_CONFIRMATORY_TERMS = (
    "confirmed",
    "definitely",
    "certainly",
    "undeniably",
    "incontrovertibly",
    "proof of",
    "proves ",
    "proven ",
    "without a doubt",
    "beyond doubt",
    "attributed to",
)
_HEDGE_MARKERS = (
    "not ", "n't", "never", "cannot", "can't", "won't", "unable", "unlikely",
    "possible", "possibly", "potential", "candidate", "may ", "might ",
    "could ", "suggest", "appears", "likely", "?",
)

# Free-text fields whose prose must not present unconfirmed claims.
_ASSERTION_FIELDS = ("summary", "anomaly_assessment")

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
    allowed_mitigations: Optional[Sequence[str]] = None,
) -> LLMExplanationOutput:
    """Validate raw LLM JSON against the schema and RAG grounding constraints.

    allowed_technique_ids maps technique_id -> technique_name as returned by RAG.
    allowed_mitigations lists retrieved ATT&CK mitigation texts; recommended
    actions quoting them are grounded by construction and exempt from the
    high-impact qualification rule.
    """
    errors: Dict[str, Any] = {}
    mitigations = [m for m in (allowed_mitigations or []) if isinstance(m, str) and m.strip()]

    if not isinstance(raw, str):
        raise LLMValidationErrorException(
            "LLM output is not valid JSON",
            details={
                "field": "root",
                "problem": f"expected a JSON string, got {type(raw).__name__}",
            },
        )
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

    _validate_no_smuggled_technique_ids(parsed, allowed_technique_ids, errors)
    _validate_no_confirmatory_language(parsed, errors)
    _validate_no_unsupported_facts(parsed, errors)
    _validate_recommended_actions(parsed, allowed_technique_ids, mitigations, errors)

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


def _free_text_spans(parsed: Dict[str, Any]) -> List[tuple]:
    """Yield (field_label, text) for every free-text span worth scanning."""
    spans: List[tuple] = []
    for field in _ASSERTION_FIELDS:
        value = parsed.get(field)
        if isinstance(value, str) and value.strip():
            spans.append((field, value))
    for list_field in ("observed_indicators", "recommended_actions", "limitations"):
        values = parsed.get(list_field)
        if isinstance(values, list):
            for idx, value in enumerate(values):
                if isinstance(value, str) and value.strip():
                    spans.append((f"{list_field}[{idx}]", value))
    entries = parsed.get("potential_attack_context")
    if isinstance(entries, list):
        for idx, entry in enumerate(entries):
            if isinstance(entry, dict) and isinstance(entry.get("reason"), str):
                spans.append((f"potential_attack_context[{idx}].reason", entry["reason"]))
    return spans


def _validate_no_smuggled_technique_ids(
    parsed: Dict[str, Any],
    allowed: Mapping[str, str],
    errors: Dict[str, Any],
) -> None:
    """Reject ATT&CK IDs mentioned in prose that RAG did not supply.

    Structured technique_id fields are validated separately; this closes the
    bypass of citing an invented ID inside a summary, reason, or recommended
    action. Comparison is case-insensitive against canonical uppercase IDs.
    """
    allowed_upper = {str(tid).upper() for tid in allowed}
    for label, text in _free_text_spans(parsed):
        # G-06: normalize obfuscated separators first so "T 9999"/"T-9999"
        # cannot trivially bypass the free-text ID guard.
        for match in _TECHNIQUE_ID_RE.findall(_normalize_technique_ids(text)):
            if match.upper() not in allowed_upper:
                errors.setdefault("ungrounded_technique_mentions", []).append(
                    {"field": label, "technique_id": match}
                )


def _normalize_technique_ids(text: str) -> str:
    """Fold obfuscated ATT&CK ID separators to canonical form (G-06).

    "T 1046" and "T-1046" become "T1046" (uppercased) so the smuggle scan
    sees them. Standard notation is untouched.
    """
    return _TECHNIQUE_ID_OBFUSCATED_RE.sub(
        lambda m: "T" + m.group(1).upper(), text
    )


def _squash_ws(text: str) -> str:
    """Collapse all whitespace runs (including newlines) to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def _split_clauses(action: str) -> List[str]:
    """Split an action into clauses for marker scoping (G-01)."""
    return [c for c in _CLAUSE_SPLIT_RE.split(action) if c.strip()]


def _redact_grounded_spans(
    action: str,
    allowed: Mapping[str, str],
    mitigations: List[str],
) -> str:
    """Remove evidence-grounded spans from an action (G-02).

    A "Mitigation (per ALLOWED-ID): <retrieved mitigation text>" template
    redacts from the template start through the quoted mitigation text, and
    bare retrieved-mitigation substrings redact where they occur. Anything
    outside those spans — including destructive clauses appended to a
    genuine quote — stays visible to the high-impact check. A template with
    an unallowed ID redacts nothing (the smuggle scan flags it separately).
    Matching is whitespace-insensitive so reflowed quotes still redact.
    """
    allowed_upper = {str(tid).upper() for tid in allowed}
    squashed = _squash_ws(action)
    redacted = squashed
    template = _MITIGATION_REF_RE.search(squashed)
    if template and template.group(1).upper() in allowed_upper:
        rest = squashed[template.end():]
        rest_squashed = _squash_ws(rest)
        for mit in mitigations:
            needle = _squash_ws(mit)
            if needle and needle.casefold() in rest_squashed.casefold():
                idx = rest_squashed.casefold().find(needle.casefold())
                cut_end = template.end() + idx + len(needle)
                redacted = squashed[:template.start()] + " " + squashed[cut_end:]
                break
        else:
            return action  # No retrieved text quoted: nothing is grounded.
        squashed = _squash_ws(redacted)
    for mit in mitigations:
        needle = _squash_ws(mit)
        if needle:
            squashed = re.sub(
                re.escape(needle), " ", squashed, flags=re.IGNORECASE
            )
    return _squash_ws(squashed)


def _verb_occurrence_excused(segment: str, match_start: int) -> bool:
    """Decide whether one high-impact verb occurrence is excused.

    Excused when negated before the verb in the same clause ("do not
    delete"), or when a qualification marker shares the clause. Cross-clause
    qualification is handled by the caller via _CONDITIONAL_MARKERS.
    """
    lowered = segment.lower()
    before = lowered[:match_start]
    if _NEGATION_RE.search(before):
        return True
    return any(marker in lowered for marker in _QUALIFICATION_MARKERS)


def _confirmatory_term_unhedged(sentence: str) -> Optional[str]:
    """Return the first unhedged confirmatory term in a sentence, if any.

    G-04: only markers *preceding* the term count ("not confirmed" passes;
    "... is confirmed, possible false positive?" fails). G-08: whitespace
    (including newlines) is collapsed before matching so line breaks cannot
    split multi-word terms such as "proof of" or detach hedges.
    """
    normalized = _squash_ws(sentence).lower()
    for term in _CONFIRMATORY_TERMS:
        pos = normalized.find(term)
        if pos != -1 and not any(
            marker in normalized[:pos] for marker in _HEDGE_MARKERS
        ):
            return term.strip()
    return None


def _validate_no_confirmatory_language(
    parsed: Dict[str, Any],
    errors: Dict[str, Any],
) -> None:
    """Reject prose that presents a technique as a confirmed attack.

    Retrieved records are candidates and an anomaly score is not proof of
    intrusion. Sentences carrying negation or hedging ("not confirmed",
    "possible attack") are left alone; only unqualified confirmatory claims
    fail. This is a deterministic backstop, not a semantic proof.
    """
    for label, text in _free_text_spans(parsed):
        for sentence in re.split(r"[.!?]+", text):
            if not sentence.strip():
                continue
            phrase = _confirmatory_term_unhedged(sentence)
            if phrase is not None:
                errors.setdefault("confirmatory_language", []).append(
                    {"field": label, "phrase": phrase}
                )


def _validate_no_unsupported_facts(
    parsed: Dict[str, Any],
    errors: Dict[str, Any],
) -> None:
    """Reject specific factual claims no pipeline evidence can support.

    Currently scoped to CVE identifiers: the detection features, flow
    summary, and retrieved ATT&CK records contain no CVE data, so any
    CVE-YYYY-NNNN mention is invented by construction. Other invented
    entities (hostnames, accounts, malware names) without high-impact verbs
    or ID patterns remain a documented human-review gap, not a string-match
    claim.
    """
    for label, text in _free_text_spans(parsed):
        for match in _CVE_RE.findall(text):
            errors.setdefault("unsupported_factual_claim", []).append(
                {"field": label, "claim": match}
            )


def _validate_recommended_actions(
    parsed: Dict[str, Any],
    allowed: Mapping[str, str],
    mitigations: List[str],
    errors: Dict[str, Any],
) -> None:
    """Require qualification for high-impact remediation actions.

    Evidence-grounded spans (a "Mitigation (per ALLOWED-ID): <retrieved
    text>" template quoting retrieved mitigation text, or bare retrieved
    mitigation quotes) are redacted before matching, so quoting STIX
    guidance still passes — but destructive clauses appended to a genuine
    quote no longer ride along (G-02). Remaining text is checked per
    clause: a qualification marker only excuses a verb in its own clause,
    with one narrow exception — an explicit conditional in an adjacent
    clause ("If the analyst confirms ...: isolate the host") genuinely
    conditions the advice (G-01). Negated ("do not delete") and
    double-quoted mentions are not instructions. Generic safe guidance
    without high-impact verbs always passes.
    """
    actions = parsed.get("recommended_actions")
    if not isinstance(actions, list):
        return  # Wrong-type errors are reported by schema validation.
    for idx, action in enumerate(actions):
        if not isinstance(action, str) or not action.strip():
            continue  # Empty items are reported by string-list validation.
        visible = _redact_grounded_spans(action, allowed, mitigations)
        clauses = _split_clauses(visible) or [visible]
        flagged = None
        for pos, clause in enumerate(clauses):
            unquoted = _QUOTED_SPAN_RE.sub(" ", clause)
            for pattern in _HIGH_IMPACT_PATTERNS:
                for hit in pattern.finditer(unquoted):
                    if _verb_occurrence_excused(unquoted, hit.start()):
                        continue
                    if _adjacent_conditional(clauses, pos):
                        continue
                    flagged = hit.group(0)
                    break
                if flagged is not None:
                    break
            if flagged is not None:
                break
        if flagged is not None:
            errors.setdefault("unqualified_high_impact_action", []).append(
                {"index": idx, "trigger": flagged[:40]}
            )


def _adjacent_conditional(clauses: List[str], pos: int) -> bool:
    """Check whether a clause next to the verb carries an explicit condition."""
    neighbors = []
    if pos > 0:
        neighbors.append(clauses[pos - 1])
    if pos + 1 < len(clauses):
        neighbors.append(clauses[pos + 1])
    return any(
        marker in neighbor.lower()
        for neighbor in neighbors
        for marker in _CONDITIONAL_MARKERS
    )


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