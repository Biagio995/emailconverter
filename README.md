# MBOX to PDF

Convert **MBOX** mail archives (Gmail export, Google Takeout, etc.) into **individual PDF files** — one PDF per email, with optional attachment export.

<p align="center">
  <a href="https://github.com/Biagio995/emailconverter/releases/latest/download/MBOXtoPDF_Setup.exe">
    <img src="https://img.shields.io/badge/Download-Windows%20Installer-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Download Windows installer">
  </a>
</p>

<p align="center">
  <a href="https://github.com/Biagio995/emailconverter/releases/latest"><strong>All releases</strong></a>
  ·
  <a href="#usage">Usage</a>
  ·
  <a href="#build-from-source">Build from source</a>
</p>

---

## Download

| Platform | File | Link |
|----------|------|------|
| **Windows** | Installer | [**MBOXtoPDF_Setup.exe**](https://github.com/Biagio995/emailconverter/releases/latest/download/MBOXtoPDF_Setup.exe) |
| **macOS** | Disk image | [**MBOXtoPDF.dmg**](https://github.com/Biagio995/emailconverter/releases/latest/download/MBOXtoPDF.dmg) *(when published)* |

> **Requirements:** Windows 10/11 (64-bit) · ~300 MB disk space (includes Chromium for HTML→PDF rendering)

**End users:** download and run **`MBOXtoPDF_Setup.exe` only** — you do not need the `dist/` folder from the repository. The installer copies everything into `Program Files`.

On each launch, the installed app checks GitHub Releases in the background. If a newer version exists, you are prompted once to download the installer (you are not asked again for the same version if you choose **No**).

**Developers:** `dist/` is a local build output (gitignored), not something users clone from GitHub.

---

## Features

- Graphical interface — pick your `.mbox` file and output folder
- **Merge PDF** tab — combine any number of PDF files into one (no 25-file limit)
- Preserves HTML email layout (images, formatting) via headless Chromium
- Merges PDF attachments into the generated email PDF when present
- Optional export of non-PDF attachments into subfolders
- CLI mode for scripting and batch workflows

---

## Usage

### GUI (recommended)

1. Install with **MBOXtoPDF_Setup.exe** or run the portable build.
2. Launch **MBOX to PDF**.
3. **Browse…** → select your `.mbox` file.
4. **Browse…** → choose the output directory.
5. Click **Start conversion**.

### Merge PDF (Unisci PDF tab)

1. Open the **Unisci PDF** tab.
2. **Aggiungi PDF...** — add as many PDF files as you need (order matters).
3. Use **Su** / **Giù** to reorder, **Rimuovi selezionati** to remove files.
4. Choose the output file path, then click **Avvia unione**.

Each message is saved as:

```text
000001_2024-01-15_10-30_Subject_line.pdf
```

### Command line

```bash
python mbox_to_pdf.py --cli --mbox "path/to/mail.mbox" --output "path/to/pdf"
```

Optional flags:

| Flag | Description |
|------|-------------|
| `--save-attachments` | Save attachments in `_allegati` subfolders |
| `--input-dir` | Scan a folder recursively for `.mbox` files |
| `--limit N` | Convert only the first N emails (testing) |

---

## Installation notes (Windows)

- If **SmartScreen** appears: *More info* → *Run anyway* (the installer is not commercially code-signed).
- Uninstall via *Settings → Apps* like any other program.

---

## Build from source

### Prerequisites

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### Run without packaging

```bash
python mbox_to_pdf.py          # opens GUI
python mbox_to_pdf.py --gui    # same
```

### Windows — create installer

Requires [Inno Setup 6](https://jrsoftware.org/isdl.php):

```bash
python build_exe.py
```

Outputs:

- `dist/MBOXtoPDF/` — portable app
- `dist/MBOXtoPDF_Setup.exe` — installer for distribution

### macOS — create `.app` and `.dmg`

**Must be built on a Mac:**

```bash
python3 build_mac.py
```

Outputs:

- `dist/MBOXtoPDF.app`
- `dist/MBOXtoPDF.dmg`

---

## Project structure

```text
mbox_to_pdf.py      # Core conversion logic + CLI entry point
gui.py              # Tkinter GUI
build_exe.py        # Windows build + Inno Setup
build_mac.py        # macOS build + DMG
installer.iss       # Inno Setup script
requirements.txt
```

---

## Tech stack

- Python 3 · [Playwright](https://playwright.dev/) (Chromium) · [PyMuPDF](https://pymupdf.readthedocs.io/) · Tkinter · PyInstaller

---

## License

See repository license file. If none is set, all rights reserved by the author.

---

<p align="center">
  <sub>Issues and feedback welcome on <a href="https://github.com/Biagio995/emailconverter/issues">GitHub Issues</a>.</sub>
</p>
