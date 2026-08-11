#!/usr/bin/env python3
"""Validate overlay skins under web/skins/<name>.

Static checks for each skin folder:
  * skin.json parses and has the required keys (name, digits, digit_prefix).
  * Every element id referenced by skin.json exists in the skin's meter.svg
    (digits, sign, unit/prefix/icon maps, battery_low, hidden, rtc_label,
    function.id, function.map values).
  * Referenced ids are unique within skin.json; ids in meter.svg are unique.
  * function.map keys (icon-based skins) and "right_aligned" entries are known
    SDK function names (requires brymenble on PYTHONPATH; skipped otherwise).
  * Warnings: SDK functions not covered by an icon skin's function.map, and
    meter.svg element ids never referenced by skin.json.

For skins that use the built-in LCD renderer (skin.js optional), the
"referenced ids exist in meter.svg" check is a full runtime coverage check —
every id the renderer can touch is exactly the set skin.json references.

Usage:
    python tools/check_skin.py              # all skins
    python tools/check_skin.py default      # one skin (name or path)
    python tools/check_skin.py default official

Exit code 0 = no errors, 1 = errors found.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKINS_DIR = ROOT / "web" / "skins"
SEGS = ["a", "b", "c", "d", "e", "f", "g", "dp"]

# Optional: SDK canonical function names, for function.map validation.
try:  # the overlay venv has brymenble installed editable
    from brymen.constants import FUNCTION_NAMES as _SDK_FN

    SDK_FUNCTIONS = set(_SDK_FN.values())
except Exception:  # SDK not importable — name checks are skipped
    SDK_FUNCTIONS = None

ID_RE = re.compile(r'\bid=["\']([^"\']+)["\']')


def svg_id_list(svg_text: str):
    return ID_RE.findall(svg_text)


def referenced_ids(skin: dict):
    """Element ids skin.json references.

    Returns (all_ids, singleton_ids): ``all_ids`` is every referenced id (used
    for the exists-in-SVG check); ``singleton_ids`` are ids expected to appear
    exactly once (sign, battery_low, rtc_label, units, icons). Shared ids
    (prefixes, function icons, hidden) legitimately repeat across entries.
    """
    all_ids, singleton = [], []

    def add(value, to):
        if isinstance(value, str) and value:
            to.append(value)
        elif isinstance(value, list):
            for item in value:
                add(item, to)
        elif isinstance(value, dict):
            for item in value.values():
                add(item, to)

    digits = skin.get("digits")
    digit_prefix = skin.get("digit_prefix")
    no_dp = set(skin.get("no_dp") or [])
    if isinstance(digits, int) and isinstance(digit_prefix, str):
        for d in range(digits):
            for s in SEGS:
                if s == "dp" and d in no_dp:
                    continue  # meter has no decimal point on this digit
                all_ids.append(f"{digit_prefix}{d}_{s}")

    add(skin.get("sign"), singleton)
    add(skin.get("battery_low"), singleton)
    add(skin.get("rtc_label"), singleton)
    add(skin.get("unit"), singleton)
    add(skin.get("icons"), singleton)

    # Shared ids: hidden + prefixes + function icons repeat on purpose.
    add(skin.get("hidden"), all_ids)
    add(skin.get("prefix"), all_ids)

    fn = skin.get("function") or {}
    if fn.get("type") == "text":
        add(fn.get("id"), singleton)
    elif fn.get("type") == "icons":
        add(fn.get("map"), all_ids)

    return all_ids + singleton, singleton


def check_skin(skin_dir: Path):
    """Return (errors, warnings) for one skin folder."""
    errors, warnings = [], []
    name = skin_dir.name

    skin_json = skin_dir / "skin.json"
    if not skin_json.exists():
        return ([f"{name}/skin.json missing"], [])

    try:
        skin = json.loads(skin_json.read_text(encoding="utf-8"))
    except Exception as e:
        return ([f"{name}/skin.json does not parse: {e}"], [])

    # Required keys / types.
    if not isinstance(skin.get("name"), str):
        errors.append("skin.json \"name\" must be a string")
    elif skin.get("name") != name:
        warnings.append(f"skin.json \"name\" is {skin.get('name')!r} but folder is {name!r}")
    # "digits"/"digit_prefix" are only needed for 7-seg LCD skins; text-based
    # skins (e.g. a large reading text) can omit them entirely.
    digits = skin.get("digits")
    digit_prefix = skin.get("digit_prefix")
    if digits is not None:
        if not isinstance(digits, int) or digits < 1:
            errors.append("skin.json \"digits\" must be a positive integer")
        elif not isinstance(digit_prefix, str) or not digit_prefix:
            errors.append("skin.json \"digit_prefix\" is required when \"digits\" is set")
    elif digit_prefix is not None:
        errors.append("skin.json \"digits\" is required when \"digit_prefix\" is set")
    if skin.get("script") and not isinstance(skin.get("script"), str):
        errors.append("skin.json \"script\" must be a string")
    no_dp = skin.get("no_dp") or []
    if not isinstance(no_dp, list) or not all(isinstance(i, int) for i in no_dp):
        errors.append("skin.json \"no_dp\" must be a list of digit indexes (ints)")

    # meter.svg must exist.
    svg_path = skin_dir / "meter.svg"
    if not svg_path.exists():
        errors.append(f"{name}/meter.svg missing — the skin cannot render")
        return (errors, warnings)
    svg_text = svg_path.read_text(encoding="utf-8")
    svg_ids = set(svg_id_list(svg_text))

    # Referenced ids must exist in the SVG.
    refs, singleton = referenced_ids(skin)
    if not refs:
        warnings.append("skin.json references no element ids")
    missing = sorted(set(refs) - svg_ids)
    for mid in missing:
        errors.append(f"id {mid!r} referenced by skin.json but missing from meter.svg")

    # Uniqueness (shared prefix/function ids intentionally repeat).
    dupe_singleton = [i for i, c in Counter(singleton).items() if c > 1]
    for mid in dupe_singleton:
        warnings.append(f"id {mid!r} referenced more than once by skin.json (expected once: sign/unit/icon/label)")
    dupe_svg = [i for i, c in Counter(svg_id_list(svg_text)).items() if c > 1]
    for mid in dupe_svg:
        errors.append(f"id {mid!r} appears more than once in meter.svg (must be unique)")

    # Unreferenced SVG ids (informational — custom skins may drive extra ids).
    unref = svg_ids - set(refs)
    if unref:
        shown = ", ".join(sorted(unref)[:12])
        more = " …" if len(unref) > 12 else ""
        warnings.append(f"{len(unref)} meter.svg id(s) never referenced: {shown}{more}")

    # Function map / right_aligned against SDK canonical names.
    fn = skin.get("function") or {}
    fn_map = fn.get("map") if fn.get("type") == "icons" else None
    right_aligned = skin.get("right_aligned") or []
    if not isinstance(right_aligned, list):
        errors.append("skin.json \"right_aligned\" must be a list of function names")

    if SDK_FUNCTIONS is None:
        if fn_map or right_aligned:
            warnings.append("brymenble SDK not importable — function-name checks skipped")
    else:
        if fn_map is not None:
            for fname in fn_map:
                if fname not in SDK_FUNCTIONS:
                    errors.append(f"function.map key {fname!r} is not a known SDK function name")
            missing = SDK_FUNCTIONS - set(fn_map)
            if missing:
                warnings.append(
                    f"function.map does not cover {len(missing)} SDK function(s): "
                    + ", ".join(sorted(missing))
                )
        for fname in right_aligned:
            if fname not in SDK_FUNCTIONS:
                errors.append(f"right_aligned entry {fname!r} is not a known SDK function name")

    return (errors, warnings)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate overlay skins.")
    ap.add_argument(
        "skins", nargs="*",
        help="skin folder name(s) or path(s); default: all skins under web/skins/",
    )
    args = ap.parse_args(argv)

    if args.skins:
        targets = []
        for s in args.skins:
            p = Path(s)
            targets.append(p if p.is_dir() else SKINS_DIR / s)
    else:
        targets = sorted(p.parent for p in SKINS_DIR.glob("*/skin.json"))

    if not targets:
        print(f"No skins found under {SKINS_DIR}")
        return 1

    total_errors = 0
    for t in targets:
        if not t.is_dir():
            print(f"[ERROR] skin folder not found: {t}")
            total_errors += 1
            continue
        errors, warnings = check_skin(t)
        tag = "OK " if not errors else "ERR"
        print(f"\n[{tag}] {t.name}")
        for w in warnings:
            print(f"      warn: {w}")
        for e in errors:
            print(f"     error: {e}")
        total_errors += len(errors)

    print(f"\n{'FAIL' if total_errors else 'PASS'}: {total_errors} error(s) total")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
