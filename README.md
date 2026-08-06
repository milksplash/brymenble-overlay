# BM78xBT Display Overlay

Emulates the BM78xBT multimeter LCD as a transparent overlay for OBS (or any
browser), driven live by the `brymenble` SDK over BLE.

## Requirements

- Python 3.9+
- The `brymenble` SDK — install from its own repo:
  `pip install -e ../brymenble`

## Run

```bash
python main.py [MAC] [--password 0000] [--port 8765]
```

Without a MAC, the first BM78xBT meter found by scanning is used.

## OBS setup

1. Run `python main.py`. You'll see:
   `Overlay server running at http://127.0.0.1:8765/`
2. In OBS add a **Browser Source**.
3. URL: `http://127.0.0.1:8765/?skin=default`
4. Set the source size to match the skin (default skin is 560×250) and scale
   in OBS as needed.

Transparency is automatic — the page background is transparent.

## Skins

Skins are pure data under `web/skins/`. Each skin is a folder containing:

- `skin.json` — maps semantic render state to SVG element ids
- `meter.svg` — the display graphic, split into named elements
- `skin.css` — colors and effects

The render state served at `/state.json` is **semantic** (no skin knowledge):
`value_digits` (per-digit `char`, `segments`, `dp`), `sign`, `unit`, `prefix`,
`function`, `icons`, `battery_low`, `rtc`. Each skin maps that to its own ids.

- `skins/default/` — self-made, distributed with this repo.
- `skins/official/` — built from the official meter graphics; **gitignored,
  never published** (kept private per licensing considerations).

Select a skin with `?skin=NAME` in the Browser Source URL.

## License

MIT. The `default/` skin is original work; the `official/` skin is private
and not distributed with this repo.
