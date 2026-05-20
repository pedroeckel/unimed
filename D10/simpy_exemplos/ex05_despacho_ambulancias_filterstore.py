"""Exemplo 5: despacho de ambulâncias com FilterStore.

Mostra como usar:
- Resource: central/regulador
- FilterStore: escolha de veículo por tipo
"""

from __future__ import annotations

import simpy

CHAMADAS = [
    ("C001", 0.0, "BASICA", 6.0),
    ("C002", 1.0, "BASICA", 5.0),
    ("C003", 2.0, "UTI", 8.0),
    ("C004", 4.0, "BASICA", 4.0),
]


def chamada(
    env: simpy.Environment,
    codigo: str,
    chegada: float,
    tipo: str,
    ciclo: float,
    central: simpy.Resource,
    frota: simpy.FilterStore,
) -> simpy.events.Process:
    yield env.timeout(chegada)
    print(f"{env.now:04.1f} h | {codigo} entra na central | tipo={tipo}")

    with central.request() as req_central:
        yield req_central
        yield env.timeout(0.2)

    ambulancia = yield frota.get(filter=lambda item: item["tipo"] == tipo)
    print(f"{env.now:04.1f} h | {codigo} despachada com {ambulancia['id']}")
    yield env.timeout(ciclo)
    yield frota.put(ambulancia)
    print(f"{env.now:04.1f} h | {ambulancia['id']} retorna à base")


def executar_simulacao() -> None:
    env = simpy.Environment()
    central = simpy.Resource(env, capacity=1)
    frota = simpy.FilterStore(env, capacity=10)
    frota.items.extend(
        [
            {"id": "AMB-1", "tipo": "BASICA"},
            {"id": "UTI-1", "tipo": "UTI"},
        ]
    )

    for dados in CHAMADAS:
        env.process(chamada(env, *dados, central, frota))

    env.run()


def main() -> None:
    print("=== Exemplo 5: Despacho de ambulâncias com FilterStore ===")
    executar_simulacao()


if __name__ == "__main__":
    main()
