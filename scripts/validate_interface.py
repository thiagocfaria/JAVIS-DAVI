#!/usr/bin/env python3
"""
Script unificado de validação do sistema de Interface para produção.

Executa todos os testes necessários para validar o sistema:
1. Testes pytest (unitários e de integração)
2. Benchmarks com gravações reais (WER, latência, endpointing)
3. Verificação de dependências (preflight)
4. Relatório consolidado

Uso:
    python scripts/validate_interface.py [--quick] [--full] [--json-out FILE] [--md-out FILE]

Opções:
    --quick     Executa apenas testes rápidos (sem gravações)
    --full      Executa todos os testes incluindo os lentos
    --json-out  Salva relatório em JSON
    --md-out    Salva relatório em Markdown
    --no-pytest Pula testes pytest
    --no-wer    Pula benchmark de WER
    --no-bench  Pula benchmarks de latência
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class TestResult:
    """Resultado de um teste."""
    name: str
    passed: bool
    duration_s: float
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ValidationReport:
    """Relatório de validação."""
    timestamp: str
    duration_s: float
    pytest_results: TestResult | None = None
    wer_results: TestResult | None = None
    transcribe_results: TestResult | None = None
    latency_results: TestResult | None = None
    preflight_results: TestResult | None = None

    @property
    def all_passed(self) -> bool:
        results = [
            self.pytest_results,
            self.wer_results,
            self.transcribe_results,
            self.latency_results,
            self.preflight_results,
        ]
        return all(r is None or r.passed for r in results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "duration_s": self.duration_s,
            "all_passed": self.all_passed,
            "pytest": self.pytest_results.__dict__ if self.pytest_results else None,
            "wer": self.wer_results.__dict__ if self.wer_results else None,
            "transcribe": self.transcribe_results.__dict__ if self.transcribe_results else None,
            "latency": self.latency_results.__dict__ if self.latency_results else None,
            "preflight": self.preflight_results.__dict__ if self.preflight_results else None,
        }

    def to_markdown(self) -> str:
        lines = [
            "# Relatório de Validação do Sistema de Interface",
            "",
            f"**Data:** {self.timestamp}",
            f"**Duração total:** {self.duration_s:.1f}s",
            f"**Status:** {'✅ PASSOU' if self.all_passed else '❌ FALHOU'}",
            "",
            "## Resultados",
            "",
            "| Teste | Status | Duração | Detalhes |",
            "| --- | --- | --- | --- |",
        ]

        for name, result in [
            ("pytest (unitários)", self.pytest_results),
            ("WER (precisão STT)", self.wer_results),
            ("Transcrição", self.transcribe_results),
            ("Latência", self.latency_results),
            ("Preflight", self.preflight_results),
        ]:
            if result is None:
                lines.append(f"| {name} | ⏭️ Pulado | - | - |")
            elif result.passed:
                details = result.details.get("summary", "-")
                lines.append(f"| {name} | ✅ Passou | {result.duration_s:.1f}s | {details} |")
            else:
                error = result.error or result.details.get("error", "Erro desconhecido")
                lines.append(f"| {name} | ❌ Falhou | {result.duration_s:.1f}s | {error[:50]}... |")

        if self.wer_results and self.wer_results.passed:
            wer = self.wer_results.details.get("wer_global")
            if wer is not None:
                lines.extend([
                    "",
                    "## Métricas de STT",
                    "",
                    f"- **WER global:** {wer:.3f}",
                ])

        if self.latency_results and self.latency_results.passed:
            p50 = self.latency_results.details.get("eos_to_first_audio_ms_p50")
            p95 = self.latency_results.details.get("eos_to_first_audio_ms_p95")
            if p50 is not None and p95 is not None:
                lines.extend([
                    "",
                    "## Métricas de Latência",
                    "",
                    f"- **EoS → primeiro áudio (p50):** {p50:.0f}ms",
                    f"- **EoS → primeiro áudio (p95):** {p95:.0f}ms",
                ])

        return "\n".join(lines)


def run_pytest(quick: bool = False) -> TestResult:
    """Executa testes pytest."""
    print("\n" + "=" * 60)
    print("Executando testes pytest...")
    print("=" * 60)

    start = time.perf_counter()

    cmd = [
        sys.executable, "-m", "pytest",
        "testes/",
        "-v",
        "--tb=short",
    ]

    if quick:
        # Exclui testes lentos
        cmd.extend(["-m", "not slow"])

    env = {**os.environ, "PYTHONPATH": "."}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )
        duration = time.perf_counter() - start
        passed = result.returncode == 0

        # Extrair contagem de testes
        summary = ""
        for line in result.stdout.splitlines():
            if "passed" in line or "failed" in line or "error" in line:
                summary = line.strip()
                break

        return TestResult(
            name="pytest",
            passed=passed,
            duration_s=duration,
            details={"summary": summary, "returncode": result.returncode},
            error=result.stderr[:500] if not passed else None,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            name="pytest",
            passed=False,
            duration_s=time.perf_counter() - start,
            error="Timeout após 10 minutos",
        )
    except Exception as e:
        return TestResult(
            name="pytest",
            passed=False,
            duration_s=time.perf_counter() - start,
            error=str(e),
        )


def run_wer_benchmark() -> TestResult:
    """Executa benchmark de WER."""
    print("\n" + "=" * 60)
    print("Executando benchmark de WER...")
    print("=" * 60)

    start = time.perf_counter()

    cmd = [
        sys.executable,
        "scripts/voice_wer_benchmark.py",
        "--audio-dir", "Documentos/DOC_INTERFACE/test_audio",
    ]

    env = {**os.environ, "PYTHONPATH": "."}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        duration = time.perf_counter() - start

        # Parsear WER global da saída
        wer_global = None
        for line in result.stdout.splitlines():
            if "WER global:" in line:
                try:
                    wer_global = float(line.split(":")[-1].strip())
                except ValueError:
                    pass

        # WER < 0.3 é considerado bom
        passed = result.returncode == 0 and (wer_global is None or wer_global < 0.3)

        return TestResult(
            name="wer_benchmark",
            passed=passed,
            duration_s=duration,
            details={
                "wer_global": wer_global,
                "summary": f"WER={wer_global:.3f}" if wer_global is not None else "N/A",
            },
            error=result.stderr[:500] if not passed else None,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            name="wer_benchmark",
            passed=False,
            duration_s=time.perf_counter() - start,
            error="Timeout após 5 minutos",
        )
    except Exception as e:
        return TestResult(
            name="wer_benchmark",
            passed=False,
            duration_s=time.perf_counter() - start,
            error=str(e),
        )


def run_transcribe_check() -> TestResult:
    """Executa verificação de transcrição."""
    print("\n" + "=" * 60)
    print("Executando verificação de transcrição...")
    print("=" * 60)

    start = time.perf_counter()

    cmd = [
        sys.executable,
        "scripts/voice_transcribe_check.py",
        "--audio-dir", "Documentos/DOC_INTERFACE/test_audio",
    ]

    env = {**os.environ, "PYTHONPATH": "."}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        duration = time.perf_counter() - start

        # Parsear resultado
        ok_count = 0
        total_count = 0
        for line in result.stdout.splitlines():
            if "Transcrições corretas:" in line:
                parts = line.split(":")[-1].strip().split("/")
                if len(parts) == 2:
                    ok_count = int(parts[0])
                    total_count = int(parts[1])

        # Pelo menos 70% de acerto
        passed = result.returncode == 0 and (total_count == 0 or ok_count / total_count >= 0.7)

        return TestResult(
            name="transcribe_check",
            passed=passed,
            duration_s=duration,
            details={
                "ok": ok_count,
                "total": total_count,
                "summary": f"{ok_count}/{total_count} corretas",
            },
            error=result.stderr[:500] if not passed else None,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            name="transcribe_check",
            passed=False,
            duration_s=time.perf_counter() - start,
            error="Timeout após 5 minutos",
        )
    except Exception as e:
        return TestResult(
            name="transcribe_check",
            passed=False,
            duration_s=time.perf_counter() - start,
            error=str(e),
        )


def run_latency_benchmark() -> TestResult:
    """Executa benchmark de latência (eos_to_first_audio)."""
    print("\n" + "=" * 60)
    print("Executando benchmark de latência...")
    print("=" * 60)

    start = time.perf_counter()

    audio_path = "Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav"
    if not Path(audio_path).exists():
        audio_path = "Documentos/DOC_INTERFACE/test_audio/oi_jarvis_clean.wav"

    cmd = [
        sys.executable,
        "scripts/bench_interface.py",
        "eos_to_first_audio",
        "--audio", audio_path,
        "--text", "ok",
        "--repeat", "5",
        "--resample",
    ]

    env = {**os.environ, "PYTHONPATH": "."}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        duration = time.perf_counter() - start

        # Parsear JSON da saída
        p50 = None
        p95 = None
        try:
            # Última linha deve ser JSON
            for line in reversed(result.stdout.splitlines()):
                if line.strip().startswith("{"):
                    data = json.loads(line)
                    p50 = data.get("eos_to_first_audio_ms_p50")
                    p95 = data.get("eos_to_first_audio_ms_p95")
                    break
        except (json.JSONDecodeError, ValueError):
            pass

        # p95 < 3000ms é considerado aceitável
        passed = result.returncode == 0 and (p95 is None or p95 < 3000)

        return TestResult(
            name="latency_benchmark",
            passed=passed,
            duration_s=duration,
            details={
                "eos_to_first_audio_ms_p50": p50,
                "eos_to_first_audio_ms_p95": p95,
                "summary": f"p50={p50:.0f}ms p95={p95:.0f}ms" if p50 and p95 else "N/A",
            },
            error=result.stderr[:500] if not passed else None,
        )
    except subprocess.TimeoutExpired:
        return TestResult(
            name="latency_benchmark",
            passed=False,
            duration_s=time.perf_counter() - start,
            error="Timeout após 5 minutos",
        )
    except Exception as e:
        return TestResult(
            name="latency_benchmark",
            passed=False,
            duration_s=time.perf_counter() - start,
            error=str(e),
        )


def run_preflight() -> TestResult:
    """Verifica dependências via preflight."""
    print("\n" + "=" * 60)
    print("Verificando dependências (preflight)...")
    print("=" * 60)

    start = time.perf_counter()

    try:
        from jarvis.cerebro.config import load_config
        from jarvis.interface.entrada.preflight import run_preflight

        config = load_config()
        report = run_preflight(config, profile="voice")
        issues = [c for c in report.checks if c.status == "FAIL"]
        duration = time.perf_counter() - start

        passed = len(issues) == 0

        return TestResult(
            name="preflight",
            passed=passed,
            duration_s=duration,
            details={
                "issues": issues,
                "summary": f"{len(issues)} problemas" if issues else "OK",
            },
            error="\n".join(f"{c.name}: {c.detail}" for c in issues) if issues else None,
        )
    except ImportError as e:
        return TestResult(
            name="preflight",
            passed=False,
            duration_s=time.perf_counter() - start,
            error=f"Import error: {e}",
        )
    except Exception as e:
        return TestResult(
            name="preflight",
            passed=False,
            duration_s=time.perf_counter() - start,
            error=str(e),
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valida o sistema de Interface para produção"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Executa apenas testes rápidos",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Executa todos os testes incluindo lentos",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Salva relatório em JSON",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        help="Salva relatório em Markdown",
    )
    parser.add_argument(
        "--no-pytest",
        action="store_true",
        help="Pula testes pytest",
    )
    parser.add_argument(
        "--no-wer",
        action="store_true",
        help="Pula benchmark de WER",
    )
    parser.add_argument(
        "--no-bench",
        action="store_true",
        help="Pula benchmarks de latência",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("VALIDAÇÃO DO SISTEMA DE INTERFACE JARVIS")
    print("=" * 60)
    print(f"Data: {datetime.now().isoformat()}")
    print(f"Modo: {'quick' if args.quick else 'full' if args.full else 'normal'}")
    print()

    start_total = time.perf_counter()
    report = ValidationReport(
        timestamp=datetime.now().isoformat(),
        duration_s=0,
    )

    # 1. Pytest
    if not args.no_pytest:
        report.pytest_results = run_pytest(quick=args.quick)
        print(f"\n→ pytest: {'✅ PASSOU' if report.pytest_results.passed else '❌ FALHOU'}")

    # 2. Preflight
    report.preflight_results = run_preflight()
    print(f"→ preflight: {'✅ PASSOU' if report.preflight_results.passed else '❌ FALHOU'}")

    # 3. Benchmarks com gravações (se não for quick)
    if not args.quick:
        if not args.no_wer:
            report.wer_results = run_wer_benchmark()
            print(f"→ WER: {'✅ PASSOU' if report.wer_results.passed else '❌ FALHOU'}")

            report.transcribe_results = run_transcribe_check()
            print(f"→ transcrição: {'✅ PASSOU' if report.transcribe_results.passed else '❌ FALHOU'}")

        if not args.no_bench:
            report.latency_results = run_latency_benchmark()
            print(f"→ latência: {'✅ PASSOU' if report.latency_results.passed else '❌ FALHOU'}")

    report.duration_s = time.perf_counter() - start_total

    # Resumo final
    print("\n" + "=" * 60)
    print("RESULTADO FINAL")
    print("=" * 60)
    print(f"Status: {'✅ VALIDAÇÃO PASSOU' if report.all_passed else '❌ VALIDAÇÃO FALHOU'}")
    print(f"Duração total: {report.duration_s:.1f}s")

    # Salvar relatórios
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\nRelatório JSON salvo em: {args.json_out}")

    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(report.to_markdown(), encoding="utf-8")
        print(f"Relatório Markdown salvo em: {args.md_out}")

    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
