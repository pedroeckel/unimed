"""
Os modelos, todos avaliados no MESMO conjunto de teste.

Protocolo de avaliação, declarado para não haver comparação injusta:

- Referências, SARIMA, árvores e boosting preveem **um dia à frente** (D+1), com todo o
  histórico real disponível até D. É o uso operacional: a escala de amanhã é fechada hoje.
- O Prophet prevê o **horizonte inteiro** de uma vez, porque ele não usa defasagens e é
  desenhado para horizonte longo. Isso é uma vantagem dele (não precisa do dado de ontem)
  é uma desvantagem na comparação (não aproveita o dado de ontem). O placar marca isso.

Ajuste: treino + validação. A validação decide o número de árvores (early stopping) e as
ordens do SARIMA; o teste nunca participa de nenhuma decisão.
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ═══════════════════════════════════════════════════════════════════════════════
# Família clássica: ARIMA e SARIMA
# ═══════════════════════════════════════════════════════════════════════════════

def grid_aic(y_ajuste: pd.Series, sazonal=(1, 1, 1, 7),
             valores_p=(0, 1, 2), valores_q=(0, 1, 2), d: int = 1) -> pd.DataFrame:
    """Metodologia de Box-Jenkins, passo 4: comparar candidatos por critério de informação.

    O AIC recompensa o ajuste e penaliza parâmetros em excesso. Entre dois modelos,
    prefere-se o de menor AIC.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    linhas = []
    for p in valores_p:
        for q in valores_q:
            try:
                m = SARIMAX(y_ajuste, order=(p, d, q), seasonal_order=sazonal,
                            enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
                linhas.append({"p": p, "d": d, "q": q,
                               "ordem": f"({p},{d},{q}){sazonal}", "AIC": round(float(m.aic), 1)})
            except Exception:
                continue
    return pd.DataFrame(linhas).sort_values("AIC").reset_index(drop=True)


def sarima_um_passo(serie: pd.Series, mascaras: dict, ordem=(1, 1, 1),
                    sazonal=(1, 1, 1, 7)) -> dict:
    """Ajusta em treino+validação e caminha pelo teste prevendo um dia à frente.

    A cada dia, a observação real é anexada ao filtro (`append` sem refit): é assim que
    o modelo roda em produção, sem reestimar os parâmetros toda madrugada.
    """
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    inicio = time.time()
    ajuste = serie[mascaras["treino"] | mascaras["validação"]]
    teste = serie[mascaras["teste"]]

    modelo = SARIMAX(ajuste, order=ordem, seasonal_order=sazonal,
                     enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)

    previsoes, li, ls = [], [], []
    estado = modelo
    for data, valor in teste.items():
        f = estado.get_forecast(steps=1)
        previsoes.append(float(f.predicted_mean.iloc[0]))
        ic = f.conf_int(alpha=0.05)
        li.append(float(ic.iloc[0, 0]))
        ls.append(float(ic.iloc[0, 1]))
        nova = pd.Series([valor], index=[data], name=serie.name)
        estado = estado.append(nova, refit=False)

    return {"previsão": np.array(previsoes), "ic_inferior": np.array(li),
            "ic_superior": np.array(ls), "aic": float(modelo.aic),
            "tempo_s": time.time() - inicio, "resumo": modelo}


def teste_adf(serie: pd.Series) -> tuple[float, float, str]:
    """Dickey-Fuller Aumentado. H0: a série NÃO é estacionária (tem raiz unitária)."""
    from statsmodels.tsa.stattools import adfuller

    r = adfuller(np.asarray(serie.dropna(), dtype=float))
    estatistica, p = float(r[0]), float(r[1])
    veredito = "ESTACIONARIA (rejeita H0)" if p < 0.05 else "NAO estacionária (não rejeita H0)"
    return estatistica, p, veredito


# ═══════════════════════════════════════════════════════════════════════════════
# Prophet
# ═══════════════════════════════════════════════════════════════════════════════

def prophet_previsao(serie: pd.Series, mascaras: dict, changepoint_prior_scale: float = 0.05,
                     usar_feriados: bool = True, sazonalidade_anual: bool = True) -> dict:
    """Ajuste de curva: y(t) = g(t) + s(t) + h(t) + ruído, cada termo inspecionável."""
    import logging

    logging.getLogger("cmdstanpy").disabled = True
    logging.getLogger("prophet").setLevel(logging.CRITICAL)
    from prophet import Prophet

    inicio = time.time()
    df = pd.DataFrame({"ds": serie.index, "y": serie.to_numpy(dtype=float)})
    ajuste = df[np.asarray(mascaras["treino"] | mascaras["validação"])]

    m = Prophet(weekly_seasonality=True, yearly_seasonality=sazonalidade_anual,
                daily_seasonality=False, changepoint_prior_scale=changepoint_prior_scale)
    if usar_feriados:
        m.add_country_holidays(country_name="BR")
    m.fit(ajuste)

    futuro = pd.DataFrame({"ds": df["ds"]})
    fc = m.predict(futuro)
    mascara_teste = np.asarray(mascaras["teste"])
    return {"previsão": fc.loc[mascara_teste, "yhat"].to_numpy(),
            "ic_inferior": fc.loc[mascara_teste, "yhat_lower"].to_numpy(),
            "ic_superior": fc.loc[mascara_teste, "yhat_upper"].to_numpy(),
            "componentes": fc, "modelo": m, "tempo_s": time.time() - inicio}


# ═══════════════════════════════════════════════════════════════════════════════
# Árvores e florestas
# ═══════════════════════════════════════════════════════════════════════════════

def _partes(X: pd.DataFrame, y: pd.Series, mascaras: dict):
    tr, va, te = mascaras["treino"], mascaras["validação"], mascaras["teste"]
    aj = tr | va
    return X[aj], y[aj], X[tr], y[tr], X[va], y[va], X[te], y[te]


def arvore(X: pd.DataFrame, y: pd.Series, mascaras: dict,
           max_depth: int = 8, min_samples_leaf: int = 1, semente: int = 42) -> dict:
    from sklearn.tree import DecisionTreeRegressor

    inicio = time.time()
    X_aj, y_aj, *_, X_te, _ = _partes(X, y, mascaras)
    m = DecisionTreeRegressor(max_depth=max_depth, min_samples_leaf=min_samples_leaf,
                              random_state=semente).fit(X_aj, y_aj)
    return {"previsão": m.predict(X_te), "modelo": m, "n_folhas": int(m.get_n_leaves()),
            "previsao_ajuste": m.predict(X_aj), "y_ajuste": y_aj.to_numpy(),
            "tempo_s": time.time() - inicio}


def curva_profundidade(X: pd.DataFrame, y: pd.Series, mascaras: dict,
                       profundidades=range(1, 21), semente: int = 42) -> pd.DataFrame:
    """A curva em U: o erro de treino só desce, o de teste desce e volta a subir.

    A distância entre as duas curvas é o tamanho do autoengano de quem avalia no treino.
    """
    from sklearn.tree import DecisionTreeRegressor

    from .avaliacao import metricas

    X_aj, y_aj, _, _, _, _, X_te, y_te = _partes(X, y, mascaras)
    linhas = []
    for prof in profundidades:
        m = DecisionTreeRegressor(max_depth=prof, random_state=semente).fit(X_aj, y_aj)
        linhas.append({"max_depth": prof,
                       "MAE treino": round(metricas(y_aj, m.predict(X_aj))[0], 2),
                       "MAE teste": round(metricas(y_te, m.predict(X_te))[0], 2),
                       "folhas": int(m.get_n_leaves())})
    return pd.DataFrame(linhas)


def random_forest(X: pd.DataFrame, y: pd.Series, mascaras: dict, n_estimators: int = 300,
                  max_depth=None, min_samples_leaf: int = 2, semente: int = 42) -> dict:
    from sklearn.ensemble import RandomForestRegressor

    inicio = time.time()
    X_aj, y_aj, *_, X_te, _ = _partes(X, y, mascaras)
    m = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth,
                              min_samples_leaf=min_samples_leaf, oob_score=True,
                              random_state=semente, n_jobs=-1).fit(X_aj, y_aj)
    return {"previsão": m.predict(X_te), "modelo": m, "oob": float(m.oob_score_),
            "importancias": pd.Series(m.feature_importances_, index=X.columns),
            "tempo_s": time.time() - inicio}


