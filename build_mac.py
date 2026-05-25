#!/usr/bin/env python3
"""
Crea l'app macOS e il pacchetto DMG per la distribuzione.

Eseguire SOLO su macOS:
  python3 build_mac.py

Output:
  dist/MBOXtoPDF.app   — applicazione
  dist/MBOXtoPDF.dmg   — pacchetto da distribuire
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from build_common import find_playwright_browsers, run


def app_macos_dir(app_path: Path) -> Path:
    return app_path / "Contents" / "MacOS"


def create_dmg(project_dir: Path, app_path: Path, dmg_path: Path) -> None:
    staging = project_dir / "build" / "dmg_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    shutil.copytree(app_path, staging / app_path.name, symlinks=True)
    applications_link = staging / "Applications"
    if not applications_link.exists():
        applications_link.symlink_to("/Applications")

    if dmg_path.exists():
        dmg_path.unlink()

    run(
        [
            "hdiutil",
            "create",
            "-volname",
            "MBOX to PDF",
            "-srcfolder",
            str(staging),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )
    shutil.rmtree(staging)


def main() -> None:
    if sys.platform != "darwin":
        print(
            "La build macOS va eseguita su un Mac.\n"
            "Su Windows usa: python build_exe.py",
            file=sys.stderr,
        )
        sys.exit(1)

    project_dir = Path(__file__).resolve().parent
    spec_file = project_dir / "mbox_to_pdf_mac.spec"
    app_path = project_dir / "dist" / "MBOXtoPDF.app"
    dmg_path = project_dir / "dist" / "MBOXtoPDF.dmg"

    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    run([sys.executable, "-m", "playwright", "install", "chromium"])
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", str(spec_file)])

    if not app_path.is_dir():
        print(f"Build fallita: {app_path} non trovato.", file=sys.stderr)
        sys.exit(1)

    browsers_src = find_playwright_browsers()
    if browsers_src is None:
        print(
            "ATTENZIONE: ms-playwright non trovato. "
            "Esegui: python3 -m playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    browsers_dest = app_macos_dir(app_path) / "ms-playwright"
    if browsers_dest.exists():
        shutil.rmtree(browsers_dest)
    print(f"Copia browser Playwright:\n  {browsers_src}\n  -> {browsers_dest}")
    shutil.copytree(browsers_src, browsers_dest)

    print("\nCreazione DMG...")
    create_dmg(project_dir, app_path, dmg_path)

    print("\nBuild macOS completata.")
    print(f"  App: {app_path}")
    print(f"  DMG: {dmg_path}")
    print("\nDistribuisci MBOXtoPDF.dmg agli utenti Mac.")


if __name__ == "__main__":
    main()
