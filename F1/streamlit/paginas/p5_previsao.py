"""Página 5 — a previsão operacional."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from nucleo import avaliacao as A
from nucleo import dados as D
from nucleo import features as F
from nucleo import graficos as G
from nucleo import modelos as M

from . import comum
from .comum import kpi, num

HORIZONTE = 14


@st.cache_data(show_spinner=False)
def _curva_horizonte(n_inicios: int = 70) -> pd.DataFrame:
    """Previsão recursiva: realimenta a própria previsão nas defasagens.

    O risco tem nome, acumulação de erro: a partir do segundo passo o modelo está olhando
    para os próprios erros. O que interessa é o formato da curva.

    Os pontos de partida são dias CONSECUTIVOS, e em número múltiplo de 7. Sem isso, cada
    horizonte cairia sobre uma mistura diferente de dias da semana e a curva ficaria
    serrilhada por um artefato de amostragem, e não pelo fenômeno.
    """
    diaria = comum.central_diaria()
    X, y = comum.features_central()
    m = D.separar(X.index)
    modelo = M.lgbm_simples(X, y, m, list(X.columns))

    serie = diaria["n_ligacoes"].copy()
    indices_teste = np.flatnonzero(serie.index.isin(X.index[m["teste"]]))
    disponiveis = indices_teste[:-HORIZONTE]
    n = min(n_inicios, (len(disponiveis) // 7) * 7)
    inicios = disponiveis[:n]

    erros = np.zeros((len(inicios), HORIZONTE))
    for a, ini in enumerate(inicios):
        historico = serie.iloc[:ini].copy()
        for passo in range(HORIZONTE):
            estendida = pd.concat([historico, pd.Series([np.nan], index=[serie.index[ini + passo]])])
            Xf, _ = F.construir_features_central(estendida.to_frame("n_ligacoes").ffill())
            previsto = float(modelo.predict(Xf.iloc[[-1]])[0])
            erros[a, passo] = abs(previsto - float(serie.iloc[ini + passo]))
            historico = pd.concat([historico,
                                   pd.Series([previsto], index=[serie.index[ini + passo]])])
    return pd.DataFrame({"horizonte (dias)": np.arange(1, HORIZONTE + 1),
                         "MAE": erros.mean(axis=0).round(2)})


@st.cache_data(show_spinner=False)
def _modelo_horario_direto() -> tuple[np.ndarray, pd.DatetimeIndex, np.ndarray]:
    horaria = comum.central_horaria()
    Xh, yh = F.construir_features_horarias(horaria)
    mh = D.separar(Xh.index)
    modelo = M.lgbm_simples(Xh, yh, mh, F.COLUNAS_HORARIAS)
    previsao = modelo.predict(Xh.loc[mh["teste"], F.COLUNAS_HORARIAS])
    return previsao, Xh.index[mh["teste"]], yh[mh["teste"]].to_numpy()


def render() -> None:
    comum.selo("Etapa 5 · Previsão operacional", "F1_07 (estratégia de duas etapas)")
    st.title("🔮 Da previsão diária para a escala horária")

    comum.problema(
        "<b>O problema de gestão.</b> O modelo entrega um número por dia. A escala, porém, é "
        "montada por turno e por hora. Falta uma etapa &mdash; e ela é mais simples do que "
        "parece.")

    campo = comum.campo_de_jogo()
    X, _ = comum.features_central()
    m = comum.mascaras()
    indice_teste = X.index[m["teste"]]
    horaria = comum.central_horaria()
    perfil, perfil_medio = comum.perfis()

    previsao = st.session_state.get("previsao_teste")
    campeao = st.session_state.get("campeão")
    if previsao is None:
        previsao = comum.referencias()["Média dos 4 últimos mesmos dias"]
        campeao = "Média dos 4 últimos mesmos dias (padrão)"
        comum.aviso_dependencia("🤖 3. Modelos → aba Placar")

    mae, rmse, mape = A.metricas(campo["y_teste"], previsao)
    margem = float(st.session_state.get("margem_seguranca", 0.0))
    previsao_ajustada = np.asarray(previsao, dtype=float) * (1 + margem)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi(campeao.split(" (")[0], "modelo em uso", "info")
    with c2:
        kpi(num(mae), "MAE diário (ligações)")
    with c3:
        kpi(num(mape, 1) + "%", "MAPE diário", "info")
    with c4:
        kpi(f"{num(100 * margem, 0)}%", "margem de segurança", "warning" if margem else "neutral")

    abas = st.tabs(["Próximos 14 dias", "Duas etapas: descendo para a hora",
                    "Até onde da para prever"])

    # ── D+1 a D+14 ─────────────────────────────────────────────────────────────
    with abas[0]:
        janela = slice(-HORIZONTE, None)
        residuos = campo["y_teste"][:-HORIZONTE] - np.asarray(previsao)[:-HORIZONTE]
        q_lo, q_hi = np.quantile(residuos, [0.1, 0.9])

        fig = G.comparar_previsoes(
            indice_teste[janela], campo["y_teste"][janela],
            {campeao: previsao_ajustada[janela]},
            "Janela operacional: as duas últimas semanas do teste", "Ligações por dia",
            banda=(previsao_ajustada[janela] + q_lo, previsao_ajustada[janela] + q_hi))
        st.plotly_chart(fig, width="stretch")

        tabela = pd.DataFrame({
            "data": indice_teste[janela].date,
            "dia": [G.NOMES_DIAS[d] for d in indice_teste[janela].dayofweek],
            "previsto": previsao_ajustada[janela].round(0),
            "faixa provável": [f"{p + q_lo:.0f} a {p + q_hi:.0f}" for p in previsao_ajustada[janela]],
            "real": campo["y_teste"][janela].round(0),
            "erro": (campo["y_teste"][janela] - previsao_ajustada[janela]).round(0),
        })
        st.dataframe(tabela, width="stretch", hide_index=True)

        mae_janela = A.metricas(campo["y_teste"][janela], previsao_ajustada[janela])[0]
        comum.leitura(f"""