def curva_bagging(X: pd.DataFrame, y: pd.Series, mascaras: dict, k_max: int = 40,
                  semente: int = 42) -> pd.DataFrame:
    """Média de k árvores profundas e sem poda. Cada uma sobreajusta; a média, não.

    O overfitting de cada árvore é, em boa parte, ruído com sinal aleatório, e ruído
    aleatório se cancela na média. O padrão real, que todas enxergam, sobrevive.
    """
    from sklearn.tree import DecisionTreeRegressor

    from .avaliacao import metricas

    X_aj, y_aj, _, _, _, _, X_te, y_te = _partes(X, y, mascaras)
    g = np.random.default_rng(semente)
    soma = np.zeros(len(X_te))
    linhas = []
    for k in range(1, k_max + 1):
        sorteio = g.integers(0, len(X_aj), len(X_aj))          # bootstrap: com reposição
        arv = DecisionTreeRegressor(random_state=semente + k).fit(
            X_aj.iloc[sorteio], y_aj.iloc[sorteio])
        soma += arv.predict(X_te)
        linhas.append({"árvores": k, "MAE": round(metricas(y_te, soma / k)[0], 3)})
    return pd.DataFrame(linhas)


# ═══════════════════════════════════════════════════════════════════════════════
# Boosting
# ═══════════════════════════════════════════════════════════════════════════════

