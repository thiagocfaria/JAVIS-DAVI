from __future__ import annotations

import argparse
import os
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path


def _tail_lines(path: Path, limit: int) -> str:
    if not path.exists():
        return ""
    try:
        data = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    lines = data.splitlines()
    return "\n".join(lines[-limit:])


def _format_log_with_timestamps(content: str) -> str:
    """Format log content with timestamps if missing."""
    if not content:
        return ""

    lines = content.splitlines()
    formatted = []

    for line in lines:
        # Check if line already has timestamp
        if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line):
            formatted.append(line)
        else:
            # Add timestamp to line without one
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted.append(f"[{timestamp}] {line}")

    return "\n".join(formatted)


def main() -> int:
    parser = argparse.ArgumentParser(description="Jarvis chat local")
    parser.add_argument("--log-path", help="path do chat log")
    parser.add_argument("--inbox-path", help="path do inbox de comandos")
    parser.add_argument("--tail", type=int, default=200, help="linhas do log para mostrar")
    parser.add_argument("--poll-ms", type=int, default=800, help="intervalo de atualizacao")
    args = parser.parse_args()

    log_path = Path(
        args.log_path
        or os.environ.get("JARVIS_CHAT_LOG_PATH", str(Path.home() / ".jarvis" / "chat.log"))
    )
    inbox_path = Path(
        args.inbox_path
        or os.environ.get("JARVIS_CHAT_INBOX_PATH", str(Path.home() / ".jarvis" / "chat_inbox.txt"))
    )

    root = tk.Tk()
    root.title("Jarvis - Chat local")
    root.geometry("720x480")

    text = tk.Text(root, wrap="word", state="disabled")
    text.pack(fill="both", expand=True, padx=10, pady=(10, 6))

    input_frame = tk.Frame(root)
    input_frame.pack(fill="x", padx=10, pady=(0, 10))

    entry = tk.Entry(input_frame)
    entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

    # Status label for feedback
    status_label = tk.Label(input_frame, text="", fg="green", font=("Arial", 8))
    status_label.pack(side="right", padx=(0, 6))

    def send_message() -> None:
        msg = entry.get().strip()
        if not msg:
            return
        inbox_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with inbox_path.open("a", encoding="utf-8") as handle:
                handle.write(f"{msg}\n")
            entry.delete(0, "end")
            # Visual feedback
            status_label.config(text="✓ Enviado", fg="green")
            root.after(1000, lambda: status_label.config(text="", fg="green"))
        except Exception:
            status_label.config(text="✗ Erro", fg="red")
            root.after(2000, lambda: status_label.config(text="", fg="green"))

    send_btn = tk.Button(input_frame, text="Enviar", command=send_message)
    send_btn.pack(side="right")

    def refresh() -> None:
        content = _tail_lines(log_path, args.tail)
        # Format with timestamps if needed
        formatted_content = _format_log_with_timestamps(content)
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("end", formatted_content)
        text.configure(state="disabled")
        text.see("end")
        root.after(args.poll_ms, refresh)

    entry.bind("<Return>", lambda _: send_message())
    refresh()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
