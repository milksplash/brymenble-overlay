"""BM78xBT display overlay — serve the emulated meter display to OBS.

Usage:
    python main.py [MAC] [--password 0000] [--host 0.0.0.0] [--port 8765]

Binds to all interfaces (0.0.0.0) by default so OBS on any machine on the
local network can point a Browser Source at this server. Without a MAC, the
first BM78xBT meter found by scanning is used.
"""
import argparse
import asyncio

from brymenble import DEFAULT_PASSWORD, BrymenbleClient, console, find_first_meter

from overlay.server import StateHolder, display_host, lan_ip, run_server
from overlay.state import build_render_state


async def stream_loop(
    client: BrymenbleClient, holder: StateHolder,
    reconnect_interval: float, link_down_grace: float = 2.0,
) -> None:
    """Stream frames into the render state; reconnects are handled by the SDK.

    ``BrymenbleClient.read_stream()`` owns the pause-vs-power-off decision: a
    data gap with the BLE link up is a function-switch pause — the display
    blanks (the meter's LCD does too), it does NOT keep the last reading on
    screen; a link drop is confirmed with ``link_down_grace``, then
    reconnected forever (``retries=None``) so a power-off never kills the
    overlay server.
    """
    def _on_lost(reason: str) -> None:
        console.lost(reason)
        holder.set({"connected": False, "mode": "offline"})

    def _on_reconnected() -> None:
        console.reconnected()
        holder.set({"connected": True, "mode": "idle"})

    def _on_pause() -> None:
        # The meter blanks its LCD during a function/range switch; mirror that.
        # Keeping the last reading (or re-sending a gap line) is strictly a
        # TestController-bridge keep-alive behaviour — the overlay stays blank.
        holder.set(build_render_state(None, None))

    async for frame in client.read_stream(
        link_down_grace=link_down_grace,
        retries=None,
        retry_interval=reconnect_interval,
        on_retry=console.retry,
        on_pause=_on_pause,
        on_lost=_on_lost,
        on_reconnected=_on_reconnected,
    ):
        info = frame.info
        reading = next((r for r in frame.readings if r is not None), None)
        holder.set(build_render_state(info, reading))


async def resolve_mac(mac: str) -> str:
    if mac:
        return mac
    meter = await find_first_meter(
        timeout=5,
        retry_interval=10,
        on_retry=console.scanning_retry,
    )
    # retry_interval > 0 -> find_first_meter loops until a meter appears.
    assert meter is not None
    console.using(meter.address, meter.name or "unknown")
    return meter.address


async def run(args) -> None:
    mac = await resolve_mac(args.mac)
    server, holder = run_server(args.host, args.port)
    console.status(f"overlay server running at http://{display_host(args.host)}:{args.port}/")
    if args.host in ("0.0.0.0", "::", ""):
        console.status(f"LAN: http://{lan_ip()}:{args.port}/  (use this URL in OBS)")
    console.connecting(mac)
    client = BrymenbleClient(mac, args.password, connect_timeout=5.0)
    try:
        await client.ensure_connected(retries=3, retry_interval=5.0, on_retry=console.retry)
        console.connected(mac, detail="add a Browser Source in OBS pointing at the URL above")
        await stream_loop(
            client, holder, args.reconnect_interval
        )
    finally:
        await client.close()
        server.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="BM78xBT display overlay for OBS")
    parser.add_argument(
        "mac", nargs="?", default=None,
        help="meter MAC address (default: auto-scan)",
    )
    parser.add_argument(
        "--password", default=DEFAULT_PASSWORD,
        help="connection password (default 0000)",
    )
    parser.add_argument(
        "--host", default="0.0.0.0",
        help="bind address (default 0.0.0.0 = all interfaces, for the LAN)",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="HTTP port (default 8765)",
    )
    parser.add_argument(
        "--reconnect-interval", type=float, default=10.0,
        help="seconds between reconnect attempts after a failure (default 10.0)",
    )
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
