from __future__ import annotations

import dataclasses
import os
import threading
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
except ImportError as exc:
    raise RuntimeError(
        "Tkinter é necessário para o painel gráfico do Jarvis. "
        "Instale python3-tk e tente novamente."
    ) from exc


def _env_int(key: str, default: int) -> int:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


class JarvisPanel:
    """Mini painel flutuante para enviar comandos e acompanhar o status."""

    def __init__(
        self,
        orchestrator,
        chat_shortcut: Optional[object] = None,
        followup_poll_ms: int | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._chat_shortcut = chat_shortcut
        self._microphone_enabled = self._is_stt_enabled()
        self._stt_prev_mode: str | None = None
        self._busy = False
        self._last_mic_error: str | None = None
        if followup_poll_ms is None:
            followup_poll_ms = _env_int("JARVIS_GUI_FOLLOWUP_POLL_MS", 500)
        self._followup_poll_ms = int(followup_poll_ms)
        self._followup_poll_enabled = True

        self.root = tk.Tk()
        self.root.title("Jarvis - Painel rápido")
        self.root.geometry("400x240+80+80")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)

        self._build_ui()
        self._update_followup_indicator()
        self._schedule_followup_poll()

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
        self._sync_mic_label()

        self.cancel_button = tk.Button(
            control_frame,
            text="Cancelar",
            command=self._request_cancel,
            width=12,
        )
        self.cancel_button.pack(side="left", padx=(4, 0))

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
        self.status_label.pack(side="left", padx=(6, 0))

        self.followup_label = tk.Label(
            control_frame,
            text="Follow-up: inativo",
            anchor="w",
        )
        self.followup_label.pack(side="left", padx=(6, 0), expand=True)

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
        target_enabled = not self._microphone_enabled
        current_mode = self._get_stt_mode() or "local"
        desired_mode = current_mode

        if target_enabled:
            desired_mode = self._stt_prev_mode or current_mode
            if desired_mode == "none":
                desired_mode = "local"
        else:
            if current_mode and current_mode != "none":
                self._stt_prev_mode = current_mode
            desired_mode = "none"

        if not self._set_stt_mode(desired_mode):
            detail = self._last_mic_error or "config indisponivel"
            self._log(f"Nao foi possivel alternar o microfone ({detail}).")
            return

        self._microphone_enabled = target_enabled
        self._sync_mic_label()
        label = (
            "Microfone: Ligado" if self._microphone_enabled else "Microfone: Desligado"
        )
        self._log(
            f"{label} (STT={'ativo' if self._microphone_enabled else 'desativado'})."
        )

    def _request_cancel(self) -> None:
        config = getattr(self._orchestrator, "config", None)
        stop_path = getattr(config, "stop_file_path", None)
        if stop_path is None:
            self._log("Cancelamento indisponivel (stop_file_path ausente).")
            return
        try:
            path = stop_path if isinstance(stop_path, Path) else Path(str(stop_path))
        except Exception:
            self._log("Cancelamento indisponivel (stop_file_path invalido).")
            return
        try:
            if path.exists():
                path.unlink()
                self._log("Cancelamento removido. Jarvis pode continuar.")
                return
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(exist_ok=True)
            self._log("Cancelamento solicitado (STOP ativado).")
        except Exception as exc:
            self._log(f"Falha ao alternar cancelamento: {exc}")

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
            self.root.after(0, self._update_followup_indicator)

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
        self._followup_poll_enabled = False
        self._log("Desligando o Jarvis...")
        if self._chat_shortcut is not None:
            stop_method = getattr(self._chat_shortcut, "stop", None)
            if stop_method is not None:
                stop_method()
        if self._busy:
            self._set_busy(False)
        self.root.destroy()

    def _get_stt_mode(self) -> Optional[str]:
        config = getattr(self._orchestrator, "config", None)
        mode = getattr(config, "stt_mode", None) if config else None
        if mode is None:
            stt = getattr(self._orchestrator, "stt", None)
            mode = getattr(getattr(stt, "config", None), "stt_mode", None)
        return str(mode) if mode is not None else None

    def _is_stt_enabled(self) -> bool:
        mode = self._get_stt_mode()
        return bool(mode and mode != "none")

    def _clone_config(self, config, **overrides):
        if hasattr(config, "__dataclass_fields__"):
            try:
                return dataclasses.replace(config, **overrides)
            except Exception:
                pass
        if not hasattr(config, "__dict__"):
            return None
        data = dict(config.__dict__)
        data.update(overrides)
        try:
            return config.__class__(**data)
        except Exception:
            return None

    def _set_stt_mode(self, mode: str) -> bool:
        self._last_mic_error = None
        config = getattr(self._orchestrator, "config", None)
        if config is None or not hasattr(config, "stt_mode"):
            self._last_mic_error = "config sem stt_mode"
            return False
        new_config = self._clone_config(config, stt_mode=mode)
        if new_config is None:
            try:
                setattr(config, "stt_mode", mode)
                new_config = config
            except Exception as exc:
                self._last_mic_error = f"config imutavel/nao clonavel: {exc}"
                return False
        self._orchestrator.config = new_config
        stt = getattr(self._orchestrator, "stt", None)
        if stt is not None and hasattr(stt, "config"):
            stt.config = new_config
        return True

    def _sync_mic_label(self) -> None:
        label = (
            "Microfone: Ligado" if self._microphone_enabled else "Microfone: Desligado"
        )
        self.mic_button.configure(text=label)

    def _get_followup_state(self) -> Optional[bool]:
        followup = getattr(self._orchestrator, "_followup", None)
        if followup is None or not hasattr(followup, "is_active"):
            return None
        try:
            return bool(followup.is_active())
        except Exception:
            return None

    def _update_followup_indicator(self) -> None:
        state = self._get_followup_state()
        if state is None:
            label = "Follow-up: n/a"
        elif state:
            label = "Follow-up: ativo"
        else:
            label = "Follow-up: inativo"
        self.followup_label.configure(text=label)

    def _schedule_followup_poll(self) -> None:
        if not self._followup_poll_enabled:
            return
        if getattr(self.root, "_immediate_after", False):
            return

        def _tick() -> None:
            if not self._followup_poll_enabled or not self.root.winfo_exists():
                return
            self._update_followup_indicator()
            self.root.after(self._followup_poll_ms, _tick)

        self.root.after(self._followup_poll_ms, _tick)