A faixa sombreada não vem de nenhuma hipótese de normalidade: são os <b>quantis 10% e 90%
dos resíduos</b> observados no próprio período de teste, antes desta janela. É a forma mais
honesta de declarar incerteza quando o modelo não produz intervalo por conta própria &mdash;
o que é o caso de todos os modelos de árvore.<br><br>
Nestes 14 dias o erro médio foi de <b>{num(mae_janela)}</b> ligações por dia. Repare na
coluna <b>erro</b>: os dias em que ele cresce são os de calendário atípico, e é exatamente
neles que a escala quebra.<br><br>
{'A previsão já está multiplicada pela <b>margem de segurança de ' + num(100 * margem, 0) + '%</b> que você adotou na etapa 4, então ela é deliberadamente um pouco alta: faltar custa mais do que sobrar.' if margem else 'Nenhuma margem de segurança foi aplicada &mdash; a previsão esta crua. Volte a etapa 4 se o custo de faltar for maior do que o de sobrar na sua operação.'}
""")

    # ── Duas etapas ────────────────────────────────────────────────────────────
    with abas[1]:
        st.latex(r"\hat{y}_{\text{hora}} \;=\; \underbrace{\hat{y}_{\text{dia}}}"
                 r"_{\text{modelo com todas as variáveis}} \;\times\; "
                 r"\underbrace{p(\text{hora} \mid \text{dia da semana})}"
                 r"_{\text{perfil intradiário histórico}}")
        st.markdown("""
