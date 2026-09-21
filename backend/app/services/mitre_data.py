"""MITRE ATT&CK STIX ingestion, normalization, and document chunking.

This module transforms official MITRE ATT&CK STIX 2.x bundles
(https://github.com/mitre/cti) into deterministic, searchable documents.

Only official STIX object content is used. No technique IDs, descriptions,
tactics, or detection guidance are invented here.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger("mitre_data")

MITRE_KILL_CHAIN = "mitre-attack"
STIX_SOURCE = "mitre-attack"


class MitreDataError(Exception):
    """Raised when MITRE STIX data is malformed or cannot be parsed."""


@dataclass
class Technique:
    """Normalized MITRE ATT&CK technique (or sub-technique)."""

    technique_id: str
    technique_name: str
    description: str
    tactics: List[str] = field(default_factory=list)
    detection: Optional[str] = None
    mitigations: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    is_subtechnique: bool = False
    is_revoked: bool = False
    is_deprecated: bool = False
    stix_id: Optional[str] = None

    @property
    def is_active(self) -> bool:
        """Revoked/deprecated techniques are excluded from retrieval."""
        return not self.is_revoked and not self.is_deprecated


@dataclass
class RagDocument:
    """A deterministic searchable chunk derived from a Technique."""

    technique_id: str
    technique_name: str
    type: str  # "technique" | "sub-technique"
    text: str
    tactics: List[str]
    description: str
    detection: Optional[str] = None
    mitigations: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)

    def to_metadata_dict(self) -> Dict[str, Any]:
        """Serializable record stored alongside the FAISS index."""
        return {
            "technique_id": self.technique_id,
            "technique_name": self.technique_name,
            "type": self.type,
            "tactics": self.tactics,
            "description": self.description,
            "detection": self.detection,
            "mitigations": self.mitigations,
            "data_sources": self.data_sources,
            "platforms": self.platforms,
            "aliases": self.aliases,
        }


def _get_external_id(obj: Dict[str, Any], source_name: str = STIX_SOURCE) -> Optional[str]:
    """Extract the canonical MITRE technique ID from external_references."""
    for ref in obj.get("external_references", []) or []:
        if ref.get("source_name") == source_name and ref.get("external_id"):
            return str(ref["external_id"])
    return None


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _safe_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    return [str(value)]


def parse_attack_pattern(obj: Dict[str, Any]) -> Technique:
    """Normalize a single STIX attack-pattern object into a Technique."""
    technique_id = _get_external_id(obj)
    if not technique_id:
        raise MitreDataError(f"attack-pattern missing mitre external_id: {obj.get('id')}")

    tactics = []
    for kcp in obj.get("kill_chain_phases", []) or []:
        if kcp.get("kill_chain_name") == MITRE_KILL_CHAIN and kcp.get("phase_name"):
            tactics.append(str(kcp["phase_name"]))

    detection = _safe_str(obj.get("x_mitre_detection")) or None

    return Technique(
        technique_id=technique_id,
        technique_name=_safe_str(obj.get("name")) or technique_id,
        description=_safe_str(obj.get("description")),
        tactics=tactics,
        detection=detection,
        data_sources=_safe_list(obj.get("x_mitre_data_sources")),
        platforms=_safe_list(obj.get("x_mitre_platforms")),
        aliases=_safe_list(obj.get("x_mitre_aliases")),
        is_subtechnique=bool(obj.get("x_mitre_is_subtechnique", False)),
        is_revoked=bool(obj.get("revoked", False)),
        is_deprecated=bool(obj.get("x_mitre_deprecated", False)),
        stix_id=obj.get("id"),
    )


def parse_stix_bundle(bundle: Dict[str, Any]) -> List[Technique]:
    """Parse an official MITRE ATT&CK STIX bundle into normalized techniques.

    Handles:
    - attack-pattern objects (techniques and sub-techniques)
    - revoked/deprecated techniques (flagged, not silently dropped)
    - missing optional fields safely
    - mitigations derived from `course-of-action mitigates attack-pattern` relationships
    """
    if not isinstance(bundle, dict) or "objects" not in bundle:
        raise MitreDataError("Provided STIX bundle has no 'objects' array")

    objects = bundle.get("objects", [])
    if not isinstance(objects, list):
        raise MitreDataError("STIX bundle 'objects' must be a list")

    by_id: Dict[str, Dict[str, Any]] = {}
    attack_patterns: List[Dict[str, Any]] = []
    mitigation_objects: Dict[str, str] = {}
    relationship_groups: Dict[str, List[str]] = {}

    for obj in objects:
        if not isinstance(obj, dict) or "id" not in obj:
            continue
        by_id[obj["id"]] = obj
        obj_type = obj.get("type")
        if obj_type == "attack-pattern":
            attack_patterns.append(obj)
        elif obj_type == "course-of-action":
            ext = _get_external_id(obj, STIX_SOURCE) or obj.get("name")
            mitigation_objects[obj["id"]] = str(ext)
        elif obj_type == "relationship":
            rel_type = obj.get("relationship_type")
            target = obj.get("target_ref")
            if rel_type == "mitigates" and target:
                relationship_groups.setdefault(target, []).append(obj.get("source_ref", ""))

    # Attach mitigation names/IDs by attack-pattern STIX id
    mitigations_by_target: Dict[str, List[str]] = {}
    for target_id, source_ids in relationship_groups.items():
        names: List[str] = []
        for source_id in source_ids:
            name = mitigation_objects.get(source_id)
            if name:
                names.append(name)
        if names:
            mitigations_by_target[target_id] = sorted(set(names))

    techniques: List[Technique] = []
    for obj in attack_patterns:
        try:
            technique = parse_attack_pattern(obj)
        except MitreDataError as e:
            logger.warning(f"Skipping attack-pattern: {e}")
            continue
        technique.mitigations = mitigations_by_target.get(obj.get("id", ""), [])
        techniques.append(technique)

    return techniques


def build_documents(
    techniques: List[Technique],
    include_inactive: bool = False,
) -> List[RagDocument]:
    """Deterministically chunk techniques into searchable documents.

    Documents are sorted by (technique_id) so the vector index and metadata
    stay in a reproducible order. Inactive (revoked/deprecated) techniques are
    excluded from retrieval by default.
    """
    documents: List[RagDocument] = []
    for tech in sorted(techniques, key=lambda t: (t.technique_id, t.technique_name)):
        if not include_inactive and not tech.is_active:
            continue
        documents.append(_to_document(tech))

    documents.sort(key=lambda d: (d.technique_id, d.technique_name))
    return documents


def _to_document(tech: Technique) -> RagDocument:
    lines = [
        f"Technique: {tech.technique_name} ({tech.technique_id})",
        f"Type: {'sub-technique' if tech.is_subtechnique else 'technique'}",
    ]
    if tech.tactics:
        lines.append(f"Tactics: {', '.join(tech.tactics)}")
    if tech.aliases:
        lines.append(f"Also known as: {', '.join(tech.aliases)}")
    if tech.description:
        lines.append(f"Description: {tech.description}")
    if tech.detection:
        lines.append(f"Detection: {tech.detection}")
    if tech.mitigations:
        lines.append(f"Mitigations: {', '.join(tech.mitigations)}")
    if tech.data_sources:
        lines.append(f"Data sources: {', '.join(tech.data_sources)}")
    if tech.platforms:
        lines.append(f"Platforms: {', '.join(tech.platforms)}")

    return RagDocument(
        technique_id=tech.technique_id,
        technique_name=tech.technique_name,
        type="sub-technique" if tech.is_subtechnique else "technique",
        text="\n".join(lines),
        tactics=tech.tactics,
        description=tech.description,
        detection=tech.detection,
        mitigations=tech.mitigations,
        data_sources=tech.data_sources,
        platforms=tech.platforms,
        aliases=tech.aliases,
    )