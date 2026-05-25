#!/usr/bin/env python3
"""Compila l'installer Inno Setup (MBOXtoPDF_Setup.exe)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def find_iscc() -> Path | None:
    if sys.platform != "win32":
        return None

    local_programs = Path.home() / "AppData" / "Local" / "Programs"
    candidates = [
        local_programs / "Inno Setup 6" / "ISCC.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
    ]
    for path in candidates:
        if path.is_file():
            return path

    found = subprocess.run(
        ["where", "iscc"],
        capture_output=True,
        text=True,
        check=False,
    )
    if found.returncode == 0:
        first = found.stdout.strip().splitlines()[0].strip()
        if first:
            return Path(first)
    return None


def main() -> None:
    if sys.platform != "win32":
        print("L'installer Inno Setup è solo per Windows.", file=sys.stderr)
        print("Su macOS usa: python3 build_mac.py", file=sys.stderr)
        sys.exit(1)

    project_dir = Path(__file__).resolve().parent
    dist_app = project_dir / "dist" / "MBOXtoPDF" / "MBOXtoPDF.exe"
    iss_file = project_dir / "installer.iss"
    setup_out = project_dir / "dist" / "MBOXtoPDF_Setup.exe"

    if not dist_app.is_file():
        print(
            "Manca la build dell'app. Esegui prima:\n  python build_exe.py",
            file=sys.stderr,
        )
        sys.exit(1)

    iscc = find_iscc()
    if iscc is None:
        print(
            "Inno Setup non trovato.\n\n"
            "Installalo da: https://jrsoftware.org/isdl.php\n"
            "Oppure con winget:\n  winget install JRSoftware.InnoSetup\n\n"
            "Poi rilancia:\n  python build_installer.py",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = [str(iscc), str(iss_file)]
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=project_dir)

    print(f"\nInstaller creato: {setup_out}")
    print("Distribuisci solo questo file .exe agli utenti finali.")


if __name__ == "__main__":
    main()
