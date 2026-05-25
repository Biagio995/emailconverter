#!/usr/bin/env python3
"""
Converte un file MBOX (Google Takeout / export Gmail) in PDF singoli.

Uso:
  python mbox_to_pdf.py --mbox "C:\\path\\to\\mail.mbox" --output "C:\\path\\to\\pdf"
  python mbox_to_pdf.py --input-dir "C:\\Takeout\\Mail" --output "C:\\export\\pdf"

Prima esecuzione:
  pip install -r requirements.txt
  python -m playwright install chromium
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import base64
import mailbox
import os
import re
import sys
import unicodedata
from email.header import decode_header, make_header
from email.message import Message
from email.utils import parsedate_to_datetime
from pathlib import Path

try:
    import fitz
except ImportError:
    fitz = None

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None  # type: ignore[misc, assignment]


def setup_playwright_browsers() -> None:
    """Imposta il percorso dei browser Playwright quando l'app è un .exe."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        bundled = base / "ms-playwright"
        if bundled.is_dir():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled)


def is_gui_mode() -> bool:
    if "--gui" in sys.argv or "-g" in sys.argv:
        return True
    if "--mbox" in sys.argv or "--input-dir" in sys.argv:
        return False
    if getattr(sys, "frozen", False):
        return len(sys.argv) == 1
    return len(sys.argv) == 1


if sys.platform == "darwin":
    INVALID_PATH_CHARS = re.compile(r"[/:\x00-\x1f]")
else:
    INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WHITESPACE = re.compile(r"\s+")
BODY_TAG_RE = re.compile(r"<body[^>]*>(.*)</body>", re.IGNORECASE | re.DOTALL)


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def sanitize_filename(text: str, max_len: int = 120) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = INVALID_PATH_CHARS.sub("_", text)
    text = WHITESPACE.sub(" ", text).strip(" .")
    if not text:
        text = "senza_oggetto"
    if len(text) > max_len:
        text = text[:max_len].rstrip(" .")
    return text


def format_date(msg: Message) -> str:
    raw = msg.get("Date")
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return raw


def get_part_text(part: Message) -> str | None:
    payload = part.get_payload(decode=True)
    if payload is None:
        payload = part.get_payload()
    if isinstance(payload, str):
        return payload
    if isinstance(payload, bytes):
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")
    return None


def get_body_parts(msg: Message) -> tuple[str | None, str | None]:
    html: str | None = None
    plain: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            ctype = part.get_content_type()
            payload = get_part_text(part)
            if payload is None:
                continue
            if ctype == "text/html" and (html is None or len(payload) > len(html)):
                html = payload
            elif ctype == "text/plain" and (plain is None or len(payload) > len(plain)):
                plain = payload
    else:
        payload = get_part_text(msg)
        if payload is not None:
            if msg.get_content_type() == "text/html":
                html = payload
            else:
                plain = payload

    return html, plain


def extract_html_body(html: str) -> str:
    match = BODY_TAG_RE.search(html)
    if match:
        return match.group(1).strip()
    return html.strip()


def embed_cid_images(html: str, msg: Message) -> str:
    cid_map: dict[str, str] = {}
    for part in msg.walk():
        content_id = part.get("Content-ID")
        if not content_id:
            continue
        content_id = content_id.strip("<>")
        data = part.get_payload(decode=True)
        if not data:
            continue
        mime = part.get_content_type()
        encoded = base64.b64encode(data).decode("ascii")
        cid_map[content_id] = f"data:{mime};base64,{encoded}"

    for content_id, data_url in cid_map.items():
        html = html.replace(f"cid:{content_id}", data_url)
    return html


def is_pdf_part(part: Message) -> bool:
    filename = decode_mime_header(part.get_filename()).lower()
    if filename.endswith(".pdf"):
        return True
    return part.get_content_type() == "application/pdf"


def get_pdf_attachments(msg: Message) -> list[bytes]:
    pdfs: list[bytes] = []
    for part in msg.walk():
        if not is_pdf_part(part):
            continue
        data = part.get_payload(decode=True)
        if data:
            pdfs.append(data)
    return pdfs


