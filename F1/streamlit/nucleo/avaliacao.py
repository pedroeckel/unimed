"""
Avaliação de modelos.

A pergunta "o modelo está bom?" não tem resposta única. Uma previsão que erra 10
pacientes por dia é excelente para um hospital de 500 atendimentos é péssima para um
de 30. Este módulo reúne as réguas e, principalmente, as réguas de referência: sem
baseline e sem piso, um número de erro não significa nada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════════
# As métricas
# ═══════════════════════════════════════════════════════════════════════════════

def metricas(y_real, y_previsto) -> tuple[float, float, float]:
    """MAE, RMSE e MAPE. Todas seguem a regra: menor é melhor."""
    y = np.asarray(y_real, dtype=float)
    p = np.asarray(y_previsto, dtype=float)
    erro = y - p
    mae = float(np.mean(np.abs(erro)))
    rmse = float(np.sqrt(np.mean(erro ** 2)))
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = np.abs(erro / np.where(y == 0, np.nan, y))
    mape = float(np.nanmean(pct) * 100)
    return mae, rmse, mape


def wmape(y_real, y_previsto) -> float:
    """MAPE ponderado: divide a SOMA dos erros pela SOMA dos reais.

    Como a divisão acontece uma vez só, no fim, um zero isolado não quebra nada e as
    horas de baixo volume deixam de dominar o resultado.
    """
    y = np.asarray(y_real, dtype=float)
    p = np.asarray(y_previsto, dtype=float)
    return float(100 * np.sum(np.abs(y - p)) / np.sum(y))


def mase(y_real, y_previsto, y_ingenuo) -> float:
    """MAE do modelo dividido pelo MAE da previsão ingênua.

    Leitura imediata: abaixo de 1, o modelo é melhor do que a regra boba.
    """
    y = np.asarray(y_real, dtype=float)
    erro_modelo = np.mean(np.abs(y - np.asarray(y_previsto, dtype=float)))
    erro_ingenuo = np.mean(np.abs(y - np.asarray(y_ingenuo, dtype=float)))
    return float(erro_modelo / erro_ingenuo)


def montar_placar(y_real, previsoes: dict[str, np.ndarray], y_ingenuo=None,
                  mae_referencia: float | None = None,
                  mae_piso: float | None = None) -> pd.DataFrame:
    """Placar completo, com as colunas que impedem leitura ingênua do resultado.

    - RMSE/MAE é o termômetro de dias de desastre: muito acima de 1 significa que
      existem poucos dias com erro enorme escondidos atrás da média.
    - "% do aproveitável" situa o modelo entre a melhor referência simples é o piso
      do problema. Sem isso, "MAE 4,2" não informa se é bom ou ruim.
    """
    linhas = []
    for nome, prev in previsoes.items():
        mae, rmse, mape = metricas(y_real, prev)
        linha = {
            "modelo": nome, "MAE": round(mae, 3), "RMSE": round(rmse, 3),
            "MAPE (%)": round(mape, 2), "WMAPE (%)": round(wmape(y_real, prev), 2),
            "RMSE/MAE": round(rmse / mae, 2) if mae > 0 else np.nan,
        }
        if y_ingenuo is not None:
            linha["MASE"] = round(mase(y_real, prev, y_ingenuo), 3)
        if mae_referencia is not None and mae_piso is not None and mae_referencia > mae_piso:
            aproveitado = 100 * (mae_referencia - mae) / (mae_referencia - mae_piso)
            linha["% do aproveitável"] = round(max(aproveitado, 0.0), 1)
        linhas.append(linha)
    return pd.DataFrame(linhas).sort_values("MAE").reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Referências ingênuas e piso
# ═══════════════════════════════════════════════════════════════════════════════

REFERENCIA_INGENUA = "Mesmo dia da semana passada (lag 7)"


def referencias_diarias(serie: pd.Series, mascara_treino: np.ndarray,
                        mascara_teste: np.ndarray) -> dict[str, np.ndarray]:
    """As referências que toda comparação precisa incluir.

    Modelo sem baseline não é resultado. Em séries com sazonalidade semanal forte,
    a média móvel é uma referência RUIM (mistura dia útil com fim de semana e prevê
    um valor intermediário que nunca acontece); o mesmo dia da semana anterior é a
    referência honesta a ser batida.
    """
    v = serie.to_numpy(dtype=float)
    n = len(v)
    idx_teste = np.flatnonzero(mascara_teste)
    media_treino = float(v[mascara_treino].mean())

    lag1 = np.array([v[i - 1] for i in idx_teste])
    lag7 = np.array([v[i - 7] for i in idx_teste])
    media7 = np.array([v[i - 7:i].mean() for i in idx_teste])
    media4x7 = np.array([np.mean([v[i - 7 * k] for k in (1, 2, 3, 4)]) for i in idx_teste])
    assert n >= 28

    return {
        "Média histórica global": np.full(len(idx_teste), media_treino),
        "Repetir ontem (lag 1)": lag1,
        REFERENCIA_INGENUA: lag7,
        "Média dos últimos 7 dias": media7,
        "Média dos 4 últimos mesmos dias": media4x7,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Walk-forward: um holdout só pode enganar
# ═══════════════════════════════════════════════════════════════════════════════

def walk_forward(serie: pd.Series, prever, n_janelas: int = 8, tamanho: int = 30,
                 inicio: int | None = None) -> pd.DataFrame:
    """Valida deslizando a janela no tempo. Cada janela treina com tudo o que existia
    até aquele momento e prevê o período seguinte, exatamente como o sistema faria.

    O resultado não é um número, é uma dispersão: se o seu relatório caiu por acaso na
    melhor janela, você reporta metade do erro que reportaria na pior.
    """
    n = len(serie)
    if inicio is None:
        inicio = n - n_janelas * tamanho
    linhas = []
    for k in range(n_janelas):
        fim_treino = inicio + k * tamanho
        historico = serie.iloc[:fim_treino]
        futuro = serie.iloc[fim_treino:fim_treino + tamanho]
        if len(futuro) < tamanho or len(historico) < 60:
            break
        previsao = prever(historico, futuro.index)
        mae, rmse, mape = metricas(futuro.to_numpy(), previsao)
        linhas.append({"janela": k + 1,
                       "início": futuro.index[0].date(), "fim": futuro.index[-1].date(),
                       "MAE": round(mae, 2), "RMSE": round(rmse, 2), "MAPE (%)": round(mape, 2)})
    return pd.DataFrame(linhas)


def modelo_nivel_x_perfil(historico: pd.Series, datas_futuras: pd.DatetimeIndex) -> np.ndarray:
    """Nível dos últimos 28 dias multiplicado pelo perfil semanal histórico.

    Simples de propósito: no walk-forward o assunto é a avaliação, não a modelagem.
    """
    perfil = historico.groupby(historico.index.dayofweek).mean() / historico.mean()
    nivel = float(historico.iloc[-28:].mean())
    return np.array([nivel * perfil.loc[d] for d in datas_futuras.dayofweek])


# ═══════════════════════════════════════════════════════════════════════════════
# Quando faltar e sobrar custam diferente
# ═══════════════════════════════════════════════════════════════════════════════

def custo_assimetrico(y_real, y_previsto, custo_falta: float, custo_sobra: float) -> dict:
    """Separa a parte do erro em que FALTOU da parte em que SOBROU.

    Toda métrica clássica é simétrica: errar 10 para mais e 10 para menos contam igual.
    Em quase nenhuma operação de saúde isso é verdade. Faltar atendente significa fila
    e reclamação; sobrar significa uma hora paga sem produção.
    """
    y = np.asarray(y_real, dtype=float)
    p = np.asarray(y_previsto, dtype=float)
    falta = float(np.mean(np.maximum(y - p, 0)))   # previu MENOS do que aconteceu
    sobra = float(np.mean(np.maximum(p - y, 0)))   # previu MAIS do que aconteceu
    return {"falta_media": falta, "sobra_media": sobra,
            "custo": custo_falta * falta + custo_sobra * sobra}


def psi(referencia, atual, faixas: int = 10) -> float:
    """Population Stability Index: o quanto a distribuição de uma variável se deslocou.

    Convenção de mercado: abaixo de 0,10 estável; até 0,25 moderado; acima, relevante.

    O uso correto é cruzado com a IMPORTÂNCIA da variável. Um desvio enorme em uma variável
    fraca faz barulho e não muda nada; um desvio moderado em uma variável forte estraga o
    modelo em silêncio. Painel ordenado por PSI ordena os alertas ao contrário da prioridade.
    """
    ref = np.asarray(referencia, dtype=float)
    atu = np.asarray(atual, dtype=float)
    limites = np.unique(np.quantile(ref, np.linspace(0, 1, faixas + 1)))
    if len(limites) < 3:
        return 0.0
    p_ref = np.clip(np.histogram(ref, bins=limites)[0] / len(ref), 1e-4, None)
    p_atual = np.clip(np.histogram(atu, bins=limites)[0] / len(atu), 1e-4, None)
    return float(np.sum((p_atual - p_ref) * np.log(p_atual / p_ref)))


def classificar_psi(valor: float) -> str:
    return "estável" if valor < 0.10 else ("moderado" if valor < 0.25 else "RELEVANTE")


def curva_margem(y_real, y_previsto, custo_falta: float, custo_sobra: float,
                 margens=(0.0, 0.02, 0.04, 0.06, 0.08, 0.12, 0.16, 0.20)) -> pd.DataFrame:
    """Varre margens de segurança e mostra que o MAE e o custo elegem decisões diferentes.

    Pelo MAE, a melhor decisão é a previsão mais precisa possível, sem margem.
    Pelo custo real da operação, a melhor decisão é prever um pouco a mais.
    """
    linhas = []
    for margem in margens:
        p = np.asarray(y_previsto, dtype=float) * (1 + margem)
        mae, rmse, _ = metricas(y_real, p)
        c = custo_assimetrico(y_real, p, custo_falta, custo_sobra)
        linhas.append({"margem": margem, "margem_%": f"{100 * margem:.0f}%",
                       "MAE": round(mae, 2), "RMSE": round(rmse, 2),
                       "falta média": round(c["falta_media"], 1),
                       "sobra média": round(c["sobra_media"], 1),
                       "custo": round(c["custo"], 1)})
    return pd.DataFrame(linhas)
