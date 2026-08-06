"""BM78xBT display overlay — serve the emulated meter display to OBS.

Usage:
    python main.py [MAC] [--password 0000] [--host 127.0.0.1] [--port 8765]

Without a MAC, the first BM78xBT meter found by scanning is used.
"""
import argparse
import asyncio

from brymen import DEFAULT_PASSWORD, BrymenClient, find_meters

from overlay.server import StateHolder, run_server
from overlay.state import build_render_state


async def _reconnect_forever(
    client: BrymenClient, holder: StateHolder, reconnect_interval: float
) -> None:
    """Keep trying to re-establish the BLE link, never raising.

    A sleeping/powered-off meter must not kill the overlay server; it just
    shows offline until the meter wakes up.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            await client.ensure_connected(retries=2, retry_interval=5.0)
            print("Reconnected and subscribed.")
            holder.set({"connected": True, "mode": "idle"})
            return
        except (ConnectionError, asyncio.TimeoutError) as exc:
            print(
                f"Reconnect attempt {attempt} failed: {exc}. "
                f"Retrying in {reconnect_interval:.0f}s..."
            )
            await asyncio.sleep(reconnect_interval)


async def stream_loop(
    client: BrymenClient, holder: StateHolder, no_data_timeout: float,
    reconnect_interval: float,
) -> None:
    while True:
        frame = await client.wait_frame(timeout=no_data_timeout)
        if frame is None:
            print("No data for a while — meter may be off. Reconnecting...")
            holder.set({"connected": False, "mode": "offline"})
            await _reconnect_forever(client, holder, reconnect_interval)
            continue
        info, readings = frame
        reading = next((r for r in readings if r is not None), None)
        holder.set(build_render_state(info, reading))


async def resolve_mac(mac: str) -> str:
    if mac:
        return mac
    while True:
        print("Scanning for BM78xBT meters...")
        meters = await find_meters(timeout=5)
        if meters:
            print(f"Found {meters[0].address} ({meters[0].name or 'unknown'}).")
            return meters[0].address
        print("No BM78xBT meters found — retrying in 10s...")
        await asyncio.sleep(10)


async def run(args) -> None:
    mac = await resolve_mac(args.mac)
    server, holder = run_server(args.host, args.port)
    print(f"Overlay server running at http://{args.host}:{args.port}/")
    print(f"Connecting to {mac}...")
    client = BrymenClient(mac, args.password, connect_timeout=5.0)
    try:
        await client.ensure_connected(retries=3, retry_interval=5.0)
        print("Connected. Add a Browser Source in OBS pointing at the URL above.")
        await stream_loop(
            client, holder, args.no_data_timeout, args.reconnect_interval
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
        "--host", default="127.0.0.1", help="bind address (default 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="HTTP port (default 8765)",
    )
    parser.add_argument(
        "--no-data-timeout", type=float, default=3.0,
        help="seconds of silence before reconnect (default 3.0)",
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
