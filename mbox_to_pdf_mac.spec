# -*- mode: python ; coding: utf-8 -*-
# Build macOS: python build_mac.py  (solo su Mac)

from pathlib import Path

block_cipher = None
project_dir = Path(SPEC).parent
entitlements = project_dir / "entitlements.plist"

a = Analysis(
    ["mbox_to_pdf.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "playwright",
        "playwright.sync_api",
        "fitz",
        "gui",
        "tkinter",
        "tkinter.filedialog",
        "tkinter.scrolledtext",
        "tkinter.ttk",
        "tkinter.messagebox",
        "email",
        "email.header",
        "email.message",
        "email.utils",
        "mailbox",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MBOXtoPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=str(entitlements) if entitlements.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MBOXtoPDF",
)

app = BUNDLE(
    coll,
    name="MBOXtoPDF.app",
    icon=None,
    bundle_identifier="com.mboxtopdf.app",
    info_plist={
        "CFBundleName": "MBOX to PDF",
        "CFBundleDisplayName": "MBOX to PDF",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1.0.0",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,
    },
)
