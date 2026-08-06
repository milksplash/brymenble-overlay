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


async def main(port: int) -> None:
    server, holder = run_server("127.0.0.1", port)
    print(f"Demo overlay: http://127.0.0.1:{port}/?skin=default")
    try:
        i = 0
        while True:
            holder.set(build_render_state(INFO, DEMO_STATES[i % len(DEMO_STATES)]))
            i += 1
            await asyncio.sleep(1.5)
    finally:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BM78xBT overlay demo")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        asyncio.run(main(args.port))
    except KeyboardInterrupt:
        print("\nStopped.")
