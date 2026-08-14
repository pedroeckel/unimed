"""Página 1 — os dados é o que eles escondem."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from nucleo import dados as D
from nucleo import graficos as G
from nucleo import modelos as M

from . import comum
from .comum import kpi, num


def render() -> None:
    comum.selo("Etapa 1 · Dados e diagnóstico", "F1_01 (fundamentos) e F1_02 (estacionariedade)")
    st.title("📈 Os dados é o que eles escondem")

    comum.problema(
        "<b>O problema de gestão.</b> Antes de prever qualquer coisa, é preciso entender o "
        "ritmo da operação: em que horas o telefone toca, que dias são cheios, o que o "
        "calendário explica é o que ele não explica. Toda escolha de modelo daqui para a "
        "frente vem desta leitura.")

    horaria = comum.central_horaria()
    diaria = comum.central_diaria()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi(f"{len(horaria):,}".replace(",", "."), "horas de operação", "info")
    with c2:
        kpi(num(horaria['n_ligacoes'].mean(), 1), "ligações por hora (média)")
    with c3:
        kpi(num(diaria['n_ligacoes'].mean(), 0), "ligações por dia (média)")
    with c4:
        kpi(f"{diaria['n_ligacoes'].min():.0f} a {diaria['n_ligacoes'].max():.0f}",
            "menor e maior dia", "warning")

    st.caption(f"Período: {horaria.index.min().date()} a {horaria.index.max().date()} · "
               "cada linha é uma hora de operação da central.")

    abas = st.tabs(["A série", "Decomposição", "Perfis (o mapa de escala)",
                    "Estacionariedade", "ACF e PACF", "Laboratório dos componentes"])

    # ── A série ────────────────────────────────────────────────────────────────
    with abas[0]:
        fig = G.serie(diaria.index, diaria["n_ligacoes"], "Total por dia", G.CINZA,
                      "Dois anos de central, total por dia", "Ligações por dia",
                      media_movel=14, altura=360)
        G.marcar_feriados(fig, D.FERIADOS, diaria.index)
        st.plotly_chart(fig, width="stretch")

        semana = st.select_slider(
            "Semana para o zoom (hora a hora)",
            options=list(pd.date_range(horaria.index.min(), horaria.index.max() - pd.Timedelta(days=7),
                                       freq="7D").date),
            value=pd.Timestamp("2025-06-02").date())
        inicio = pd.Timestamp(semana)
        recorte = horaria.loc[inicio:inicio + pd.Timedelta(days=13, hours=23)]
        st.plotly_chart(G.serie(recorte.index, recorte["n_ligacoes"], "Ligações por hora",
                                G.AZUL2, "Zoom de duas semanas", "Ligações por hora",
                                altura=300), width="stretch")

        surto_max = diaria["surto"].max()
        dias_surto = int((diaria["surto"] > 0.05).sum())
        comum.leitura(f"""
No painel de cima, a linha cinza é o total diário e a verde é a média móvel de 14 dias.
Ela <b>não é plana nem puramente sazonal</b>: tem platôs e corcovas que duram semanas.
Essas corcovas são as <b>ondas epidemiológicas</b>, o estado latente que plantamos na base
&mdash; em {dias_surto} dos {len(diaria)} dias houve alguma onda ativa, chegando a somar
<b>{num(100 * surto_max, 0)}%</b> ao nível no pico. As linhas vermelhas pontilhadas são os
feriados nacionais, e elas caem quase sempre sobre os vales mais fundos.<br><br>
No zoom, o <b>ciclo de 24 horas</b> se repete dia após dia e o <b>ciclo de 7 dias</b>
aparece como a diferença de altura entre dias úteis e fim de semana. São esses dois ciclos
que os modelos das próximas etapas vão precisar aprender &mdash; e a onda epidemiológica,
que <b>nenhuma coluna de calendário captura</b>, é o que vai separar um modelo bom de um
modelo médio.
""")

    # ── Decomposição ───────────────────────────────────────────────────────────
    with abas[1]:
        comum.info("Os quatro componentes de uma série temporal", r"""
Toda série temporal pode ser lida como a combinação de quatro componentes:

| Componente | O que é | Exemplo na operadora |
| --- | --- | --- |
| **Tendência** $T_t$ | movimento de longo prazo | crescimento da carteira de beneficiários |
| **Sazonalidade** $S_t$ | padrão que se repete em intervalo **fixo** | o ciclo de 24h e o de 7 dias |
| **Ciclo** $C_t$ | oscilação sem período fixo | a onda epidemiológica |
| **Resíduo** $R_t$ | o que sobra, imprevisível | a variação do dia a dia |

No modelo aditivo, $y_t = T_t + S_t + C_t + R_t$.
""")
        nivel = st.radio("Granularidade", ["Diária (ciclo semanal, s=7)",
                                           "Horária (ciclo diário, s=24)"], horizontal=True)
        from statsmodels.tsa.seasonal import seasonal_decompose

        if nivel.startswith("Diária"):
            s, periodo = diaria["n_ligacoes"], 7
        else:
            s, periodo = horaria["n_ligacoes"].iloc[:24 * 60], 24

        r = seasonal_decompose(s, model="additive", period=periodo)
        st.plotly_chart(G.decomposicao(s.index, s.to_numpy(), r.trend, r.seasonal, r.resid),
                        width="stretch")

        amp = float(np.nanmax(r.seasonal) - np.nanmin(r.seasonal))
        dp_res = float(np.nanstd(r.resid))
        tend = pd.Series(r.trend).dropna()
        comum.leitura(f"""
A decomposição separou a série em quatro faixas. A <b>tendência</b> sai de
{num(tend.iloc[0], 0)} e chega a {num(tend.iloc[-1], 0)}, ou seja, o nível de longo prazo
cresceu <b>{num(100 * (tend.iloc[-1] / tend.iloc[0] - 1), 1)}%</b> no período &mdash; e a
carteira aumentando. A <b>sazonalidade</b> tem amplitude de <b>{num(amp, 0)}</b> entre o
vale e o pico do ciclo, e o <b>resíduo</b> ficou com desvio-padrão de {num(dp_res, 1)}.<br><br>
A lição: quase toda a variação é explicada por tendência mais sazonalidade. O que sobra no
resíduo não é só ruído &mdash; parte dele é a onda epidemiológica, que a decomposição
clássica <b>não sabe isolar</b> porque ela não tem período fixo.
""")

    # ── Perfis ─────────────────────────────────────────────────────────────────
    with abas[2]:
        perfil_hora = horaria.groupby(horaria.index.hour)["n_ligacoes"].mean()
        perfil_dia = horaria.groupby(horaria.index.dayofweek)["n_ligacoes"].mean()
        f1, f2 = G.perfil_duplo(perfil_hora, perfil_dia)
        e, d = st.columns(2)
        e.plotly_chart(f1, width="stretch")
        d.plotly_chart(f2, width="stretch")

        comum.leitura(f"""
A esquerda, o retrato de um call center: vale de madrugada
(<b>{num(perfil_hora.min(), 1)} ligações/h por volta de {perfil_hora.idxmin()}h</b>), forte
subida pela manhã até o <b>pico de {num(perfil_hora.max(), 1)} ligações/h às
{perfil_hora.idxmax()}h</b>, queda no horário de almoço e segundo platô à tarde. São
<b>{num(perfil_hora.max() / perfil_hora.min(), 1)} vezes</b> de diferença entre o vale e o pico.<br><br>
À direita, o ciclo semanal: <b>{G.NOMES_DIAS[int(perfil_dia.idxmax())]} é o dia mais cheio</b>
({num(perfil_dia.max(), 1)}) e <b>{G.NOMES_DIAS[int(perfil_dia.idxmin())]} o mais calmo</b>
({num(perfil_dia.min(), 1)}).<br><br>
Para o gestor, esses dois perfis <b>são o mapa de escala</b>: dizem em que horas e em que
dias colocar mais atendentes. Para o modelo, são a sazonalidade que ele precisa reproduzir.
E guarde o perfil da esquerda: ele volta na etapa 5, como a tabela que desce a previsão
diária para a hora.
""")

    # ── Estacionariedade ───────────────────────────────────────────────────────
    with abas[3]:
        comum.info("O teste de Dickey-Fuller Aumentado (ADF)", """
- **Hipótese nula ($H_0$):** a série **não** é estacionária (possui raiz unitária).
- **Hipótese alternativa:** a série é estacionária.