O perfil $p$ é a fração média das chegadas do dia que acontece em cada hora, estimada
**apenas no treino** e separada por dia da semana (o perfil de sábado não é o de segunda).
E uma tabela simples, estável é fácil de auditar.
""")

        horaria_teste = horaria.loc[indice_teste[0]:indice_teste[-1] + pd.Timedelta(hours=23)]
        fracoes = np.array([
            perfil[(perfil.dia_semana == d) & (perfil.hora == h)]["fracao"].iloc[0]
            for d, h in zip(horaria_teste.index.dayofweek, horaria_teste.index.hour)])
        fracoes_medias = np.array([
            perfil_medio[(perfil_medio.dia_semana == d) & (perfil_medio.hora == h)]["fracao"].iloc[0]
            for d, h in zip(horaria_teste.index.dayofweek, horaria_teste.index.hour)])

        mapa_dia = pd.Series(previsao_ajustada, index=indice_teste)
        total_por_hora = horaria_teste.index.normalize().map(mapa_dia).to_numpy(dtype=float)
        duas_etapas = total_por_hora * fracoes

        media_treino = float(comum.central_diaria().loc[X.index, "n_ligacoes"][m["treino"]].mean())
        estatico = media_treino * fracoes_medias

        real_h = horaria_teste["n_ligacoes"].to_numpy()
        piso_h = horaria_teste["intensidade"].to_numpy()

        prev_direto, idx_direto, real_direto = _modelo_horario_direto()
        alinhado = pd.Series(prev_direto, index=idx_direto).reindex(horaria_teste.index)

        linhas = [
            ("Input estático (média histórica x perfil único)", estatico),
            ("Duas etapas (modelo diário x perfil por dia da semana)", duas_etapas),
            ("Modelo horário direto (LightGBM em 17.520 linhas)", alinhado.to_numpy()),
            ("PISO horário (intensidade verdadeira)", piso_h),
        ]
        tabela = pd.DataFrame([
            {"abordagem": nome,
             "MAE (ligações/hora)": round(A.metricas(real_h[~np.isnan(v)], np.asarray(v)[~np.isnan(v)])[0], 3),
             "RMSE": round(A.metricas(real_h[~np.isnan(v)], np.asarray(v)[~np.isnan(v)])[1], 3)}
            for nome, v in linhas])
        st.dataframe(tabela, width="stretch", hide_index=True)

        dia_exemplo = st.select_slider("Dia para inspecionar hora a hora",
                                       options=list(indice_teste.date),
                                       value=indice_teste.date[-8])
        recorte = horaria_teste.loc[str(dia_exemplo)]
        mascara = horaria_teste.index.normalize() == pd.Timestamp(dia_exemplo)
        st.plotly_chart(G.comparar_previsoes(
            recorte.index, recorte["n_ligacoes"],
            {"Duas etapas": duas_etapas[mascara], "Input estático": estatico[mascara]},
            f"{dia_exemplo} — {G.NOMES_DIAS[pd.Timestamp(dia_exemplo).dayofweek]}",
            "Ligações por hora"), width="stretch")

        m_duas = tabela.iloc[1]["MAE (ligações/hora)"]
        m_direto = tabela.iloc[2]["MAE (ligações/hora)"]
        m_est = tabela.iloc[0]["MAE (ligações/hora)"]
        m_piso = tabela.iloc[3]["MAE (ligações/hora)"]
        comum.leitura(f"""
