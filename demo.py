"""Demo mode: serve the overlay with a synthetic meter state (no BLE needed).

Usage:
    python demo.py [--port 8765]

Cycles through a few example readings so you can verify the skin renders
correctly before hooking up a real meter. Requires the `brymen` SDK to be
importable (run from the venv that has brymenble installed).
"""
import argparse
import asyncio

from brymen.parsers import InfoPacket, ReadingPacket, RtcTime

from overlay.server import run_server
from overlay.state import build_render_state


def reading(**kw) -> ReadingPacket:
    defaults = dict(
        function_name="DCV", unit="V", raw_value=12345, decimal_pos=3,
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

DEMO_STATES = [
    reading(function_name="DCV", unit="V", raw_value=12345, decimal_pos=3,
            prefix="", display_digit_count=5, is_auto_range=True, is_held=True),
    reading(function_name="T1", unit="°C", raw_value=2560, decimal_pos=2,
            prefix="", display_digit_count=4, is_negative=True),
    reading(function_name="ACV", unit="V", raw_value=0, decimal_pos=0,
            prefix="", display_digit_count=5, is_overload=True),
    reading(function_name="AUTO", unit="V", raw_value=1, decimal_pos=0,
            prefix="", display_digit_count=5, is_ascii=True,
            ascii_text="Auto", is_auto_range=True),
    reading(function_name="Resistance", unit="Ω", raw_value=23456,
            decimal_pos=4, prefix="M", display_digit_count=5,
            is_recording=True),
    reading(function_name="DCmA", unit="A", raw_value=-1234, decimal_pos=2,
            prefix="m", display_digit_count=5, is_relative=True,
            is_auto_range=True),
]

# Every decimal-point position on a 5-digit display (0 = no dp, 1..5 = dp
# after digit index 0..4). Same raw value everywhere so the dp position is
# unambiguous for manual inspection.
DP_DEMO_STATES = [
    reading(function_name="DP", unit="V", raw_value=12345, decimal_pos=p,
            prefix="", display_digit_count=5)
    for p in range(6)
]


async def main(port: int, dp_demo: bool) -> None:
    server, holder = run_server("127.0.0.1", port)
    print(f"Demo overlay: http://127.0.0.1:{port}/?skin=default")
    if dp_demo:
        print("DP demo: cycling decimal point positions 0..5 "
              "(label shown bottom-left).")
    try:
        i = 0
        while True:
            if dp_demo:
                p = i % len(DP_DEMO_STATES)
                state = build_render_state(INFO, DP_DEMO_STATES[p])
                state["rtc"] = f"dp={p}"
                period = 2.5
            else:
                state = build_render_state(INFO, DEMO_STATES[i % len(DEMO_STATES)])
                period = 1.5
            holder.set(state)
            i += 1
            await asyncio.sleep(period)
    finally:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BM78xBT overlay demo")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--dp", action="store_true",
        help="cycle through every decimal point position (for manual inspection)",
    )
    args = parser.parse_args()
    try:
        asyncio.run(main(args.port, args.dp))
    except KeyboardInterrupt:
        print("\nStopped.")
