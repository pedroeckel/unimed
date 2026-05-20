"""Exemplo 1: triagem de urgência com classificação de risco.

Mostra como usar:
- Resource: triagem de enfermagem
- PriorityResource: fila médica com prioridade clínica
"""

from __future__ import annotations

import simpy

PRIORIDADE = {"vermelho": 0, "laranja": 1, "amarelo": 2, "verde": 3}

PACIENTES = [
    ("P001", 0, "amarelo", 3, 12),
    ("P002", 1, "verde", 3, 8),
    ("P003", 2, "vermelho", 2, 20),
    ("P004", 4, "laranja", 3, 10),
    ("P005", 7, "amarelo", 3, 9),
]


def paciente(
    env: simpy.Environment,
    nome: str,
    chegada: int,
    cor: str,
    tempo_triagem: int,
    tempo_medico: int,
    triagem: simpy.Resource,
    medico: simpy.PriorityResource,
    resultados: list[dict[str, int | str]],
) -> simpy.events.Process:
    yield env.timeout(chegada)
    print(f"{env.now:02.0f} min | {nome} chega ({cor})")

    with triagem.request() as req_triagem:
        yield req_triagem
        print(f"{env.now:02.0f} min | {nome} inicia triagem")
        yield env.timeout(tempo_triagem)
        fim_triagem = env.now
        print(f"{env.now:02.0f} min | {nome} termina triagem")

    with medico.request(priority=PRIORIDADE[cor]) as req_medico:
        yield req_medico
        inicio_medico = env.now
        espera_medica = inicio_medico - fim_triagem
        print(
            f"{env.now:02.0f} min | {nome} inicia médico "
            f"(espera médica={espera_medica:02.0f} min)"
        )
        yield env.timeout(tempo_medico)
        print(f"{env.now:02.0f} min | {nome} recebe alta")
        resultados.append(
            {
                "nome": nome,
                "cor": cor,
                "tempo_total": int(env.now - chegada),
                "espera_medica": int(espera_medica),
            }
        )


def executar_simulacao() -> list[dict[str, int | str]]:
    env = simpy.Environment()
    triagem = simpy.Resource(env, capacity=1)
    medico = simpy.PriorityResource(env, capacity=1)
    resultados: list[dict[str, int | str]] = []

    for dados in PACIENTES:
        env.process(paciente(env, *dados, triagem, medico, resultados))

    env.run()
    return resultados


def main() -> None:
    print("=== Exemplo 1: Triagem com classificação de risco ===")
    resultados = executar_simulacao()

    print("\nResumo final")
    for item in resultados:
        print(
            f"{item['nome']} | cor={str(item['cor']):8s} | "
            f"tempo total={int(item['tempo_total']):02d} min | "
            f"espera por médico={int(item['espera_medica']):02d} min"
        )


if __name__ == "__main__":
    main()
