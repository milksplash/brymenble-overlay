# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the brymenble-overlay Windows EXE.
#
# Build (from the repo root, with the venv active):
#   pyinstaller brymenble-overlay.spec
#
# Output: dist/brymenble-overlay.exe  (single-file, console app)

from pathlib import Path

# SPECPATH is the directory containing this spec file.
ROOT = Path(SPECPATH)

# Static web payload (index.html, overlay.js, skins/...). Bundled so the EXE
# serves the overlay with no external files. The "official" skin is private
# (gitignored) and must NOT ship in the binary, so it is excluded here.
#
# Each file is added individually with its path relative to web/, so the
# directory structure is preserved (adding a whole directory would flatten
# its contents into the destination).
def _web_datas() -> list:
    web = ROOT / "web"
    datas = []
    for path in sorted(web.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(web)
        if rel.parts and rel.parts[0] == "skins" and len(rel.parts) > 1 and rel.parts[1] == "official":
            continue
        datas.append((str(path), str(rel.parent)))
    return datas


a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=_web_datas(),
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="brymenble-overlay",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,           # show a console window so the user sees the OBS URL / status
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "img" / "icon.ico") if (ROOT / "img" / "icon.ico").exists() else None,
)