from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from jarvis.cerebro.config import ensure_dirs, load_config
from jarvis.cerebro.orchestrator import Orchestrator
from jarvis.interface.infra.chat_inbox import ChatInbox
from jarvis.interface.infra.voice_profile import auto_configure_voice_profile
from jarvis.seguranca.kill_switch import stop_requested
from .preflight import format_report, run_preflight
from .shortcut import ChatShortcut
from .stt import check_stt_deps


def _ensure_stt_ready(config) -> bool:
    deps = check_stt_deps()
    mode = config.stt_mode
    missing: list[str] = []
    pip_map = {
        "sounddevice": "sounddevice",
        "numpy": "numpy",
        "faster-whisper": "faster-whisper",
    }

    if not deps.get("sounddevice"):
        missing.append("sounddevice")
    if not deps.get("numpy"):
        missing.append("numpy")
    if mode in {"local", "auto"} and not deps.get("faster_whisper"):
        missing.append("faster-whisper")

    if mode == "none":
        print("Voz desativada (JARVIS_STT_MODE=none).")
        return False

    if missing:
        print(f"Voz indisponivel: faltando {', '.join(missing)}.")
        pip_install = " ".join(pip_map[item] for item in missing if item in pip_map)
        if pip_install:
            print(f"Dica: pip install {pip_install}")
        return False

    return True


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _ensure_parent_writable(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        return False
    except OSError:
        return False


def _auto_relocate_unwritable_paths(config) -> bool:
    """
    If a `.env` has hardcoded paths that are not writable, relocate them into
    `config.data_dir` automatically for a smoother UX.
    """
    if not _env_bool("JARVIS_AUTO_RELOCATE_PATHS", True):
        return False

    mapping = {
        "JARVIS_PROCEDURES_PATH": config.data_dir / "procedures.db",
        "JARVIS_STOP_FILE_PATH": config.data_dir / "STOP",
        "JARVIS_CHAT_LOG_PATH": config.data_dir / "chat.log",
        "JARVIS_CHAT_INBOX_PATH": config.data_dir / "chat_inbox.txt",
        "JARVIS_POLICY_USER_PATH": config.data_dir / "policy_user.json",
        "JARVIS_BUDGET_PATH": config.data_dir / "orcamento.json",
    }

    changed = False
    for env_key, fallback_path in mapping.items():
        raw = os.environ.get(env_key)
        if not raw:
            continue
        try:
            current = Path(raw).expanduser()
        except Exception:
            current = Path(raw)
        if _ensure_parent_writable(current):
            continue
        os.environ[env_key] = str(fallback_path)
        changed = True
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis MVP")
    parser.add_argument("--text", help="command text to run once")
    parser.add_argument(
        "--voice", action="store_true", help="capture voice for a single command"
    )
    parser.add_argument(
        "--voice-loop", action="store_true", help="continuous voice loop"
    )
    parser.add_argument(
        "--voice-loop-sleep",
        type=float,
        default=0.5,
        help="sleep between voice loop iterations (seconds)",
    )
    parser.add_argument(
        "--voice-loop-max-iter",
        type=int,
        help="limite de iteracoes do voice loop (0 = infinito)",
    )
    parser.add_argument(
        "--audio-device",
        type=int,
        help="audio input device index (override JARVIS_AUDIO_DEVICE)",
    )
    parser.add_argument(
        "--audio-capture-sr",
        type=int,
        help="audio capture sample rate (override JARVIS_AUDIO_CAPTURE_SR)",
    )
    parser.add_argument("--loop", action="store_true", help="interactive loop")
    parser.add_argument(
        "--gui-panel",
        action="store_true",
        help="open a floating panel for writing commands instead of the terminal loop",
    )
    parser.add_argument(
        "--gui-followup-poll-ms",
        type=int,
        help="intervalo (ms) para atualizar o indicador de follow-up no painel",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="plan only, do not execute actions"
    )
    parser.add_argument(
        "--preflight", action="store_true", help="check dependencies and exit"
    )
    parser.add_argument(
        "--preflight-profile",
        help="perfil do preflight: full, voice, ui, desktop (ou combinacoes)",
    )
    parser.add_argument(
        "--open-chat", action="store_true", help="open chat log and exit"
    )
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

    if args.audio_device is not None:
        os.environ["JARVIS_AUDIO_DEVICE"] = str(args.audio_device)
    if args.audio_capture_sr is not None:
        os.environ["JARVIS_AUDIO_CAPTURE_SR"] = str(args.audio_capture_sr)
    if args.gui_followup_poll_ms is not None:
        os.environ["JARVIS_GUI_FOLLOWUP_POLL_MS"] = str(args.gui_followup_poll_ms)

    config = load_config()
    # Painel e dry-run não devem ficar presos em aprovação: desligamos aprovação aqui.
    if args.dry_run:
        config = config.__class__(
            **{**config.__dict__, "dry_run": True, "require_approval": False}
        )
    if args.gui_panel:
        config = config.__class__(**{**config.__dict__, "require_approval": False})
    try:
        ensure_dirs(config)
    except PermissionError:
        repo_root = Path(__file__).resolve().parents[3]
        fallback = repo_root / "storage" / "jarvis_data"
        print(
            f"Aviso: sem permissao para escrever em {config.data_dir}. "
            f"Usando data dir local: {fallback}"
        )
        os.environ["JARVIS_DATA_DIR"] = str(fallback)
        # Se o .env tiver paths hardcoded (ex.: /home/u/.jarvis), forçar tudo para o data_dir
        # para garantir que o modo voz funcione "sem configurar nada".
        os.environ["JARVIS_PROCEDURES_PATH"] = str(fallback / "procedures.db")
        os.environ["JARVIS_STOP_FILE_PATH"] = str(fallback / "STOP")
        os.environ["JARVIS_CHAT_LOG_PATH"] = str(fallback / "chat.log")
        os.environ["JARVIS_CHAT_INBOX_PATH"] = str(fallback / "chat_inbox.txt")
        os.environ["JARVIS_POLICY_USER_PATH"] = str(fallback / "policy_user.json")
        os.environ["JARVIS_BUDGET_PATH"] = str(fallback / "orcamento.json")
        config = load_config()
        ensure_dirs(config)

    if _auto_relocate_unwritable_paths(config):
        config = load_config()
        ensure_dirs(config)

    if args.preflight:
        report = run_preflight(config, profile=args.preflight_profile)
        print(format_report(report))
        if args.preflight_strict and report.has_failures:
            return 2
        return 0

    if args.open_chat:
        from jarvis.interface.infra.chat_log import ChatLog

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
        ok, reason = auto_configure_voice_profile(config)
        if not ok:
            print(reason or "Falha ao configurar perfil de voz.")
            return 2
        # Voice profile sets env defaults that affect config/STT initialization.
        # Reload config so `Orchestrator` and `SpeechToText` see the updated values.
        config = load_config()
        ensure_dirs(config)
        if not _ensure_stt_ready(config):
            return 2

    orchestrator = Orchestrator(config)
    chat_inbox = ChatInbox(config.chat_inbox_path)

    # Initialize shortcut if enabled
    chat_shortcut: ChatShortcut | None = None
    if args.enable_shortcut:
        # Prefer a dedicated command for the chat UI (not the 'open chat log' command).
        chat_cmd = getattr(config, "chat_ui_command", None) or None
        combo = getattr(config, "chat_shortcut_combo", None) or os.environ.get(
            "JARVIS_CHAT_SHORTCUT_COMBO", "ctrl+shift+j"
        )
        chat_shortcut = ChatShortcut(chat_command=chat_cmd, shortcut_combo=combo)
        if chat_shortcut.start():
            print(f"Atalho global ativado: {combo} para abrir a Chat UI")
        else:
            reason = getattr(chat_shortcut, "last_error", None)
            if reason == "pynput_missing":
                print("Aviso: atalho global indisponível (pynput ausente).")
                print(
                    "Dica: instale com `pip install pynput` ou configure um atalho do sistema."
                )
            elif reason == "wayland_no_x11":
                print("Aviso: atalho global indisponível (Wayland sem X11).")
                print(
                    "Dica: configure um atalho do sistema para executar: python -m jarvis.entrada.chat_ui"
                )
            else:
                print("Aviso: atalho global indisponível (falha ao iniciar listener).")
                print(
                    "Dica: configure um atalho do sistema para executar: python -m jarvis.entrada.chat_ui"
                )
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
        sleep_s = max(0.0, float(args.voice_loop_sleep))
        max_iter = args.voice_loop_max_iter
        if max_iter is None:
            env_max_iter = os.environ.get("JARVIS_VOICE_LOOP_MAX_ITER")
            if env_max_iter:
                try:
                    max_iter = max(0, int(env_max_iter))
                except ValueError:
                    max_iter = 0
        if max_iter is None:
            max_iter = 0
        iter_count = 0
        try:
            while True:
                if stop_requested(config.stop_file_path):
                    print("Kill switch ativo. Saindo do loop.")
                    break
                drain_chat_inbox()
                if not _ensure_stt_ready(config):
                    print("Voz indisponivel durante o loop. Encerrando.")
                    break
                orchestrator.transcribe_and_handle()
                iter_count += 1
                if max_iter and iter_count >= max_iter:
                    print("Voice loop: limite de iteracoes atingido.")
                    break
                time.sleep(sleep_s)
        except KeyboardInterrupt:
            pass
        finally:
            if chat_shortcut:
                chat_shortcut.stop()
        return 0

    if args.gui_panel:
        from .gui_panel import JarvisPanel

        panel = JarvisPanel(
            orchestrator,
            chat_shortcut,
            followup_poll_ms=args.gui_followup_poll_ms,
        )
        panel.run()
        return 0

    if args.loop or not args.text:
        print("Jarvis MVP - type commands or 'exit' to quit")
        try:
            from jarvis.cerebro.utils import normalize_text

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
