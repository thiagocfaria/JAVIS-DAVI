#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def is_probably_text(path: Path, sample_size: int = 8192) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(sample_size)
        if b"\x00" in chunk:
            return False
        return True
    except OSError:
        return False


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def convert_svg_to_pdf(svg_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if shutil.which("rsvg-convert"):
        subprocess.run(
            ["rsvg-convert", "-f", "pdf", "-o", str(pdf_path), str(svg_path)],
            check=True,
        )
        return
    if shutil.which("inkscape"):
        subprocess.run(
            [
                "inkscape",
                str(svg_path),
                "--export-type=pdf",
                "--export-filename",
                str(pdf_path),
            ],
            check=True,
        )
        return
    if shutil.which("convert"):
        subprocess.run(["convert", str(svg_path), str(pdf_path)], check=True)
        return

    try:
        import cairosvg  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Nenhum conversor SVG->PDF encontrado. Instale cairosvg ou librsvg/inkscape."
        ) from exc

    cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))


def add_if_exists(path: Path, files: list[Path], missing: list[Path]) -> None:
    if path.exists():
        files.append(path)
    else:
        missing.append(path)


def collect_interface_files(root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    missing: list[Path] = []
    skipped_binary: list[Path] = []

    code_files: list[Path] = []
    interface_dir = root / "jarvis" / "interface"
    if interface_dir.exists():
        code_files.extend(sorted(interface_dir.rglob("*.py")))
    else:
        missing.append(interface_dir)

    comunicacao_dir = root / "jarvis" / "comunicacao"
    add_if_exists(comunicacao_dir / "chat_inbox.py", code_files, missing)
    add_if_exists(comunicacao_dir / "chat_log.py", code_files, missing)
    add_if_exists(comunicacao_dir / "protocolo.py", code_files, missing)

    # Camada de compat/adapters antiga (jarvis/voz)
    voz_dir = root / "jarvis" / "voz"
    if voz_dir.exists():
        code_files.extend(sorted(voz_dir.glob("*.py")))
        adapters_dir = voz_dir / "adapters"
        if adapters_dir.exists():
            code_files.extend(sorted(adapters_dir.glob("*.py")))
        else:
            missing.append(adapters_dir)
    else:
        missing.append(voz_dir)

    rust_files: list[Path] = []
    rust_dir = root / "rust" / "jarvis_audio"
    if rust_dir.exists():
        add_if_exists(rust_dir / "Cargo.toml", rust_files, missing)
        add_if_exists(rust_dir / "Cargo.lock", rust_files, missing)
        src_dir = rust_dir / "src"
        if src_dir.exists():
            rust_files.extend(sorted(src_dir.rglob("*.rs")))
        else:
            missing.append(src_dir)
    else:
        missing.append(rust_dir)

    test_files: list[Path] = []
    tests_dir = root / "testes"
    if tests_dir.exists():
        test_files.extend(sorted(tests_dir.glob("test_preflight_*.py")))
        test_names = [
            "test_audio_utils.py",
            "test_chat_inbox.py",
            "test_chat_log.py",
            "test_chat_ui_interface.py",
            "test_gui_panel_interface.py",
            "test_shortcut_interface.py",
            "test_app_voice_interface.py",
            "test_stt_flow.py",
            "test_stt_metrics.py",
            "teste_stt_gap_latency.py",
            "test_stt_whisper_kwargs.py",
            "test_stt_streaming_controls.py",
            "test_stt_partials.py",
            "test_stt_silero_deactivity.py",
            "test_stt_rust_trim.py",
            "test_stt_trim_guard.py",
            "test_stt_speech_fallback.py",
            "test_stt_realtimestt_backend.py",
            "test_stt_filters.py",
            "test_stt_capture_config.py",
            "test_stt_vad_env.py",
            "test_audio_resample.py",
            "test_vad_pre_roll.py",
            "test_vad_metrics.py",
            "test_vad_streaming_interface.py",
            "test_vad_strategy.py",
            "test_aec_interface.py",
            "test_followup_mode.py",
            "test_voice_adapters.py",
            "test_speaker_verify_interface.py",
            "test_voice_max_seconds_env.py",
            "test_tts_interface.py",
            "test_bench_interface.py",
            "test_protocolo_validar.py",
        ]
        for name in test_names:
            add_if_exists(tests_dir / name, test_files, missing)
    else:
        missing.append(tests_dir)

    script_files: list[Path] = []
    scripts_dir = root / "scripts"
    add_if_exists(scripts_dir / "bench_interface.py", script_files, missing)
    add_if_exists(scripts_dir / "auto_voice_bench.py", script_files, missing)

    doc_files: list[Path] = []
    docs_dir = root / "Documentos" / "DOC_INTERFACE"
    if docs_dir.exists():
        for path in sorted(docs_dir.rglob("*")):
            if not path.is_file():
                continue
            # Ignorar arquivos de histórico massivo de benchmark arquivado
            if "bench_audio" in path.parts and "archive" in path.parts:
                continue
            if is_probably_text(path):
                doc_files.append(path)
            else:
                skipped_binary.append(path)
    else:
        missing.append(docs_dir)

    all_files = code_files + rust_files + doc_files + test_files + script_files
    return all_files, missing, skipped_binary


def write_bundle(
    root: Path,
    output_path: Path,
    files: list[Path],
    missing: list[Path],
    skipped_binary: list[Path],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def rel(path: Path) -> str:
        try:
            return str(path.relative_to(root))
        except ValueError:
            return str(path)

    unique_files = []
    seen = set()
    for path in files:
        key = rel(path)
        if key in seen:
            continue
        seen.add(key)
        unique_files.append(path)

    # Caminhos para documentos especiais
    deps_doc = root / "Documentos" / "DOC_INTERFACE" / "DEPENDENCIAS_INTERFACE.md"
    testes_doc = (
        root / "Documentos" / "DOC_INTERFACE" / "testes" / "TESTES_INTERFACE.md"
    )
    testes_realizados_doc = root / "Documentos" / "DOC_INTERFACE" / "TESTES_REALISADOS_INTERFACE.MD"
    repos_doc = root / "Documentos" / "DOC_INTERFACE" / "repositorios_interface.md"
    evolucao_doc = root / "Documentos" / "DOC_INTERFACE" / "EVOLUCAO_PERFOMACE.MD"
    plano_doc = root / "Documentos" / "DOC_INTERFACE" / "PLANO_OURO_INTERFACE.md"

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("=" * 80 + "\n")
        handle.write("NOTEBOOKLM BUNDLE: INTERFACE ENTRADA/SAIDA\n")
        handle.write("Documento completo para analise de competencia atual\n")
        handle.write("=" * 80 + "\n\n")

        # Indice rapido das secoes
        handle.write("Indice:\n")
        handle.write("1) Arquivos incluidos (lista)\n")
        handle.write("2) Dependencias\n")
        handle.write("3) Testes (suite + registro)\n")
        handle.write("4) Repositorios\n")
        handle.write("5) Historico de performance\n")
        handle.write("6) Codigos fonte e documentacao completa\n\n")

        # Seção 1: Lista de arquivos incluídos
        handle.write("=" * 80 + "\n")
        handle.write("SECAO 1: ARQUIVOS INCLUIDOS\n")
        handle.write("=" * 80 + "\n\n")
        handle.write("Incluidos:\n")
        for path in unique_files:
            handle.write(f"- {rel(path)}\n")

        if missing:
            handle.write("\nAusentes (nao encontrados):\n")
            for path in missing:
                handle.write(f"- {rel(path)}\n")

        if skipped_binary:
            handle.write("\nIgnorados (binarios):\n")
            for path in skipped_binary:
                handle.write(f"- {rel(path)}\n")

        # Seção 2: Dependências
        handle.write("\n\n" + "=" * 80 + "\n")
        handle.write("SECAO 2: DEPENDENCIAS DA INTERFACE\n")
        handle.write("=" * 80 + "\n\n")
        if deps_doc.exists():
            handle.write(read_text(deps_doc))
        else:
            handle.write("AVISO: Documento de dependencias nao encontrado.\n")
        handle.write("\n")

        # Seção 3: Testes e Resultados
        handle.write("\n" + "=" * 80 + "\n")
        handle.write("SECAO 3: TESTES DA INTERFACE\n")
        handle.write("=" * 80 + "\n\n")
        if testes_doc.exists():
            handle.write("--- TESTES AUTOMATIZADOS ---\n\n")
            handle.write(read_text(testes_doc))
            handle.write("\n")
        else:
            handle.write("AVISO: Documento de testes nao encontrado.\n")

        handle.write("\n--- TESTES REALIZADOS (REGISTRO HISTORICO) ---\n\n")
        if testes_realizados_doc.exists():
            handle.write(read_text(testes_realizados_doc))
        else:
            handle.write("Sem registro dedicado no momento.\n")
        handle.write("\n")

        # Seção 4: Repositórios
        handle.write("\n" + "=" * 80 + "\n")
        handle.write("SECAO 4: REPOSITORIOS DA INTERFACE\n")
        handle.write("=" * 80 + "\n\n")
        if repos_doc.exists():
            repos_content = read_text(repos_doc)
            handle.write(repos_content)

            # Adicionar status de clonagem
            handle.write("\n\n--- STATUS DE CLONAGEM DOS REPOSITORIOS ---\n\n")
            repos_info = [
                ("vercel-ai-chatbot", "jarvis/REPOSITORIOS_CLONAR/vercel-ai-chatbot"),
                ("livekit-agents", "jarvis/REPOSITORIOS_CLONAR/livekit-agents"),
                ("realtimestt", "jarvis/REPOSITORIOS_CLONAR/realtimestt"),
                ("realtimetts", "jarvis/REPOSITORIOS_CLONAR/realtimetts"),
                ("realtimevoicechat", "jarvis/REPOSITORIOS_CLONAR/realtimevoicechat"),
                ("speechbrain", "jarvis/REPOSITORIOS_CLONAR/speechbrain"),
                (
                    "speechbrain-emotion-model",
                    "jarvis/REPOSITORIOS_CLONAR/speechbrain-emotion-model",
                ),
                ("opensmile", "jarvis/REPOSITORIOS_CLONAR/opensmile"),
                ("tauri", "jarvis/REPOSITORIOS_CLONAR/tauri"),
            ]

            handle.write("Repositorios JA CLONADOS:\n")
            for repo_name, repo_path in repos_info:
                repo_full_path = root / repo_path
                if repo_full_path.exists() and any(repo_full_path.iterdir()):
                    handle.write(f"- [x] {repo_name}: {repo_path}\n")
                else:
                    handle.write(
                        f"- [ ] {repo_name}: {repo_path} (diretorio vazio ou nao existe)\n"
                    )

            handle.write("\nRepositorios NAO CLONADOS (desejados):\n")
            for repo_name, repo_path in repos_info:
                repo_full_path = root / repo_path
                if not repo_full_path.exists() or not any(repo_full_path.iterdir()):
                    handle.write(f"- [ ] {repo_name}: {repo_path}\n")
        else:
            handle.write("AVISO: Documento de repositorios nao encontrado.\n")
        handle.write("\n")

        # Seção 5: Histórico de Benchmarks
        handle.write("\n" + "=" * 80 + "\n")
        handle.write("SECAO 5: HISTORICO DE PERFORMANCE\n")
        handle.write("=" * 80 + "\n\n")
        if evolucao_doc.exists():
            handle.write("--- EVOLUCAO_PERFOMACE.MD ---\n\n")
            handle.write(read_text(evolucao_doc))
            handle.write("\n")
        else:
            handle.write("AVISO: Documento de evolucao de performance nao encontrado.\n\n")
        if plano_doc.exists():
            handle.write("--- PLANO_OURO_INTERFACE.md (estado/metricas) ---\n\n")
            handle.write(read_text(plano_doc))
            handle.write("\n")
        handle.write("\n")

        # Seção 6: Códigos Fonte e Documentação
        handle.write("\n" + "=" * 80 + "\n")
        handle.write("SECAO 6: CODIGOS FONTE E DOCUMENTACAO COMPLETA\n")
        handle.write("=" * 80 + "\n\n")
        handle.write(
            "Resumo rapido: STT padrão whisper.cpp tiny com warmup; TTS Piper in-proc com warmup; "
            "latencia EoS->1o audio p95 ~1077ms; barge-in ainda best-effort (~1s). "
            "Backend streaming RealtimeSTT é opcional; wake word por audio é opcional "
            "(Porcupine/OpenWakeWord). Profiles e dependencias detalhados nos docs.\n\n"
            "Nota: Seção 6 é um dump integral dos arquivos listados na Seção 1 "
            "para facilitar ingestão pela IA. Use o índice da Seção 1 para localizar caminhos.\n\n"
        )
        for path in unique_files:
            content = read_text(path)
            handle.write(f"==== FILE: {rel(path)} ====\n")
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
            handle.write("==== END FILE ====\n\n")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    default_out_dir = root / "NOTBOOKLM"
    default_diagram = root / "Documentos" / "DOC_INTERFACE" / "DIAGRAMA_INTERFACE.svg"

    parser = argparse.ArgumentParser(
        description="Gera bundle do NotebookLM (PDF do diagrama + TXT da interface)."
    )
    parser.add_argument("--out-dir", default=str(default_out_dir))
    parser.add_argument("--diagram", default=str(default_diagram))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    diagram_path = Path(args.diagram)
    pdf_path = out_dir / "DIAGRAMA_ARQUITETURA.pdf"
    txt_path = out_dir / "interface_entrada_saida.txt"

    if not diagram_path.exists():
        print(f"Aviso: Diagrama nao encontrado: {diagram_path}")
    else:
        try:
            convert_svg_to_pdf(diagram_path, pdf_path)
            print(f"PDF gerado: {pdf_path}")
        except RuntimeError as e:
            print(f"Aviso: Nao foi possivel converter SVG para PDF: {e}")
            print("Continuando apenas com a geracao do TXT...")

    files, missing, skipped_binary = collect_interface_files(root)
    write_bundle(root, txt_path, files, missing, skipped_binary)

    print(f"TXT gerado: {txt_path}")
    if missing:
        print("Aviso: arquivos ausentes foram listados no TXT.")
    if skipped_binary:
        print("Aviso: arquivos binarios foram ignorados e listados no TXT.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise
