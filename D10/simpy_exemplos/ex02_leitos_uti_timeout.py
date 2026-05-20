"""Exemplo 2: alocação de leitos de UTI com timeout de espera.

Mostra como usar:
- Store: leitos nomeados
- pedido | timeout: o paciente segue quando qualquer um dos eventos ocorre
"""

from __future__ import annotations

import simpy

PACIENTES = [
    ("P101", 0, 10, 7),
    ("P102", 1, 12, 6),
    ("P103", 4, 8, 7),
    ("P104", 5, 6, 4),
]


def internacao_uti(
    env: simpy.Environment,
    nome: str,
    chegada: int,
    permanencia: int,
    espera_maxima: int,
    leitos: simpy.Store,
) -> simpy.events.Process:
    yield env.timeout(chegada)
    print(f"{env.now:02.0f} h | {nome} solicita leito de UTI")

    pedido = leitos.get()
    resultado = yield pedido | env.timeout(espera_maxima)

    if pedido in resultado:
        leito = resultado[pedido]
        print(f"{env.now:02.0f} h | {nome} ocupa {leito}")
        yield env.timeout(permanencia)
        print(f"{env.now:02.0f} h | {nome} recebe alta do {leito}")
        yield leitos.put(leito)
    else:
        pedido.cancel()
        print(f"{env.now:02.0f} h | {nome} não conseguiu leito e é transferido")


def executar_simulacao() -> None:
    env = simpy.Environment()
    leitos = simpy.Store(env, capacity=2)
    leitos.items.extend(["UTI-A", "UTI-B"])

    for dados in PACIENTES:
        env.process(internacao_uti(env, *dados, leitos))

    env.run()


def main() -> None:
    print("=== Exemplo 2: Leitos de UTI com timeout ===")
    executar_simulacao()


if __name__ == "__main__":
    main()
