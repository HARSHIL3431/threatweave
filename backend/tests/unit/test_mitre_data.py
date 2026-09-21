"""Tests for MITRE ATT&CK STIX parsing, normalization, and document chunking."""
import pytest

from app.services.mitre_data import (
    MitreDataError,
    RagDocument,
    Technique,
    build_documents,
    parse_attack_pattern,
    parse_stix_bundle,
)


def _technique_obj(oid: str) -> dict:
    return {
        "id": oid,
        "type": "attack-pattern",
        "name": "Test Technique",
        "description": "A test description",
        "external_references": [{"source_name": "mitre-attack", "external_id": "T1000"}],
        "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": "discovery"}],
        "x_mitre_detection": "Monitor logs",
        "x_mitre_platforms": ["Windows", "Linux"],
        "x_mitre_data_sources": ["Process creation"],
        "x_mitre_is_subtechnique": False,
        "revoked": False,
    }


def test_parse_attack_pattern_normalizes_fields():
    tech = parse_attack_pattern(_technique_obj("attack-pattern--1111"))
    assert tech.technique_id == "T1000"
    assert tech.technique_name == "Test Technique"
    assert tech.tactics == ["discovery"]
    assert tech.detection == "Monitor logs"
    assert tech.platforms == ["Windows", "Linux"]
    assert not tech.is_subtechnique
    assert tech.is_active


def test_parse_attack_pattern_missing_external_id_raises():
    obj = _technique_obj("attack-pattern--1111")
    obj["external_references"] = []
    with pytest.raises(MitreDataError):
        parse_attack_pattern(obj)


def test_parse_attack_pattern_missing_optional_fields_is_safe():
    obj = _technique_obj("attack-pattern--1111")
    for key in ["kill_chain_phases", "x_mitre_detection", "x_mitre_platforms", "x_mitre_data_sources"]:
        obj.pop(key, None)
    tech = parse_attack_pattern(obj)
    assert tech.tactics == []
    assert tech.detection is None
    assert tech.platforms == []
    assert tech.data_sources == []


def test_revoked_and_deprecated_are_flagged_not_active():
    revoked = _technique_obj("attack-pattern--r1")
    revoked["revoked"] = True
    deprecated = _technique_obj("attack-pattern--d1")
    deprecated["x_mitre_deprecated"] = True

    assert not parse_attack_pattern(revoked).is_active
    assert not parse_attack_pattern(deprecated).is_active


def test_parse_stix_bundle_handles_subtechniques_mitigations_and_relationships():
    tech = _technique_obj("attack-pattern--tech")
    sub = _technique_obj("attack-pattern--sub")
    sub["name"] = "Test SubTechnique"
    sub["external_references"] = [{"source_name": "mitre-attack", "external_id": "T1000.001"}]
    sub["x_mitre_is_subtechnique"] = True

    mitigation = {
        "id": "course-of-action--m1",
        "type": "course-of-action",
        "name": "Network Segmentation",
        "external_references": [{"source_name": "mitre-attack", "external_id": "M1030"}],
    }
    relationship = {
        "id": "relationship--r1",
        "type": "relationship",
        "relationship_type": "mitigates",
        "source_ref": "course-of-action--m1",
        "target_ref": "attack-pattern--tech",
    }
    bundle = {"objects": [tech, sub, mitigation, relationship]}

    techniques = parse_stix_bundle(bundle)
    assert len(techniques) == 2
    by_id = {t.technique_id: t for t in techniques}
    assert by_id["T1000"].is_subtechnique is False
    assert by_id["T1000"].mitigations == ["M1030"]
    assert by_id["T1000.001"].is_subtechnique is True
    assert by_id["T1000.001"].mitigations == []


def test_parse_stix_bundle_non_attack_pattern_objects_ignored():
    bundle = {"objects": [
        _technique_obj("attack-pattern--a"),
        {"id": "malware--x", "type": "malware", "name": "Some malware"},
        {"id": "tool--y", "type": "tool", "name": "Some tool"},
        {"type": "relationship", "relationship_type": "uses",
         "source_ref": "attack-pattern--a", "target_ref": "malware--x"},
    ]}
    assert len(parse_stix_bundle(bundle)) == 1


def test_parse_stix_bundle_requires_objects():
    with pytest.raises(MitreDataError):
        parse_stix_bundle({"not_objects": []})


def test_build_documents_is_deterministic_and_sorted():
    techs = [
        Technique(technique_id="T2000", technique_name="Zed", description="d"),
        Technique(technique_id="T1000", technique_name="Alpha", description="a"),
        Technique(technique_id="T1000.001", technique_name="Alpha sub", description="s"),
    ]
    docs_a = build_documents(techs)
    docs_b = build_documents(techs)
    assert [d.technique_id for d in docs_a] == ["T1000", "T1000.001", "T2000"]
    assert [d.text for d in docs_a] == [d.text for d in docs_b]
    assert all(isinstance(d, RagDocument) for d in docs_a)


def test_build_documents_excludes_inactive_by_default():
    techs = [
        Technique(technique_id="T1000", technique_name="Active", description="a"),
        Technique(technique_id="T2000", technique_name="Revoked", description="r", is_revoked=True),
        Technique(technique_id="T3000", technique_name="Old", description="o", is_deprecated=True),
    ]
    active_docs = build_documents(techs)
    assert [d.technique_id for d in active_docs] == ["T1000"]

    all_docs = build_documents(techs, include_inactive=True)
    assert [d.technique_id for d in all_docs] == ["T1000", "T2000", "T3000"]


def test_document_text_contains_grounded_fields():
    tech = Technique(
        technique_id="T1046",
        technique_name="Network Service Discovery",
        description="Scanning network services.",
        tactics=["discovery"],
        detection="Collect network connections.",
        mitigations=["M1030"],
        data_sources=["Connection metadata"],
    )
    doc = build_documents([tech])[0]
    assert "T1046" in doc.text
    assert "Network Service Discovery" in doc.text
    assert "discovery" in doc.text.lower()
    assert "Scanning network services." in doc.text
    assert "M1030" in doc.text
    assert doc.type == "technique"
    meta = doc.to_metadata_dict()
    assert meta["technique_id"] == "T1046"
    assert meta["tactics"] == ["discovery"]