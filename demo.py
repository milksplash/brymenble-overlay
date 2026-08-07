"""Demo mode: serve the overlay with a synthetic meter state (no BLE needed).

Usage:
    python demo.py [--host 0.0.0.0] [--port 8765] [--function DCV] [--cycle] [--dp]

The demo binds to all interfaces by default (like main.py), so OBS or a
browser on any machine on the LAN can open it. Pass --host 127.0.0.1 to
restrict it to this machine.

The menu at startup lists EVERY meter function the SDK decodes
(brymen.constants.FUNCTION_NAMES) plus a few special/flag demos, each with
the value the SDK would decode — so you can verify every function and status
flag renders correctly before hooking up a real meter.

Interactive controls (Windows console — works in VS Code / PowerShell):
    n / Right  -> next item
    p / Left   -> previous item
    <number> + Enter -> jump straight to an item (menu is printed at start)
    c          -> toggle auto-cycle through every item
    q          -> quit

Per-function demo values (unit, prefix, raw_value, decimal_pos, digits) live
in the FUNCTION_SPECS dict below — edit that dict to change what the demo
shows. The DCV entry (60780 / decimal_pos 3) renders as "607.80", the
highest reasonable value for a 5-digit meter (60.780 and 6.0780 are the same
digits with decimal_pos 2 and 1).
"""
import argparse
import asyncio
import threading
from typing import Any, Dict, List, Optional, Tuple

from brymen import constants
from brymen.formatter import format_reading
from brymen.parsers import InfoPacket, ReadingPacket, RtcTime

from overlay.server import display_host, lan_ip, run_server
from overlay.state import build_render_state

try:
    import msvcrt          # Windows-only raw console input
    HAS_KEYS = True
except ImportError:        # pragma: no cover - non-Windows fallback
    msvcrt = None
    HAS_KEYS = False


# --- Reading factory ----------------------------------------------------------

def reading(**kw) -> ReadingPacket:
    defaults = dict(
        function_name="DCV", unit="V", raw_value=60780, decimal_pos=3,
        prefix="", display_digit_count=5, logging_data_set_id=1,
        device_reading_pk_id=1, device_type=1, status0=0, status1=0,
        rtc=RtcTime(2026, 8, 6, 12, 34, 56, 789),
        is_crest=False, is_relative=False, is_held=False, is_auto_range=False,
        is_auto_hold=False, is_ascii=False, is_negative=False,
        is_overload=False, is_recording=False, is_max=False, is_min=False,
        is_avg=False, ascii_text=None, crc_ok=True, raw=b"",
    )
    defaults.update(kw)
    return ReadingPacket(**defaults)


INFO = InfoPacket(
    device_category=2, mac=bytes.fromhex("001122334455"), battery_status=0,
    power_source=0, reading_packet_count=4, device_reading_pk_id=1,
    crc_ok=True, raw=b"",
)

# --- Per-function demo values --------------------------------------------------
# name -> (unit, prefix, raw_value, decimal_pos, display_digits)
# This is the single place to edit the demo values. Every function the SDK
# decodes must have an entry here (a missing entry raises KeyError loudly so
# nothing is silently shown with the wrong value).
FUNCTION_SPECS = {
    "LoZ-ACV":           ("V",  "",      60780, 3, 5),
    "LoZ-DCV":           ("V",  "",      60780, 3, 5),
    "AUTO":              ("V",  "",      60780, 3, 5),
    "ACV":               ("V",  "",      60780, 3, 5),
    "DCV":               ("V",  "",      60780, 3, 5),
    "DC+ACV":            ("V",  "",      60780, 3, 5),
    "Hz of VFD-ACV":     ("Hz", "",      60780, 2, 5),
    "VFD-ACV":           ("V",  "",      60780, 3, 5),
    "ACmV":              ("V",  "m",     60780, 3, 5),
    "DCmV":              ("V",  "m",     60780, 3, 5),
    "DC+ACmV":           ("V",  "m",     60780, 3, 5),
    "ACµA":              ("A",  "µ",     60780, 3, 5),
    "DCµA":              ("A",  "µ",     60780, 3, 5),
    "DC+ACµA":           ("A",  "µ",     60780, 3, 5),
    "ACmA":              ("A",  "m",     60780, 3, 5),
    "DCmA":              ("A",  "m",     60780, 3, 5),
    "DC+ACmA":           ("A",  "m",     60780, 3, 5),
    "%4~20mA":           ("%4~20mA", "", 60780, 3, 5),
    "ACA":               ("A",  "",      60780, 1, 5),
    "DCA":               ("A",  "",      60780, 1, 5),
    "DC+ACA":            ("A",  "",      60780, 1, 5),
    "T1":                ("°C", "",      256,   3, 4),
    "T2":                ("°F", "",      891,   3, 4),
    "T1-T2":             ("°C", "",      -61,   3, 4),
    "Resistance":        ("Ω",  "M",     60780, 2, 5),
    "Capacitance":       ("F",  "µ",     6078,  2, 4),
    "Continuity":        ("Ω",  "",      607,   3, 5),
    "Diode":             ("V",  "",      6078,  1, 5),
    "nS Conductance":    ("S",  "n",     6078,  2, 4),
    "Duty Cycle (%)":    ("%",  "",      6078,  2, 4),
    "Logic-Hz":          ("Hz", "k",     60780, 2, 5),
    "Hz of Line Signal": ("Hz", "",      60780, 2, 5),
}

