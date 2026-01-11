#!/usr/bin/env python3
"""
Gera relatório HTML/JSON dos resultados de benchmarks.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from string import Template
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def generate_html_report(results: dict[str, Any], output_path: Path) -> None:
    """Gera relatório HTML."""
    html = Template("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Benchmarks - Jarvis</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .section {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #4CAF50;
            color: white;
        }
        tr:hover {
            background: #f9f9f9;
        }
        .metric {
            font-weight: bold;
            color: #2196F3;
        }
        .warning {
            color: #FF9800;
        }
        .error {
            color: #F44336;
        }
        .success {
            color: #4CAF50;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <h1>📊 Relatório de Benchmarks - Jarvis MVP</h1>
    <div class="timestamp">Gerado em: $timestamp</div>
    
    <div class="section">
        <h2>📈 Métricas de Performance</h2>
        <table>
            <thead>
                <tr>
                    <th>Métrica</th>
                    <th>Latência (ms)</th>
                    <th>CPU (%)</th>
                    <th>Memória (MB)</th>
                </tr>
            </thead>
            <tbody>
$metrics_rows
            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>⚙️ Informações do Sistema</h2>
        <pre>$system_info</pre>
    </div>
    
    <div class="section">
        <h2>📝 Notas</h2>
        <p>Este relatório foi gerado automaticamente pelos scripts de benchmark do Jarvis.</p>
        <p>Para comparar com baseline, use: <code>scripts/compare_baseline.py &lt;arquivo.json&gt;</code></p>
    </div>
</body>
</html>""")

    # Gerar linhas da tabela
    metrics_rows = []
    if "latency" in results:
        for key, value in results["latency"].items():
            cpu_val = results.get("cpu", {}).get(key, "N/A")
            mem_val = results.get("memory", {}).get(key, "N/A")
            metrics_rows.append(
                f"                <tr>"
                f"<td class='metric'>{key}</td>"
                f"<td>{value:.2f}</td>"
                f"<td>{cpu_val if isinstance(cpu_val, (int, float)) else 'N/A'}</td>"
                f"<td>{mem_val if isinstance(mem_val, (int, float)) else 'N/A'}</td>"
                f"</tr>"
            )

    system_info = json.dumps(results.get("system", {}), indent=2, ensure_ascii=False)

    html_content = html.substitute(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        metrics_rows="\n".join(metrics_rows) if metrics_rows else "<tr><td colspan='4'>Sem dados</td></tr>",
        system_info=system_info,
    )

    output_path.write_text(html_content, encoding="utf-8")
    print(f"✓ Relatório HTML gerado: {output_path}")


def generate_json_report(results: dict[str, Any], output_path: Path) -> None:
    """Gera relatório JSON."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"✓ Relatório JSON gerado: {output_path}")


def main() -> None:
    """Função principal."""
    if len(sys.argv) < 2:
        print("Uso: generate_report.py <arquivo_resultados.json> [--html] [--json]")
        sys.exit(1)

    results_path = Path(sys.argv[1])
    if not results_path.exists():
        print(f"ERRO: Arquivo não encontrado: {results_path}")
        sys.exit(1)

    with open(results_path, encoding="utf-8") as f:
        results = json.load(f)

    output_dir = results_path.parent
    base_name = results_path.stem

    generate_html = "--html" in sys.argv or len(sys.argv) == 2
    generate_json = "--json" in sys.argv or len(sys.argv) == 2

    if generate_html:
        html_path = output_dir / f"{base_name}_report.html"
        generate_html_report(results, html_path)

    if generate_json:
        json_path = output_dir / f"{base_name}_report.json"
        generate_json_report(results, json_path)


if __name__ == "__main__":
    main()











