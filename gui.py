"""Interfaccia grafica per la conversione MBOX -> PDF."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk


class MboxToPdfApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MBOX to PDF")
        self.minsize(520, 420)
        self.geometry("640x480")

        self.mbox_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.save_attachments = tk.BooleanVar(value=False)
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}
        frame = ttk.Frame(self, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="File MBOX:").grid(row=0, column=0, sticky=tk.W, **pad)
        ttk.Entry(frame, textvariable=self.mbox_path, width=52).grid(
            row=0, column=1, sticky=tk.EW, **pad
        )
        ttk.Button(frame, text="Sfoglia...", command=self._pick_mbox).grid(
            row=0, column=2, **pad
        )

        ttk.Label(frame, text="Cartella output:").grid(row=1, column=0, sticky=tk.W, **pad)
        ttk.Entry(frame, textvariable=self.output_dir, width=52).grid(
            row=1, column=1, sticky=tk.EW, **pad
        )
        ttk.Button(frame, text="Sfoglia...", command=self._pick_output).grid(
            row=1, column=2, **pad
        )

        ttk.Checkbutton(
            frame,
            text="Salva anche gli allegati in sottocartelle",
            variable=self.save_attachments,
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, **pad)

        self.convert_btn = ttk.Button(
            frame, text="Avvia conversione", command=self._start_conversion
        )
        self.convert_btn.grid(row=3, column=0, columnspan=3, pady=(8, 4))

        ttk.Label(frame, text="Log:").grid(row=4, column=0, sticky=tk.NW, **pad)
        self.log_text = scrolledtext.ScrolledText(
            frame, height=14, state=tk.DISABLED, wrap=tk.WORD
        )
        self.log_text.grid(row=4, column=1, columnspan=2, sticky=tk.NSEW, **pad)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(4, weight=1)

    def _pick_mbox(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleziona file MBOX",
            filetypes=[("File MBOX", "*.mbox"), ("Tutti i file", "*.*")],
        )
        if path:
            self.mbox_path.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="Seleziona cartella di salvataggio")
        if path:
            self.output_dir.set(path)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _poll_log_queue(self) -> None:
        try:
            while True:
                self._append_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.after(100, self._poll_log_queue)

    def _log(self, message: str) -> None:
        self.log_queue.put(message)

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.convert_btn.configure(state=state)

    def _validate_inputs(self) -> tuple[Path, Path] | None:
        mbox = self.mbox_path.get().strip()
        output = self.output_dir.get().strip()

        if not mbox:
            messagebox.showwarning("Attenzione", "Seleziona un file .mbox.")
            return None
        mbox_path = Path(mbox)
        if not mbox_path.is_file():
            messagebox.showerror("Errore", f"File non trovato:\n{mbox_path}")
            return None
        if mbox_path.suffix.lower() != ".mbox":
            messagebox.showwarning(
                "Attenzione", "Il file selezionato non ha estensione .mbox."
            )

        if not output:
            messagebox.showwarning("Attenzione", "Seleziona la cartella di salvataggio.")
            return None
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        return mbox_path, output_path

    def _build_cli_command(self, mbox_path: Path, output_path: Path) -> list[str]:
        if getattr(sys, "frozen", False):
            cmd = [sys.executable]
        else:
            cmd = [sys.executable, str(Path(__file__).resolve().parent / "mbox_to_pdf.py")]
        cmd.extend(["--mbox", str(mbox_path), "--output", str(output_path)])
        if self.save_attachments.get():
            cmd.append("--save-attachments")
        return cmd

    def _start_conversion(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        inputs = self._validate_inputs()
        if inputs is None:
            return

        mbox_path, output_path = inputs
        self._set_busy(True)
        self._log(f"\n--- Avvio: {mbox_path.name} ---")
        self._log("Preparazione conversione (può richiedere alcuni secondi)...")

        def task() -> None:
            cmd = self._build_cli_command(mbox_path, output_path)
            try:
                env = os.environ.copy()
                env["PYTHONUNBUFFERED"] = "1"
                kwargs: dict = {
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.STDOUT,
                    "text": True,
                    "encoding": "utf-8",
                    "errors": "replace",
                    "bufsize": 1,
                    "env": env,
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

                with subprocess.Popen(cmd, **kwargs) as proc:
                    assert proc.stdout is not None
                    for line in proc.stdout:
                        text = line.rstrip()
                        if text:
                            self._log(text)
                    return_code = proc.wait()

                self.after(
                    0,
                    lambda: self._on_finished(return_code, output_path),
                )
            except Exception as exc:
                self.after(0, lambda: self._on_error(str(exc)))

        self.worker = threading.Thread(target=task, daemon=True)
        self.worker.start()

    def _on_finished(self, return_code: int, output_path: Path) -> None:
        self._set_busy(False)
        if return_code == 0:
            messagebox.showinfo(
                "Conversione completata",
                f"PDF salvati in:\n{output_path}",
            )
        else:
            messagebox.showwarning(
                "Conversione terminata con errori",
                f"Controlla il log per i dettagli.\n\nOutput:\n{output_path}",
            )

    def _on_error(self, message: str) -> None:
        self._set_busy(False)
        self._log(f"\nERRORE: {message}")
        messagebox.showerror("Errore", message)


def launch_gui() -> None:
    app = MboxToPdfApp()
    app.mainloop()
