"""Página 6 — o gêmeo digital."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from nucleo import dados as D
from nucleo import gemeo as GE
from nucleo import graficos as G

from . import comum
from .comum import kpi, num


@st.cache_data(show_spinner=False)
def _previsao_horaria_padrao() -> pd.DataFrame:
    """Se o aluno pulou a etapa 5, monta a mesma previsão horária com o modelo padrão."""
    from nucleo import avaliacao as A

    horaria = comum.central_horaria()
    X, _ = comum.features_central()
    m = comum.mascaras()
    indice_teste = X.index[m["teste"]]
    perfil, perfil_medio = comum.perfis()

    previsao = comum.referencias()["Média dos 4 últimos mesmos dias"]
    recorte = horaria.loc[indice_teste[0]:indice_teste[-1] + pd.Timedelta(hours=23)]
    fr = np.array([perfil[(perfil.dia_semana == d) & (perfil.hora == h)]["fracao"].iloc[0]
                   for d, h in zip(recorte.index.dayofweek, recorte.index.hour)])
    fr_med = np.array([perfil_medio[(perfil_medio.dia_semana == d)
                                    & (perfil_medio.hora == h)]["fracao"].iloc[0]
                       for d, h in zip(recorte.index.dayofweek, recorte.index.hour)])
    mapa = pd.Series(previsao, index=indice_teste)
    total = recorte.index.normalize().map(mapa).to_numpy(dtype=float)
    media_treino = float(comum.central_diaria().loc[X.index, "n_ligacoes"][m["treino"]].mean())
    return pd.DataFrame({"datahora": recorte.index, "previsto": total * fr,
                         "estatico": media_treino * fr_med,
                         "real": recorte["n_ligacoes"].to_numpy(),
                         "intensidade": recorte["intensidade"].to_numpy()})


@st.cache_data(show_spinner=False)
def _simular(lam: tuple, escala: tuple, tma: float, paciencia: float, n_rep: int) -> dict:
    r = GE.rodar_replicacoes(np.array(lam), np.array(escala), tma, paciencia, n_rep)
    return {"resumo": r["resumo"], "esperas": r["esperas"],
            "por_replicacao": r["por_replicacao"]}


def render() -> None:
    comum.selo("Etapa 6 · Gêmeo digital", "SimPy (D9/D10) + Erlang C")
    st.title("🏥 O gêmeo digital da central")

    comum.problema(
        "<b>O problema de gestão.</b> Previsão não é decisão. O gestor não pergunta "
        "\"qual será o MAE?\"; ele pergunta <b>quantos atendentes escalar em cada turno</b>, e "
        "o que acontece com a fila se ele errar. Esta é a página que traduz erro de previsão "
        "em fila, nível de serviço e custo.")

    dados = st.session_state.get("previsao_horaria")
    if dados is None:
        comum.aviso_dependencia("🔮 5. Previsão operacional")
        dados = _previsao_horaria_padrao()
    dados = dados.copy()
    dados["data"] = pd.DatetimeIndex(dados["datahora"]).normalize()

    # Dia padrão: aquele em que o input estático mais erra. É nos dias atípicos que a
    # operação quebra; na média dos dias, tanto faz.
    por_dia = dados.groupby("data")[["real", "estatico"]].sum()
    dia_padrao = (por_dia["real"] - por_dia["estatico"]).abs().idxmax()

    e, d = st.columns([2, 3])
    with e:
        dia = st.selectbox("Dia da operação", options=list(por_dia.index.date),
                           index=list(por_dia.index.date).index(dia_padrao.date()))
        st.caption(f"Padrão: {dia_padrao.date()}, o dia do período em que o input estático "
                   "mais se afasta da realidade.")
    with d:
        c1, c2, c3, c4 = st.columns(4)
        tma = c1.slider("TMA (min)", 2.0, 10.0, 5.0, 0.5)
        paciencia = c2.slider("Paciência (min)", 0.5, 10.0, 3.0, 0.5)
        meta_sl = c3.slider("Meta de nível de serviço", 0.5, 0.95, 0.80, 0.05)
        n_rep = c4.slider("Replicações", 3, 20, 8)

    dia_ts = pd.Timestamp(dia)
    do_dia = dados[dados["data"] == dia_ts].sort_values("datahora")
    lam_real = do_dia["intensidade"].to_numpy()
    lam_previsto = do_dia["previsto"].to_numpy()
    lam_estatico = do_dia["estatico"].to_numpy()

    custo_hora = 38.0
    escala = GE.prescrever_escala(lam_previsto, tma, meta_sl)

    comum.info("Como o gêmeo funciona por dentro", """