# Electric-field functions show the meter's ASCII EF-L / EF-H glyphs
# (ASCII_READING_MAP 0x0B / 0x0A) instead of a numeric reading.
ASCII_FUNCTIONS = {
    "EF-Lo": ("EF-L", 0x00000B),
    "EF-Hi": ("EF-H", 0x00000A),
}

# Pretty menu labels with the raw protocol function IDs for debugging.
FUNCTION_LABELS = {
    name: f"{name} ({mid:02X},{sid:02X})"
    for (mid, sid), name in constants.FUNCTION_NAMES.items()
}


def _spec_reading(name: str, **overrides) -> ReadingPacket:
    """Build a ReadingPacket from a FUNCTION_SPECS entry (plus overrides)."""
    unit, prefix, raw, dp, digits = FUNCTION_SPECS[name]
    kwargs = dict(
        function_name=name, unit=unit, prefix=prefix,
        raw_value=raw, decimal_pos=dp, display_digit_count=digits,
    )
    # A negative spec value means a negative reading — set the sign flag too,
    # mirroring the real meter (the sign flag and the signed raw value encode
    # the same thing). Explicit overrides can still force it either way.
    if raw < 0 and "is_negative" not in overrides:
        kwargs["is_negative"] = True
    kwargs.update(overrides)                     # overrides win over the spec
    return reading(**kwargs)


def function_items() -> List[Tuple[str, ReadingPacket]]:
    """One item per meter function decoded by the SDK, in protocol order."""
    items = []
    for name in constants.FUNCTION_NAMES.values():
        if name in ASCII_FUNCTIONS:
            text, code = ASCII_FUNCTIONS[name]
            r = reading(
                function_name=name, unit="", prefix="", raw_value=code,
                decimal_pos=0, display_digit_count=5,
                is_ascii=True, ascii_text=text,
            )
        else:
            r = _spec_reading(name)
        items.append((FUNCTION_LABELS[name], r))
    return items


def flag_items() -> List[Tuple[str, ReadingPacket]]:
    """A few states that exercise the status flags / icons (overload etc.).

    Values come from FUNCTION_SPECS (DCV by default) with just the flag bits
    overridden, so editing a spec updates the flag demos too.
    """
    return [
        ("DCV (HOLD)", _spec_reading("DCV", is_held=True)),
        ("T1 (negative)", _spec_reading("T1", is_negative=True)),
        ("ACV (overload)",
         _spec_reading("ACV", raw_value=0, decimal_pos=0, is_overload=True)),
        ("AUTO (ASCII 'Auto')",
         _spec_reading("AUTO", raw_value=1, decimal_pos=0,
                       is_ascii=True, ascii_text="Auto", is_auto_range=True)),
        ("Resistance (REC)", _spec_reading("Resistance", is_recording=True)),
        ("DCmA (REL)",
         _spec_reading("DCmA", is_relative=True, is_auto_range=True)),
        ("DCV (MAX+AVG)", _spec_reading("DCV", is_max=True, is_avg=True)),
        ("DCV (MIN)", _spec_reading("DCV", is_min=True)),
        ("DCV (CREST)", _spec_reading("DCV", is_crest=True)),
        ("DCV (AUTO-HOLD)", _spec_reading("DCV", is_auto_hold=True)),
    ]


