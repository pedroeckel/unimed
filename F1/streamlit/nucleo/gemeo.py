"""
O gêmeo digital da central de atendimento.

Previsão não é decisão. O gêmeo é a peça que traduz "o MAE caiu de 80 para 36" em
"a fila caiu de 4 minutos para 40 segundos e o SLA subiu 12 pontos".

Dois motores rodam lado a lado, de propósito:

- **SimPy** (simulação de eventos discretos): fila M/G/c com capacidade que muda por
  turno, tempo de atendimento lognormal e ABANDONO por impaciência. É o gêmeo de fato.
- **Erlang C** (fórmula analítica clássica de call center): instantânea, mas assume
  paciência infinita e atendimento exponencial. Serve de teste de sanidade: se a
  simulação e a fórmula divergirem muito em regime estável, o bug é da simulação.

Aprender a checar uma simulação contra a teoria é parte da aula.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import simpy

TURNOS = {"Madrugada (0h-5h)": range(0, 6), "Manhã (6h-11h)": range(6, 12),
          "Tarde (12h-17h)": range(12, 18), "Noite (18h-23h)": range(18, 24)}

NIVEL_SERVICO_SEG = 20.0     # meta clássica de call center: atender em 20 segundos
SIGMA_LOG = 0.5              # dispersão do tempo de atendimento (lognormal)


# ═══════════════════════════════════════════════════════════════════════════════
# Erlang C: o benchmark analítico
# ═══════════════════════════════════════════════════════════════════════════════

def _erlang_b(c: int, a: float) -> float:
    b = 1.0
    for i in range(1, c + 1):
        b = a * b / (i + a * b)
    return b


def erlang_c(c: int, a: float) -> float:
    """Probabilidade de o beneficiário ter que esperar (fila M/M/c, paciência infinita)."""
    if c <= a:
        return 1.0
    b = _erlang_b(c, a)
    return b / (1 - (a / c) * (1 - b))


def kpis_erlang(lambda_hora: np.ndarray, agentes_hora: np.ndarray, tma_min: float) -> dict:
    """Espera média e nível de serviço previstos pela fórmula, hora a hora."""
    espera, sl, ocup, chamadas = [], [], [], []
    for h in range(24):
        lam, c = float(lambda_hora[h]), int(agentes_hora[h])
        a = lam * tma_min / 60.0                    # intensidade de tráfego, em erlangs
        if c <= 0:
            espera.append(np.inf); sl.append(0.0); ocup.append(np.inf); chamadas.append(lam)
            continue
        rho = a / c
        if rho >= 1:                                 # sistema instável: a fila cresce sem limite
            espera.append(np.inf); sl.append(0.0); ocup.append(rho); chamadas.append(lam)
            continue
        pw = erlang_c(c, a)
        asa = pw * tma_min / (c - a)                                  # em minutos
        nivel = 1 - pw * np.exp(-(c - a) * (NIVEL_SERVICO_SEG / 60.0) / tma_min)
        espera.append(asa); sl.append(nivel); ocup.append(rho); chamadas.append(lam)

    peso = np.array(chamadas, dtype=float)
    peso = peso / peso.sum() if peso.sum() > 0 else np.ones(24) / 24
    esp = np.array(espera, dtype=float)
    return {
        "espera_media_min": float(np.sum(np.where(np.isfinite(esp), esp, 60.0) * peso)),
        "nivel_servico": float(np.sum(np.array(sl) * peso)),
        "ocupacao_max": float(np.nanmax(ocup)),
        "por_hora": pd.DataFrame({"hora": range(24), "lambda": lambda_hora,
                                  "agentes": agentes_hora, "espera_min": esp,
                                  "nivel_servico": sl, "ocupacao": ocup}),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SimPy: o gêmeo
# ═══════════════════════════════════════════════════════════════════════════════

def _gestor_turno(env, recurso, agentes_hora, cap_max, bloqueios):
    """Faz a capacidade mudar por turno.

    O recurso é criado com a capacidade MAXIMA do dia; nas horas de escala menor, este
    processo ocupa os postos excedentes com prioridade máxima. É o mesmo truque usado
    no gêmeo do PA (D10): a redução de escala só vale quando o atendente em curso
    termina a ligação, que é exatamente o que acontece na vida real.
    """
    for h in range(24):
        alvo = cap_max - int(agentes_hora[h])
        while len(bloqueios) > alvo:
            recurso.release(bloqueios.pop())
        while len(bloqueios) < alvo:
            req = recurso.request(priority=-1)
            yield req
            bloqueios.append(req)
        yield env.timeout(60.0)


def _beneficiario(env, recurso, chegada, tma_min, paciencia_min, rng, registros):
    with recurso.request(priority=0) as req:
        if np.isfinite(paciencia_min):
            paciencia = rng.exponential(paciencia_min)
            resultado = yield req | env.timeout(paciencia)
            atendido = req in resultado
        else:
            yield req
            atendido = True

        espera = env.now - chegada
        if not atendido:
            registros.append({"espera": espera, "atendido": False})
            return

        mu = np.log(tma_min) - SIGMA_LOG ** 2 / 2
        yield env.timeout(float(rng.lognormal(mu, SIGMA_LOG)))
        registros.append({"espera": espera, "atendido": True})


def simular_dia(lambda_hora, agentes_hora, tma_min: float = 5.0,
                paciencia_min: float = 3.0, semente: int = 42) -> pd.DataFrame:
    """Uma replicação de 24 horas de operação da central."""
    rng = np.random.default_rng(semente)
    lambda_hora = np.asarray(lambda_hora, dtype=float)
    agentes_hora = np.asarray(agentes_hora, dtype=int)
    cap_max = max(int(agentes_hora.max()), 1)

    env = simpy.Environment()
    recurso = simpy.PriorityResource(env, capacity=cap_max)
    registros: list[dict] = []

    env.process(_gestor_turno(env, recurso, agentes_hora, cap_max, []))

    # Chegadas: processo de Poisson não homogêneo. Com taxa constante dentro da hora,
    # sortear a contagem por hora e espalhar os instantes uniformemente é exato.
    for h in range(24):
        n = rng.poisson(lambda_hora[h])
        for instante in np.sort(rng.uniform(h * 60, (h + 1) * 60, n)):
            env.process(_agendar(env, recurso, float(instante), tma_min, paciencia_min,
                                 rng, registros))

    env.run(until=36 * 60)      # roda além das 24h para a fila drenar e nada ser truncado
    return pd.DataFrame(registros)


def _agendar(env, recurso, instante, tma_min, paciencia_min, rng, registros):
    yield env.timeout(max(instante - env.now, 0))
    yield env.process(_beneficiario(env, recurso, env.now, tma_min, paciencia_min,
                                    rng, registros))


# ═══════════════════════════════════════════════════════════════════════════════
# A mesma replicação, instrumentada minuto a minuto
# ═══════════════════════════════════════════════════════════════════════════════

def _beneficiario_observado(env, recurso, chegada, tma_min, paciencia_min, rng,
                            registros, estado):
    """Igual a `_beneficiario`, mas anotando em `estado` o que um supervisor veria."""
    estado["fila"] += 1
    with recurso.request(priority=0) as req:
        if np.isfinite(paciencia_min):
            paciencia = rng.exponential(paciencia_min)
            resultado = yield req | env.timeout(paciencia)
            atendido = req in resultado
        else:
            yield req
            atendido = True

        espera = env.now - chegada
        estado["fila"] -= 1
        if not atendido:
            estado["abandonos"] += 1
            registros.append({"chegada": chegada, "espera": espera, "atendido": False,
                              "inicio": np.nan, "fim": np.nan})
            return

        estado["ocupados"] += 1
        estado["atendidos"] += 1
        if espera <= NIVEL_SERVICO_SEG / 60:
            estado["no_prazo"] += 1
        inicio = env.now

        mu = np.log(tma_min) - SIGMA_LOG ** 2 / 2
        yield env.timeout(float(rng.lognormal(mu, SIGMA_LOG)))
        estado["ocupados"] -= 1
        registros.append({"chegada": chegada, "espera": espera, "atendido": True,
                          "inicio": inicio, "fim": env.now})


def _agendar_observado(env, recurso, instante, tma_min, paciencia_min, rng, registros, estado):
    yield env.timeout(max(instante - env.now, 0))
    estado["chegadas"] += 1
    yield env.process(_beneficiario_observado(env, recurso, env.now, tma_min, paciencia_min,
                                              rng, registros, estado))


def _observador(env, estado, agentes_hora, linhas, minutos: int):
    """Fotografa a operação a cada minuto simulado. É o traço que uma torre de
    controle mostraria ao vivo: fila, atendentes ocupados, acumulados do dia."""
    for minuto in range(minutos):
        linhas.append({
            "minuto": minuto,
            "fila": estado["fila"],
            "ocupados": estado["ocupados"],
            "capacidade": int(agentes_hora[min(minuto // 60, 23)]),
            "chegadas_acum": estado["chegadas"],
            "atendidos_acum": estado["atendidos"],
            "abandonos_acum": estado["abandonos"],
            "no_prazo_acum": estado["no_prazo"],
        })
        yield env.timeout(1.0)


def simular_dia_detalhado(lambda_hora, agentes_hora, tma_min: float = 5.0,
                          paciencia_min: float = 3.0, semente: int = 42,
                          minutos: int = 24 * 60) -> dict:
    """Uma replicação de 24 horas com o traço minuto a minuto da operação.

    Mesmo motor de `simular_dia` — mesmas chegadas de Poisson não homogêneo, mesma
    fila com prioridade, mesmo abandono por impaciência. O que muda é que um processo
    observador registra o estado do sistema a cada minuto, o que permite **reproduzir
    o dia** fora da simulação (num painel operacional, por exemplo) em vez de olhar
    apenas o resumo do fim do dia.

    Devolve `por_minuto` (o traço) e `chamadas` (uma linha por ligação oferecida).
    """
    rng = np.random.default_rng(semente)
    lambda_hora = np.asarray(lambda_hora, dtype=float)
    agentes_hora = np.asarray(agentes_hora, dtype=int)
    cap_max = max(int(agentes_hora.max()), 1)

    env = simpy.Environment()
    recurso = simpy.PriorityResource(env, capacity=cap_max)
    registros: list[dict] = []
    estado = {"fila": 0, "ocupados": 0, "chegadas": 0, "atendidos": 0,
              "abandonos": 0, "no_prazo": 0}
    linhas: list[dict] = []

    env.process(_gestor_turno(env, recurso, agentes_hora, cap_max, []))
    env.process(_observador(env, estado, agentes_hora, linhas, minutos))

    for h in range(24):
        n = rng.poisson(lambda_hora[h])
        for instante in np.sort(rng.uniform(h * 60, (h + 1) * 60, n)):
            env.process(_agendar_observado(env, recurso, float(instante), tma_min,
                                           paciencia_min, rng, registros, estado))

    env.run(until=36 * 60)
    return {"por_minuto": pd.DataFrame(linhas),
            "chamadas": pd.DataFrame(registros).sort_values("chegada").reset_index(drop=True)}


def rodar_replicacoes(lambda_hora, agentes_hora, tma_min: float = 5.0,
                      paciencia_min: float = 3.0, n_rep: int = 8,
                      semente: int = 42) -> dict:
    """Várias replicações independentes, com intervalo de confiança de 95%.

    Uma única rodada de simulação é um sorteio. O que se reporta é a média entre
    replicações e a incerteza dessa média.
    """
    linhas, esperas = [], []
    for r in range(n_rep):
        df = simular_dia(lambda_hora, agentes_hora, tma_min, paciencia_min, semente + r)
        atendidos = df[df["atendido"]]
        esperas.append(atendidos["espera"].to_numpy())
        # Nível de serviço sobre as chamadas OFERECIDAS, não sobre as atendidas: quem
        # abandonou conta como não atendido. Medir só entre as atendidas premia a operação
        # que perde beneficiário no meio do caminho.
        dentro_do_prazo = (df["atendido"] & (df["espera"] <= NIVEL_SERVICO_SEG / 60))
        linhas.append({
            "replicacao": r + 1,
            "chamadas": len(df),
            "espera_media_min": float(atendidos["espera"].mean()) if len(atendidos) else 0.0,
            "espera_p90_min": float(atendidos["espera"].quantile(0.90)) if len(atendidos) else 0.0,
            "nivel_servico": float(dentro_do_prazo.mean()) if len(df) else 0.0,
            "taxa_abandono": float(1 - df["atendido"].mean()) if len(df) else 0.0,
        })
    por_rep = pd.DataFrame(linhas)

    resumo = {}
    for coluna in ["espera_media_min", "espera_p90_min", "nivel_servico", "taxa_abandono",
                   "chamadas"]:
        v = por_rep[coluna].to_numpy(dtype=float)
        meia = 1.96 * v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else 0.0
        resumo[coluna] = {"media": float(v.mean()), "ic": float(meia)}

    return {"por_replicacao": por_rep, "resumo": resumo,
            "esperas": np.concatenate(esperas) if esperas else np.array([])}


# ═══════════════════════════════════════════════════════════════════════════════
# Da previsão para a escala
# ═══════════════════════════════════════════════════════════════════════════════

def lambda_por_hora(total_dia: float, perfil: pd.DataFrame, dia_semana: int) -> np.ndarray:
    """Distribui o total previsto do dia pelas 24 horas, usando o perfil intradiário.

    Estratégia de duas etapas: um modelo diário, onde as variáveis externas atuam e onde
    há 730 observações em vez de 17.520, mais uma tabela de perfil fácil de auditar.
    """
    fatias = perfil[perfil["dia_semana"] == dia_semana].sort_values("hora")["fracao"].to_numpy()
    return total_dia * fatias


def prescrever_escala(lambda_hora, tma_min: float = 5.0, meta_sl: float = 0.80,
                      maximo: int = 40) -> np.ndarray:
    """Menor escala por hora que mantem o nível de serviço acima da meta.

    Busca incremental sobre a fórmula de Erlang C, que é instantânea. A simulação
    depois valida a recomendação: é o par correto entre dimensionar e verificar.
    """
    escala = np.zeros(24, dtype=int)
    for h in range(24):
        lam = float(lambda_hora[h])
        a = lam * tma_min / 60.0
        c = max(int(np.ceil(a)), 1)
        while c <= maximo:
            pw = erlang_c(c, a)
            sl = 1 - pw * np.exp(-(c - a) * (NIVEL_SERVICO_SEG / 60.0) / tma_min) if c > a else 0.0
            if sl >= meta_sl:
                break
            c += 1
        escala[h] = min(c, maximo)
    return escala


def escala_por_turno(agentes_hora) -> pd.DataFrame:
    agentes_hora = np.asarray(agentes_hora, dtype=int)
    linhas = []
    for nome, horas in TURNOS.items():
        h = list(horas)
        linhas.append({"turno": nome, "horas": f"{h[0]}h-{h[-1]}h",
                       "agentes (média)": round(float(agentes_hora[h].mean()), 1),
                       "agentes (pico)": int(agentes_hora[h].max())})
    return pd.DataFrame(linhas)


def custo_escala(agentes_hora, custo_hora: float = 38.0) -> float:
    """Custo de um dia de escala. Um atendente-hora é a unidade de decisão do gestor."""
    return float(np.sum(np.asarray(agentes_hora, dtype=float)) * custo_hora)


def comparar_fontes(lambda_real, fontes: dict[str, np.ndarray], tma_min: float = 5.0,
                    paciencia_min: float = 3.0, meta_sl: float = 0.80, n_rep: int = 6,
                    custo_hora: float = 38.0, semente: int = 42) -> pd.DataFrame:
    """O experimento que justifica o módulo inteiro.

    O gestor dimensiona a escala a partir de uma FONTE DE DEMANDA (a previsão do modelo,
    a média histórica, ou a demanda real de um oráculo impossível). Depois o dia
    acontece de verdade: a simulação roda sempre com a DEMANDA REAL e com a escala que
    aquela fonte recomendou.

    A diferença de KPI entre as fontes é o valor operacional da previsão, medido em fila
    e em SLA, e não em MAE.
    """
    linhas = []
    for nome, lam_fonte in fontes.items():
        escala = prescrever_escala(lam_fonte, tma_min, meta_sl)
        r = rodar_replicacoes(lambda_real, escala, tma_min, paciencia_min, n_rep, semente)
        resumo = r["resumo"]
        linhas.append({
            "fonte usada para dimensionar": nome,
            "atendentes-hora": int(np.sum(escala)),
            "custo do dia (R$)": round(custo_escala(escala, custo_hora), 0),
            "espera média (min)": round(resumo["espera_media_min"]["media"], 2),
            "espera P90 (min)": round(resumo["espera_p90_min"]["media"], 2),
            "nível de serviço": round(resumo["nivel_servico"]["media"], 3),
            "abandono": round(resumo["taxa_abandono"]["media"], 3),
        })
    return pd.DataFrame(linhas)
