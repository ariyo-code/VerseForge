"""Deterministic UI mock and UMG handoff from a *validated* visual plan.

Produces a browser preview and editor implementation manifest. Never claims to
create a .uasset, infer interaction from pixels, or compile Verse.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import stat
from .asset_license import check_asset_manifest
from pathlib import Path
from typing import Any

from .visual_reverse import plan_from_observations
from .verse_ui_generator import generate_verse_ui

_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _safe_token(val: Any, field: str) -> str:
    if not isinstance(val, str) or not _ID.fullmatch(val):
        raise ValueError(f"Invalid {field}")
    return val


def render_ui(spec: dict[str, Any], output: Path, *, theme: str = "dark", emit_verse: bool = False,
              assets_dir: Path | None = None, design_tokens: dict[str,Any] | None = None) -> dict:
    """Input is the host vision observation JSON, not a screenshot itself."""
    if theme not in {"dark", "light"}:
        raise ValueError("Unsupported theme")
    plan = plan_from_observations(spec)
    output = Path(output).expanduser()
    if output.exists() or output.is_symlink() or output.parent.is_symlink():
        raise ValueError("UI output must be a new directory without symlinks")
    screens = plan["screens"]
    requested_assets = sorted({item["asset"] for screen in screens for item in screen["elements"] if item.get("asset")})
    asset_files = {}
    asset_manifest = None
    if assets_dir is not None:
        assets_dir = Path(assets_dir).expanduser()
        if assets_dir.is_symlink() or not assets_dir.is_dir():
            raise ValueError("Asset source must be a non-symlinked local directory")
        manifest_file = assets_dir / "ASSET_MANIFEST.json"
        if manifest_file.is_symlink() or not manifest_file.is_file() or manifest_file.stat().st_size>128*1024:
            raise ValueError("UI asset directory lacks a valid manifest")
        asset_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        for rec in asset_manifest.get("assets",[]):
            path = rec.get("path")
            if not isinstance(path,str) or not re.fullmatch(r"(?:UI|Assets)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp|wav|ogg)",path):
                raise ValueError("Invalid asset manifest path")
            actual = assets_dir / path
            cursor = assets_dir
            for component in path.split('/'):
                cursor = cursor / component
                if cursor.is_symlink():
                    raise ValueError("UI preview cannot follow an asset symlink")
            if not actual.is_file() or actual.stat().st_size>8*1024*1024:
                raise ValueError("Asset source missing or oversized")
            asset_files[path] = actual.read_bytes()
        check_asset_manifest(manifest_file.read_bytes(),asset_files)
        if set(requested_assets)-set(asset_files):
            raise ValueError("UI refers to undeclared local artwork")
    elif requested_assets:
        # Preserve original layout but do not pretend an asset was imported.
        pass
    bg, fg, panel = (("#101217", "#f5f6fa", "#222632") if theme == "dark" else
                     ("#f2f4f8", "#1c212b", "#ffffff"))
    palette = {'background':bg,'surface':panel,'text':fg,'primary':'#6a92ff'}
    if design_tokens is not None:
        if not isinstance(design_tokens,dict) or not isinstance(design_tokens.get('palette'),dict):
            raise ValueError('Design tokens must contain a color palette')
        provided=design_tokens['palette']
        if not set(provided).issubset({'background','surface','text','primary','danger'}):
            raise ValueError('Unknown or unsupported color token')
        for key,value in provided.items():
            if not isinstance(value,str) or not re.fullmatch(r'#[A-Fa-f0-9]{6}',value):
                raise ValueError('Color tokens must be literal six-digit hex codes')
        palette.update(provided)
    bg,fg,panel=palette['background'],palette['text'],palette['surface']
    css = f"""
