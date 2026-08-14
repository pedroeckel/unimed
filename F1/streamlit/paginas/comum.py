"""Utilitários compartilhados pelas páginas: CSS, cartões, blocos didáticos e cache.

O núcleo (`núcleo/`) não importa Streamlit em nenhum lugar: é código puro, testável
sem subir a aplicação. Todo o cache mora aqui.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from nucleo import avaliacao as A
from nucleo import dados as D
from nucleo import features as F
from nucleo import modelos as M
from nucleo.graficos import AZUL, LARANJA, VERDE, VERDE2, VERMELHO  # noqa: F401

CSS = """
<style>
.kpi-card {
    background: linear-gradient(135deg,#1A5E3A 0%,#2E7D52 100%);
    padding:1.0rem .8rem; border-radius:12px; color:white;
    text-align:center; margin-bottom:.5rem;
}
.kpi-card.warning { background:linear-gradient(135deg,#E65100 0%,#F57C00 100%); }
.kpi-card.info    { background:linear-gradient(135deg,#1F4E79 0%,#2E86C1 100%); }
.kpi-card.neutral { background:linear-gradient(135deg,#424242 0%,#616161 100%); }
.kpi-card.danger  { background:linear-gradient(135deg,#922B21 0%,#C0392B 100%); }
.kpi-value { font-size:1.7rem; font-weight:700; line-height:1.1; }
.kpi-label { font-size:.74rem; opacity:.88; margin-top:.2rem; }
.selo {
    display:inline-block; background:#EEF3EF; color:#1A5E3A; border:1px solid #CFE0D5;
    border-radius:20px; padding:.15rem .7rem; font-size:.75rem; margin-bottom:.6rem;
}
/* As caixas didáticas têm fundo claro fixo, então a cor do texto também precisa ser
   fixa: sem isso, no tema escuro o Streamlit herda texto branco sobre fundo claro. */
.leitura {
    background:#F3F7F4; border-left:4px solid #2E7D52; color:#1F2328;
    padding:.85rem 1rem; border-radius:0 8px 8px 0; margin:.8rem 0;
    font-size:.92rem; line-height:1.55;
}
.leitura b, .leitura strong { color:#12472C; }
.alerta {
    background:#FDECEA; border-left:4px solid #C0392B; color:#1F2328;
    padding:.8rem 1rem; border-radius:0 8px 8px 0; margin:.6rem 0;
    font-size:.9rem; line-height:1.5;
}
.alerta b, .alerta strong { color:#8E2A20; }
.problema {
    background:#FFF8E1; border-left:4px solid #E65100; color:#1F2328;
    padding:.8rem 1rem; border-radius:0 8px 8px 0; margin:.4rem 0 1rem 0;
    font-size:.92rem; line-height:1.5;
}
.problema b, .problema strong { color:#A33F00; }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Blocos visuais
# ═══════════════════════════════════════════════════════════════════════════════

def selo(etapa: str, origem: str) -> None:
    st.markdown(f'<span class="selo">{etapa} &nbsp;·&nbsp; baseado em {origem}</span>',
                unsafe_allow_html=True)


def problema(texto: str) -> None:
    """O problema de gestão: por que um gestor de operadora se importa com esta página."""
    st.markdown(f'<div class="problema">{texto}</div>', unsafe_allow_html=True)


def info(titulo: str, conteudo_md: str) -> None:
    with st.expander(f"ℹ️ {titulo}"):
        st.markdown(conteudo_md)


def leitura(texto_md: str) -> None:
    """A caixa 'Lendo o resultado'. Um gráfico sem leitura guiada é decoração."""
    st.markdown(f'<div class="leitura">📖 <b>Lendo o resultado.</b><br>{texto_md}</div>',
                unsafe_allow_html=True)


def alerta(texto_md: str) -> None:
    st.markdown(f'<div class="alerta">🚨 {texto_md}</div>', unsafe_allow_html=True)


def kpi(valor: str, rotulo: str, tipo: str = "") -> None:
    classe = f"kpi-card {tipo}".strip()
    st.markdown(f'<div class="{classe}"><div class="kpi-value">{valor}</div>'
                f'<div class="kpi-label">{rotulo}</div></div>', unsafe_allow_html=True)


def sinal(v: float, casas: int = 2) -> str:
    """Formata sempre com sinal explícito: útil para saldos, que podem ser negativos."""
    return ("+" if v > 0 else "") + num(v, casas)


def num(v: float, casas: int = 2) -> str:
    """Formata no padrão brasileiro: 1.234,56."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    texto = f"{v:,.{casas}f}"
    return texto.replace(",", "@").replace(".", ",").replace("@", ".")


# ═══════════════════════════════════════════════════════════════════════════════
# Dados (cache)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def central_horaria() -> pd.DataFrame:
    return D.gerar_central_horaria()


@st.cache_data(show_spinner=False)
def central_diaria() -> pd.DataFrame:
    return D.agregar_diario(central_horaria())


@st.cache_data(show_spinner=False)
def features_central() -> tuple[pd.DataFrame, pd.Series]:
    return F.construir_features_central(central_diaria())


@st.cache_data(show_spinner=False)
def perfis() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Perfil intradiário por dia da semana e perfil único (input estático).

    Ambos estimados APENAS até o fim do treino.
    """
    c = central_horaria()
    return (D.perfil_intradiario(c, D.CORTE_VALIDACAO),
            D.perfil_intradiario_medio(c, D.CORTE_VALIDACAO))


@st.cache_data(show_spinner=False)
def pa_diario():
    return D.gerar_pa_diario()


@st.cache_data(show_spinner=False)
def autorizacoes() -> pd.DataFrame:
    return D.gerar_autorizacoes()


@st.cache_data(show_spinner=False)
def teleconsultas() -> pd.DataFrame:
    return D.gerar_teleconsultas()


# Cortes do painel de carteiras: 30 meses de treino, 6 de validação, 6 de teste.
CORTE_VAL_CARTEIRA = pd.Timestamp("2025-01-01")
CORTE_TESTE_CARTEIRA = pd.Timestamp("2025-07-01")


@st.cache_data(show_spinner=False)
def carteiras() -> pd.DataFrame:
    return D.gerar_carteiras()


@st.cache_data(show_spinner=False)
def features_carteira() -> pd.DataFrame:
    return F.construir_features_carteira(carteiras())


def mascaras_carteira() -> dict:
    dados = features_carteira()
    return D.separar(pd.DatetimeIndex(dados["data"]), CORTE_VAL_CARTEIRA, CORTE_TESTE_CARTEIRA)


def colunas_carteira() -> list[str]:
    return [c for bloco in F.BLOCOS_CARTEIRA.values() for c in bloco]


def mascaras() -> dict:
    X, _ = features_central()
    return D.separar(X.index)


def oraculo_teste() -> np.ndarray:
    """A intensidade verdadeira no período de teste: o piso do problema."""
    X, _ = features_central()
    diario = central_diaria()
    m = mascaras()
    return diario.loc[X.index, "intensidade"][m["teste"]].to_numpy()


@st.cache_data(show_spinner=False)
def referencias() -> dict[str, np.ndarray]:
    X, y = features_central()
    m = D.separar(X.index)
    return A.referencias_diarias(y, m["treino"], m["teste"])


def campo_de_jogo() -> dict:
    """Os três números que definem se um resultado é bom: pior referência, melhor
    referência e piso. Sem eles, 'MAE = 36' não informa nada."""
    X, y = features_central()
    m = D.separar(X.index)
    y_te = y[m["teste"]].to_numpy()
    refs = referencias()
    maes = {k: A.metricas(y_te, v)[0] for k, v in refs.items()}
    melhor = min(maes, key=maes.get)
    piso = A.metricas(y_te, oraculo_teste())[0]
    return {"maes_referencia": maes, "melhor_referencia": melhor,
            "mae_referencia": maes[melhor], "mae_piso": piso,
            "ingênuo": refs[A.REFERENCIA_INGENUA], "y_teste": y_te}


# ═══════════════════════════════════════════════════════════════════════════════
# Modelos (cache)
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def modelo_boosting(biblioteca: str, learning_rate: float, num_leaves: int,
                    min_child_samples: int, max_depth: int) -> dict:
    X, y = features_central()
    return M.boosting(biblioteca, X, y, D.separar(X.index), learning_rate=learning_rate,
                      num_leaves=num_leaves, min_child_samples=min_child_samples,
                      max_depth=max_depth)


@st.cache_resource(show_spinner=False)
def modelo_floresta(n_estimators: int, max_depth, min_samples_leaf: int) -> dict:
    X, y = features_central()
    return M.random_forest(X, y, D.separar(X.index), n_estimators=n_estimators,
                           max_depth=max_depth, min_samples_leaf=min_samples_leaf)


@st.cache_resource(show_spinner=False)
def modelo_arvore(max_depth: int, min_samples_leaf: int) -> dict:
    X, y = features_central()
    return M.arvore(X, y, D.separar(X.index), max_depth=max_depth,
                    min_samples_leaf=min_samples_leaf)


@st.cache_resource(show_spinner=False)
def modelo_sarima(ordem: tuple, sazonal: tuple) -> dict:
    X, y = features_central()
    return M.sarima_um_passo(y, D.separar(X.index), ordem=ordem, sazonal=sazonal)


@st.cache_resource(show_spinner=False)
def modelo_prophet(changepoint_prior_scale: float, usar_feriados: bool,
                   sazonalidade_anual: bool) -> dict:
    X, y = features_central()
    return M.prophet_previsao(y, D.separar(X.index), changepoint_prior_scale,
                              usar_feriados, sazonalidade_anual)


@st.cache_resource(show_spinner=False)
def modelo_prophet_teleconsultas() -> dict:
    """O caso original do F1_03: três anos, com changepoint de tendência plantado."""
    import logging

    logging.getLogger("cmdstanpy").disabled = True
    logging.getLogger("prophet").setLevel(logging.CRITICAL)
    from prophet import Prophet

    tele = teleconsultas()
    m = Prophet(weekly_seasonality=True, yearly_seasonality=True, daily_seasonality=False,
                changepoint_prior_scale=0.05)
    m.add_country_holidays(country_name="BR")
    m.fit(tele)
    fc = m.predict(tele[["ds"]])

    deltas = np.array(m.params["delta"]).mean(axis=0)
    relevantes = [c for c, d in zip(m.changepoints, deltas) if abs(d) > 0.01]
    return {"componentes": fc, "n_changepoints": len(m.changepoints),
            "changepoints_relevantes": relevantes}


@st.cache_data(show_spinner=False)
def contrato_de_features() -> dict | None:
    """Le o contrato salvo pelo notebook F1_08, se ele existir no repositório."""
    import json
    import os

    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "pipeline_features_autorizacao.json")
    if not os.path.exists(caminho):
        return None
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


@st.cache_data(show_spinner=False)
def grid_sarima() -> pd.DataFrame:
    X, y = features_central()
    m = D.separar(X.index)
    return M.grid_aic(y[m["treino"] | m["validação"]])


@st.cache_data(show_spinner=False)
def curva_profundidade() -> pd.DataFrame:
    X, y = features_central()
    return M.curva_profundidade(X, y, D.separar(X.index))


@st.cache_data(show_spinner=False)
def curva_bagging() -> pd.DataFrame:
    X, y = features_central()
    return M.curva_bagging(X, y, D.separar(X.index))


# ═══════════════════════════════════════════════════════════════════════════════
# Estado compartilhado entre páginas
# ═══════════════════════════════════════════════════════════════════════════════

PADROES = {
    "campeão": None,            # nome do modelo escolhido na página 3/4
    "previsao_teste": None,     # np.ndarray com a previsão diária no teste
    "margem_seguranca": 0.0,    # decidida na página 4, usada na 6 e na 7
    "custo_falta": 3.0,
    "custo_sobra": 1.0,
    "previsao_horaria": None,   # DataFrame produzido na página 5, consumido na 6
    "modelos_rodados": {},      # nome -> MAE, para o placar da visão geral
}


def iniciar_estado() -> None:
    for chave, valor in PADROES.items():
        st.session_state.setdefault(chave, valor)


def registrar_modelo(nome: str, mae: float) -> None:
    st.session_state["modelos_rodados"][nome] = float(mae)


def definir_campeao(nome: str, previsao: np.ndarray, mae: float) -> None:
    st.session_state["campeão"] = nome
    st.session_state["previsao_teste"] = np.asarray(previsao, dtype=float)
    registrar_modelo(nome, mae)


def aviso_dependencia(pagina_origem: str) -> None:
    st.info(f"Esta página consome o resultado de **{pagina_origem}**. "
            "Enquanto você não passar por la, ela usa o modelo campeão padrão.")