Regra de decisão: **p-valor abaixo de 0,05 → rejeitamos $H_0$ → série estacionária**.

Isso importa porque a estacionariedade é o **pressuposto central do ARIMA**: os componentes
AR e MA só têm interpretação válida sobre uma série estacionária. O parâmetro $d$ do
ARIMA é, literalmente, quantas diferenciações foram necessárias.
""")
        n_dif = st.slider("Número de diferenciações (d)", 0, 2, 0)
        s = diaria["n_ligacoes"]
        for _ in range(n_dif):
            s = s.diff()
        s = s.dropna()

        est, p, veredito = M.teste_adf(s)
        c1, c2, c3 = st.columns(3)
        with c1:
            kpi(num(est, 3), "Estatística ADF", "info")
        with c2:
            kpi(num(p, 4), "p-valor", "danger" if p >= 0.05 else "")
        with c3:
            kpi("NAO estacionária" if p >= 0.05 else "ESTACIONARIA", "Veredito",
                "danger" if p >= 0.05 else "")

        fig = G.serie(s.index, s.to_numpy(), "Série", G.VERDE2,
                      f"Série com d = {n_dif}", "Ligações por dia", media_movel=7)
        if n_dif > 0:
            fig.add_hline(y=0, line=dict(color=G.VERMELHO, dash="dash"))
        st.plotly_chart(fig, width="stretch")

        _, p0, _ = M.teste_adf(diaria["n_ligacoes"])
        _, p1, _ = M.teste_adf(diaria["n_ligacoes"].diff())
        comum.leitura(f"""
Na série original, o p-valor é <b>{num(p0, 4)}</b>. Depois de <b>uma única diferença</b>,
ele cai para <b>{num(p1, 4)}</b>, bem abaixo de 0,05: a série passa a oscilar em torno de
zero, sem subir nem descer no longo prazo.<br><br>
Conclusão prática: <b>uma diferenciação basta</b>, e esse é exatamente o parâmetro
<b>d = 1</b> que o SARIMA vai usar na etapa 3. Repare também no que a diferenciação
<b>custa</b>: ela remove o nível, e com ele a informação de escala. Nenhum modelo de
árvore precisa disso &mdash; eles não têm pressuposto de estacionariedade.
""")

    # ── ACF e PACF ─────────────────────────────────────────────────────────────
    with abas[4]:
        from statsmodels.tsa.stattools import acf, pacf

        granularidade = st.radio("Série", ["Diária (lags em dias)", "Horária (lags em horas)"],
                                 horizontal=True)
        if granularidade.startswith("Diária"):
            base = diaria["n_ligacoes"].diff().dropna()
            n_lags, destaque, unidade = 28, [7, 14, 21, 28], "dias"
        else:
            base = horaria["n_ligacoes"]
            n_lags, destaque, unidade = 48, [24, 48], "horas"

        a = acf(base, nlags=n_lags)
        p_ = pacf(base, nlags=min(n_lags, len(base) // 2 - 1), method="ywm")
        limite = 1.96 / np.sqrt(len(base))

        # As duas figuras parecem a mesma coisa e respondem a perguntas diferentes.
        # Sem isso explicito, o aluno le as duas como "correlacao com o passado".
        singular = "dia" if unidade == "dias" else "hora"
        ciclo = destaque[0]
        st.markdown("Os dois gráficos abaixo respondem a **perguntas diferentes** sobre a "
                    "memória da série.")

        ex, px = st.columns(2)
        with ex:
            st.markdown(f"""
##### ACF — função de autocorrelação
Pergunta:

> *“O valor de hoje está correlacionado com o valor de 1 {singular} atrás? 2 {unidade} atrás?
> 3 {unidade} atrás? … {ciclo} {unidade} atrás?”*

Formalmente, no lag $k$:
""")
            st.latex(r"\mathrm{ACF}(k) \;=\; \mathrm{Corr}\big(y_t,\; y_{t-k}\big)")
            st.caption(
                f"É a correlação TOTAL, incluindo o que chega por caminho indireto: se hoje "
                f"depende de ontem e ontem depende de anteontem, a ACF acusa correlação em "
                f"k = 2 mesmo que anteontem não influencie hoje diretamente.")

        with px:
            st.markdown(f"""