**Motor:** SimPy, simulação de eventos discretos. As chegadas seguem um processo de Poisson
não homogêneo (a taxa muda a cada hora, vinda da previsão). Cada beneficiário disputa um
atendente; se a espera passar da sua paciência, ele **abandona** a ligação. O tempo de
atendimento é lognormal em torno do TMA. A capacidade **muda por turno**, e a redução de
escala só vale quando o atendente em curso termina a ligação &mdash; como na vida real.

**Benchmark:** a fórmula de **Erlang C** roda em paralelo. Ela é instantânea, mas assume
paciência infinita e atendimento exponencial. Serve de teste de sanidade: se a simulação e a
fórmula divergirem muito em regime estável, o bug é da simulação.

**Replicações:** uma única rodada é um sorteio. O que se reporta é a média entre replicações
independentes, com intervalo de confiança de 95%.
""")

    abas = st.tabs(["A operação do dia", "Erro de previsão → KPI", "Simulação × Erlang C"])

    # ── A operação do dia ──────────────────────────────────────────────────────
    with abas[0]:
        with st.spinner("Rodando o gêmeo..."):
            r = _simular(tuple(lam_real), tuple(escala), tma, paciencia, n_rep)
        resumo = r["resumo"]
        erlang = GE.kpis_erlang(lam_real, escala, tma)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            kpi(f"{num(resumo['espera_media_min']['media'] * 60, 0)}s",
                f"espera média (± {num(resumo['espera_media_min']['ic'] * 60, 0)}s)")
        with c2:
            sl = resumo["nivel_servico"]["media"]
            kpi(f"{num(100 * sl, 1)}%", "atendidas em até 20s",
                "" if sl >= meta_sl else "danger")
        with c3:
            kpi(f"{num(100 * resumo['taxa_abandono']['media'], 1)}%", "abandono",
                "warning" if resumo["taxa_abandono"]["media"] > 0.05 else "info")
        with c4:
            kpi(f"{int(escala.sum())}", "atendentes-hora", "neutral")
        with c5:
            kpi(f"R$ {num(GE.custo_escala(escala, custo_hora), 0)}", "custo do dia", "info")

        st.plotly_chart(G.escala_versus_demanda(lam_real, escala,
                                                erlang["por_hora"]["ocupacao"]),
                        width="stretch")

        e, d_ = st.columns([3, 2])
        with e:
            p90 = float(np.quantile(r["esperas"], 0.9)) if len(r["esperas"]) else 0.0
            st.plotly_chart(G.histograma(r["esperas"] * 60, "Distribuição do tempo de espera",
                                         "Espera (segundos)", p90 * 60), width="stretch")
        with d_:
            st.dataframe(GE.escala_por_turno(escala), width="stretch", hide_index=True)
            st.caption(f"Ocupação máxima do dia: {num(erlang['ocupacao_max'], 2)}. "
                       "Acima de 0,85 a fila deixa de crescer devagar e passa a explodir.")

        hora_pico = int(np.argmax(lam_real))
        comum.leitura(f"""