def list_attachments(msg: Message) -> list[tuple[str, int | None]]:
    attachments: list[tuple[str, int | None]] = []
    for part in msg.walk():
        disposition = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if filename:
            filename = decode_mime_header(filename)
        elif "attachment" not in disposition:
            continue
        else:
            filename = "allegato_senza_nome"

        if "attachment" in disposition or filename:
            size = len(part.get_payload(decode=True) or b"")
            attachments.append((filename, size))
    return attachments


def save_attachments(msg: Message, dest_dir: Path) -> list[str]:
    saved: list[str] = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    seen: dict[str, int] = {}

    for part in msg.walk():
        disposition = (part.get("Content-Disposition") or "").lower()
        filename = part.get_filename()
        if not filename and "attachment" not in disposition:
            continue
        if not filename:
            filename = "allegato_senza_nome"
        filename = sanitize_filename(decode_mime_header(filename), max_len=180)

        count = seen.get(filename, 0)
        seen[filename] = count + 1
        if count:
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            filename = f"{stem}_{count + 1}{suffix}"

        data = part.get_payload(decode=True)
        if data is None:
            continue
        (dest_dir / filename).write_bytes(data)
        saved.append(filename)

    return saved


def build_html(msg: Message, attachment_names: list[str]) -> str:
    html_body, plain_body = get_body_parts(msg)

    if html_body:
        body_html = embed_cid_images(extract_html_body(html_body), msg)
    elif plain_body:
        body_html = (
            f"<pre style='white-space:pre-wrap;font-family:Consolas,monospace;'>"
            f"{escape_html(plain_body)}</pre>"
        )
    else:
        body_html = "<p><em>(Nessun contenuto testuale)</em></p>"

    non_pdf_attachments = [
        name for name in attachment_names if not name.lower().endswith(".pdf")
    ]
    if non_pdf_attachments:
        items = "".join(f"<li>{escape_html(name)}</li>" for name in non_pdf_attachments)
        body_html += f"<hr><p><strong>Altri allegati</strong></p><ul>{items}</ul>"

    return f"""<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: "Segoe UI", Arial, sans-serif;
      font-size: 12px;
      color: #111 !important;
      background: #fff !important;
      margin: 24px;
    }}
    .email-body, .email-body * {{
      visibility: visible !important;
      opacity: 1 !important;
      max-height: none !important;
      overflow: visible !important;
    }}
    .email-body span, .email-body p, .email-body td, .email-body div {{
      font-size: inherit !important;
      line-height: 1.4 !important;
    }}
    .email-body img {{
      max-width: 100%;
      height: auto;
    }}
  </style>
</head>
<body>
  <div class="email-body">{body_html}</div>
</body>
</html>"""


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def merge_pdf_files(base_pdf: Path, extra_pdfs: list[bytes], output_pdf: Path) -> None:
    if fitz is None:
        raise RuntimeError("Serve pymupdf: pip install pymupdf")

    doc = fitz.open(base_pdf)
    for pdf_bytes in extra_pdfs:
        attachment = fitz.open(stream=pdf_bytes, filetype="pdf")
        doc.insert_pdf(attachment)
        attachment.close()
    doc.save(output_pdf)
    doc.close()


def render_email_pdf(
    html: str,
    pdf_path: Path,
    pdf_attachments: list[bytes],
    browser,
) -> None:
    temp_pdf = pdf_path.with_suffix(".part.pdf")
    page = browser.new_page()
    try:
        page.set_content(html, wait_until="domcontentloaded")
        page.emulate_media(media="screen")
        page.pdf(
            path=str(temp_pdf),
            format="A4",
            print_background=True,
            margin={"top": "12mm", "bottom": "12mm", "left": "12mm", "right": "12mm"},
        )
    finally:
        page.close()

    if pdf_attachments:
        merge_pdf_files(temp_pdf, pdf_attachments, pdf_path)
        temp_pdf.unlink(missing_ok=True)
    else:
        temp_pdf.replace(pdf_path)


def find_mbox_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.mbox"))


