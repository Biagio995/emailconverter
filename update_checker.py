"""Controllo aggiornamenti tramite GitHub Releases all'avvio dell'app impacchettata."""

from __future__ import annotations

import json
import re
import sys
import threading
import webbrowser
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from version import __version__

GITHUB_REPO = "Biagio995/emailconverter"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
USER_AGENT = f"MBOXtoPDF/{__version__}"

_VERSION_PART = re.compile(r"\d+")


def parse_version(value: str) -> tuple[int, ...]:
    """Converte 'v1.2.3' o '1.2.3' in tupla numerica per confronto."""
    cleaned = value.strip().lstrip("vV")
    parts: list[int] = []
    for segment in re.split(r"[.\-+]", cleaned):
        match = _VERSION_PART.match(segment)
        if match:
            parts.append(int(match.group()))
        elif parts:
            break
    return tuple(parts) if parts else (0,)


def is_newer(latest: str, current: str) -> bool:
    return parse_version(latest) > parse_version(current)


def _platform_asset_name() -> str:
    if sys.platform == "darwin":
        return "MBOXtoPDF.dmg"
    return "MBOXtoPDF_Setup.exe"


def fetch_latest_release() -> dict | None:
    request = Request(
        RELEASES_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=12) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def get_download_url(release: dict) -> str:
    target = _platform_asset_name()
    for asset in release.get("assets", []):
        if asset.get("name") == target:
            return asset["browser_download_url"]
    return release.get("html_url", f"https://github.com/{GITHUB_REPO}/releases/latest")


def check_for_update(on_update: Callable[[str, str, str], None]) -> None:
    """
    Controlla in background se esiste una release più recente.
    on_update(versione_nuova, versione_corrente, url_download) viene chiamato se serve aggiornare.
    """
    if not getattr(sys, "frozen", False):
        return

    release = fetch_latest_release()
    if not release:
        return

    tag = release.get("tag_name", "")
    if not tag or not is_newer(tag, __version__):
        return

    on_update(tag.lstrip("vV"), __version__, get_download_url(release))


def prompt_download(
    parent,
    new_version: str,
    current_version: str,
    download_url: str,
) -> None:
    from tkinter import messagebox

    if not messagebox.askyesno(
        "Aggiornamento disponibile",
        (
            f"È disponibile la versione {new_version}.\n"
            f"Versione installata: {current_version}.\n\n"
            "Vuoi scaricare l'aggiornamento ora?\n"
            "(Si aprirà il download nel browser.)"
        ),
        parent=parent,
    ):
        return

    webbrowser.open(download_url)


def schedule_update_check(app) -> None:
    """Avvia il controllo aggiornamenti e mostra il dialog sulla finestra principale."""

    def on_update(new_version: str, current_version: str, download_url: str) -> None:
        app.after(
            0,
            lambda: prompt_download(app, new_version, current_version, download_url),
        )

    def worker() -> None:
        check_for_update(on_update)

    threading.Thread(target=worker, daemon=True).start()
