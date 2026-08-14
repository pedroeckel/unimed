"""Página 7 — cenários e decisão."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from nucleo import gemeo as GE
from nucleo import graficos as G

from . import comum
from .comum import kpi, num
from .p6_gemeo import _previsao_horaria_padrao

CENARIOS = {
    "Operação normal": {
        "fator": 1.00, "cor": G.AZUL2,
        "descrição": "A previsão do modelo, sem nenhum ajuste.",
        "origem": "linha de base"},
    "Onda epidemiológica": {
        "fator": 1.40, "cor": G.VERMELHO,
        "descrição": "Surto respiratório em curso eleva o contato com a central.",
        "origem": "estado latente medido na própria base (F1_06)"},
    "Campanha de comunicação": {
        "fator": 1.25, "cor": G.LARANJA,
        "descrição": "Disparo de SMS em massa: pico de poucos dias, conhecido de antemão.",
        "origem": "efeito de +45,6% medido em autorizações prévia (F1_08); aqui, +25% na central"},
    "Crescimento da carteira": {
        "fator": 1.08, "cor": G.VERDE2,
        "descrição": "Entrada de um contrato coletivo grande, com 8% mais vidas.",
        "origem": "modelo de variação de carteira (F1_05)"},
    "Feriado": {
        "fator": 0.45, "cor": G.CINZA,
        "descrição": "Operação praticamente parada, com repique no dia seguinte.",
        "origem": "efeito medido na base (-55%) e pós-feriado (+7,7%) do F1_07"},
}


def render() -> None:
    comum.selo("Etapa 7 · Cenários e decisão", "E4 (análise de decisão) + o gêmeo da etapa 6")
    st.title("🎯 Cenários e prescrição de escala")

    comum.problema(
        "<b>O problema de gestão.</b> Planejar o que ainda não aconteceu. A previsão cobre o "
        "esperado; a gestão precisa saber o que fazer quando o inesperado chegar &mdash; e "
        "quanto custa estar preparado.")

    dados = st.session_state.get("previsao_horaria")
    if dados is None:
        comum.aviso_dependencia("🔮 5. Previsão operacional")
        dados = _previsao_horaria_padrao()
    dados = dados.copy()
    dados["data"] = pd.DatetimeIndex(dados["datahora"]).normalize()

    por_dia = dados.groupby("data")["previsto"].sum()
    dia_base = por_dia.idxmax()      # um dia de pico: é onde a decisão pesa

    c1, c2, c3, c4 = st.columns(4)
    dia = c1.selectbox("Dia de referência", options=list(por_dia.index.date),
                       index=list(por_dia.index.date).index(dia_base.date()))
    tma = c2.slider("TMA (min)", 2.0, 10.0, 5.0, 0.5)
    meta_sl = c3.slider("Meta de nível de serviço", 0.5, 0.95, 0.80, 0.05)
    custo_hora = c4.number_input("Custo do atendente-hora (R$)", 20.0, 120.0, 38.0, 2.0)

    do_dia = dados[dados["data"] == pd.Timestamp(dia)].sort_values("datahora")
    lam_base = do_dia["previsto"].to_numpy()
    paciencia = 3.0
    margem = float(st.session_state.get("margem_seguranca", 0.0))

    abas = st.tabs(["Cenários", "Fronteira custo × serviço", "A prescrição"])

    # ── Cenários ───────────────────────────────────────────────────────────────
    with abas[0]:
        st.markdown("Cada cenário multiplica a demanda prevista. A escala é **redimensionada** "
                    "para cada um, e o gêmeo mede o resultado.")

        escolhidos = st.multiselect("Cenários a comparar", list(CENARIOS),
                                    default=["Operação normal", "Onda epidemiológica",
                                             "Campanha de comunicação"])
        if not escolhidos:
            st.warning("Selecione ao menos um cenário.")
            return

        linhas, curvas = [], {}
        with st.spinner("Rodando o gêmeo em cada cenário..."):
            for nome in escolhidos:
                cfg = CENARIOS[nome]
                lam = lam_base * cfg["fator"] * (1 + margem)
                escala = GE.prescrever_escala(lam, tma, meta_sl)
                r = GE.rodar_replicacoes(lam, escala, tma, paciencia, n_rep=5)
                linhas.append({
                    "cenário": nome,
                    "demanda do dia": int(round(lam.sum())),
                    "atendentes-hora": int(escala.sum()),
                    "pico de atendentes": int(escala.max()),
                    "custo (R$)": round(GE.custo_escala(escala, custo_hora), 0),
                    "espera média (s)": round(r["resumo"]["espera_media_min"]["media"] * 60, 1),
                    "nível de serviço": round(r["resumo"]["nivel_servico"]["media"], 3),
                    "abandono": round(r["resumo"]["taxa_abandono"]["media"], 3),
                })
                curvas[nome] = escala

        tabela = pd.DataFrame(linhas)
        st.dataframe(tabela, width="stretch", hide_index=True)

        fig = G.escala_versus_demanda(lam_base, curvas[escolhidos[0]])
        for nome in escolhidos[1:]:
            fig.add_scatter(x=list(range(24)), y=curvas[nome], name=f"Escala — {nome}",
                            yaxis="y2", mode="lines",
                            line=dict(color=CENARIOS[nome]["cor"], width=2, shape="hv"))
        st.plotly_chart(fig, width="stretch")

        st.markdown("##### De onde vem cada cenário")
        st.dataframe(pd.DataFrame([
            {"cenário": n, "fator sobre a demanda": f"x{CENARIOS[n]['fator']:.2f}",
             "o que representa": CENARIOS[n]["descrição"], "origem do número": CENARIOS[n]["origem"]}
            for n in escolhidos]), width="stretch", hide_index=True)

        base = tabela[tabela["cenário"] == "Operação normal"]
        if len(base) and len(tabela) > 1:
            b = base.iloc[0]
            pior = tabela.loc[tabela["custo (R$)"].idxmax()]
            comum.leitura(f"""
