from __future__ import annotations

import threading
from typing import Optional

try:
    import tkinter as tk
except ImportError as exc:
    raise RuntimeError(
        "Tkinter é necessário para o painel gráfico do Jarvis. "
        "Instale python3-tk e tente novamente."
    ) from exc


class JarvisPanel:
    """Mini painel flutuante para enviar comandos e acompanhar o status."""

    def __init__(self, orchestrator, chat_shortcut: Optional[object] = None) -> None:
        self._orchestrator = orchestrator
        self._chat_shortcut = chat_shortcut
        self._microphone_enabled = False
        self._busy = False

        self.root = tk.Tk()
        self.root.title("Jarvis - Painel rápido")
        self.root.geometry("400x240+80+80")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)

        self._build_ui()

    def _build_ui(self) -> None:
        padding = 8
        container = tk.Frame(self.root, padx=padding, pady=padding)
        container.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            container,
            height=7,
            state="disabled",
            wrap="word",
            bg="#121212",
            fg="#f0f0f0",
        )
        self.log_text.pack(fill="both", expand=True)

        entry_frame = tk.Frame(container)
        entry_frame.pack(fill="x", pady=(6, 0))

        self.command_entry = tk.Entry(entry_frame, width=32)
        self.command_entry.pack(side="left", fill="x", expand=True)
        self.command_entry.bind("<Return>", self._on_send)
        self.command_entry.focus_set()

        self.send_button = tk.Button(
            entry_frame,
            text="Enviar",
            command=self._on_send,
            width=10,
            bg="#2c6ebd",
            fg="white",
        )
        self.send_button.pack(side="left", padx=(6, 0))

        control_frame = tk.Frame(container)
        control_frame.pack(fill="x", pady=(6, 0))

        self.mic_button = tk.Button(
            control_frame,
            text="Microfone: Desligado",
            command=self._toggle_microphone,
            width=18,
        )
        self.mic_button.pack(side="left")

        self.power_button = tk.Button(
            control_frame,
            text="Desligar Jarvis",
            command=self._shutdown,
            width=18,
        )
        self.power_button.pack(side="left", padx=(4, 0))

        self.status_label = tk.Label(
            control_frame,
            text="Pronto para ouvir comandos",
            anchor="w",
        )
        self.status_label.pack(side="left", padx=(6, 0), expand=True)

    def _log(self, message: str) -> None:
        """Append message to the log safely."""
        def updater() -> None:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

        self.root.after(0, updater)

    def _set_busy(self, busy: bool) -> None:
        """Enable/disable the entry and button while a command runs."""
        if self._busy == busy:
            return
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.send_button.configure(state=state)
        self.command_entry.configure(state=state)
        status = "Executando..." if busy else "Pronto para ouvir comandos"
        self.status_label.configure(text=status)

    def _toggle_microphone(self) -> None:
        self._microphone_enabled = not self._microphone_enabled
        label = "Microfone: Ligado" if self._microphone_enabled else "Microfone: Desligado"
        self.mic_button.configure(text=label)
        self._log(f"{label} (indicador apenas, STT permanece nas configurações padrão).")

    def _on_send(self, event: Optional[tk.Event] = None) -> None:
        if event:
            event.widget.after_idle(lambda: None)
        text = self.command_entry.get().strip()
        if not text or self._busy:
            return
        self.command_entry.delete(0, "end")
        self._set_busy(True)
        self._log(f"→ Enviando comando: {text}")
        thread = threading.Thread(
            target=self._execute_command,
            args=(text,),
            daemon=True,
        )
        thread.start()

    def _execute_command(self, text: str) -> None:
        try:
            self._orchestrator.handle_text(text)
            self._log(f"✅ Comando processado: {text}")
        except Exception as exc:
            self._log(f"❌ Erro ao processar '{text}': {exc}")
        finally:
            self.root.after(0, lambda: self._set_busy(False))

    def run(self) -> None:
        """Start the Tk event loop."""
        self._log("Painel pronto. Escreva para o Jarvis e pressione Enviar.")
        try:
            self.root.mainloop()
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        if not self.root.winfo_exists():
            return
        self._log("Desligando o Jarvis...")
        if self._chat_shortcut:
            self._chat_shortcut.stop()
        if self._busy:
            self._set_busy(False)
        self.root.destroy()
