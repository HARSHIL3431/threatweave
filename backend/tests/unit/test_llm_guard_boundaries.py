"""P1-17 behavior documentation: LLM guard boundaries that must keep holding.

These tests lock in existing rejection behavior only. They assert nothing
about bypass inputs that currently pass (G-01..G-08 in
docs/reliability/LLM_GUARD_AND_REMEDIATION_GAP_AUDIT.md): fixing a guard
must update the audit, not silently pass here. Synthetic inputs only.
"""
import json

import pytest

from app.core.exceptions import LLMValidationErrorException
from app.services.llm_validation import validate_llm_output

_ALLOWED = {"T1046": "Network Service Discovery"}
_MITS = ["Monitor network traffic for unusual activity"]


def _output(**overrides):
    data = {
        "summary": "Anomalous flow observed.",
        "anomaly_assessment": "Score exceeds threshold.",
        "observed_indicators": ["Elevated packet rate"],
        "potential_attack_context": [],
        "recommended_actions": ["Investigate the flow."],
        "limitations": ["Not confirmed."],
    }
    data.update(overrides)
    return json.dumps(data)


def _rejects(raw, key):
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(raw, _ALLOWED, _MITS)
    assert key in exc.value.details


def _accepts(raw):
    assert validate_llm_output(raw, _ALLOWED, _MITS) is not None


_FULL_MITS = [
    "Monitor network traffic for unusual activity",
    "Disable unused services",
]


def _accepts_with(raw, mits):
    assert validate_llm_output(raw, _ALLOWED, mits) is not None


def _action_output(action):
    return _output(recommended_actions=[action])


# A terminal question mark is a sentence delimiter, not a hedge exemption.
def test_terminal_question_confirmatory_still_rejected():
    _rejects(_output(summary="The attack is confirmed?"), "confirmatory_language")


def test_no_doubt_confirmatory_still_rejected():
    _rejects(_output(summary="No doubt this is confirmed."), "confirmatory_language")


@pytest.mark.parametrize("summary", [
    "There is proof of an intrusion here.",
    "This is without a doubt an attack.",
])
def test_sameline_multiword_terms_still_rejected(summary):
    _rejects(_output(summary=summary), "confirmatory_language")


def test_cve_shape_in_actions_still_rejected():
    _rejects(
        _output(recommended_actions=["Patch CVE-2024-1234 on the mail server now."]),
        "unsupported_factual_claim",
    )


@pytest.mark.parametrize("raw", ["null", "[]", "42", "", "   "])
def test_malformed_and_empty_still_rejected(raw):
    with pytest.raises(LLMValidationErrorException):
        validate_llm_output(raw, _ALLOWED, _MITS)


def test_none_input_still_rejected():
    with pytest.raises(LLMValidationErrorException):
        validate_llm_output(None, _ALLOWED, _MITS)


# --- P1-18 G-01: a marker elsewhere must not exempt a separate instruction.
@pytest.mark.parametrize("action", [
    "Wipe the server. Consider implications later.",
    "Review: delete all logs now.",
    "Possible side effects include downtime; delete all logs now.",
    "Isolate the host. This may require downtime.",
])
def test_cross_clause_markers_no_longer_exempt(action):
    _rejects(_action_output(action), "unqualified_high_impact_action")


@pytest.mark.parametrize("action", [
    "Consider isolating the host if follow-up confirms malicious activity.",
    "Isolate the host after verifying scope with the on-call analyst.",
    "Block the suspicious address once corroborated by firewall logs.",
    "If the analyst confirms malicious activity: isolate the host.",
])
def test_genuinely_qualified_advice_still_passes(action):
    _accepts(_action_output(action))


def test_negated_instruction_is_a_prohibition_not_an_order():
    _accepts(_action_output("Do not delete the logs."))
    _accepts(_action_output("Never wipe a workstation without a ticket."))


def test_quoted_mention_is_not_an_instruction():
    _accepts(_action_output('Search logs for the word "delete".'))


# --- P1-18 G-02: mitigation mentions must not exempt unrelated instructions.
@pytest.mark.parametrize("action", [
    "Delete all system logs. Monitor network traffic for unusual activity",
    "Mitigation (per T1046): Delete everything now.",
    "Mitigation (per T1046): Disable unused services. Also delete all logs.",
])
def test_smuggled_destruction_beside_mitigation_rejected(action):
    _rejects(_action_output(action), "unqualified_high_impact_action")


