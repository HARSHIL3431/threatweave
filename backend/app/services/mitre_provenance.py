"""MITRE ATT&CK source provenance and knowledge-base age helpers (P0-1).

Pure, offline helpers: no network access, no model loading, no file I/O.
Used by scripts/build_mitre_index.py (write path) and RagService.status()
(read path) so newly built indexes carry verifiable source provenance while
older artifacts without provenance keep loading.

Honesty rules enforced here:
- The ATT&CK *release* version is exposed only when trustworthy bundle-level
  source metadata establishes it. MITRE CTI STIX bundles carry per-object
  ``x_mitre_version`` values (which vary across objects) and a STIX *spec*
  version (``x_mitre_attack_spec_version``, a schema version, not a content
  release), so no release can be inferred: ``attack_version`` is None.
- Build time (``built_at``) is never presented as release time.
- Missing/invalid timestamps yield age status ``unknown``, never ``fresh``.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Knowledge older than this many days (from a *valid* build timestamp only)
# is flagged stale. Unknown build dates are "unknown", never stale/fresh.
STALE_AFTER_DAYS = 180

AGE_FRESH = "fresh"
AGE_STALE = "stale"
AGE_UNKNOWN = "unknown"


def sha256_hex(data: bytes) -> str:
    """SHA-256 hex digest of the exact bytes provided."""
    return hashlib.sha256(data).hexdigest()


def parse_timestamp(value: Any) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    Returns None for missing, non-string, or unparseable values.
    Naive datetimes are assumed UTC. Never raises.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        # fromisoformat does not accept a trailing 'Z' on older Pythons.
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def max_modified_of(objects: List[Dict[str, Any]]) -> Optional[str]:
    """Latest valid ``modified`` timestamp among attack-pattern objects.

    Only ``attack-pattern`` objects (the indexed technique source) are
    considered. Returns a normalized ISO-8601 string, or None when no
    valid timestamp exists. Never raises.
    """
    latest: Optional[datetime] = None
    for obj in objects or []:
        if not isinstance(obj, dict) or obj.get("type") != "attack-pattern":
            continue
        parsed = parse_timestamp(obj.get("modified"))
        if parsed is not None and (latest is None or parsed > latest):
            latest = parsed
    return latest.isoformat() if latest is not None else None


def extract_attack_version(bundle: Dict[str, Any]) -> Optional[str]:
    """Best-effort ATT&CK release version from bundle-level source metadata.

    Currently always returns None: MITRE CTI STIX bundles expose no
    trustworthy bundle-level release identifier. Per-object
    ``x_mitre_version`` values vary across objects (content revisions, not
    releases) and ``x_mitre_attack_spec_version`` is the STIX *schema*
    version, not the dataset release. Returning None keeps the API honest
    instead of mislabeling the ``master`` branch URL as a release.
    """
    _ = bundle
    return None


def compute_provenance(
    *,
    source_url: str,
    bundle_bytes: bytes,
    bundle: Dict[str, Any],
    built_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build the provenance record for the exact bundle bytes parsed.

    ``bundle_bytes`` must be the exact bytes ``bundle`` was parsed from so
    that ``bundle_sha256``/``bundle_bytes`` verifiably describe the source.
    """
    objects: List[Dict[str, Any]] = []
    if isinstance(bundle, dict):
        raw_objects = bundle.get("objects", [])
        if isinstance(raw_objects, list):
            objects = [o for o in raw_objects if isinstance(o, dict)]
    attack_patterns = [o for o in objects if o.get("type") == "attack-pattern"]
    moment = built_at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return {
        "source_url": source_url,
        "bundle_sha256": sha256_hex(bundle_bytes),
        "bundle_bytes": len(bundle_bytes),
        "attack_pattern_count": len(attack_patterns),
        "attack_version": extract_attack_version(bundle),
        "max_modified": max_modified_of(objects),
        "built_at": moment.astimezone(timezone.utc).isoformat(),
    }


def knowledge_age(
    built_at_value: Any,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Derive knowledge-base age from a stored build timestamp.

    Returns ``{"age_days": int | None, "age_status": fresh|stale|unknown,
    "is_stale": bool}``. Missing/invalid timestamps yield ``unknown`` with
    ``is_stale=False``: unknown must never read as fresh, and staleness is
    only asserted from a valid timestamp older than STALE_AFTER_DAYS.
    ``built_at`` is an *index build* time, never the ATT&CK release time.
    """
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    built = parse_timestamp(built_at_value)
    if built is None:
        return {"age_days": None, "age_status": AGE_UNKNOWN, "is_stale": False}
    age_days = max(0, (moment - built).days)
    if age_days > STALE_AFTER_DAYS:
        return {"age_days": age_days, "age_status": AGE_STALE, "is_stale": True}
    return {"age_days": age_days, "age_status": AGE_FRESH, "is_stale": False}