def dp_items() -> List[Tuple[str, ReadingPacket]]:
    """Same DCV value at every decimal-point position (0 = no dp, 1..5)."""
    return [
        (f"DP={p}", _spec_reading("DCV", decimal_pos=p))
        for p in range(6)
    ]


def ascii_items() -> List[Tuple[str, ReadingPacket]]:
    """One item per ASCII (non-numeric) display state from the protocol map.

    Built directly from constants.ASCII_READING_MAP so every possible text
    ("Auto", "InEr", the dashes, "EF-H"/"EF-L") is covered. Note "Auto" also
    appears under the flag demos, and EF-H/EF-L also under their EF functions.
    """
    items = []
    for code, text in constants.ASCII_READING_MAP.items():
        r = reading(
            function_name="", unit="", prefix="", raw_value=code,
            decimal_pos=0, display_digit_count=5,
            is_ascii=True, ascii_text=text,
        )
        items.append((f"ASCII {text!r} (0x{code:06X})", r))
    return items


# Sentinel for the "light everything" demo item (not a real ReadingPacket).
LIGHT_ALL = object()


def light_all_state() -> Dict[str, Any]:
    """Render state for the display self-test (state.mode == "all").

    Tells the skin's render() to turn on every element it owns: all digit
    segments/DPs, all units, all prefixes, all icons and annunciators.
    """
    return {
        "connected": True,
        "mode": "all",
        "value_digits": [
            {"char": "8", "segments": ["a", "b", "c", "d", "e", "f", "g"], "dp": True}
            for _ in range(5)
        ],
        "sign": True,
        "unit": "V",
        "prefix": "k",
        "function": "DCV",
        "icons": {
            "hold": True, "relative": True, "auto": True, "auto_hold": True,
            "crest": True, "record": True, "max": True, "min": True, "avg": True,
        },
        "battery_low": True,
        "rtc": "2026-08-06 12:34:56.789",
    }


def light_all_item() -> Tuple[str, object]:
    """Menu item (label, LIGHT_ALL sentinel) that lights everything on."""
    return ("ALL (light everything)", LIGHT_ALL)


# --- Console output -----------------------------------------------------------

def _menu_entry(i: int, items) -> str:
    """Format one menu entry as 'N. label value' ('' if out of range)."""
    if i >= len(items):
        return ""
    label, r = items[i]
    if r is LIGHT_ALL:
        value = "(all elements on)"
    else:
        value = format_reading(r)
    return f"{i + 1:>3}. {label:<28} {value}"


def print_menu(items: List[Tuple[str, ReadingPacket]], dp_demo: bool) -> None:
    rule = "=" * 100
    print(rule)
    if dp_demo:
        print(" BM78xBT overlay — DEMO: decimal-point positions")
    else:
        print(" BM78xBT overlay — DEMO: all functions, flags & ASCII readings")
    print("-" * 100)
    print(" Controls: n/\u2192 next   p/\u2190 prev   <number>+Enter jump   c auto-cycle   q quit")
    print("-" * 100)
    # Two-column layout: items fill the left column top-to-bottom first, then
    # the right column (column-major), so the <number>+Enter jump still
    # matches the printed order.
    rows = (len(items) + 1) // 2
    left_entries = [_menu_entry(row, items) for row in range(rows)]
    left_width = max(len(e) for e in left_entries)
    for row in range(rows):
        left = left_entries[row]
        right = _menu_entry(rows + row, items)
        if right:
            print(f" {left:<{left_width}}  |  {right}")
        else:
            print(f" {left}")
    print(rule)


def print_status(idx: int, total: int, label: str, r: ReadingPacket,
                 auto_cycle: bool) -> None:
    text = f"[{idx + 1:>2}/{total}] {label:<28} {format_reading(r)}"
    if auto_cycle:
        text += "  (auto-cycle ON)"
    print("\r" + text + "   ", end="", flush=True)


# --- Interactive key handling -------------------------------------------------

