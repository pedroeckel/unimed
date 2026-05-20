"""Exemplo 4: escala de enfermagem com Container e start_delayed().

Mostra como usar:
- Container: capacidade agregada de profissionais
- start_delayed(): processos que começam no futuro
"""

from __future__ import annotations

import simpy
from simpy.util import start_delayed

BASE_HORA = 7


def relogio(tempo: float) -> str:
    horas = int(BASE_HORA + tempo) % 24
    minutos = int(round((tempo - int(tempo)) * 60))
    return f"{horas:02d}:{minutos:02d}"


def turno(
    env: simpy.Environment,
    equipe: simpy.Container,
    nome: str,
    quantidade: int,
    duracao: float,
) -> simpy.events.Process:
    print(f"{relogio(env.now)} | entra turno {nome} (+{quantidade})")
    yield equipe.put(quantidade)
    print(f"{relogio(env.now)} | disponíveis={equipe.level:.0f}")
    yield env.timeout(duracao)
    yield equipe.get(quantidade)
    print(
        f"{relogio(env.now)} | sai turno {nome} (-{quantidade}) | "
        f"disponíveis={equipe.level:.0f}"
    )


def tarefa(
    env: simpy.Environment,
    equipe: simpy.Container,
    nome: str,
    inicio: float,
    duracao: float,
    quantidade: int,
) -> simpy.events.Process:
    yield env.timeout(inicio)
    yield equipe.get(quantidade)
    print(
        f"{relogio(env.now)} | inicia {nome} (-{quantidade}) | "
        f"disponíveis={equipe.level:.0f}"
    )
    yield env.timeout(duracao)
    yield equipe.put(quantidade)
    print(
        f"{relogio(env.now)} | termina {nome} (+{quantidade}) | "
        f"disponíveis={equipe.level:.0f}"
    )


def executar_simulacao() -> None:
    env = simpy.Environment()
    equipe = simpy.Container(env, capacity=20, init=0)

    env.process(turno(env, equipe, "MANHA", 6, 6.0))
    start_delayed(env, turno(env, equipe, "TARDE", 5, 6.5), 5.5)
    start_delayed(env, turno(env, equipe, "NOITE", 4, 12.5), 11.5)

    start_delayed(env, tarefa(env, equipe, "MEDICACAO_MATINAL", 0, 1.0, 2), 1.0)
    start_delayed(env, tarefa(env, equipe, "PICO_ADMISSOES", 0, 2.0, 3), 5.0)
    start_delayed(env, tarefa(env, equipe, "MEDICACAO_NOITE", 0, 1.0, 2), 13.0)

    # Rodamos até esgotar os eventos para não cortar a saída exatamente no marco de 24h.
    env.run()


def main() -> None:
    print("=== Exemplo 4: Escala de enfermagem com Container ===")
    executar_simulacao()


if __name__ == "__main__":
    main()