A estratégia de <b>duas etapas</b> alcanca MAE de <b>{num(m_duas, 3)}</b> ligações por hora,
contra <b>{num(m_direto, 3)}</b> do modelo treinado <b>diretamente na série horária</b>, com
todas as features e 17.520 linhas. A diferença é de <b>{num(abs(m_duas - m_direto), 3)}</b>
&mdash; para efeito de decisão de escala, <b>nenhuma</b>. E o piso horário é {num(m_piso, 3)}.<br><br>
Isso tem três consequências práticas grandes:<br>
• <b>Um modelo em vez de dois.</b> Você treina no nível diário, onde as variáveis externas
atuam é onde há 730 observações em vez de 17.520.<br>
• <b>Muito mais fácil de explicar.</b> "Prevemos 620 ligações amanhã, e historicamente 7%
delas chegam entre 10h e 11h" é uma frase que qualquer gestor audita.<br>
• <b>Mais fácil de manter.</b> O perfil é uma tabela; modelo horário é mais um artefato para
versionar e monitorar.<br><br>
O <b>input estático</b> erra {num(m_est, 3)}, quase
{num(m_est / m_duas, 1)}x mais. No gráfico do dia, ele aparece como uma curva de altura
sempre igual, que não sabe se é segunda ou domingo, nem se há campanha. É assim que a
central é dimensionada quando não existe modelo &mdash; e é essa diferença que a etapa 6
vai converter em fila e SLA.
""")

        if st.button("💾 Enviar esta previsão horária para o gêmeo digital", type="primary"):
            st.session_state["previsao_horaria"] = pd.DataFrame({
                "datahora": horaria_teste.index,
                "previsto": duas_etapas,
                "estatico": estatico,
                "real": real_h,
                "intensidade": piso_h,
            })
            st.success("Previsão horária registrada. Siga para a etapa 6 — Gêmeo digital.")

    # ── Horizonte ──────────────────────────────────────────────────────────────
    with abas[2]:
        st.markdown("""
Até aqui previmos **um dia à frente**, sempre com o volume de ontem disponível. Mas a escala
costuma ser fechada com duas semanas de antecedência. A forma mais simples de estender o
horizonte é a **previsão recursiva**: prever amanhã, **inserir a própria previsão** no lugar do
dado observado, e repetir.

O risco é evidente e tem nome: **acumulação de erro**. A partir do segundo passo, o modelo
está olhando para os próprios erros.
""")
        if st.button("▶️ Medir o erro por horizonte (1 a 14 dias)"):
            with st.spinner("Rodando previsões recursivas..."):
                curva = _curva_horizonte()
            st.session_state["curva_horizonte"] = curva

        curva = st.session_state.get("curva_horizonte")
        if curva is not None:
            fig = G.serie(curva["horizonte (dias)"], curva["MAE"], "MAE", G.LARANJA,
                          "Erro médio por horizonte de previsão", "MAE (ligações/dia)",
                          "Dias a frente")
            fig.add_hline(y=campo["mae_referencia"], line=dict(color=G.CINZA, dash="dash"))
            fig.add_annotation(x=HORIZONTE, y=campo["mae_referencia"],
                               text="melhor referência simples", showarrow=False, yshift=12,
                               font=dict(size=10, color=G.CINZA))
            st.plotly_chart(fig, width="stretch")

            d1, d7, d14 = curva["MAE"].iloc[0], curva["MAE"].iloc[6], curva["MAE"].iloc[13]
            comum.leitura(f"""
A curva conta uma história em três atos. <b>Em D+1</b> o erro é {num(d1)} e a previsão é
confiável &mdash; é a janela útil para remanejar equipe dentro da semana. <b>Em D+7</b> ele
sobe para {num(d7)}: a informação de curto prazo, que dominava a previsão de um passo,
já se esgotou. <b>Em D+14</b> chega a {num(d14)}.<br><br>
O ponto que não é óbvio: a curva <b>satura</b> em vez de explodir. O modelo não entra em
espiral porque as colunas de <b>calendário</b> continuam sendo alimentadas com valores reais
&mdash; a hora, o dia da semana e o feriado do futuro são conhecidos. No horizonte longo, o
modelo degrada para algo próximo de "prever o perfil típico daquele dia", que é exatamente
o que a melhor referência simples faz.<br><br>
Tradução operacional: <b>feche a escala base com 14 dias usando o calendário, e ajuste o
fino em D-1 com o modelo completo.</b> Essa é a rotina que o erro por horizonte recomenda.
""")
