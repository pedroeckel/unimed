"""
Engenharia de variáveis.

Duas regras governam este módulo inteiro, e as duas vêm de erro real de projeto:

1. TODA janela móvel começa com shift. Sem exceção. Se um `.rolling(` não tiver um
   `.shift(` antes, ele está errado até prova em contrário, porque inclui o próprio
   dia que queremos prever dentro da pergunta.
2. Em painel, o shift é DENTRO do grupo (`groupby(...).shift(1)`). Sem o groupby, a
   última linha de uma especialidade contamina a primeira da seguinte.

E existe uma terceira, que é a razão de este arquivo existir como função única:
a MESMA função roda no treino e em produção. Duas implementações começam iguais e
divergem na primeira correção feita em apenas um dos lados (training-serving skew).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import dados as D


# ═══════════════════════════════════════════════════════════════════════════════
# Caso principal: central de atendimento (série diária)
# ═══════════════════════════════════════════════════════════════════════════════

BLOCOS_CENTRAL: dict[str, list[str]] = {
    "temporais": ["dia_semana", "mês", "dia_mes", "semana_mes", "eh_fim_semana", "dia_do_ano"],
    "cíclicas": ["dsem_sin", "dsem_cos", "doy_sin", "doy_cos"],
    "calendário": ["eh_feriado", "eh_vespera", "eh_pos_feriado", "ferias_escolares"],
    "operacionais": ["janela_vencimento", "fim_trimestre", "campanha", "dias_restantes_mes"],
    "histórico": ["lag1", "lag7", "lag14", "media7", "media28", "desvio7", "tendencia_7_28"],
}

ROTULO_BLOCO = {
    "temporais": "Temporais (saem de graça do índice)",
    "cíclicas": "Cíclicas (seno e cosseno)",
    "calendário": "Calendário e feriados",
    "operacionais": "Operacionais da operadora",
    "histórico": "Histórico da própria série",
    "clima": "Clima (defasado)",
    "epidemia": "Epidemiologia (defasada)",
}


def _bloco_temporal(idx: pd.DatetimeIndex, X: pd.DataFrame) -> None:
    X["dia_semana"] = idx.dayofweek
    X["mês"] = idx.month
    X["dia_mes"] = idx.day
    X["semana_mes"] = (idx.day - 1) // 7 + 1
    X["eh_fim_semana"] = (idx.dayofweek >= 5).astype(int)
    X["dia_do_ano"] = idx.dayofyear


def _bloco_ciclico(idx: pd.DatetimeIndex, X: pd.DataFrame) -> None:
    # 23h fica colada em 0h, e domingo colado em segunda. A codificação ordinal
    # afirma que são os pontos mais distantes possíveis, o que é falso.
    X["dsem_sin"] = np.sin(2 * np.pi * idx.dayofweek / 7)
    X["dsem_cos"] = np.cos(2 * np.pi * idx.dayofweek / 7)
    X["doy_sin"] = np.sin(2 * np.pi * idx.dayofyear / 365.25)
    X["doy_cos"] = np.cos(2 * np.pi * idx.dayofyear / 365.25)


def _bloco_calendario(idx: pd.DatetimeIndex, X: pd.DataFrame) -> None:
    # O feriado não é um efeito único: é uma sequência de três dias com sinais diferentes.
    X["eh_feriado"] = D.eh_feriado(idx)
    X["eh_vespera"] = D.eh_vespera(idx)
    X["eh_pos_feriado"] = D.eh_pos_feriado(idx)
    X["ferias_escolares"] = D.ferias_escolares(idx)


def _bloco_operacional(idx: pd.DatetimeIndex, X: pd.DataFrame) -> None:
    X["janela_vencimento"] = D.janela_vencimento(idx)
    X["fim_trimestre"] = D.fim_trimestre(idx)
    X["campanha"] = D.em_campanha(idx)
    X["dias_restantes_mes"] = idx.days_in_month - idx.day


def _bloco_historico(s: pd.Series, X: pd.DataFrame) -> None:
    passado = s.shift(1)                      # <- o shift que separa honestidade de vazamento
    X["lag1"] = passado
    X["lag7"] = s.shift(7)
    X["lag14"] = s.shift(14)
    X["media7"] = passado.rolling(7).mean()
    X["media28"] = passado.rolling(28).mean()
    X["desvio7"] = passado.rolling(7).std()
    X["tendencia_7_28"] = X["media7"] - X["media28"]


def construir_features_central(diario: pd.DataFrame,
                               coluna: str = "n_ligacoes") -> tuple[pd.DataFrame, pd.Series]:
    """Constrói TODAS as features da série diária da central. Os blocos são
    selecionados depois, por nome, em `BLOCOS_CENTRAL`."""
    idx = pd.DatetimeIndex(diario.index)
    s = diario[coluna].astype(float)

    X = pd.DataFrame(index=idx)
    _bloco_temporal(idx, X)
    _bloco_ciclico(idx, X)
    _bloco_calendario(idx, X)
    _bloco_operacional(idx, X)
    _bloco_historico(s, X)

    validas = X.notna().all(axis=1)
    return X[validas], s[validas]


COLUNAS_HORARIAS = ["hora", "hora_sin", "hora_cos", "dia_semana", "eh_fim_semana",
                    "eh_feriado", "janela_vencimento", "campanha", "mês",
                    "lag24", "lag168", "media24", "media168"]


def construir_features_horarias(horaria: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Features no nível da hora, para comparar com a estratégia de duas etapas.

    Note que aqui as defasagens são de 24 e 168 horas (um dia e uma semana), e não de 1
    hora: no uso operacional a escala do dia inteiro é fechada na véspera, então o volume
    da hora anterior ainda não existe.
    """
    idx = pd.DatetimeIndex(horaria.index)
    s = horaria["n_ligacoes"].astype(float)

    X = pd.DataFrame(index=idx)
    X["hora"] = idx.hour
    X["hora_sin"] = np.sin(2 * np.pi * idx.hour / 24)
    X["hora_cos"] = np.cos(2 * np.pi * idx.hour / 24)
    X["dia_semana"] = idx.dayofweek
    X["eh_fim_semana"] = (idx.dayofweek >= 5).astype(int)
    X["eh_feriado"] = D.eh_feriado(idx)
    X["janela_vencimento"] = D.janela_vencimento(idx)
    X["campanha"] = D.em_campanha(idx)
    X["mês"] = idx.month
    X["lag24"] = s.shift(24)
    X["lag168"] = s.shift(168)
    X["media24"] = s.shift(24).rolling(24).mean()
    X["media168"] = s.shift(24).rolling(168).mean()

    validas = X.notna().all(axis=1)
    return X[validas], s[validas]