##### PACF — função de autocorrelação parcial
Pergunta algo mais específico:

> *“Quanto o valor de $k$ {unidade} atrás explica **diretamente** o valor de hoje, depois de
> descontar o efeito dos lags intermediários?”*
""")
            st.latex(r"\mathrm{PACF}(k) \;=\; \mathrm{Corr}\big(y_t,\; y_{t-k} \;\big|\; "
                     r"y_{t-1}, y_{t-2}, \ldots, y_{t-k+1}\big)")
            st.caption(
                "É o que sobra da correlação depois de remover a influência de tudo o que está "
                "no meio do caminho. Por isso ela costuma cair rápido: só os primeiros lags "
                "têm efeito próprio.")

        e, d = st.columns(2)
        e.plotly_chart(G.correlograma(a, limite, f"ACF ({unidade})", destaque=destaque),
                       width="stretch")
        d.plotly_chart(G.correlograma(p_, limite, f"PACF ({unidade})", destaque=destaque),
                       width="stretch")

        picos = ", ".join(f"lag {k} = {num(a[k], 2)}" for k in destaque if k < len(a))
        comum.leitura(f"""
Cada barra é a correlação da série com ela mesma defasada; a faixa pontilhada é o intervalo
de confiança (barras dentro dela são compatíveis com ruído).<br><br>
Na <b>ACF</b>, os picos que se destacam são exatamente os múltiplos do ciclo:
<b>{picos}</b>. Essa repetição é a assinatura da sazonalidade, e é a justificativa direta
para usar <b>s = {'7' if granularidade.startswith('Diária') else '24'}</b> no SARIMA.<br><br>
Na <b>PACF</b>, as barras despencam depois dos primeiros lags: um componente
autorregressivo de ordem baixa já captura boa parte da estrutura. Na prática, a ACF orienta
o <b>q</b> e a PACF orienta o <b>p</b> do ARIMA.
""")

    # ── Laboratório ────────────────────────────────────────────────────────────
    with abas[5]:
        st.markdown("Mexa nos componentes e veja a série se transformar. "
                    "E o jeito mais direto de sentir o peso de cada um separadamente.")
        c1, c2, c3 = st.columns(3)
        amp_diaria = c1.slider("Amplitude do ciclo diário", 0.0, 2.0, 1.0, 0.1)
        amp_semanal = c2.slider("Amplitude do ciclo semanal", 0.0, 3.0, 1.0, 0.1)
        forca_surto = c3.slider("Forca da onda epidemiológica", 0.0, 3.0, 1.0, 0.1)

        base_h = horaria.iloc[:24 * 21]
        hora = base_h.index.hour.to_numpy()
        dsem = base_h.index.dayofweek.to_numpy()
        nivel = 22.0
        fator_h = 1 + amp_diaria * (D.PERFIL_HORARIO[hora] / nivel)
        fator_d = 1 + amp_semanal * (D.PERFIL_SEMANAL[dsem] / nivel)
        surto = 1 + forca_surto * base_h["surto"].to_numpy()
        simulada = nivel * fator_h * fator_d * surto

        fig = G.serie(base_h.index, base_h["n_ligacoes"], "Série real", G.CINZA,
                      "Três semanas: real contra a série que você montou", "Ligações por hora")
        fig.add_scatter(x=base_h.index, y=simulada, name="Sua série",
                        line=dict(color=G.LARANJA, width=2))
        st.plotly_chart(fig, width="stretch")

        comum.leitura("""
Zere a <b>amplitude diária</b> e as ondas de 24 horas somem: sobra apenas o degrau entre
semana e fim de semana. Zere a <b>semanal</b> e todos os dias ficam iguais. Suba a
<b>onda epidemiológica</b> e aparecem as corcovas de várias semanas &mdash; e repare que
elas <b>não seguem nenhum calendário</b>: começam em datas arbitrárias e decaem devagar.<br><br>
Essa é a distinção que organiza o módulo inteiro. Ciclo diário e semanal são
<b>sazonalidade</b>, e qualquer coluna de calendário os captura. A onda é <b>ciclo</b>, sem
período fixo, é só o <b>histórico recente</b> a percebe. Guarde isso para a etapa 2, quando
formos medir quanto vale cada bloco de variáveis.
""")