def boosting(biblioteca: str, X: pd.DataFrame, y: pd.Series, mascaras: dict,
             learning_rate: float = 0.05, num_leaves: int = 31, max_depth: int = 6,
             min_child_samples: int = 10, n_estimators: int = 2000,
             semente: int = 42) -> dict:
    """XGBoost, LightGBM ou CatBoost com early stopping na validação.

    Diferença prática mais importante em relação ao bagging: aqui MAIS ARVORES PODEM
    PIORAR. Como cada árvore é treinada para corrigir o resíduo, e parte do resíduo é
    ruído puro, chega um momento em que as novas árvores corrigem aleatoriedade.
    """
    inicio = time.time()
    X_aj, y_aj, X_tr, y_tr, X_va, y_va, X_te, _ = _partes(X, y, mascaras)
    curvas: dict[str, list[float]] = {}

    if biblioteca == "LightGBM":
        import lightgbm as lgb
        comuns = dict(learning_rate=learning_rate, num_leaves=num_leaves,
                      min_child_samples=min_child_samples, subsample=0.8, subsample_freq=1,
                      colsample_bytree=0.8, random_state=semente, verbose=-1)
        m = lgb.LGBMRegressor(n_estimators=n_estimators, **comuns)
        m.fit(X_tr, y_tr, eval_set=[(X_tr, y_tr), (X_va, y_va)],
              eval_names=["treino", "validação"], eval_metric="l1",
              callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(0)])
        curvas = {"treino": list(m.evals_result_["treino"]["l1"]),
                  "validação": list(m.evals_result_["validação"]["l1"])}
        n_arvores = int(m.best_iteration_ or n_estimators)
        final = lgb.LGBMRegressor(n_estimators=n_arvores, **comuns).fit(X_aj, y_aj)
        importâncias = pd.Series(final.feature_importances_, index=X.columns)

    elif biblioteca == "XGBoost":
        import xgboost as xgb
        comuns = dict(learning_rate=learning_rate, max_depth=max_depth, subsample=0.8,
                      colsample_bytree=0.8, reg_lambda=1.0, min_child_weight=5,
                      tree_method="hist", eval_metric="mae", random_state=semente)
        m = xgb.XGBRegressor(n_estimators=n_estimators, early_stopping_rounds=100, **comuns)
        m.fit(X_tr, y_tr, eval_set=[(X_tr, y_tr), (X_va, y_va)], verbose=False)
        r = m.evals_result()
        curvas = {"treino": list(r["validation_0"]["mae"]),
                  "validação": list(r["validation_1"]["mae"])}
        n_arvores = int(m.best_iteration) + 1
        final = xgb.XGBRegressor(n_estimators=n_arvores, **comuns).fit(X_aj, y_aj, verbose=False)
        importâncias = pd.Series(final.feature_importances_, index=X.columns)

    elif biblioteca == "CatBoost":
        from catboost import CatBoostRegressor
        comuns = dict(learning_rate=learning_rate, depth=max_depth, loss_function="MAE",
                      random_seed=semente, verbose=0, allow_writing_files=False)
        m = CatBoostRegressor(iterations=n_estimators, early_stopping_rounds=100, **comuns)
        m.fit(X_tr, y_tr, eval_set=(X_va, y_va))
        ev = m.get_evals_result()
        curvas = {"treino": list(ev["learn"]["MAE"]), "validação": list(ev["validation"]["MAE"])}
        n_arvores = int(m.get_best_iteration()) + 1
        final = CatBoostRegressor(iterations=n_arvores, **comuns).fit(X_aj, y_aj)
        importâncias = pd.Series(final.get_feature_importance(), index=X.columns)

    else:
        raise ValueError(f"biblioteca desconhecida: {biblioteca}")

    # A validação escolheu QUANTAS árvores; o modelo final é reajustado em treino+validação,
    # para não desperdicar os meses mais recentes, que são os mais informativos.
    return {"previsão": final.predict(X_te), "modelo": final, "n_arvores": n_arvores,
            "curvas": curvas, "importancias": importâncias, "tempo_s": time.time() - inicio}


