"""Tests for ``overlay/state.py`` — parsing SDK packets into render state.

The render state is the skin-agnostic JSON the browser polls at
``/state.json``, so these are the correctness-critical pure functions.
"""
from brymen import constants
from brymen.parsers import RtcTime

from overlay.state import SEGMENTS, build_render_state


def test_reading_none_yields_idle_state(make_info):
    state = build_render_state(make_info(), None)
    assert state["connected"] is True
    assert state["mode"] == "idle"
    assert state["value_digits"] == []
    assert state["sign"] is False
    assert state["unit"] is None
    assert state["prefix"] is None
    assert state["function"] is None


def test_numeric_reading(make_info, make_reading):
    # Default reading is 607.80 V on DCV (5 digits, dp after digit index 2).
    state = build_render_state(make_info(), make_reading())
    assert state["mode"] == "numeric"
    assert state["sign"] is False
    assert state["unit"] == "V"
    assert state["prefix"] is None
    assert state["function"] == "DCV"
    digits = state["value_digits"]
    assert [d["char"] for d in digits] == ["6", "0", "7", "8", "0"]
    assert [d["dp"] for d in digits] == [False, False, True, False, False]
    # The digit cells must use the shared 7-segment decoder.
    assert digits[0]["segments"] == SEGMENTS["6"]
    assert digits[1]["segments"] == SEGMENTS["0"]


def test_negative_reading(make_info, make_reading):
    state = build_render_state(make_info(), make_reading(is_negative=True))
    assert state["sign"] is True


def test_prefix_passthrough(make_info, make_reading):
    state = build_render_state(make_info(), make_reading(prefix="m"))
    assert state["prefix"] == "m"


def test_overload_reading(make_info, make_reading):
    # OL is rendered at fixed digit indexes 1 and 2 (the real meter layout).
    state = build_render_state(make_info(), make_reading(is_overload=True))
    assert state["mode"] == "overload"
    assert [d["char"] for d in state["value_digits"]] == [None, "O", "L", None, None]


def test_ascii_text_left_aligned(make_info, make_reading):
    # Text states like "Auto" start at digit 0.
    state = build_render_state(
        make_info(), make_reading(is_ascii=True, ascii_text="Auto")
    )
    assert state["mode"] == "ascii"
    assert [d["char"] for d in state["value_digits"]] == ["A", "u", "t", "o", None]


def test_ascii_ef_right_aligned(make_info, make_reading):
    # EF-H / EF-L are right-aligned on the meter.
    state = build_render_state(
        make_info(), make_reading(is_ascii=True, ascii_text="EF-H")
    )
    assert state["mode"] == "ascii"
    assert [d["char"] for d in state["value_digits"]] == [None, "E", "F", "-", "H"]


def test_icons_from_flags(make_info, make_reading):
    state = build_render_state(
        make_info(),
        make_reading(
            is_crest=True, is_relative=True, is_held=True, is_auto_range=True,
            is_auto_hold=True, is_recording=True, is_max=True, is_min=True,
            is_avg=True,
        ),
    )
    assert state["icons"] == {
        "hold": True, "relative": True, "auto": True, "auto_hold": True,
        "crest": True, "record": True, "max": True, "min": True, "avg": True,
    }


def test_battery_status(make_info, make_reading):
    low = build_render_state(
        make_info(battery_status=constants.BATTERY_LOW), make_reading()
    )
    assert low["battery_low"] is True
    normal = build_render_state(
        make_info(battery_status=constants.BATTERY_NORMAL), make_reading()
    )
    assert normal["battery_low"] is False


def test_rtc_string_formatting(make_info, make_reading):
    rtc = RtcTime(2026, 8, 11, 12, 34, 56, 789)
    state = build_render_state(make_info(), make_reading(rtc=rtc))
    assert state["rtc"] == "2026-08-11 12:34:56.789"
