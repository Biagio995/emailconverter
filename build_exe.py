#!/usr/bin/env python3
"""
Crea l'eseguibile Windows e l'installer unico.

Output:
  dist/MBOXtoPDF/          — app portabile
  dist/MBOXtoPDF_Setup.exe — installer per distribuzione

Per macOS (solo su Mac): python3 build_mac.py

Prerequisiti:
  pip install -r requirements.txt
  python -m playwright install chromium
  Inno Setup 6 (per l'installer): winget install JRSoftware.InnoSetup
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from build_common import find_playwright_browsers, run


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    dist_dir = project_dir / "dist" / "MBOXtoPDF"
    spec_file = project_dir / "mbox_to_pdf.spec"

    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    run([sys.executable, "-m", "playwright", "install", "chromium", "chromium-headless-shell"])
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_file)])

    browsers_src = find_playwright_browsers()
    if browsers_src is None:
        print(
            "ATTENZIONE: cartella ms-playwright non trovata. "
            "L'exe potrebbe non avviare Chromium.",
            file=sys.stderr,
        )
        sys.exit(1)

    browsers_dest = dist_dir / "ms-playwright"
    if browsers_dest.exists():
        shutil.rmtree(browsers_dest)
    print(f"Copia browser Playwright:\n  {browsers_src}\n  -> {browsers_dest}")
    shutil.copytree(browsers_src, browsers_dest)

    headless = [
        p for p in browsers_dest.iterdir()
        if p.is_dir() and p.name.startswith("chromium_headless_shell-")
    ]
    chromium = [
        p for p in browsers_dest.iterdir()
        if p.is_dir() and p.name.startswith("chromium-")
    ]
    if not headless or not chromium:
        print(
            "ATTENZIONE: browser Playwright incompleti in ms-playwright. "
            "Riesegui: python -m playwright install chromium chromium-headless-shell",
            file=sys.stderr,
        )
        sys.exit(1)

    exe_path = dist_dir / "MBOXtoPDF.exe"
    print(f"\nBuild app completata: {exe_path}")

    from build_installer import find_iscc

    iscc = find_iscc()
    if iscc is None:
        print(
            "\nInstaller non creato: installa Inno Setup 6, poi esegui:\n"
            "  python build_installer.py\n"
            "  winget install JRSoftware.InnoSetup",
        )
        return

    iss_file = project_dir / "installer.iss"
    print(f"\nCompilazione installer con {iscc}...")
    run([str(iscc), str(iss_file)])

    setup_path = project_dir / "dist" / "MBOXtoPDF_Setup.exe"
    print(f"\nTutto pronto.")
    print(f"  App:       {exe_path}")
    print(f"  Installer: {setup_path}")
    print("\nDistribuisci MBOXtoPDF_Setup.exe agli utenti finali.")


if __name__ == "__main__":
    main()
