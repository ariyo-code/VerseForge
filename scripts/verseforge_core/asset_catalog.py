"""Curated source discovery, not an asset download or rights clearance service."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_MAX_CATALOG = 120
_ALLOWED_CATEGORIES = {"icon", "aggregator", "game-assets", "marketplace", "official", "texture", "font", "illustration", "audio"}


def discover_sources(catalog: Path, *, query: str = "", category: str | None = None, reviewed_only: bool = False) -> dict[str, Any]:
    if not isinstance(query, str) or len(query) > 120 or any(ord(c) < 32 for c in query):
        raise ValueError("Invalid asset catalog query")
    if category is not None and category not in _ALLOWED_CATEGORIES:
        raise ValueError("Unknown asset category")
    raw = json.loads(Path(catalog).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or len(raw) > _MAX_CATALOG:
        raise ValueError("Invalid or oversized asset catalog")
    names: set[str] = set()
    entries = []
    terms = [p.casefold() for p in re.split(r"\s+", query.strip()) if p]
    for obj in raw:
        if not isinstance(obj, dict) or not all(isinstance(obj.get(k), str) for k in ("name", "url", "category", "license", "review_status", "redistribution")):
            raise ValueError("Asset catalog entry lacks required fields")
        name = obj["name"]
        if len(name) > 120 or name.casefold() in names or obj["category"] not in _ALLOWED_CATEGORIES:
            raise ValueError("Invalid or duplicate asset source")
        names.add(name.casefold())
        if not obj["url"].startswith("https://"):
            raise ValueError("Catalog source must use HTTPS")
        searchable = " ".join(str(obj.get(k, "")) for k in ("name", "category", "author", "license")).casefold()
        if category and obj["category"] != category:
            continue
        if reviewed_only and obj["review_status"] != "catalog-license-verified-per-asset-check-still-required":
            continue
        if any(term not in searchable for term in terms):
            continue
        entries.append({"name": name, "url": obj["url"], "category": obj["category"],
                        "license_claim": obj["license"], "catalog_status": obj["review_status"],
                        "license_evidence_url": obj.get("license_evidence_url"),
                        "import_authorized": False, "redistribution_authorized": False})
    return {"schema": "verseforge-asset-source-results-v1", "query": query, "category": category,
            "matches": entries, "count": len(entries), "total_catalog_entries": len(raw),
            "rights_warning": "Discovery only. Each individual asset needs source, rights and UEFN compatibility review before importing. No asset was downloaded."}
