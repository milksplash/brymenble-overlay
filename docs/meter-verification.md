# Real-Meter Verification Checklist

> **TODO (owner):** walk every function on the physical meter and confirm the
> SDK parses and the overlay renders it correctly. This is the single best
> end-to-end test of both `brymenble` (parsing) and `brymenble-overlay`
> (rendering) at once.

## How to use this checklist

1. Power on the meter, connect it (`python main.py --port 8765`), and open the
   overlay (`http://127.0.0.1:8765/?skin=official`).
2. For each row below, put the meter into that function and give it a stable,
   known reading.
3. Compare **three** things at once:
   - the **meter's physical display**,
   - the **parsed data** (browser → `/state.json`, or `examples/console.py`
     which prints `Value / Function / Status`),
   - the **overlay render** (digits, dp, leading zeros, unit/prefix elements,
     function icons).
4. Tick each column that matches. Put any discrepancy in **Notes**.

Legend: ✅ = verified correct · ❌ = mismatch (fix + report) · ? = unknown/untested

---

## Functions

| Function (SDK `function_name`) | Expected unit / prefix | SDK `function_name` | Unit | Prefix | Value + dp | Leading zeros | Official icons | Notes |
|---|---|---|---|---|---|---|---|---|
| LoZ-ACV | V | ☐ | ☐ | ☐ | ☐ | ☐ | LoZ + AC | |
| LoZ-DCV | V | ☐ | ☐ | ☐ | ☐ | ☐ | LoZ + DC | |
| AUTO (AutoCheck) | V | ☐ | ☐ | ☐ | ☐ | ☐ | — (shares `icon_auto`) | verify no icon conflict |
| ACV | V | ☐ | ☐ | ☐ | ☐ | ☐ | AC | |
| DCV | V | ☐ | ☐ | ☐ | ☐ | ☐ | DC | |
| DC+ACV | V | ☐ | ☐ | ☐ | ☐ | ☐ | DC + AC | |
| Hz of VFD-ACV | Hz / V | ☐ | ☐ | ☐ | ☐ | ☐ | VFD | unit on Hz display? |
| VFD-ACV | V | ☐ | ☐ | ☐ | ☐ | ☐ | VFD + AC | |
| ACmV | mV | ☐ | ☐ | ☐ | ☐ | ☐ | AC | uses `prefix_milli_v`? |
| DCmV | mV | ☐ | ☐ | ☐ | ☐ | ☐ | DC | uses `prefix_milli_v`? |
| DC+ACmV | mV | ☐ | ☐ | ☐ | ☐ | ☐ | DC + AC | |
| ACµA | µA | ☐ | ☐ | ☐ | ☐ | ☐ | AC | |
| DCµA | µA | ☐ | ☐ | ☐ | ☐ | ☐ | DC | |
| DC+ACµA | µA | ☐ | ☐ | ☐ | ☐ | ☐ | DC + AC | |
| ACmA | mA | ☐ | ☐ | ☐ | ☐ | ☐ | AC | |
| DCmA | mA | ☐ | ☐ | ☐ | ☐ | ☐ | DC | |
| DC+ACmA | mA | ☐ | ☐ | ☐ | ☐ | ☐ | DC + AC | |
| %4~20mA | %4~20mA | ☐ | ☐ | ☐ | ☐ | ☐ | — | verify unit code `0x4F` |
| ACA | A | ☐ | ☐ | ☐ | ☐ | ☐ | AC | |
| DCA | A | ☐ | ☐ | ☐ | ☐ | ☐ | DC | |
| DC+ACA | A | ☐ | ☐ | ☐ | ☐ | ☐ | DC + AC | |
| T1 | °C or °F | ☐ | ☐ | ☐ | ☐ | ☐ | T1 | |
| T2 | °C or °F | ☐ | ☐ | ☐ | ☐ | ☐ | T2 | |
| T1-T2 | °C or °F | ☐ | ☐ | ☐ | ☐ | ☐ | T1 + T2 + Δ | |
| Resistance | Ω | ☐ | ☐ | ☐ | ☐ | ☐ | — | GΩ exists on meter? |
| Capacitance | F | ☐ | ☐ | ☐ | ☐ | ☐ | — | |
| Continuity | Ω | ☐ | ☐ | ☐ | ☐ | ☐ | continuity | |
| Diode | V | ☐ | ☐ | ☐ | ☐ | ☐ | diode | |
| nS Conductance | nS | ☐ | ☐ | ☐ | ☐ | ☐ | — | does `unit_nanosiemen` include the "n"? (double-prefix check) |
| Duty Cycle (%) | % | ☐ | ☐ | ☐ | ☐ | ☐ | duty cycle | |
| Logic-Hz | Hz | ☐ | ☐ | ☐ | ☐ | ☐ | — | |
| EF-Lo | — | ☐ | ☐ | ☐ | ☐ | ☐ | — | any unit shown? |
| EF-Hi | — | ☐ | ☐ | ☐ | ☐ | ☐ | — | any unit shown? |
| Hz of Line Signal | Hz | ☐ | ☐ | ☐ | ☐ | ☐ | — | |

