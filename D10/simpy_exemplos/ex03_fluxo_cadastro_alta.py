"""Exemplo 3: fluxo do paciente do cadastro à alta.

Mostra como usar:
- múltiplos Resource no mesmo fluxo
- retorno ao médico como retrabalho no processo
"""

from __future__ import annotations

import simpy

PACIENTES = [
    ("P201", 0, 6, 4, True),
    ("P202", 1, 5, 0, False),
    ("P203", 3, 7, 5, True),
    ("P204", 5, 4, 0, False),
]


def fluxo_paciente(
    env: simpy.Environment,
    nome: str,
    chegada: int,
    consulta_inicial: int,
    laboratorio_min: int,
    retorna_ao_medico: bool,
    cadastro: simpy.Resource,
    medico: simpy.Resource,
    laboratorio: simpy.Resource,
) -> simpy.events.Process:
    yield env.timeout(chegada)
    inicio = env.now
    print(f"{env.now:02.0f} min | {nome} chega")

    with cadastro.request() as req_cadastro:
        yield req_cadastro
        yield env.timeout(2)
        print(f"{env.now:02.0f} min | {nome} conclui cadastro")

    with medico.request() as req_consulta:
        yield req_consulta
        yield env.timeout(consulta_inicial)
        print(f"{env.now:02.0f} min | {nome} conclui consulta inicial")

    if retorna_ao_medico:
        with laboratorio.request() as req_lab:
            yield req_lab
            yield env.timeout(laboratorio_min)
            print(f"{env.now:02.0f} min | {nome} conclui laboratório")

        with medico.request() as req_retorno:
            yield req_retorno
            yield env.timeout(2)
            print(f"{env.now:02.0f} min | {nome} conclui retorno médico")

    print(f"{env.now:02.0f} min | {nome} recebe alta | lead time={env.now - inicio:02.0f} min")


def executar_simulacao() -> None:
    env = simpy.Environment()
    cadastro = simpy.Resource(env, capacity=1)
    medico = simpy.Resource(env, capacity=1)
    laboratorio = simpy.Resource(env, capacity=1)

    for dados in PACIENTES:
        env.process(fluxo_paciente(env, *dados, cadastro, medico, laboratorio))

    env.run()


def main() -> None:
    print("=== Exemplo 3: Fluxo do cadastro à alta ===")
    executar_simulacao()


if __name__ == "__main__":
    main()
