# Benchmarks QA (local)

Este diretorio guarda resultados de benchmarks locais e o baseline usado para comparacao.

## Suite baseline (local)
1) Rodar: `scripts/run_benchmarks.sh`
2) Revisar os relatórios HTML/JSON gerados no diretório de output.
3) Comparar com baseline: `scripts/compare_baseline.py <arquivo_resultados.json>`
4) Registrar aprovacao humana em `Documentos/benchmarks/APPROVAL.md`.

## Metricas e cenarios de pior caso
- OCR full: `JARVIS_OCR_FAST_MAX_DIM=0` + cache desativado.
- OCR fast: `JARVIS_OCR_FAST_MAX_DIM=540` + cache desativado.
- Screenshot: `Validator.take_screenshot()` (quando disponivel).
- Validator full OCR: `Validator.validate()` com OCR full.
- Automacao (click/type/open): medicao em dry-run por padrao; para real, usar `--real-actions`.

## Regressao visual (OCR fast vs full)
`scripts/bench_vision_actions.py` calcula similaridade de texto (ratio). Use como alerta
para investigar degradacao no OCR rapido.

## Cenarios reais (manual)
- Defina cenarios em `Documentos/benchmarks/scenarios.json`.
- Rode `scripts/bench_vision_actions.py --real-actions` somente em maquina dedicada.

## Arquivos gerados (exemplo)
- `local_weights_report.json` + `_report.html` + `_report.json`
- `vision_actions.json` + `_report.html` + `_report.json`
- `compare_python_rust.txt`
- `compare_python_rust_vision.json`

