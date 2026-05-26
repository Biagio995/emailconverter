"""Interfaccia grafica per la conversione MBOX -> PDF e unione PDF."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from mbox_to_pdf import fitz, merge_pdf_paths


class MboxToPdfApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MBOX to PDF")
        self.minsize(560, 520)
        self.geometry("680x560")

        self.mbox_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.output_mode = tk.StringVar(value="separate")
        self.save_attachments = tk.BooleanVar(value=False)
        self.merge_output_path = tk.StringVar()
        self.merge_pdf_list: list[Path] = []

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()
        self._poll_log_queue()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.mbox_tab = ttk.Frame(self.notebook, padding=4)
        self.merge_tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(self.mbox_tab, text="MBOX → PDF")
        self.notebook.add(self.merge_tab, text="Unisci PDF")

        self._build_mbox_tab()
        self._build_merge_tab()

        pad = {"padx": 0, "pady": (10, 0)}
        ttk.Label(root, text="Log:").pack(anchor=tk.W, **pad)
        self.log_text = scrolledtext.ScrolledText(
            root, height=10, state=tk.DISABLED, wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    def _build_mbox_tab(self) -> None:
        pad = {"padx": 8, "pady": 6}
        frame = self.mbox_tab
        frame.columnconfigure(1, weight=1)

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

        mode_frame = ttk.LabelFrame(frame, text="Modalità output", padding=(8, 4))
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, **pad)
        ttk.Radiobutton(
            mode_frame,
            text="Un PDF per ogni email (con allegati PDF integrati)",
            variable=self.output_mode,
            value="separate",
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            mode_frame,
            text="Un unico PDF con tutte le email e gli allegati",
            variable=self.output_mode,
            value="single",
        ).pack(anchor=tk.W)

        ttk.Checkbutton(
            frame,
            text="Salva anche gli allegati in sottocartelle (modalità separata)",
            variable=self.save_attachments,
        ).grid(row=3, column=0, columnspan=3, sticky=tk.W, **pad)

        self.convert_btn = ttk.Button(
            frame, text="Avvia conversione", command=self._start_conversion
        )
        self.convert_btn.grid(row=4, column=0, columnspan=3, pady=(8, 4))

    def _build_merge_tab(self) -> None:
        pad = {"padx": 8, "pady": 6}
        frame = self.merge_tab
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Aggiungi tutti i PDF da unire (nessun limite al numero di file). "
            "L'ordine nella lista è l'ordine nel documento finale.",
            wraplength=600,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, **pad)

        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, columnspan=2, sticky=tk.NSEW, padx=8, pady=4)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.merge_listbox = tk.Listbox(
            list_frame,
            height=10,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.merge_listbox.yview)
        self.merge_listbox.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        btn_col = ttk.Frame(frame)
        btn_col.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=8, pady=4)
        ttk.Button(btn_col, text="Aggiungi PDF...", command=self._merge_add_files).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_col, text="Rimuovi selezionati", command=self._merge_remove).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_col, text="Su", command=lambda: self._merge_move(-1)).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_col, text="Giù", command=lambda: self._merge_move(1)).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btn_col, text="Svuota lista", command=self._merge_clear).pack(side=tk.LEFT)

        ttk.Label(frame, text="File PDF di output:").grid(
            row=3, column=0, sticky=tk.W, **pad
        )
        out_row = ttk.Frame(frame)
        out_row.grid(row=4, column=0, columnspan=2, sticky=tk.EW, padx=8, pady=4)
        out_row.columnconfigure(0, weight=1)
        ttk.Entry(out_row, textvariable=self.merge_output_path).grid(
            row=0, column=0, sticky=tk.EW, padx=(0, 8)
        )
        ttk.Button(out_row, text="Sfoglia...", command=self._merge_pick_output).grid(
            row=0, column=1
        )

        self.merge_btn = ttk.Button(
            frame, text="Avvia unione", command=self._start_merge
        )
        self.merge_btn.grid(row=5, column=0, columnspan=2, pady=(8, 4))

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

    def _merge_refresh_listbox(self) -> None:
        self.merge_listbox.delete(0, tk.END)
        for path in self.merge_pdf_list:
            self.merge_listbox.insert(tk.END, path.name)

    def _merge_add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Seleziona file PDF",
            filetypes=[("File PDF", "*.pdf"), ("Tutti i file", "*.*")],
        )
        if not paths:
            return
        existing = {p.resolve() for p in self.merge_pdf_list}
        added = 0
        for raw in paths:
            path = Path(raw)
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in existing:
                continue
            self.merge_pdf_list.append(path)
            existing.add(resolved)
            added += 1
        self._merge_refresh_listbox()
        if added:
            self._log(f"Aggiunti {added} PDF (totale: {len(self.merge_pdf_list)})")

    def _merge_remove(self) -> None:
        selection = list(self.merge_listbox.curselection())
        if not selection:
            return
        for index in reversed(selection):
            del self.merge_pdf_list[index]
        self._merge_refresh_listbox()

    def _merge_move(self, direction: int) -> None:
        selection = list(self.merge_listbox.curselection())
        if len(selection) != 1:
            messagebox.showinfo(
                "Ordine file",
                "Seleziona un solo file nella lista per spostarlo.",
            )
            return
        index = selection[0]
        new_index = index + direction
        if new_index < 0 or new_index >= len(self.merge_pdf_list):
            return
        self.merge_pdf_list[index], self.merge_pdf_list[new_index] = (
            self.merge_pdf_list[new_index],
            self.merge_pdf_list[index],
        )
        self._merge_refresh_listbox()
        self.merge_listbox.selection_clear(0, tk.END)
        self.merge_listbox.selection_set(new_index)
        self.merge_listbox.see(new_index)

    def _merge_clear(self) -> None:
        if not self.merge_pdf_list:
            return
        if messagebox.askyesno("Conferma", "Rimuovere tutti i PDF dalla lista?"):
            self.merge_pdf_list.clear()
            self._merge_refresh_listbox()

    def _merge_pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Salva PDF unito come",
            defaultextension=".pdf",
            filetypes=[("File PDF", "*.pdf")],
        )
        if path:
            self.merge_output_path.set(path)

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

    def _is_busy(self) -> bool:
        return self.worker is not None and self.worker.is_alive()

    def _set_busy(self, busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        self.convert_btn.configure(state=state)
        self.merge_btn.configure(state=state)

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

    def _validate_merge_inputs(self) -> tuple[list[Path], Path] | None:
        if fitz is None:
            messagebox.showerror(
                "Errore",
                "Manca pymupdf.\nEsegui: pip install -r requirements.txt",
            )
            return None

        if len(self.merge_pdf_list) < 2:
            messagebox.showwarning(
                "Attenzione",
                "Aggiungi almeno due file PDF da unire.",
            )
            return None

        missing = [p for p in self.merge_pdf_list if not p.is_file()]
        if missing:
            messagebox.showerror(
                "Errore",
                "Alcuni file non esistono più:\n" + "\n".join(str(p) for p in missing),
            )
            return None

        output = self.merge_output_path.get().strip()
        if not output:
            messagebox.showwarning("Attenzione", "Indica il percorso del PDF di output.")
            return None

        output_path = Path(output)
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")

        if output_path.exists():
            if not messagebox.askyesno(
                "File esistente",
                f"Il file esiste già:\n{output_path}\n\nSovrascriverlo?",
            ):
                return None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        return self.merge_pdf_list.copy(), output_path

    def _build_cli_command(self, mbox_path: Path, output_path: Path) -> list[str]:
        if getattr(sys, "frozen", False):
            cmd = [sys.executable]
        else:
            cmd = [sys.executable, str(Path(__file__).resolve().parent / "mbox_to_pdf.py")]
        cmd.extend(["--mbox", str(mbox_path), "--output", str(output_path)])
        if self.output_mode.get() == "single":
            cmd.append("--single-pdf")
        if self.save_attachments.get():
            cmd.append("--save-attachments")
        return cmd

    def _start_conversion(self) -> None:
        if self._is_busy():
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

    def _start_merge(self) -> None:
        if self._is_busy():
            return

        inputs = self._validate_merge_inputs()
        if inputs is None:
            return

        pdf_paths, output_path = inputs
        self._set_busy(True)
        self._log(f"\n--- Unione di {len(pdf_paths)} PDF ---")
        for i, path in enumerate(pdf_paths, start=1):
            self._log(f"  {i}. {path.name}")

        def task() -> None:
            try:
                merge_pdf_paths(pdf_paths, output_path)
                self.after(0, lambda: self._on_merge_finished(output_path))
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

    def _on_merge_finished(self, output_path: Path) -> None:
        self._set_busy(False)
        self._log(f"Unione completata: {output_path}")
        messagebox.showinfo(
            "Unione completata",
            f"PDF salvato in:\n{output_path}",
        )

    def _on_error(self, message: str) -> None:
        self._set_busy(False)
        self._log(f"\nERRORE: {message}")
        messagebox.showerror("Errore", message)


def launch_gui() -> None:
    app = MboxToPdfApp()
    if getattr(sys, "frozen", False):
        from update_checker import schedule_update_check

        schedule_update_check(app)
    app.mainloop()