Na <b>operação normal</b>, manter o nível de serviço em {num(100 * meta_sl, 0)}% custa
R$ {num(b['custo (R$)'], 0)} e {int(b['atendentes-hora'])} atendentes-hora.<br><br>
No cenário mais pesado selecionado (<b>{pior['cenário']}</b>), a demanda sobe para
{int(pior['demanda do dia'])} chamadas e a escala necessária vai para
{int(pior['atendentes-hora'])} atendentes-hora &mdash; um acréscimo de
<b>{num(100 * (pior['custo (R$)'] / b['custo (R$)'] - 1), 0)}%</b> no custo do dia.<br><br>
Repare no que <b>não</b> aconteceu: o nível de serviço ficou parecido entre os cenários. É o
resultado esperado, porque a escala foi <b>redimensionada</b> em cada um. A pergunta de gestão
não é "o que acontece com a fila se vier um surto" &mdash; é <b>"quanto custa manter o SLA se
vier um surto, e eu consigo mobilizar essa gente a tempo?"</b>. O gêmeo responde a primeira
parte; a segunda é uma conversa com o RH, e ela precisa acontecer <b>antes</b> do surto.
""")

    # ── Fronteira ──────────────────────────────────────────────────────────────
    with abas[1]:
        st.markdown("""
Nem toda decisão é "atingir a meta". Muitas vezes a pergunta é outra: **quanto de serviço eu
compro com cada real a mais?** A fronteira abaixo varre escalas do subdimensionado ao
generoso e mede as duas coisas ao mesmo tempo.
""")
        with st.spinner("Varrendo configurações de escala..."):
            base_escala = GE.prescrever_escala(lam_base, tma, meta_sl)
            custos, servicos, rotulos = [], [], []
            for delta in range(-3, 4):
                escala = np.maximum(base_escala + delta, 1)
                r = GE.rodar_replicacoes(lam_base, escala, tma, paciencia, n_rep=4)
                custos.append(GE.custo_escala(escala, custo_hora))
                servicos.append(r["resumo"]["nivel_servico"]["media"])
                rotulos.append(f"{delta:+d}" if delta else "meta")

        st.plotly_chart(G.fronteira(custos, servicos, rotulos), width="stretch")
        st.dataframe(pd.DataFrame({
            "ajuste na escala": rotulos,
            "atendentes-hora": [int(np.maximum(base_escala + d, 1).sum()) for d in range(-3, 4)],
            "custo (R$)": [round(c, 0) for c in custos],
            "nível de serviço": [round(s, 3) for s in servicos],
        }), width="stretch", hide_index=True)

        ganhos = np.diff(servicos) / np.maximum(np.diff(custos), 1e-9)
        joelho = int(np.argmax(ganhos < ganhos.max() * 0.35)) if len(ganhos) else 0
        comum.leitura(f"""
