"""Funzioni condivise per le build Windows e macOS."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print(">", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=cwd)


def find_playwright_browsers() -> Path | None:
    home = Path.home()
    candidates: list[Path] = []

    if sys.platform == "darwin":
        candidates.extend(
            [
                home / "Library" / "Caches" / "ms-playwright",
                home / ".cache" / "ms-playwright",
            ]
        )
    else:
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidates.append(Path(local_app) / "ms-playwright")
        candidates.extend(
            [
                home / "AppData" / "Local" / "ms-playwright",
                home / ".cache" / "ms-playwright",
            ]
        )

    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None