No gráfico, as barras são as chamadas por hora e a linha laranja em degraus é a escala. Elas
<b>acompanham uma a outra</b>, e é essa a diferença entre uma escala dimensionada por modelo
é uma tabela fixa: no pico das {hora_pico}h são {num(lam_real[hora_pico], 0)} chamadas com
{escala[hora_pico]} atendentes; na madrugada, {num(lam_real[3], 0)} chamadas com
{escala[3]}.<br><br>
A linha vermelha pontilhada é a <b>ocupação</b>. Ela é o indicador que o gestor precisa
vigiar: a relação entre ocupação e fila <b>não é linear</b>. Sair de 0,70 para 0,80 custa
pouco; sair de 0,85 para 0,92 multiplica a espera. É por isso que dimensionar "pela média"
falha &mdash; a média esconde as horas em que a ocupação passa do joelho da curva.<br><br>
O histograma mostra que a distribuição da espera é <b>fortemente assimétrica</b>: a maioria
é atendida quase na hora, e uma cauda espera muito mais. O P90 é de
<b>{num(p90 * 60, 0)} segundos</b>, contra uma média de
{num(resumo['espera_media_min']['media'] * 60, 0)}s. <b>Reportar só a média esconde a cauda</b>,
e é a cauda que gera reclamação.
""")

    # ── Erro de previsão → KPI ────────────────────────────────────────────────
    with abas[1]:
        st.markdown("""
Este é o experimento que justifica o módulo inteiro.

O gestor dimensiona a escala a partir de uma **fonte de demanda**. Depois **o dia acontece de
verdade**. Então rodamos o gêmeo três vezes, sempre com a **demanda real**, mudando apenas a
fonte que recomendou a escala:
""")
        fontes = {
            "Média histórica (input estático)": lam_estatico,
            "Previsão do modelo": lam_previsto,
            "Demanda real (previsão perfeita, impossível)": lam_real,
        }
        with st.spinner("Rodando o gêmeo para as três fontes..."):
            tabela = GE.comparar_fontes(lam_real, fontes, tma, paciencia, meta_sl,
                                        max(n_rep // 2, 3), custo_hora)
        st.dataframe(tabela, width="stretch", hide_index=True)

        fig = G.escala_versus_demanda(lam_real, GE.prescrever_escala(lam_previsto, tma, meta_sl))
        fig.add_scatter(x=list(range(24)),
                        y=GE.prescrever_escala(lam_estatico, tma, meta_sl),
                        name="Escala do input estático", yaxis="y2", mode="lines",
                        line=dict(color=G.VERMELHO, width=2, dash="dot", shape="hv"))
        st.plotly_chart(fig, width="stretch")

        est = tabela.iloc[0]
        prev = tabela.iloc[1]
        real = tabela.iloc[2]
        delta_sl = 100 * (prev["nível de serviço"] - est["nível de serviço"])
        delta_custo = est["custo do dia (R$)"] - prev["custo do dia (R$)"]
        comum.leitura(f"""
Leia a tabela linha a linha, porque ela é a resposta à pergunta "e daí?".<br><br>
Dimensionando pela <b>média histórica</b>, o dia termina com nível de serviço de
<b>{num(100 * est['nível de serviço'], 1)}%</b>, espera média de
{num(est['espera média (min)'] * 60, 0)}s e {num(100 * est['abandono'], 1)}% de abandono,
a um custo de R$ {num(est['custo do dia (R$)'], 0)}.<br><br>
Dimensionando pela <b>previsão do modelo</b>, o nível de serviço vai para
<b>{num(100 * prev['nível de serviço'], 1)}%</b> &mdash; uma diferença de
<b>{num(delta_sl, 1)} pontos</b> &mdash; com espera de
{num(prev['espera média (min)'] * 60, 0)}s e custo de R$ {num(prev['custo do dia (R$)'], 0)}
({'economia' if delta_custo > 0 else 'acréscimo'} de R$ {num(abs(delta_custo), 0)}).<br><br>
E a <b>previsão perfeita</b>, impossível de obter, que conhece a demanda real de antemão, chega a
{num(100 * real['nível de serviço'], 1)}%. Ele é o limite: a distância entre a linha da
previsão e a dele é <b>tudo o que ainda há para ganhar melhorando o modelo</b>. A distância
entre a previsão e o input estático é <b>o que já foi ganho</b>.<br><br>
Repare no gráfico: a escala do input estático (vermelha pontilhada) tem <b>a forma certa e o
nível errado</b>, porque ela não sabe que dia da semana é hoje nem que há campanha em curso.
É assim que se escala gente demais em um domingo e gente de menos numa segunda de pico.
""")

    # ── Simulação x Erlang ─────────────────────────────────────────────────────
    with abas[2]:
        st.markdown("""