def _read_keys(loop, commands) -> None:
    """Background thread: read console keys and post commands to the loop."""
    digits = ""
    while True:
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):                      # arrow / special keys
            ch = msvcrt.getwch()
            cmd = {"H": ("prev",), "P": ("next",),
                   "K": ("prev",), "M": ("next",)}.get(ch)
            digits = ""
        elif ch.isdigit():
            digits += ch                               # build the jump number
            cmd = None
        elif ch in ("\r", "\n"):                       # Enter commits jump
            cmd = ("jump", int(digits)) if digits else None
            digits = ""
        elif ch in ("n", "N"):
            cmd = ("next",); digits = ""
        elif ch in ("p", "P"):
            cmd = ("prev",); digits = ""
        elif ch in ("c", "C"):
            cmd = ("cycle",); digits = ""
        elif ch in ("q", "Q") or ch == "\x03":         # q or Ctrl+C
            cmd = ("quit",); digits = ""
        else:
            cmd = None; digits = ""
        if cmd:
            loop.call_soon_threadsafe(commands.put_nowait, cmd)


# --- Main loop -----------------------------------------------------------------

def _resolve_start(items, start: Optional[str]) -> int:
    """Map the --function arg to a menu index (menu number, then name)."""
    if not start:
        return 0
    try:
        n = int(start)                                 # menu number (1-based)
        if 1 <= n <= len(items):
            return n - 1
    except ValueError:
        pass
    for i, (label, _) in enumerate(items):
        if label.split(" (")[0] == start:              # exact base name
            return i
    for i, (label, _) in enumerate(items):
        if start.lower() in label.lower():             # substring fallback
            return i
    return 0


async def run(host: str, port: int, dp_demo: bool, start: Optional[str],
              auto_cycle: bool) -> None:
    server, holder = run_server(host, port)
    if dp_demo:
        items = dp_items()
    else:
        items = function_items() + flag_items() + ascii_items() + [light_all_item()]
    idx = _resolve_start(items, start)
    period = 2.5 if dp_demo else 1.5

    print(f"Demo overlay running at http://{display_host(host)}:{port}/?skin=default")
    if host in ("0.0.0.0", "::", ""):
        print("  LAN: "
              f"http://{lan_ip()}:{port}/?skin=default  (use this URL in OBS)")
    print_menu(items, dp_demo)
    if not HAS_KEYS:
        print("(no Windows console available — auto-cycling through all items)")
        auto_cycle = True

    commands: asyncio.Queue = asyncio.Queue()
    if HAS_KEYS:
        threading.Thread(
            target=_read_keys, args=(asyncio.get_running_loop(), commands),
            daemon=True,
        ).start()

    loop = asyncio.get_running_loop()
    current = -1
    next_advance = loop.time() + period
    try:
        while True:
            nav = False
            while True:                                # drain pending commands
                try:
                    cmd = commands.get_nowait()
                except asyncio.QueueEmpty:
                    break
                kind = cmd[0]
                if kind == "next":
                    idx = (idx + 1) % len(items); nav = True
                elif kind == "prev":
                    idx = (idx - 1) % len(items); nav = True
                elif kind == "jump":
                    n = cmd[1]
                    if 1 <= n <= len(items):
                        idx = n - 1; nav = True
                elif kind == "cycle":
                    auto_cycle = not auto_cycle
                    current = -1                       # force status refresh
                elif kind == "quit":
                    return
            if nav:
                next_advance = loop.time() + period

            if idx != current:
                current = idx
                label, r = items[idx]
                if r is LIGHT_ALL:
                    holder.set(light_all_state())
                    print(f"\r[{idx + 1:>2}/{len(items)}] {label}   ",
                          end="", flush=True)
                else:
                    holder.set(build_render_state(INFO, r))
                    print_status(idx, len(items), label, r, auto_cycle)

            if auto_cycle and loop.time() >= next_advance:
                idx = (idx + 1) % len(items)
                next_advance = loop.time() + period
            await asyncio.sleep(0.05)
    finally:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BM78xBT overlay demo")
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="bind address (default 0.0.0.0 = all interfaces, for the LAN)",
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--function", default="DCV",
        help="function name (or menu number) to show at startup (default DCV)",
    )
    parser.add_argument(
        "--cycle", action="store_true",
        help="start with auto-cycle through every item on",
    )
    parser.add_argument(
        "--dp", action="store_true",
        help="cycle through every decimal point position (for manual inspection)",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(args.host, args.port, args.dp, args.function, args.cycle))
    except KeyboardInterrupt:
        print("\nStopped.")