def convert_mbox(
    mbox_path: Path,
    output_dir: Path,
    save_attachments_flag: bool,
    limit: int | None,
    browser,
    log: Callable[[str], None] = print,
) -> tuple[int, int]:
    output_dir.mkdir(parents=True, exist_ok=True)
    log(f"Apertura MBOX: {mbox_path.name}")
    mbox = mailbox.mbox(str(mbox_path))
    ok = 0
    errors = 0

    for index, msg in enumerate(mbox, start=1):
        if index == 1 or index % 25 == 0:
            log(f"Elaborazione email #{index}...")
        if limit is not None and index > limit:
            break

        subject = decode_mime_header(msg.get("Subject")) or "senza_oggetto"
        date_prefix = format_date(msg).replace(":", "-").replace(" ", "_") or f"{index:06d}"
        base_name = sanitize_filename(f"{date_prefix}_{subject}")
        pdf_path = output_dir / f"{index:06d}_{base_name}.pdf"
        attach_dir = output_dir / f"{index:06d}_{base_name}_allegati"

        attachment_names: list[str] = []
        if save_attachments_flag:
            attachment_names = save_attachments(msg, attach_dir)
        else:
            attachment_names = [name for name, _ in list_attachments(msg)]

        html = build_html(msg, attachment_names)
        pdf_attachments = get_pdf_attachments(msg)

        try:
            render_email_pdf(html, pdf_path, pdf_attachments, browser)
            ok += 1
            log(f"[OK] {pdf_path.name}")
        except Exception as exc:
            errors += 1
            log(f"[ERR] email #{index}: {exc}")

    mbox.close()
    return ok, errors


def run_conversion(
    mbox_path: Path,
    output_dir: Path,
    save_attachments: bool = False,
    limit: int | None = None,
    log: Callable[[str], None] = print,
) -> tuple[int, int]:
    if fitz is None:
        raise RuntimeError("Manca pymupdf. Esegui: pip install -r requirements.txt")
    if sync_playwright is None:
        raise RuntimeError("Manca playwright. Esegui: pip install -r requirements.txt")

    setup_playwright_browsers()
    mbox_files = find_mbox_files(mbox_path)
    if not mbox_files:
        raise FileNotFoundError("Nessun file .mbox trovato.")

    total_ok = 0
    total_err = 0

    log("Avvio browser Chromium...")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        log("Browser pronto.")
        try:
            for mbox_file in mbox_files:
                sub_output = (
                    output_dir / mbox_file.stem if len(mbox_files) > 1 else output_dir
                )
                log(f"\n=== {mbox_file} -> {sub_output} ===")
                ok, err = convert_mbox(
                    mbox_file,
                    sub_output,
                    save_attachments,
                    limit,
                    browser,
                    log=log,
                )
                total_ok += ok
                total_err += err
        finally:
            browser.close()

    return total_ok, total_err


def main_cli() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    if fitz is None:
        print("Manca pymupdf. Esegui: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)
    if sync_playwright is None:
        print("Manca playwright. Esegui: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Converte MBOX in PDF singoli.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mbox", type=Path, help="Percorso di un singolo file .mbox")
    group.add_argument(
        "--input-dir",
        type=Path,
        help="Cartella Takeout (cerca ricorsivamente tutti i .mbox)",
    )
    parser.add_argument("--output", type=Path, required=True, help="Cartella di output PDF")
    parser.add_argument(
        "--save-attachments",
        action="store_true",
        help="Salva anche gli allegati in sottocartelle accanto ai PDF",
    )
    parser.add_argument("--limit", type=int, help="Converte solo le prime N email (test)")
    args = parser.parse_args()

    input_path = args.mbox if args.mbox else args.input_dir
    assert input_path is not None

    mbox_files = find_mbox_files(input_path)
    if not mbox_files:
        print("Nessun file .mbox trovato.", file=sys.stderr)
        sys.exit(1)

    total_ok = 0
    total_err = 0

    setup_playwright_browsers()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            for mbox_file in mbox_files:
                sub_output = (
                    args.output / mbox_file.stem if len(mbox_files) > 1 else args.output
                )
                print(f"\n=== {mbox_file} -> {sub_output} ===")
                ok, err = convert_mbox(
                    mbox_file,
                    sub_output,
                    args.save_attachments,
                    args.limit,
                    browser,
                )
                total_ok += ok
                total_err += err
        finally:
            browser.close()

    print(f"\nCompletato: {total_ok} PDF creati, {total_err} errori.")
    if total_err:
        sys.exit(1)


def main() -> None:
    if is_gui_mode():
        from gui import launch_gui

        launch_gui()
    else:
        main_cli()


if __name__ == "__main__":
    main()