# ═══════════════════════════════════════════════════════════════════════════════
# Caso PA: variáveis externas com defasagem
# ═══════════════════════════════════════════════════════════════════════════════

BLOCOS_PA: dict[str, list[str]] = {
    "temporais": BLOCOS_CENTRAL["temporais"],
    "cíclicas": BLOCOS_CENTRAL["cíclicas"],
    "calendário": BLOCOS_CENTRAL["calendário"],
    "histórico": BLOCOS_CENTRAL["histórico"],
    "clima": ["temp_lag", "graus_frio_lag", "chuva_lag"],
    "epidemia": ["gripe_lag", "dengue_lag", "gripe_media7", "dengue_media7"],
}


def construir_features_pa(chegadas: pd.DataFrame, externas: pd.DataFrame,
                          lags: dict[str, int] | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Features do PA. `lags` permite ao aluno testar defasagens erradas e ver o custo."""
    lags = lags or {"temp": D.LAG_TEMPERATURA, "chuva": D.LAG_CHUVA,
                    "gripe": D.LAG_GRIPE, "dengue": D.LAG_DENGUE}
    idx = pd.DatetimeIndex(chegadas.index)
    s = chegadas["chegadas"].astype(float)
    ext = externas.reindex(idx)

    X = pd.DataFrame(index=idx)
    _bloco_temporal(idx, X)
    _bloco_ciclico(idx, X)
    _bloco_calendario(idx, X)
    _bloco_historico(s, X)

    X["temp_lag"] = ext["temp_media"].shift(lags["temp"])
    X["graus_frio_lag"] = np.maximum(0, 19 - X["temp_lag"])
    X["chuva_lag"] = ext["chuva_mm"].shift(lags["chuva"])
    X["gripe_lag"] = ext["alerta_gripe"].shift(lags["gripe"])
    X["dengue_lag"] = ext["alerta_dengue"].shift(lags["dengue"])
    X["gripe_media7"] = ext["alerta_gripe"].shift(1).rolling(7).mean()
    X["dengue_media7"] = ext["alerta_dengue"].shift(1).rolling(7).mean()

    validas = X.notna().all(axis=1)
    return X[validas], s[validas]


# ═══════════════════════════════════════════════════════════════════════════════
# Descoberta de defasagem: a correlação bruta engana
# ═══════════════════════════════════════════════════════════════════════════════

def correlacao_cruzada(alvo: np.ndarray, externa: np.ndarray, max_lag: int = 10) -> np.ndarray:
    saida = []
    for k in range(max_lag + 1):
        a = alvo[k:] if k else alvo
        b = externa[:len(externa) - k] if k else externa
        saida.append(float(np.corrcoef(a, b)[0, 1]))
    return np.array(saida)


def _matriz_sazonal(indice: pd.DatetimeIndex) -> np.ndarray:
    """Tendência + 3 harmônicos anuais + dia da semana: o que já consideramos explicado."""
    t = np.arange(len(indice))
    colunas = [np.ones(len(indice)), t]
    for k in (1, 2, 3):
        colunas += [np.sin(2 * np.pi * k * t / 365.25), np.cos(2 * np.pi * k * t / 365.25)]
    colunas += [(indice.dayofweek == k).astype(float) for k in range(6)]
    return np.column_stack(colunas)


def residuo_sazonal(valores: np.ndarray, indice: pd.DatetimeIndex) -> np.ndarray:
    """Remove tendência, sazonalidade anual e dia da semana. O que sobra é o
    componente idiossincrático: o surto fora de época, a frente fria atípica."""
    base = _matriz_sazonal(indice)
    v = np.asarray(valores, dtype=float)
    coef, *_ = np.linalg.lstsq(base, v, rcond=None)
    return v - base @ coef


def descobrir_defasagens(chegadas: pd.DataFrame, externas: pd.DataFrame,
                         max_lag: int = 10) -> pd.DataFrame:
    """Compara o método ingênuo (correlação bruta) com o correto (correlação dos resíduos).

    O ingênuo erra as quatro defasagens e ainda inverte o sinal da temperatura, porque
    todas as séries sobem e descem juntas ao longo do ano (sazonalidade compartilhada).
    """
    idx = pd.DatetimeIndex(chegadas.index)
    y = chegadas["chegadas"].to_numpy(dtype=float)
    res_y = residuo_sazonal(y, idx)

    verdadeiras = {"temp_media": D.LAG_TEMPERATURA, "chuva_mm": D.LAG_CHUVA,
                   "alerta_gripe": D.LAG_GRIPE, "alerta_dengue": D.LAG_DENGUE}
    linhas = []
    for coluna, lag_real in verdadeiras.items():
        v = externas[coluna].to_numpy(dtype=float)
        bruta = correlacao_cruzada(y, v, max_lag)
        residual = correlacao_cruzada(res_y, residuo_sazonal(v, idx), max_lag)
        k_bruto = int(np.argmax(np.abs(bruta)))
        k_res = int(np.argmax(np.abs(residual)))
        linhas.append({
            "variável": coluna, "lag_verdadeiro": lag_real,
            "lag_bruto": k_bruto, "corr_bruta": round(float(bruta[k_bruto]), 3),
            "lag_residual": k_res, "corr_residual": round(float(residual[k_res]), 3),
            "acertou_bruto": k_bruto == lag_real, "acertou_residual": k_res == lag_real,
            "curva_bruta": bruta, "curva_residual": residual,
        })
    return pd.DataFrame(linhas)


# ═══════════════════════════════════════════════════════════════════════════════
# Painel de autorizações prévia: agregações por entidade e LGPD
# ═══════════════════════════════════════════════════════════════════════════════

BLOCOS_AUTORIZACAO: dict[str, list[str]] = {
    "especialidade": ["especialidade_cod"],
    "calendário": ["dia_semana", "dia_mes", "mês", "semana_mes", "eh_feriado", "eh_vespera"],
    "operacionais": ["janela_vencimento", "fim_trimestre", "campanha", "dias_restantes_mes"],
    "agregadas": ["total_operadora_lag1", "total_operadora_media7", "share_especialidade",
                  "desvio_vs_media28"],
    "histórico": ["lag1", "lag7", "media7", "media28"],
    "perfil_anonimo": ["faixa_60mais"],
    "perfil_detalhado": ["idade_media7", "cronico_media7", "alta_complexidade7", "negativa7"],
}


def construir_features_autorizacao(painel: pd.DataFrame) -> pd.DataFrame:
    """Pipeline UNICO de features do painel. A mesma função roda no treino e em produção.

    Todo histórico é defasado DENTRO da especialidade. O perfil do beneficiário
    descreve o próprio dia, então só entra em média móvel dos dias anteriores.
    """
    df = painel.sort_values(["especialidade", "data"]).reset_index(drop=True).copy()
    d = pd.DatetimeIndex(df["data"])

    df["especialidade_cod"] = df["especialidade"].astype("category").cat.codes
    df["dia_semana"] = d.dayofweek
    df["dia_mes"] = d.day
    df["mês"] = d.month
    df["semana_mes"] = (d.day - 1) // 7 + 1
    df["eh_feriado"] = D.eh_feriado(d)
    df["eh_vespera"] = D.eh_vespera(d)
    df["janela_vencimento"] = D.janela_vencimento(d)
    df["fim_trimestre"] = D.fim_trimestre(d)
    df["campanha"] = D.em_campanha(d)
    df["dias_restantes_mes"] = d.days_in_month - d.day

    g = df.groupby("especialidade", sort=False)["solicitacoes"]
    df["lag1"] = g.shift(1)
    df["lag7"] = g.shift(7)
    df["media7"] = g.shift(1).rolling(7).mean().reset_index(level=0, drop=True)
    df["media28"] = g.shift(1).rolling(28).mean().reset_index(level=0, drop=True)

    # Agregações por entidade: o que o painel permite e a série única não permite.
    total_dia = df.groupby("data")["solicitacoes"].sum()
    df["total_operadora_lag1"] = df["data"].map(total_dia.shift(1))
    df["total_operadora_media7"] = df["data"].map(total_dia.shift(1).rolling(7).mean())
    df["share_especialidade"] = df["media28"] / df["total_operadora_media7"]
    # Razão adimensional: esta especialidade está acima ou abaixo do próprio normal?
    df["desvio_vs_media28"] = df["media7"] / df["media28"]

    # --- perfil do beneficiário (dado pessoal). Sempre defasado é sempre em média.
    for origem, destino in [("idade_media", "idade_media7"), ("pct_cronico", "cronico_media7"),
                            ("pct_alta_complexidade", "alta_complexidade7"),
                            ("taxa_negativa", "negativa7")]:
        gg = df.groupby("especialidade", sort=False)[origem]
        df[destino] = gg.shift(1).rolling(7).mean().reset_index(level=0, drop=True)

    # Nível 1 de granularidade: proporção 60+ agregada em faixas de 5 pontos percentuais.
    pct60 = df.groupby("especialidade", sort=False)["pct_60mais"].shift(1)
    df["faixa_60mais"] = (pct60 * 20).round() / 20

    colunas = [c for bloco in BLOCOS_AUTORIZACAO.values() for c in bloco]
    return df.dropna(subset=colunas).reset_index(drop=True)


def verificar_treino_producao(painel: pd.DataFrame, dia_alvo: pd.Timestamp,
                              especialidade: str) -> dict:
    """O teste que a primeira versão do notebook F1_08 REPROVOU.

    Constrói o vetor de features de duas rotas: em lote (painel inteiro) e em modo
    produção (painel recortado até a véspera, como o sistema faria às 6h da manhã).
    As duas rotas têm que produzir exatamente o mesmo número.
    """
    completo = construir_features_autorizacao(painel)
    recorte = painel[painel["data"] <= dia_alvo].copy()
    producao = construir_features_autorizacao(recorte)

    colunas = [c for bloco in BLOCOS_AUTORIZACAO.values() for c in bloco]
    sel = lambda df: df[(df["data"] == dia_alvo) & (df["especialidade"] == especialidade)][colunas]
    a, b = sel(completo), sel(producao)
    if len(a) == 0 or len(b) == 0:
        return {"ok": False, "diferenca_maxima": float("nan"), "coluna_pior": "linha ausente"}

    diff = (a.to_numpy(dtype=float)[0] - b.to_numpy(dtype=float)[0])
    pior = int(np.argmax(np.abs(diff)))
    return {"ok": bool(np.max(np.abs(diff)) < 1e-9),
            "diferenca_maxima": float(np.max(np.abs(diff))),
            "coluna_pior": colunas[pior], "n_colunas": len(colunas)}


# ═══════════════════════════════════════════════════════════════════════════════
# Painel de carteiras: variação líquida de vidas por contrato
# ═══════════════════════════════════════════════════════════════════════════════

BLOCOS_CARTEIRA: dict[str, list[str]] = {
    "cadastro": ["vidas_inicio_mes", "reajuste_vigente", "meses_desde_reajuste",
                 "eh_pos_reajuste", "mês", "trimestre", "meses_de_contrato"],
    "categórico": ["setor_cod", "porte_cod", "regiao_cod", "modalidade_cod",
                   "coparticipacao_cod", "canal_cod"],
    "histórico": ["variacao_lag1", "variacao_lag2", "variacao_lag3",
                  "media_variacao_3m", "media_variacao_6m", "taxa_crescimento_3m"],
    "macro": ["desemprego_anterior", "desemprego_var_3m", "sinistralidade_anterior"],
}

CATEGORICAS_CARTEIRA = ["setor", "porte", "regiao", "modalidade", "coparticipacao",
                        "canal_venda"]


def construir_features_carteira(painel: pd.DataFrame) -> pd.DataFrame:
    """Features do painel de carteiras, sem vazamento.

    Regra que organiza tudo: como estamos prevendo o mês t, nenhuma coluna pode conter
    informação que só existe depois que o mês t terminou. Classifique cada candidata em
    uma de três categorias:

    | Categoria | Exemplo | Pode usar? |
    | conhecida ANTES do mês | cadastro, calendário, reajuste contratado | sim, direto |
    | conhecida DEPOIS do mês | sinistralidade do mês, adesões do mês | só defasada |
    | o próprio alvo | variação do mês | nunca |
    """
    df = painel.sort_values(["carteira_id", "data"]).reset_index(drop=True).copy()
    d = pd.DatetimeIndex(df["data"])
    g = df.groupby("carteira_id", sort=False)

    # --- cadastro e calendário: conhecidos antes de o mês começar
    df["mês"] = d.month
    df["trimestre"] = d.quarter
    df["eh_pos_reajuste"] = (df["meses_desde_reajuste"] <= 2).astype(int)
    df["meses_de_contrato"] = g.cumcount()

    for coluna in CATEGORICAS_CARTEIRA:
        df[f"{coluna.replace('canal_venda', 'canal')}_cod"] = \
            df[coluna].astype("category").cat.codes

    # --- histórico da própria carteira: SEMPRE defasado dentro do grupo
    alvo = df.groupby("carteira_id", sort=False)["variacao_vidas"]
    for defasagem in (1, 2, 3):
        df[f"variacao_lag{defasagem}"] = alvo.shift(defasagem)
    passado = alvo.shift(1)
    df["media_variacao_3m"] = passado.rolling(3).mean().reset_index(level=0, drop=True)
    df["media_variacao_6m"] = passado.rolling(6).mean().reset_index(level=0, drop=True)
    df["taxa_crescimento_3m"] = df["media_variacao_3m"] / df["vidas_inicio_mes"]

    # --- macro e risco: o indicador oficial também sai com atraso
    df["desemprego_anterior"] = g["taxa_desemprego"].shift(1)
    df["desemprego_var_3m"] = g["taxa_desemprego"].shift(1) - g["taxa_desemprego"].shift(4)
    df["sinistralidade_anterior"] = g["sinistralidade_12m"].shift(1)

    colunas = [c for bloco in BLOCOS_CARTEIRA.values() for c in bloco]
    return df.dropna(subset=colunas).reset_index(drop=True)


def target_encoding(dados: pd.DataFrame, mascaras: dict, modo: str,
                    coluna: str = "carteira_id", alvo: str = "variacao_vidas",
                    n_folds: int = 5) -> pd.Series:
    """Substitui uma categórica de alta cardinalidade pela média do alvo naquela categoria.

    - `modo="ingênuo"`: média calculada em TODO o treino. A média de cada categoria inclui
      a PROPRIA LINHA que vamos prever, então a feature contém um pedaço da resposta.
      O erro de treino cai, o de validação piora, e quem olhar só o treino comemora.
    - `modo="out_of_fold"`: a média de cada linha é calculada sem ela, em k dobras. É o
      jeito correto de fazer manualmente (é o que o CatBoost faz com estatísticas ordenadas).
    """
    from sklearn.model_selection import KFold

    treino = mascaras["treino"]
    codificado = pd.Series(np.nan, index=dados.index, dtype=float)
    media_global = float(dados.loc[treino, alvo].mean())

    if modo == "ingênuo":
        mapa = dados.loc[treino].groupby(coluna)[alvo].mean()
        codificado[:] = dados[coluna].map(mapa).astype(float)
    elif modo == "out_of_fold":
        indices = np.flatnonzero(np.asarray(treino))
        for dentro, fora in KFold(n_folds, shuffle=True, random_state=42).split(indices):
            mapa = dados.iloc[indices[dentro]].groupby(coluna)[alvo].mean()
            alvos = dados.index[indices[fora]]
            codificado.loc[alvos] = dados.loc[alvos, coluna].map(mapa).astype(float)
        # Validação e teste usam a média do treino inteiro: no dia da previsão, é o que existe.
        mapa_completo = dados.loc[treino].groupby(coluna)[alvo].mean()
        resto = ~np.asarray(treino)
        codificado.loc[dados.index[resto]] = dados.loc[resto, coluna].map(mapa_completo).astype(float)
    else:
        raise ValueError(f"modo desconhecido: {modo}")

    return codificado.fillna(media_global)


# ═══════════════════════════════════════════════════════════════════════════════
# Vazamento: a armadilha do rolling sem shift
# ═══════════════════════════════════════════════════════════════════════════════

def demonstrar_vazamento(serie: pd.Series, n: int = 8) -> tuple[pd.DataFrame, float, float]:
    """Mostra, linha a linha, a média móvel que já 'sabe' o valor do próprio dia."""
    demo = pd.DataFrame({"valor": serie.iloc[:n].to_numpy()}, index=serie.index[:n])
    demo["media3_ERRADA"] = demo["valor"].rolling(3).mean().round(1)   # vazamento-proposital
    demo["media3_CORRETA"] = demo["valor"].shift(1).rolling(3).mean().round(1)
    demo["lag1"] = demo["valor"].shift(1)
    corr_errada = float(serie.rolling(3).mean().corr(serie))           # vazamento-proposital
    corr_correta = float(serie.shift(1).rolling(3).mean().corr(serie))
    return demo, corr_errada, corr_correta