@pytest.mark.parametrize("action", [
    "Mitigation (per T1046): Disable unused services.",
    "Monitor network traffic for unusual activity on the flagged host.",
    "Disable unused services on the host.",
])
def test_legitimate_bounded_mitigation_still_passes(action):
    _accepts_with(_action_output(action), _FULL_MITS)


def test_mixed_safe_and_unsafe_actions_rejected_at_unsafe_index():
    raw = _output(recommended_actions=[
        "Review the flagged flow and corroborate indicators before acting.",
        "Wipe the server. Consider implications later.",
    ])
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(raw, _ALLOWED, _MITS)
    entry = exc.value.details["unqualified_high_impact_action"][0]
    assert entry["index"] == 1


# --- P1-18 G-03: disruptive synonyms.
@pytest.mark.parametrize("action", [
    "Reset every user password in the directory now.",
    "Take the mail server offline immediately.",
    "Suspend all contractor accounts at once.",
    "Reboot the core switch during business hours.",
    "Lock out the finance department until further notice.",
    "Deactivate the backup service permanently.",
])
def test_disruptive_synonyms_require_qualification(action):
    _rejects(_action_output(action), "unqualified_high_impact_action")


@pytest.mark.parametrize("action", [
    "Reset every user password only after the incident commander approves.",
    "Take the mail server offline if the on-call analyst confirms the scope.",
    "Restart the print spooler.",
    "Review the password reset policy for compliance.",
])
def test_synonym_qualified_or_routine_cases_pass(action):
    _accepts(_action_output(action))


# --- P1-18 G-04: trailing hedges must not neutralize a definitive claim.
def test_trailing_hedge_no_longer_neutralizes_confirmation():
    _rejects(
        _output(summary="The intrusion is confirmed, possible false positive?"),
        "confirmatory_language",
    )


@pytest.mark.parametrize("summary", [
    "A possible attack that is not confirmed.",
    "The technique is a candidate only, not confirmed.",
    "The evidence has not confirmed an attack.",
])
def test_genuinely_uncertain_statements_still_pass(summary):
    _accepts(_output(summary=summary))


# --- P1-18 G-05: CVE separator variants.
@pytest.mark.parametrize("summary", [
    "Exploits CVE 2024 1234 against the mail server.",
    "Exploits CVE–2024–1234 against the mail server.",
    "Exploits CVE—2024—1234 against the mail server.",
])
def test_cve_separator_variants_rejected(summary):
    _rejects(_output(summary=summary), "unsupported_factual_claim")


@pytest.mark.parametrize("summary", [
    "Check vendor advisories for known issues.",
    "Review published vulnerabilities during the next maintenance window.",
])
def test_generic_vulnerability_prose_still_passes(summary):
    _accepts(_output(summary=summary))


# --- P1-18 G-06: ATT&CK ID separator obfuscation.
@pytest.mark.parametrize("summary", [
    "Follow playbook T 9999 now.",
    "Follow playbook T-9999 now.",
    "Follow playbook t 9999 now.",
])
def test_obfuscated_ids_rejected(summary):
    _rejects(_output(summary=summary), "ungrounded_technique_mentions")


@pytest.mark.parametrize("summary", [
    "Candidate T1046 matches.",
    "Candidate t1046 matches.",
])
def test_legitimate_id_references_still_pass(summary):
    _accepts(_output(summary=summary))


def test_subtechnique_prose_mention_requires_exact_rag_id():
    # The prose guard enforces exact RAG-supplied IDs; the retrieval
    # parent/sub-technique policy does not apply here. T1046.001 was not
    # supplied, so it is rejected even though its parent was.
    _rejects(
        _output(summary="Candidate T1046.001 matches the sub-technique record."),
        "ungrounded_technique_mentions",
    )


# --- P1-18 G-08: newline-split confirmatory phrases.
@pytest.mark.parametrize("summary", [
    "There is proof\nof an intrusion here.",
    "This is without\na doubt an attack.",
    "The activity is attributed\nto APT29.",
])
def test_newline_split_phrases_rejected(summary):
    _rejects(_output(summary=summary), "confirmatory_language")