:root{{--bg:{bg};--fg:{fg};--panel:{panel};--accent:{palette['primary']}}}
*{{box-sizing:border-box}} body{{margin:0;background:#080b10;color:#e6eaf5;font:14px system-ui,sans-serif}}
header{{padding:16px 20px}}main{{max-width:1180px;margin:0 auto;padding:16px}}
.screen{{position:relative;width:100%;aspect-ratio:16 / 9;background:var(--bg);color:var(--fg);border:1px solid #59627e;border-radius:18px;overflow:hidden;display:none}}
.screen.active{{display:block}}
.widget{{position:absolute;overflow:hidden;border-radius:8px;padding:8px;background:var(--panel);color:var(--fg);font-size:clamp(10px,1.2vw,20px)}}
.widget[data-kind="text"]{{background:transparent}}.widget[data-kind="button"]{{background:var(--accent);border:0;cursor:pointer;color:#080b10;font-weight:700}}
.widget[data-kind="image"],.widget[data-kind="icon"]{{border:1px dashed #7f889f;background:transparent}}
.widget:focus-visible{{outline:3px solid orange}}.widget[data-kind="input"]{{border:1px solid #7f889f}}
nav button{{cursor:pointer;padding:8px 12px;margin:0 6px 10px 0;border:1px solid #626c84;border-radius:8px;background:#242c3f;color:white}}
.footnote{{color:#a9b2c5;font-size:12px;padding:12px 0}}
"""
    blocks = []
    manifest_screens = []
    for sidx, screen in enumerate(screens):
        sid = _safe_token(screen["id"], "screen id")
        elements = []
        widgets_html = []
        for item in screen["elements"]:
            eid = _safe_token(item["id"], "widget id")
            action = item["action"]
            bounds = item["bounds"]
            style = ";".join(f"{k}:{bounds[v] * 100:.3f}%" for k, v in
                             [("left","x"),("top","y"),("width","w"),("height","h")])
            tag = "button" if item["kind"] == "button" else "div"
            # UI mock does not implement unspecified game behavior; a button without a
            # confirmed navigation target is visibly disabled.
            attributes = f'data-kind="{html.escape(item["kind"], quote=True)}" data-evidence="{html.escape(item["evidence"], quote=True)}"'
            label = html.escape(item["text"] or f"{item['kind']}: {eid}")
            if item.get('asset') and item['asset'] in asset_files:
                label = f'<img loading="lazy" alt="{html.escape(item["text"] or eid,quote=True)}" src="preview-assets/{html.escape(item["asset"],quote=True)}" style="width:100%;height:100%;object-fit:contain" />' 
            if tag == "button":
                if item.get('target') and action == 'navigate':
                    attributes += f' type="button" data-target="{html.escape(item["target"],quote=True)}" title="Mock screen navigation only"'
                elif action == 'close':
                    attributes += ' type="button" data-close="true" title="Close preview"'
                else:
                    attributes += ' type="button" disabled title="Editor wiring required"' 
            widgets_html.append(f'<{tag} class="widget" id="w_{sid}_{eid}" {attributes} style="{style}">{label}</{tag}>')
            elements.append({"id": eid, "kind": item["kind"], "bounds": bounds, "text": item["text"],
                             "evidence": item["evidence"], "requested_action": action, "target": item.get("target"), "asset": item.get("asset"),
                             "implementation": "REQUIRES VERSE/UMG WIRING" if action != "display" else "VISUAL ONLY"})
        html_widgets = "\n".join(widgets_html)
        blocks.append(f'<section class="screen{" active" if sidx == 0 else ""}" id="screen_{sid}" aria-label="Screen {html.escape(sid)}">{html_widgets}</section>')
        manifest_screens.append({"id": sid, "widgets": elements, "uefn_asset": "NOT GENERATED"})
    screen_html = "\n".join(blocks)
    tabs = " ".join(f'<button type="button" data-screen="{s["id"]}">{html.escape(s["id"])}</button>' for s in screens)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>VerseForge UI Prototype</title><style>{css}</style></head>
<body><header><strong>VERSEFORGE / UI PROTOTYPE</strong> · <span>Design preview only — not Fortnite</span></header>
<main><nav aria-label="Screen selector">{tabs}</nav>{screen_html}<p class="footnote">Visual mock. Game actions are disabled until explicitly implemented in Verse/UMG. Screens and positions come from supplied observations.</p></main>
<script>function show(id){{document.querySelectorAll('.screen').forEach(s=>s.classList.toggle('active',s.id==='screen_'+id));}}document.querySelectorAll('[data-screen]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.screen)));document.querySelectorAll('[data-target]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.target)));document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'))));</script></body></html>"""
    manifest = {"schema": "verseforge-umg-handoff-v1", "theme": theme, "palette":palette,
                "reference": plan["reference"], "screens": manifest_screens,
                "interaction_checks": plan["interaction_checks"], "uncertainties": plan["uncertainties"],
                "attached_assets": requested_assets if assets_dir is not None else [],
                "verse_source": "NOT GENERATED", "umg_asset": "NOT GENERATED", "uefn_compile": "NOT TESTED"}
    instructions = ("# UMG implementation handoff\n\n"
                    "1. Open UEFN Widget Blueprint in the editor; design an original UI using the coordinate hierarchy in `UMG_HANDOFF.json`.\n"
                    "2. Connect controls to verified Verse UI interaction APIs and gameplay state.\n"
                    "3. Import only licensed assets with manifest evidence; the HTML is a visual mock, not an editor import.\n"
                    "4. Test keyboard, touch and controller focus, then compile Verse inside the actual UEFN editor.\n"
                    "5. Compare a real in-game screenshot with the reference; check multiplayer ownership and lifecycle.\n\n"
                    "**Statuses: UMG NOT GENERATED, Verse NOT GENERATED, UEFN NOT TESTED.**\n")
    verse_result = generate_verse_ui(spec) if emit_verse else None
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "preview.html").write_text(page, encoding="utf-8")
        (output / "UMG_HANDOFF.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (output / "IMPLEMENTATION.md").write_text(instructions, encoding="utf-8")
        (output / "DESIGN_TOKENS.json").write_text(json.dumps({'schema':'verseforge-ui-tokens-v1','palette':palette},indent=2)+'\n',encoding='utf-8')
        if assets_dir is not None and requested_assets:
            for name in requested_assets:
                target = output / 'preview-assets' / name
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(asset_files[name])
            subset = {"schema":"verseforge-asset-manifest-v1", "assets":[x for x in asset_manifest['assets'] if x['path'] in requested_assets]}
            (output/'ASSET_MANIFEST.json').write_text(json.dumps(subset,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        if verse_result is not None:
            (output / "Verse").mkdir()
            (output / "Verse" / verse_result["filename"]).write_text(verse_result["source"], encoding="utf-8")
            (output / "VERSE_UI_STATUS.json").write_text(json.dumps({k:v for k,v in verse_result.items() if k != "source"},indent=2) + "\n", encoding="utf-8")
    except Exception:
        import shutil
        shutil.rmtree(output)
        raise
    return {"result": "PREVIEW AND HANDOFF CREATED", "screens": len(screens), "widgets": sum(len(x["widgets"]) for x in manifest_screens),
            "output": str(output), "attached_assets": len(requested_assets) if assets_dir is not None else 0, "umg_asset": "NOT GENERATED", "verse_source": "UNCOMPILED SCAFFOLD" if emit_verse else "NOT GENERATED", "uefn_compile": "NOT TESTED"}
