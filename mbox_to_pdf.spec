# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec Windows: python build_exe.py
# macOS: mbox_to_pdf_mac.spec via python build_mac.py

import sys
from pathlib import Path

block_cipher = None
project_dir = Path(SPEC).parent

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
        "update_checker",
        "version",
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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="MBOXtoPDF",
)
