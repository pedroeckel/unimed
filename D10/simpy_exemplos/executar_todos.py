"""Executa todos os exemplos didáticos de SimPy da pasta D10."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ARQUIVOS = [
    "ex01_triagem_classificacao_risco.py",
    "ex02_leitos_uti_timeout.py",
    "ex03_fluxo_cadastro_alta.py",
    "ex04_escala_enfermagem_container.py",
    "ex05_despacho_ambulancias_filterstore.py",
]


def main() -> None:
    base_dir = Path(__file__).resolve().parent

    for nome_arquivo in ARQUIVOS:
        caminho = base_dir / nome_arquivo
        print(f"\n{'=' * 80}", flush=True)
        print(f"Executando {nome_arquivo}", flush=True)
        print(f"{'=' * 80}\n", flush=True)
        subprocess.run([sys.executable, str(caminho)], check=True)


if __name__ == "__main__":
    main()