A curva é <b>côncava</b>, e essa forma é a coisa mais importante da tela. Sair da escala mais
enxuta para a próxima compra muitos pontos de serviço por pouco dinheiro; depois de um certo
ponto, cada real adicional compra quase nada.<br><br>
O <b>joelho</b> fica em torno do ajuste <b>{rotulos[min(joelho + 1, len(rotulos) - 1)]}</b>.
À esquerda dele, cortar custo destrói serviço de forma desproporcional; à direita, gastar mais
e desperdício. Essa é a tela que vai para a diretoria: ela não pede uma decisão técnica, pede
<b>uma escolha de posição na curva</b>.<br><br>
E vale dizer o que a curva <b>não</b> mostra: o custo de perder o beneficiário que abandonou a
ligação, é o custo regulatório de estourar prazo. Quando esses entram na conta, o ponto ótimo
se desloca para a direita &mdash; foi exatamente isso que a etapa 4 mediu com o custo
assimétrico.
""")

    # ── Prescrição ─────────────────────────────────────────────────────────────
    with abas[2]:
        escala = GE.prescrever_escala(lam_base * (1 + margem), tma, meta_sl)
        r = GE.rodar_replicacoes(lam_base, escala, tma, paciencia, n_rep=8)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi(f"{int(escala.sum())}", "atendentes-hora recomendados")
        with c2:
            kpi(f"R$ {num(GE.custo_escala(escala, custo_hora), 0)}", "custo do dia", "info")
        with c3:
            kpi(f"{num(100 * r['resumo']['nivel_servico']['media'], 1)}%",
                "nível de serviço simulado")
        with c4:
            kpi(f"{num(r['resumo']['espera_media_min']['media'] * 60, 0)}s", "espera média",
                "warning")

        turnos = GE.escala_por_turno(escala)
        turnos["custo do turno (R$)"] = [
            round(sum(escala[h] for h in horas) * custo_hora, 0) for horas in GE.TURNOS.values()]
        st.dataframe(turnos, width="stretch", hide_index=True)

        detalhe = pd.DataFrame({
            "hora": range(24),
            "chamadas previstas": np.round(lam_base, 1),
            "atendentes": escala,
            "ocupacao": np.round(GE.kpis_erlang(lam_base, escala, tma)["por_hora"]["ocupacao"], 2),
        })
        st.dataframe(detalhe, width="stretch", hide_index=True, height=260)

        st.markdown("""
##### A rotina que sai daqui

1. **D-14** — feche a escala base com o calendário (feriado, campanha, vencimento). O erro
   por horizonte da etapa 5 mostra que, a duas semanas, o modelo já degradou para "perfil
   típico do dia" — e isso basta para a escala base.
2. **D-1** — ajuste o fino com o modelo completo, que a essa altura já viu o volume de ontem
   e percebeu se há onda epidemiológica em curso.
3. **No dia** — monitore ocupação por hora. Acima de 0,85, acione o plano de contingência
   antes que a fila apareça; depois que ela aparece, já é tarde.
4. **Sempre** — reporte espera **e** abandono juntos. Espera sozinha premia a operação que
   perde beneficiário no meio do caminho.
""")

        comum.leitura(f"""
A prescrição acima não é um número mágico: é o resultado de uma cadeia inteira que você
percorreu. O <b>{int(escala.sum())} atendentes-hora</b> vem da previsão do modelo (etapas 3 e 5),
distribuida pelo perfil intradiário, ajustada pela margem de
{num(100 * margem, 0)}% que a análise de custo assimétrico recomendou (etapa 4), dimensionada
por Erlang C e validada por simulação (etapa 6).<br><br>
Cada elo dessa corrente pode ser auditado separadamente, e é isso que diferencia um número
defensável de um chute bem apresentado.
""")
