from __future__ import annotations

import argparse
import json
import os
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path

from ..comunicacao.chat_inbox import append_line


def _tail_lines(path: Path, limit: int) -> str:
    if limit <= 0:
        return ""
    if not path.exists():
        return ""
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            pos = handle.tell()
            chunks: list[bytes] = []
            lines = 0
            while pos > 0 and lines <= limit:
                read_size = min(4096, pos)
                pos -= read_size
                handle.seek(pos)
                chunk = handle.read(read_size)
                chunks.append(chunk)
                lines += chunk.count(b"\n")
        data = b"".join(reversed(chunks))
    except Exception:
        return ""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    return "\n".join(lines[-limit:])


def _format_log_with_timestamps(content: str) -> str:
    """Format log content with timestamps if missing."""
    if not content:
        return ""

    lines = content.splitlines()
    formatted = []

    for line in lines:
        if not line:
            continue
        parsed = None
        try:
            parsed = json.loads(line)
        except Exception:
            parsed = None
        if isinstance(parsed, dict) and "message" in parsed:
            ts = str(parsed.get("ts") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            role = str(parsed.get("role") or "")
            message = str(parsed.get("message") or "")
            rendered = f"[{ts}] {role}: {message}".strip()
            meta = parsed.get("meta")
            if isinstance(meta, dict) and meta:
                rendered += " | meta=" + json.dumps(meta, ensure_ascii=True)
            formatted.append(rendered)
            continue
        # Check if line already has timestamp
        if re.match(r"^\[?\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", line):
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
        try:
            ok = append_line(inbox_path, msg)
            if not ok:
                raise RuntimeError("append_line failed")
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