def lgbm_simples(X: pd.DataFrame, y: pd.Series, mascaras: dict, colunas: list[str],
                 semente: int = 42):
    """LightGBM padrão usado nas ablações: rápido, para a exploração ficar fluida.

    Mesmo protocolo do `boosting`: a validação decide o número de árvores é o modelo
    final é reajustado em treino+validação.
    """
    import lightgbm as lgb

    comuns = dict(learning_rate=0.05, num_leaves=31, min_child_samples=10, subsample=0.8,
                  subsample_freq=1, colsample_bytree=0.8, random_state=semente, verbose=-1)
    X_tr, y_tr = X.loc[mascaras["treino"], colunas], y[mascaras["treino"]]
    X_va, y_va = X.loc[mascaras["validação"], colunas], y[mascaras["validação"]]
    m = lgb.LGBMRegressor(n_estimators=800, **comuns)
    m.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], eval_metric="l1",
          callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(0)])

    ajuste = mascaras["treino"] | mascaras["validação"]
    n_arvores = int(m.best_iteration_ or 300)
    return lgb.LGBMRegressor(n_estimators=n_arvores, **comuns).fit(
        X.loc[ajuste, colunas], y[ajuste])


def ablacao(X: pd.DataFrame, y: pd.Series, mascaras: dict, blocos: dict[str, list[str]],
            ordem: list[str], mae_referencia: float, mae_piso: float) -> pd.DataFrame:
    """Treina o mesmo modelo N vezes, acrescentando um bloco de cada vez.

    A ordem é a de um projeto real: começa pelo que sai de graça do índice de tempo e
    termina pelo que custa integração de dados.
    """
    from .avaliacao import metricas

    X_te, y_te = X[mascaras["teste"]], y[mascaras["teste"]]
    acumulado: list[str] = []
    linhas = []
    for nome in ordem:
        acumulado = acumulado + blocos[nome]
        m = lgbm_simples(X, y, mascaras, acumulado)
        mae, rmse, mape = metricas(y_te, m.predict(X_te[acumulado]))
        aproveitado = 100 * (mae_referencia - mae) / (mae_referencia - mae_piso)
        linhas.append({"bloco acrescentado": nome, "variáveis": len(acumulado),
                       "MAE": round(mae, 2), "RMSE": round(rmse, 2), "MAPE (%)": round(mape, 2),
                       "% do aproveitável": round(max(aproveitado, 0.0), 1)})
    tabela = pd.DataFrame(linhas)
    tabela["ganho do bloco"] = (-tabela["MAE"].diff()).round(2)
    return tabela


def importancia_permutacao(modelo, X_teste: pd.DataFrame, y_teste, n_repeats: int = 8,
                           semente: int = 42) -> pd.Series:
    """Embaralha uma coluna de cada vez e mede quanto o MAE PIORA.

    Mais confiável do que a importância interna: é medida fora da amostra e na métrica
    que interessa. Importância negativa significa que embaralhar melhorou o modelo,
    ou seja, aquela coluna estava atrapalhando.
    """
    from sklearn.inspection import permutation_importance

    r = permutation_importance(modelo, X_teste, y_teste, n_repeats=n_repeats,
                               random_state=semente, scoring="neg_mean_absolute_error")
    return pd.Series(r.importances_mean, index=X_teste.columns).sort_values()
