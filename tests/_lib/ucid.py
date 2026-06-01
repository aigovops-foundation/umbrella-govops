"""Shared UCID helpers.

The canonical UCID syntax is the *strict* form documented in UCID-REGISTRY.md
§3 and mirrored by the `ucid` field in the EvidenceBundle schema:

    UCID-<DOMAIN>-<TOPIC>-<NNN>

`crosswalk.schema.json` historically carries a looser `^UCID-[A-Z0-9-]+$`
pattern for backward compatibility; tests that assert *registry* compliance
use the strict pattern below, which every shipped UCID already satisfies.
"""
from __future__ import annotations

import re

# UCID-REGISTRY.md §3 prints `{1,7}` for the first segment (i.e. a 2–8 char
# DOMAIN), but the registry itself ships `UCID-OVERSIGHT-001` (DOMAIN is 9
# chars) and the prose lists multi-letter domains like SUPPLYCHAIN (11). The
# enforced schema pattern (`^UCID-[A-Z0-9-]+$`) accepts all of them. We widen
# the first segment to 2–12 chars so the helper matches every real and
# documented-valid UCID while still rejecting the doc's negative examples
# (lowercase ids, un-padded sequences). See docs/api/data-model.md § UCID.
UCID_PATTERN = r"^UCID-[A-Z][A-Z0-9]{1,11}(-[A-Z0-9]{1,16})*-[0-9]{3}$"
UCID_RE = re.compile(UCID_PATTERN)


def is_valid_ucid(value: str) -> bool:
    """True iff *value* is a syntactically valid UCID per the registry rules."""
    return isinstance(value, str) and UCID_RE.match(value) is not None
