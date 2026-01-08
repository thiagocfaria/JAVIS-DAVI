#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def _now_date() -> str:
    return time.strftime("%Y-%m-%d")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"history": []}
    data = _load_json(path)
    if not isinstance(data, dict) or "history" not in data:
        raise ValueError("formato invalido de bench_history.json")
    if not isinstance(data["history"], list):
        raise ValueError("campo history deve ser uma lista")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Anexa um registro ao bench_history.json"
    )
    parser.add_argument(
        "--record",
        required=True,
        help="arquivo JSON com um registro (baseline/commands/results)",
    )
    parser.add_argument(
        "--history",
        default="Documentos/DOC_INTERFACE/bench_history.json",
        help="arquivo de historico (default: Documentos/DOC_INTERFACE/bench_history.json)",
    )
    parser.add_argument(
        "--record-id",
        default="",
        help="id do registro (se vazio, usa record_id do arquivo ou gera)",
    )
    parser.add_argument(
        "--created-at",
        default="",
        help="data do registro (YYYY-MM-DD). Se vazio, usa do arquivo ou data atual",
    )
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="permite record_id duplicado",
    )
    args = parser.parse_args()

    record_path = Path(args.record)
    history_path = Path(args.history)

    if not record_path.exists():
        raise SystemExit(f"arquivo de record nao encontrado: {record_path}")

    record = _load_json(record_path)
    if not isinstance(record, dict):
        raise SystemExit("record deve ser um objeto JSON")

    record_id = args.record_id or str(record.get("record_id") or "").strip()
    if not record_id:
        record_id = f"record_{int(time.time())}"
    record["record_id"] = record_id

    created_at = args.created_at or str(record.get("created_at") or "").strip()
    if not created_at:
        created_at = _now_date()
    record["created_at"] = created_at

    history = _ensure_history(history_path)
    if not args.allow_duplicate:
        for item in history["history"]:
            if isinstance(item, dict) and item.get("record_id") == record_id:
                raise SystemExit(f"record_id duplicado: {record_id}")

    history["history"].append(record)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(history, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    print(f"ok: anexado {record_id} em {history_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