---

## Special display states

| State | What to check | Result | Notes |
|---|---|---|---|
| **Overload (OL)** | "O" on digit 1, "L" on digit 2, **no dp** | ☐ | we fixed dp-off — confirm on real meter |
| **ASCII: `Auto` / `InEr` / dashes** | text rendered via segments, left-aligned | ☐ | |
| **ASCII: `EF-H` / `EF-L`** | text rendered via segments, right-aligned | ☐ | |
| **ASCII: `InEr`** | text rendered | ☐ | |
| **ASCII: `----`** | dashes | ☐ | |
| **ASCII: `EF-H` / `EF-L`** | text rendered | ☐ | |
| **Negative** | `sign_neg` lit, value magnitude correct | ☐ | |
| **Leading zeros** | e.g. `00.250` (digit0 lit as 0) | ☐ | real meter zero-pads |
| **Battery low** | `icon_bat` lit when meter shows low battery | ☐ | |

---

## Known unknowns to resolve while testing

- **`unit_db` / `prefix_milli_v`** — only meaningful for dBm, which the BM78xBT
  (BT model) never sends (dBm is BM789-only). Confirm they stay dark / are
  hidden.
- **`unit_nanosiemen`** — if the glyph already contains the "n", the `n`
  prefix must not double-light for nS Conductance.
- **`%4~20mA`** — confirm the SDK's unit code `0x4F` actually arrives (the
  function table says main `0x06` sub `0x08`).
  - **TODO: verify 100% behavior (20 mA = full scale)** — what raw value the
    meter sends at 100%, how it should display (e.g. `100.0` / `100.00`), and
    whether anything special lights at full scale. Current official skin has
    no 100% handling; a `100.00`-style raw with dp=2 renders as `10.000`
    (decimal misplaced) until the real encoding is confirmed.
- **Function → icon map** (`official/skin.json` `function.map`) is a
  best-guess; correct any mode the meter lights differently.
- **`AUTO` (AutoCheck)** shares `icon_auto` with the auto-range boolean —
  confirm no conflict in AutoCheck mode.
- **Hz functions** — confirm which unit/prefix elements the meter lights for
  "Hz of VFD-ACV" vs "Hz of Line Signal".
- **Giga (G) prefix** — the real meter reportedly has no GΩ; confirm the
  highest resistance range.
- **Function change blanks the reading** — the real display clears during a
  function switch; the SDK has no "blanked" signal (only a data gap), so the
  overlay will hold the previous value / show a pause instead of blanking.
  Expected, not a bug.
- **Auto-range decimal shift** — on an aggressive change (most visible in
  Resistance) the real meter steps ranges and moves the decimal; the overlay
  shows each settled frame with its own dp/prefix and does not animate the
  shift. Expected, not a bug.

---

## Bugs found while testing

| Date | Function | Symptom | Fixed in | Notes |
|---|---|---|---|---|
| | | | | |
