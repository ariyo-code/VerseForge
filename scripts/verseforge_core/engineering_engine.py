"""Project engineering planner: validated specs, module ownership, DAG and safe scaffolding.

No claim of automatic Verse correctness or runtime compilation. Agents must supply
real feature implementations and editor-validated API evidence separately.
"""
from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any

SCHEMA = "verseforge-engineering-spec-v1"
_ID = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
_KINDS = {"player", "economy", "inventory", "vehicle", "property", "organization", "job", "moderation", "ui", "integration", "custom"}
_STATE_SCOPES = {"none", "session", "player-persistent"}


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"Invalid {field}; use 2–48 lowercase snake_case characters")
    return value


def _text(value: Any, field: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or "\x00" in value or any(ord(x) < 32 and x not in "\n\t" for x in value):
        raise ValueError(f"Invalid {field}")
    return value


def _names(values: Any, field: str, limit: int = 32) -> list[str]:
    if not isinstance(values, list) or len(values) > limit:
        raise ValueError(f"{field} must be a bounded array")
    out = [_name(x, field) for x in values]
    if len(set(out)) != len(out):
        raise ValueError(f"Duplicated {field}")
    return out


def architecture(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a declared project architecture; no inferred APIs."""
    if not isinstance(spec, dict) or spec.get("schema") != SCHEMA:
        raise ValueError("Unsupported engineering spec")
    project = _name(spec.get("project"), "project")
    description = _text(spec.get("description"), "description", 2000)
    modules = spec.get("modules")
    if not isinstance(modules, list) or not 1 <= len(modules) <= 48:
        raise ValueError("Expected 1–48 modules")
    normalized = {}
    writer_owners = {}
    for m in modules:
        if not isinstance(m, dict):
            raise ValueError("Module must be an object")
        mid = _name(m.get("id"), "module")
        if mid in normalized:
            raise ValueError("Duplicate module id")
        kind = m.get("kind", "custom")
        if kind not in _KINDS:
            raise ValueError(f"Unsupported module kind: {kind}")
        scope = m.get("state_scope", "none")
        if scope not in _STATE_SCOPES:
            raise ValueError(f"Invalid state scope for {mid}")
        owns = _names(m.get("owns", []), "state owner")
        depends = _names(m.get("depends_on", []), "dependency")
        requirements = m.get("requirements", [])
        if not isinstance(requirements, list) or len(requirements) > 50:
            raise ValueError("Requirement count exceeded")
        requirements = [_text(x, "requirement", 500) for x in requirements]
        permissions = _names(m.get("permissions", []), "permission")
        api = m.get("api_claims", [])
        if not isinstance(api, list) or len(api) > 64:
            raise ValueError("Invalid API claim list")
        api = [_text(x, "api claim", 150) for x in api]
        if owns and scope == "none":
            raise ValueError(f"{mid} owns state but declares no state scope")
        for state in owns:
            if state in writer_owners:
                raise ValueError(f"Multiple state owners for {state}: {writer_owners[state]}, {mid}")
            writer_owners[state] = mid
        normalized[mid] = dict(id=mid, kind=kind, state_scope=scope, owns=owns,
                               depends_on=depends, requirements=requirements,
                               permissions=permissions, api_claims=api)
    for mid, m in normalized.items():
        if mid in m["depends_on"]:
            raise ValueError(f"Module {mid} depends on itself")
        for dep in m["depends_on"]:
            if dep not in normalized:
                raise ValueError(f"Unknown dependency: {mid} -> {dep}")
    # Sorted Kahn algorithm for a stable reproducible dependency order.
    pending = {mid: set(m["depends_on"]) for mid, m in normalized.items()}
    order = []
    while pending:
        ready = sorted(mid for mid, deps in pending.items() if not deps)
        if not ready:
            raise ValueError("Cyclic module dependency graph")
        order.extend(ready)
        for mid in ready:
            del pending[mid]
        for deps in pending.values():
            deps.difference_update(ready)
    phases = []
    for index, mid in enumerate(order, start=1):
        m = normalized[mid]
        phases.append({"order": index, "module": mid, "depends_on": m["depends_on"],
                       "source": f"Verse/{mid}_device.verse", "requirements": m["requirements"],
                       "api_evidence": "REQUIRED" if m["api_claims"] else "NO API CLAIMS",
                       "uefn_compile": "NOT TESTED", "runtime": "NOT TESTED"})
    risks = []
    if any(m["state_scope"] == "player-persistent" for m in normalized.values()):
        risks.append("Persistent player schema changes require compatibility and FitsInPlayerMap checks in UEFN")
    if any(m["kind"] in {"economy", "inventory", "vehicle"} for m in normalized.values()):
        risks.append("Mutating gameplay operations require server-authoritative permissions and duplicate protection")
    if any(m["kind"] == "ui" for m in normalized.values()):
        risks.append("UMG widget assets and runtime wiring must be created in the editor")
    return {"schema": "verseforge-engineering-plan-v1", "project": project,
            "description": description, "module_order": order, "state_owners": writer_owners,
            "modules": [normalized[mid] for mid in order], "phases": phases, "risks": risks,
            "api_claim_status": "NOT VERIFIED", "uefn_compile": "NOT TESTED",
            "gameplay": "NOT TESTED", "multiplayer": "NOT TESTED"}


def load_engineering_spec(path: Path) -> dict:
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
        raise ValueError("Expected regular engineering spec <= 256 KiB")
    return json.loads(path.read_text(encoding="utf-8"))


def scaffold(plan: dict[str, Any], target: Path) -> dict:
    """Create new files only. Never overwrite even one user-authored module."""
    if plan.get("schema") != "verseforge-engineering-plan-v1":
        raise ValueError("Expected validated engineering plan")
    base = Path(target).expanduser()
    if base.exists() or base.is_symlink():
        raise ValueError("Refusing to overwrite an existing project directory")
    if base.parent.is_symlink():
        raise ValueError("Refusing a symlinked parent")
    created = []
    try:
        (base / "Verse").mkdir(parents=True, exist_ok=False)
        for module in plan["modules"]:
            name = _name(module["id"], "module")
            source = ("# VerseForge engineering scaffold; NOT a functional game system.\n"
                      "# Replace TODOs after authoritative API verification.\n"
                      "using { /Fortnite.com/Devices }\n"
                      "using { /Verse.org/Simulation }\n"
                      "using { /UnrealEngine.com/Temporary/Diagnostics }\n\n"
                      f"{name}_device := class(creative_device):\n"
                      "    OnBegin<override>()<suspends>:void =\n"
                      f"        Print(\"{name} scaffold — implementation pending\")\n")
            p = base / "Verse" / f"{name}_device.verse"
            p.write_text(source, encoding="utf-8")
            created.append(p)
        (base / "ARCHITECTURE.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        lines = [f"# {plan['project']} — Architecture", "", plan["description"], "",
                 "## Order of implementation", ""]
        for phase in plan["phases"]:
            lines.append(f"{phase['order']}. **{phase['module']}** — depends on: {', '.join(phase['depends_on']) or 'none'}")
        lines += ["", "## Invariants", "", "- Only one module owns each mutable state namespace.",
                  "- Dependencies must be wired explicitly, no invented Verse API symbols.",
                  "- Generated sources are *scaffolds only*; functionality remains to implement.",
                  "- UEFN compile, runtime and multiplayer are NOT TESTED.", ""]
        (base / "README.md").write_text("\n".join(lines), encoding="utf-8")
        checks = [{"module": m["id"], "expected": m["requirements"],
                   "status": "NOT IMPLEMENTED"} for m in plan["modules"]]
        (base / "ACCEPTANCE.json").write_text(json.dumps({"schema":"verseforge-engineering-acceptance-v1", "checks":checks,
              "uefn_compile":"NOT TESTED", "runtime":"NOT TESTED"}, indent=2) + "\n", encoding="utf-8")
    except Exception:
        import shutil
        if base.exists() and not base.is_symlink():
            shutil.rmtree(base)
        raise
    return {"result": "SCAFFOLD CREATED", "root": str(base), "files": len(created) + 3,
            "functions_implemented": False, "uefn_compile": "NOT TESTED", "source_sha256":
            {p.relative_to(base).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in created}}
