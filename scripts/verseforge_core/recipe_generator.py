"""Small, deterministic Verse device generators based on bundled original examples.

This is not open-ended Verse synthesis. No remote models or UEFN compilation.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

_RE = re.compile(r"^[a-z][a-z0-9_]{1,47}$")


def generate_button_hud(spec: dict[str, Any], destination: Path) -> dict[str, Any]:
    """Generate a usable (editor-wiring required) Button -> HUD Verse device.

    Only a safe device identifier and a short, literal message are accepted.
    The message uses Verse string escaping and no raw source interpolation of syntax.
    """
    if not isinstance(spec, dict) or set(spec) != {'schema', 'device_name', 'message', 'duration_seconds'} or spec['schema'] != 'verseforge-button-hud-v1':
        raise ValueError('Expected complete verseforge-button-hud-v1 specification')
    name = spec['device_name']
    msg = spec['message']
    duration = spec['duration_seconds']
    if not isinstance(name, str) or not _RE.fullmatch(name):
        raise ValueError('Invalid device name')
    if not isinstance(msg, str) or not 1 <= len(msg) <= 120 or any(ord(c) < 32 for c in msg) or any(c in msg for c in '{}"\\'):
        raise ValueError('Message contains unsupported Verse interpolation or escape characters')
    if type(duration) not in (int, float) or not 0.5 <= duration <= 10.0:
        raise ValueError('Duration must be 0.5 to 10 seconds')
    class_name = name if name.endswith("_device") else f"{name}_device"
    if len(class_name) > 55:
        raise ValueError("Resulting device class name is too long")
    target = Path(destination).expanduser()
    if target.exists() or target.is_symlink() or target.parent.is_symlink():
        raise ValueError('Output directory already exists or is symlinked')
    content = ("using { /Fortnite.com/Devices }\nusing { /Verse.org/Simulation }\n\n"
               "# VerseForge original Button/HUD recipe. Compile status: NOT TESTED.\n"
               f"{class_name} := class(creative_device):\n"
               "    @editable\n    Trigger:button_device = button_device{}\n\n"
               "    @editable\n    Notice:hud_message_device = hud_message_device{}\n\n"
               "    var InteractionSubscription:?cancelable = false\n\n"
               f"    Message<localizes>:message = \"{msg}\"\n\n"
               "    OnBegin<override>()<suspends>:void =\n"
               "        set InteractionSubscription = option{Trigger.InteractedWithEvent.Subscribe(OnPress)}\n\n"
               "    OnPress(Who:agent):void =\n"
               f"        Notice.Show(Who, Message, {float(duration):.2f})\n\n"
               "    OnEnd<override>():void =\n"
               "        if (Subscription := InteractionSubscription?):\n"
               "            Subscription.Cancel()\n"
               "        set InteractionSubscription = false\n")
    target.mkdir(parents=True, exist_ok=False)
    try:
        verse = target / 'Verse'
        verse.mkdir()
        file = verse / f'{class_name}.verse'
        file.write_text(content, encoding='utf-8')
        (target / 'INSTALL.md').write_text(
            f'# Installing {name}\n\n1. Copy Verse/{name}.verse into a UEFN test project.\n'
            '2. Run Build Verse Code and resolve any compiler diagnostics.\n'
            f'3. Place {class_name} in the level, plus a Button Device and HUD Message Device.\n'
            '4. Set its Trigger and Notice references in the Details panel.\n'
            '5. Start a Fortnite session, press the button, and test multiple players.\n\n'
            '**Compilation, runtime, and multiplayer: NOT TESTED.**\n', encoding='utf-8')
        (target / 'README.md').write_text(
            f'# Generated Button/HUD recipe: {name}\n\n'
            f'- Source SHA-256: `{hashlib.sha256(content.encode()).hexdigest()}`\n'
            '- API evidence: bundled template only; target UEFN API must be rechecked.\n'
            '- Compilation: NOT TESTED.\n- Runtime: NOT TESTED.\n'
            '- Multiplayer: NOT TESTED.\n', encoding='utf-8')
    except Exception:
        import shutil
        shutil.rmtree(target)
        raise
    return {'result':'GENERATED', 'files':3, 'output':str(target),
            'source_sha256':hashlib.sha256(content.encode()).hexdigest(),
            'uefn_compile':'NOT TESTED','runtime':'NOT TESTED'}
