# BM78xBT Display Overlay

Emulates the BM78xBT multimeter LCD as a transparent overlay for OBS (or any
browser), driven live by the `brymenble` SDK over BLE.

## Setup

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -e ../brymenble
```

The `brymenble` editable install also pulls in its `bleak` dependency.

## Run

```bash
.venv\Scripts\python main.py [MAC] [--password 0000] [--port 8765]
```

Or activate the venv first, then use plain `python`:

```powershell
.venv\Scripts\Activate.ps1
python main.py [MAC] [--password 0000] [--port 8765]
```

Without a MAC, the first BM78xBT meter found by scanning is used. The server
reconnects automatically if the meter powers off, and never crashes.

Demo mode (no meter needed): `python demo.py [--port 8765]`.

Like `main.py`, the demo binds to all interfaces (`--host 0.0.0.0`, the
default) so OBS or a browser on any machine on the LAN can open it — use
`--host 127.0.0.1` to restrict it to this machine.

The demo prints a numbered menu of **every meter function the SDK decodes**
(plus special/flag states) and lets you interactively switch function mode:

- `n` / `→` — next item, `p` / `←` — previous item
- `<number>` + `Enter` — jump straight to that menu item
- `c` — toggle auto-cycle through everything
- `q` — quit

It starts on DCV showing the dummy reading **607.80 V** (the highest
reasonable value for a 5-digit display). Start elsewhere with
`--function <name>` (e.g. `--function T1`), auto-cycle with `--cycle`, and
inspect decimal-point placement with `--dp`. Interactive keys need a local
Windows console; on other platforms the demo auto-cycles.

## Tests

Offline unit tests (no meter or OBS needed):

```bash
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

These cover the render-state builder (`overlay/state.py`), the HTTP server
(`overlay/server.py`, including the path-traversal guard), and skin
validation via `tools/check_skin.py` (also run in CI).

## OBS setup

1. Run `python main.py`. You'll see:
   `Overlay server running at http://127.0.0.1:8765/`
2. In OBS add a **Browser Source**.
3. URL: `http://127.0.0.1:8765/?skin=default`
4. Set the source size to match the skin (default skin is 560×250) and scale
   in OBS as needed.

Transparency is automatic — the page background is transparent.

## Skins

Each skin lives under `web/skins/` in its own folder:

- `skin.json` — static config: element-id maps plus `"script"` (the render
  module filename, default `"skin.js"`)
- `skin.js` — the skin's **render logic** (how it paints its own SVG)
- `meter.svg` — the display graphic, split into named elements
- `skin.css` — colors and effects

`web/overlay.js` is a thin host: it loads `skin.json`, injects `meter.svg`,
loads `skin.js`, polls `/state.json`, and calls the skin's `render(state, ctx)`.

### Render state (`/state.json`)

Semantic, skin-agnostic data built by `overlay/state.py`:
`value_digits` (per-digit `char`, `segments`, `dp`), `sign`, `unit`, `prefix`,
`function`, `icons`, `battery_low`, `rtc`. Each skin decides how to paint it.
The demo's "ALL (light everything)" item serves `state.mode: "all"` — a
self-test in which each skin turns on every element it owns (all segments/DPs,
units, prefixes, icons and annunciators).

### Skin module contract

A skin module registers on `window.__bm_skins`:

```js
window.__bm_skins = window.__bm_skins || {};
window.__bm_skins.default = {
  name: 'default',
  render(state, ctx) { /* paint this skin's SVG */ },
};
```

`ctx` provides small shared paint helpers bound to the skin's config:

- `ctx.skin` — parsed `skin.json`
- `ctx.byId(id)` / `ctx.show(id, on)` — element lookup / visibility
- `ctx.lightDigits(cells, offset)` — light `digit<k>_<seg>` from `value_digits`
  (offset 0 = left-aligned, `digits - cells.length` = right-aligned)
- `ctx.lightSign(on)`, `ctx.lightUnits(unit)`, `ctx.lightPrefixes(unit, prefix)`,
  `ctx.lightIcons(icons)`, `ctx.lightBattery(low)` — annunciator helpers

`skin.json` maps semantic keys to element ids (`digit_prefix`, `sign`, `unit`,
`prefix`, `icons`, `battery_low`, `hidden`, `function`, `rtc_label`).

- **`prefix`** is unit-aware: `{ unit: { symbol: id } }`, so a skin can use
  different glyphs for the same symbol on different units (e.g. a special
  milli used only for voltage).
- **`function`** is a skin decision — handled in `skin.js`, typically either:
  - `{ "type": "text", "id": "fn_text" }` — write the function name into a
    text element (used by `default`).
  - `{ "type": "icons", "map": { "DCV": "icon_dc", "DC+ACV": ["icon_dc", "icon_ac"], … } }`
    — light icon(s) for the active function (used by `official`).
- **`function_labels`** (optional) — per-skin display overrides for the SDK's
  canonical function names (used with `function.type: "text"`), e.g.
  `{ "Duty Cycle (%)": "DUTY", "nS Conductance": "nS" }`. Functions not
  listed fall back to the canonical name, so the SDK stays protocol-faithful.

- `skins/default/` — self-made, distributed with this repo.
- `skins/official/` — built from the official meter graphics; **gitignored,
  never published** (kept private per licensing considerations).

Select a skin with `?skin=NAME` in the Browser Source URL.

## License

MIT. The `default/` skin is original work; the `official/` skin is private
and not distributed with this repo.
