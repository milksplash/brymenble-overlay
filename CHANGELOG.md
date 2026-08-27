# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - Unreleased

### Changed

- **Default HTTP bind is now `127.0.0.1`** — the overlay server no longer
  listens on all interfaces by default. LAN access is opt-in via
  `--host 0.0.0.0`, so `/state.json` is not exposed to the network unless
  explicitly requested.
- **`pyproject.toml` uses the portable license table form** — replaces the
  plain `license = "MIT"` string (which requires setuptools >= 77) with the
  portable `license = { text = "MIT" }` table form, so the build works on the
  declared `setuptools >= 61` backend.

### Fixed

- **`server.server_close()` is now called after shutdown** in `main.py` and
  `demo.py`, releasing the listening socket cleanly instead of leaving it
  bound.
- **`resolve_mac` raises an explicit `ValueError`** instead of relying on an
  `assert`, so a missing/invalid MAC fails with a clear, non-optimizable
  error.
- **`StateHolder.mutate` is atomic** — the server now uses a single atomic
  mutation for pause-state updates instead of a read-modify-write that could
  race with concurrent updates.
- **`value_digits` is truncated to the display width on overflow** — an
  over-long digit string no longer overflows the LCD skin layout.
- **`check_skin` accepts a `js_ids` allowlist** — script-driven element IDs
  are now validated against an explicit allowlist rather than being rejected.
- **Skin scripts are always cache-busted** — `overlay.js` appends a fresh
  query string to skin script loads so updated skins are picked up instead of
  being served from the browser cache.

### Docs

- **README documents LAN exposure of `/state.json`** on `0.0.0.0` and the
  `--host` flag (fixes #10).
- **README clarifies that digits are required only for LCD skins** and
  documents `js_ids` (fixes #11).

## [0.1.1] - 2026-08-22

### Added

- **PyInstaller packaging** — `brymenble-overlay.spec` builds a single-file
  Windows EXE bundling the static web payload (index.html, overlay.js,
  skins/...), with the private "official" skin excluded from the binary.
- **Release workflow** — GitHub Actions builds the EXE and auto-attaches it
  to the release; the workflow grants `contents: write` so the artifact can be
  uploaded.
- **`brymenble>=0.5.2` dependency** — the SDK is now installed from PyPI.

### Changed

- **CI smoke-test** — dropped the launch smoke-test in favor of build +
  auto-attach, and made the remaining smoke-test robust to slow onefile
  startup using PowerShell-native `Start-Process`.

## [0.1.0] - 2026-08-20

### Added

- Initial release of the BM78xBT LCD emulation overlay for OBS, driven live
  by the brymenble SDK over BLE.
- `pyproject.toml` project scaffolding.
- Showcase image and run instructions in the README.