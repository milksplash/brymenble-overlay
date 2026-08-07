"""Convert parsed SDK packets into a skin-agnostic render state.

The render state is pure JSON data — no SVG ids, no skin knowledge. Each skin
maps this semantic state to its own SVG element ids via skin.json.
"""
from typing import Any, Dict, List, Optional

from brymen import constants
from brymen.parsers import InfoPacket, ReadingPacket

# 7-segment decoder: character -> lit segments (a..g).
SEGMENTS: Dict[str, List[str]] = {
    "0": ["a", "b", "c", "d", "e", "f"],
    "1": ["b", "c"],
    "2": ["a", "b", "g", "e", "d"],
    "3": ["a", "b", "g", "c", "d"],
    "4": ["f", "g", "b", "c"],
    "5": ["a", "f", "g", "c", "d"],
    "6": ["a", "f", "g", "e", "c", "d"],
    "7": ["a", "b", "c"],
    "8": ["a", "b", "c", "d", "e", "f", "g"],
    "9": ["a", "b", "c", "d", "f", "g"],
    # ASCII display letters — lit on the 5-digit display for text states
    # (e.g. AutoCheck AUTO shows "Auto", errors show "InEr"/"EF-H"/"EF-L").
    # These are distinct from the static auto-ranging annunciator
    # (icons.auto -> icon_auto).
    "A": ["a", "b", "c", "e", "f", "g"],
    "E": ["a", "d", "e", "f", "g"],
    "F": ["a", "e", "f", "g"],
    "H": ["b", "c", "e", "f", "g"],
    "I": ["b", "c"],
    "n": ["c", "e", "g"],
    "o": ["c", "d", "e", "g"],
    "r": ["e", "g"],
    "t": ["d", "e", "f", "g"],
    "u": ["c", "d", "e"],
    "-": ["g"],
    "O": ["a", "b", "c", "d", "e", "f"],
    "L": ["d", "e", "f"],
}


def _cells_from_text(
    text: str,
    display_digits: int,
    dp_index: Optional[int] = None,
    fill: str = " ",
    align: str = "right",
) -> List[Dict[str, Any]]:
    """Digit cells for a display text string.

    ``fill`` is the character used for padding: " " (blank) for text
    displays, or "0" for numeric readings (the meter shows leading zeros,
    e.g. "00.250"). ``align`` controls which side is padded: "right" keeps
    the text ending at the last digit (numeric readings), "left" starts it
    at digit 0 (ASCII text such as "Auto").
    """
    text = text.strip()
    if len(text) < display_digits:
        pad = fill * (display_digits - len(text))
        text = text + pad if align == "left" else pad + text
    cells = []
    for i, ch in enumerate(text):
        if ch == " ":
            cells.append({"char": None, "segments": [], "dp": False})
        else:
            cells.append(
                {
                    "char": ch,
                    "segments": SEGMENTS.get(ch, []),
                    "dp": i == dp_index,
                }
            )
    return cells


def _fixed_text_cells(
    text: str, display_digits: int, start_index: int, dp_indexes=()
) -> List[Dict[str, Any]]:
    """Place text at fixed digit positions, e.g. the meter's fixed 'OL' layout."""
    cells = []
    for i in range(display_digits):
        pos = i - start_index
        if 0 <= pos < len(text):
            ch = text[pos]
            cells.append(
                {
                    "char": ch,
                    "segments": SEGMENTS.get(ch, []),
                    "dp": i in dp_indexes,
                }
            )
        else:
            cells.append({"char": None, "segments": [], "dp": i in dp_indexes})
    return cells


def _numeric_cells(reading: ReadingPacket) -> List[Dict[str, Any]]:
    display_digits = reading.display_digit_count or 5
    raw = abs(reading.raw_value)
    decimal_pos = reading.decimal_pos
    if decimal_pos == 0:
        text = str(raw)
        dp_index = None
    else:
        decimals = display_digits - decimal_pos
        if decimals < 0:
            decimals = 0
        decimals = min(decimals, 6)
        value = raw / (10 ** decimals)
        number_str = f"{value:.{decimals}f}"
        # The decimal point is a "dp" flag on a digit cell, not its own cell —
        # strip it so values stay right-aligned within the display digit count.
        text = number_str.replace(".", "")
        # Protocol Decimal Point Map: decimal_pos = number of integer digits,
        # so the dp sits after digit index (decimal_pos - 1). Using the literal
        # "." position in number_str would shift it one to the right.
        dp_index = decimal_pos - 1 if decimal_pos > 0 else None
    return _cells_from_text(text, display_digits, dp_index, fill="0")


def build_render_state(
    info: Optional[InfoPacket], reading: Optional[ReadingPacket]
) -> Dict[str, Any]:
    """Build a semantic render state from one parsed frame."""
    state: Dict[str, Any] = {
        "connected": True,
        "mode": "idle",
        "value_digits": [],
        "sign": False,
        "unit": None,
        "prefix": None,
        "function": None,
        "icons": {
            "hold": False,
            "relative": False,
            "auto": False,
            "auto_hold": False,
            "crest": False,
            "record": False,
            "max": False,
            "min": False,
            "avg": False,
        },
        "battery_low": False,
        "rtc": None,
    }
    if reading is None:
        return state

    display_digits = reading.display_digit_count or 5
    if reading.is_overload:
        state["mode"] = "overload"
        # The real meter lights "O" on digit 1 and "L" on digit 2.
        state["value_digits"] = _fixed_text_cells(
            "OL", display_digits, start_index=1, dp_indexes=()
        )
    elif reading.is_ascii:
        state["mode"] = "ascii"
        text = reading.ascii_text or "---"
        # "EF-H"/"EF-L" are right-aligned on the meter; other text states
        # ("Auto", "InEr", dashes) are left-aligned.
        align = "right" if text in ("EF-H", "EF-L") else "left"
        state["value_digits"] = _cells_from_text(text, display_digits, align=align)
    else:
        state["mode"] = "numeric"
        state["value_digits"] = _numeric_cells(reading)

    state["sign"] = reading.is_negative
    state["unit"] = reading.unit
    state["prefix"] = reading.prefix or None
    state["function"] = reading.function_name
    state["icons"].update(
        {
            "hold": reading.is_held,
            "relative": reading.is_relative,
            "auto": reading.is_auto_range,
            "auto_hold": reading.is_auto_hold,
            "crest": reading.is_crest,
            "record": reading.is_recording,
            "max": reading.is_max,
            "min": reading.is_min,
            "avg": reading.is_avg,
        }
    )

    if info is not None:
        state["battery_low"] = info.battery_status == constants.BATTERY_LOW
        rtc = reading.rtc
        state["rtc"] = (
            f"{rtc.year}-{rtc.month:02d}-{rtc.date:02d} "
            f"{rtc.hour:02d}:{rtc.minute:02d}:{rtc.second:02d}.{rtc.millisecond:03d}"
        )
    return state