Toda simulação precisa de um teste de sanidade. O nosso é a fórmula de **Erlang C**, o padrão
da indústria de call center desde 1917. Ela é exata sob hipóteses restritas: chegadas de
Poisson, atendimento **exponencial** e **paciência infinita** (ninguém desiste).

Rodamos a simulação nas mesmas condições da fórmula (sem abandono) e depois com abandono,
para ver o efeito de cada hipótese separadamente.
""")
        with st.spinner("Rodando as duas versões..."):
            sem_abandono = _simular(tuple(lam_real), tuple(escala), tma, float("inf"), n_rep)
            com_abandono = _simular(tuple(lam_real), tuple(escala), tma, paciencia, n_rep)
        erlang = GE.kpis_erlang(lam_real, escala, tma)

        comparacao = pd.DataFrame([
            {"método": "Erlang C (fórmula)",
             "espera média (s)": round(erlang["espera_media_min"] * 60, 1),
             "nível de serviço": round(erlang["nivel_servico"], 3),
             "hipóteses": "atendimento exponencial, paciência infinita"},
            {"método": "SimPy sem abandono",
             "espera média (s)": round(sem_abandono["resumo"]["espera_media_min"]["media"] * 60, 1),
             "nível de serviço": round(sem_abandono["resumo"]["nivel_servico"]["media"], 3),
             "hipóteses": "atendimento lognormal, paciência infinita"},
            {"método": "SimPy com abandono (o gêmeo)",
             "espera média (s)": round(com_abandono["resumo"]["espera_media_min"]["media"] * 60, 1),
             "nível de serviço": round(com_abandono["resumo"]["nivel_servico"]["media"], 3),
             "hipóteses": f"lognormal, paciência média de {num(paciencia, 1)} min"},
        ])
        st.dataframe(comparacao, width="stretch", hide_index=True)

        st.dataframe(com_abandono["por_replicacao"].round(3), width="stretch", hide_index=True)

        e_erlang = erlang["espera_media_min"] * 60
        e_sem = sem_abandono["resumo"]["espera_media_min"]["media"] * 60
        e_com = com_abandono["resumo"]["espera_media_min"]["media"] * 60
        comum.leitura(f"""
A fórmula de Erlang C prevê <b>{num(e_erlang, 0)}s</b> de espera média. A simulação <b>nas
mesmas hipóteses de paciência</b> devolve <b>{num(e_sem, 0)}s</b>. Estão na mesma ordem de
grandeza, e é isso que o teste de sanidade precisava mostrar: <b>o gêmeo não está com bug
estrutural</b>.<br><br>
A diferença que resta tem explicação, e ela é didática. O Erlang C assume atendimento
<b>exponencial</b> (coeficiente de variação 1); o nosso é <b>lognormal</b> com dispersão
menor. Menos variabilidade no atendimento significa <b>fila menor</b> &mdash; é por isso a
fórmula tende a ser <b>conservadora</b> aqui. Em dimensionamento, errar para o lado
conservador é aceitável; o perigoso é o contrário.<br><br>
Ligando o <b>abandono</b>, a espera cai para <b>{num(e_com, 0)}s</b>. Cuidado com essa
leitura, porque ela é uma armadilha clássica: <b>a espera média melhorou porque parte dos
beneficiários desistiu</b>. Quem abandona não entra na conta da espera. Nunca reporte tempo
de espera sem reportar <b>taxa de abandono</b> ao lado &mdash; sozinho, ele premia a
operação que perde clientes.<br><br>
A tabela de replicações mostra a variabilidade entre rodadas. Um único dia simulado não é
um resultado; a média entre replicações, com o intervalo de confiança, é.
""")
