from __future__ import annotations

import argparse
import sys
import time

from ..cerebro.config import ensure_dirs, load_config
from ..cerebro.orchestrator import Orchestrator
from ..comunicacao.chat_inbox import ChatInbox
from ..seguranca.kill_switch import stop_requested
from .preflight import format_report, run_preflight
from .shortcut import ChatShortcut
from .stt import check_stt_deps


def _ensure_stt_ready(config) -> bool:
    deps = check_stt_deps()
    mode = config.stt_mode
    has_audio = deps.get("sounddevice") and deps.get("numpy")
    has_local = has_audio and deps.get("faster_whisper")

    if mode == "none":
        print("Voz desativada (JARVIS_STT_MODE=none).")
        return False

    if not has_audio:
        print("Voz indisponivel: faltam sounddevice/numpy (pip install sounddevice numpy).")
        return False

    if mode in {"local", "auto"} and not has_local:
        print("Voz indisponivel: faltando faster-whisper (pip install faster-whisper).")
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis MVP")
    parser.add_argument("--text", help="command text to run once")
    parser.add_argument("--voice", action="store_true", help="capture voice for a single command")
    parser.add_argument("--voice-loop", action="store_true", help="continuous voice loop")
    parser.add_argument("--loop", action="store_true", help="interactive loop")
    parser.add_argument(
        "--gui-panel",
        action="store_true",
        help="open a floating panel for writing commands instead of the terminal loop",
    )
    parser.add_argument("--dry-run", action="store_true", help="plan only, do not execute actions")
    parser.add_argument("--preflight", action="store_true", help="check dependencies and exit")
    parser.add_argument("--open-chat", action="store_true", help="open chat log and exit")
    parser.add_argument("--chat-ui", action="store_true", help="open chat UI and exit")
    parser.add_argument("--s3", help="run Agent S3 GUI loop with a task instruction")
    parser.add_argument(
        "--preflight-strict",
        action="store_true",
        help="exit with error if critical checks fail (use with --preflight)",
    )
    parser.add_argument(
        "--enable-shortcut",
        action="store_true",
        help="enable global keyboard shortcut (Ctrl+Shift+J) to open chat UI",
    )
    args = parser.parse_args()

    config = load_config()
    # Painel e dry-run não devem ficar presos em aprovação: desligamos aprovação aqui.
    if args.dry_run:
        config = config.__class__(**{**config.__dict__, "dry_run": True, "require_approval": False})
    if args.gui_panel:
        config = config.__class__(**{**config.__dict__, "require_approval": False})
    ensure_dirs(config)

    if args.preflight:
        report = run_preflight(config)
        print(format_report(report))
        if args.preflight_strict and report.has_failures:
            return 2
        return 0

    if args.open_chat:
        from ..comunicacao.chat_log import ChatLog
        ChatLog(
            config.chat_log_path,
            auto_open=True,
            open_command=config.chat_open_command,
            open_cooldown_s=config.chat_open_cooldown_s,
        ).open()
        return 0

    if args.chat_ui:
        from .chat_ui import main as chat_main
        return chat_main()

    if args.voice or args.voice_loop:
        if not _ensure_stt_ready(config):
            return 2

    orchestrator = Orchestrator(config)
    chat_inbox = ChatInbox(config.chat_inbox_path)

    # Initialize shortcut if enabled
    chat_shortcut: ChatShortcut | None = None
    if args.enable_shortcut:
        chat_shortcut = ChatShortcut(
            chat_command=config.chat_open_command or None,
        )
        if chat_shortcut.start():
            print("Atalho global ativado: Ctrl+Shift+J para abrir chat UI")
        else:
            print("Aviso: pynput não disponível. Atalho desabilitado.")
            chat_shortcut = None

    def drain_chat_inbox() -> None:
        for line in chat_inbox.drain():
            orchestrator.handle_text(line)

    if args.text:
        orchestrator.handle_text(args.text)
        return 0

    if args.s3:
        orchestrator.run_s3_loop(args.s3)
        return 0

    if args.voice:
        orchestrator.transcribe_and_handle()
        return 0

    if args.voice_loop:
        print("Jarvis MVP - voice loop (Ctrl+C para sair)")
        try:
            while True:
                if stop_requested(config.stop_file_path):
                    print("Kill switch ativo. Saindo do loop.")
                    break
                drain_chat_inbox()
                orchestrator.transcribe_and_handle()
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            if chat_shortcut:
                chat_shortcut.stop()
        return 0

    if args.gui_panel:
        from .gui_panel import JarvisPanel

        panel = JarvisPanel(orchestrator, chat_shortcut)
        panel.run()
        return 0

    if args.loop or not args.text:
        print("Jarvis MVP - type commands or 'exit' to quit")
        try:
            from ..cerebro.utils import normalize_text
            while True:
                if stop_requested(config.stop_file_path):
                    print("Kill switch ativo. Saindo do loop.")
                    break
                drain_chat_inbox()
                try:
                    text = input("> ")
                except EOFError:
                    break
                if normalize_text(text) in {"exit", "quit"}:
                    break
                orchestrator.handle_text(text)
        finally:
            if chat_shortcut:
                chat_shortcut.stop()
        return 0

    # Cleanup shortcut if it was started
    if chat_shortcut:
        chat_shortcut.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
