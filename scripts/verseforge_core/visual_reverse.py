"""Experimental visual reference evidence + strict host-vision UI reconstruction contract.

Image pixels alone do NOT reveal Verse code, events, ownership or implementation.
The host model may propose a semantic component map; this module validates and
transforms it into a reproducible UEFN implementation *plan*, never a compiled UI.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 16_000_000
MAX_SCREENS = 10
MAX_COMPONENTS = 120
ALLOWED_SOURCE_TYPES = {"observed", "inferred", "user-specified", "unknown"}
ALLOWED_KINDS = {"panel", "text", "button", "image", "icon", "list", "input", "progress", "unknown"}
ALLOWED_ACTIONS = {"open", "close", "navigate", "submit", "interact", "display", "unknown"}
_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ASSET_REF = re.compile(r"^(?:UI|Assets)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp)$")


def inspect_image(path: Path) -> dict[str, Any]:
    """Read safe low-level image properties, without OCR or semantic inference.

    Requires Pillow as an optional dependency; never sends user images remotely.
    """
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ValueError("Install optional Pillow to inspect image pixels") from exc
    path = Path(path).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError("A regular local image is required; symlinks not accepted")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds the 15 MiB input limit")
    try:
        with Image.open(path) as im:
            if getattr(im, "n_frames", 1) != 1:
                raise ValueError("Animated/multipage image not supported")
            width, height = im.size
            if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                raise ValueError("Image dimensions exceed safety limits")
            fmt = im.format
            if fmt not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("Accepted formats: PNG, JPEG, WEBP")
            frame = ImageOps.exif_transpose(im).convert("RGB")
            frame.thumbnail((128, 128))
            buckets = Counter(tuple((c // 32) * 32 + 16 for c in rgb) for rgb in (frame.get_flattened_data() if hasattr(frame, "get_flattened_data") else frame.getdata()))
            total = sum(buckets.values())
            colors = [{"hex": "#%02X%02X%02X" % rgb, "approx_coverage": round(count / total, 3)}
                      for rgb, count in buckets.most_common(8)]
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Invalid or damaged image") from exc
    return {
        "schema": "verseforge-image-evidence-v1", "name": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "format": fmt, "dimensions": {"width": width, "height": height},
        "sampled_palette": colors, "palette_is_approximate": True,
        "detected_widgets": "NOT PERFORMED", "code_recovery": "NOT POSSIBLE FROM IMAGE ALONE",
        "image_sent_remotely": False,
    }


def _clean_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"Invalid {label}: use a lowercase snake_case identifier")
    return value


def _plain(value: Any, label: str, limit: int = 256) -> str:
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError(f"Invalid {label}")
    return value


def _fraction(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not 0 <= value <= 1:
        raise ValueError(f"Invalid normalized {label}")
    return float(value)


def plan_from_observations(data: dict[str, Any], image_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate host-produced observations; never claim they came from built-in CV."""
    if not isinstance(data, dict) or data.get("schema") != "verseforge-visual-observations-v1":
        raise ValueError("Unsupported visual observations schema")
    screens = data.get("screens")
    if not isinstance(screens, list) or not 1 <= len(screens) <= MAX_SCREENS:
        raise ValueError("Require 1–10 screens")
    if image_evidence and (not isinstance(image_evidence, dict) or image_evidence.get("schema") != "verseforge-image-evidence-v1"):
        raise ValueError("Invalid image evidence")
    all_ids = set()
    result_screens = []
    action_checks = []
    uncertainties = []
    for screen in screens:
        if not isinstance(screen, dict):
            raise ValueError("Each screen must be an object")
        sid = _clean_id(screen.get("id"), "screen id")
        if sid in all_ids:
            raise ValueError("Duplicate screen id")
        all_ids.add(sid)
        elements = screen.get("elements")
        if not isinstance(elements, list) or len(elements) > MAX_COMPONENTS:
            raise ValueError("Screen element count exceeds limit")
        local_ids = set()
        output_elements = []
        for element in elements:
            if not isinstance(element, dict):
                raise ValueError("Element must be an object")
            eid = _clean_id(element.get("id"), "element id")
            if eid in local_ids:
                raise ValueError("Duplicate element id")
            local_ids.add(eid)
            kind = element.get("kind")
            if kind not in ALLOWED_KINDS:
                raise ValueError("Unsupported element kind")
            evidence = element.get("evidence")
            if evidence not in ALLOWED_SOURCE_TYPES:
                raise ValueError("Every element requires an evidence label")
            rect = element.get("bounds")
            if not isinstance(rect, dict) or set(rect) != {"x", "y", "w", "h"}:
                raise ValueError("Bounds require x,y,w,h")
            bounds = {key: _fraction(rect[key], key) for key in ("x", "y", "w", "h")}
            if bounds["w"] <= 0 or bounds["h"] <= 0 or bounds["x"] + bounds["w"] > 1.000001 or bounds["y"] + bounds["h"] > 1.000001:
                raise ValueError("Element bounds must fit inside the screen")
            caption = _plain(element.get("text", ""), "element text")
            asset = element.get("asset")
            if asset is not None:
                if kind not in {"image", "icon"} or not isinstance(asset, str) or len(asset)>180 or not _ASSET_REF.fullmatch(asset):
                    raise ValueError("Asset references require bounded UI/Assets raster paths on icon/image widgets")
            action = element.get("action", "unknown")
            target = element.get("target")
            if target is not None:
                _clean_id(target, "target screen")
                if action != "navigate" or kind != "button":
                    raise ValueError("Navigation target requires a button with navigate action")
            if action not in ALLOWED_ACTIONS:
                raise ValueError("Unsupported action")
            if action in {"submit", "interact", "navigate"}:
                action_checks.append({"screen": sid, "element": eid, "action": action, "status": "NOT IMPLEMENTED"})
            if evidence in {"unknown", "inferred"} or action == "unknown":
                uncertainties.append(f"{sid}/{eid}: behavior or evidence is not established")
            output_elements.append({"id": eid, "kind": kind, "text": caption, "bounds": bounds,
                                    "evidence": evidence, "action": action, "target": target, "asset": asset})
        result_screens.append({"id": sid, "elements": output_elements,
                               "recommended_layer": "UMG or Verse UI — verify with installed UEFN"})
    for screen in result_screens:
        for element in screen["elements"]:
            if element.get("target") is not None and element["target"] not in all_ids:
                raise ValueError(f"Navigation target does not exist: {element['target']}")
    user_behavior = data.get("requested_behavior", "")
    _plain(user_behavior, "requested behavior", 3000)
    return {
        "schema": "verseforge-visual-plan-v1", "reference": image_evidence,
        "screens": result_screens, "requested_behavior": user_behavior,
        "implementation_steps": [
            "Verify local Verse API/UMG capabilities and the actual editor toolset.",
            "Build original widgets from observed layout; apply a consistent design system.",
            "Define app state, per-player ownership and events from user-specified requirements.",
            "Implement Verse interactions and wire editable device references where needed.",
            "Compile in UEFN and inspect runtime, controls and multiplayer behavior.",
            "Compare a real UI screenshot against the reference and iterate."
        ],
        "interaction_checks": action_checks, "uncertainties": uncertainties,
        "static_layout": "PLANNED", "verse_source": "NOT GENERATED", "umg_asset": "NOT GENERATED",
        "uefn_compile": "NOT TESTED", "runtime": "NOT TESTED", "multiplayer": "NOT TESTED",
        "note": "Host vision observations are unverified data; this utility does not create Verse or import UMG."
    }


def load_visual_spec(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.stat().st_size > 256 * 1024:
        raise ValueError("Visual specification too large")
    return json.loads(path.read_text(encoding="utf-8"))
