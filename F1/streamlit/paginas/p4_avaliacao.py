"""Página 4 — avaliação honesta."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from nucleo import avaliacao as A
from nucleo import dados as D
from nucleo import graficos as G

from . import comum
from .comum import kpi, num

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


@st.cache_data(show_spinner=False)
def _walk_forward() -> pd.DataFrame:
    diaria = comum.central_diaria()
    return A.walk_forward(diaria["n_ligacoes"], A.modelo_nivel_x_perfil,
                          n_janelas=8, tamanho=30)


@st.cache_data(show_spinner=False)
def _aleatorio_versus_temporal() -> tuple[float, float]:
    """O mesmo modelo, os mesmos dados, duas formas de dividir."""
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeRegressor

    diaria = comum.central_diaria()
    n = len(diaria)
    X = np.column_stack([np.arange(n), diaria.index.dayofweek])
    y = diaria["n_ligacoes"].to_numpy()

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    mae_aleatorio = A.metricas(y_te, DecisionTreeRegressor(random_state=42)
                               .fit(X_tr, y_tr).predict(X_te))[0]
    corte = int(n * 0.8)
    mae_temporal = A.metricas(y[corte:], DecisionTreeRegressor(random_state=42)
                              .fit(X[:corte], y[:corte]).predict(X[corte:]))[0]
    return mae_aleatorio, mae_temporal


def render() -> None:
    comum.selo("Etapa 4 · Avaliação honesta", "F1_09 (MAE, RMSE, MAPE)")
    st.title("📏 Avaliação honesta")

    comum.problema(
        "<b>O problema de gestão.</b> O número que você reporta decide se o projeto continua. "
        "Uma previsão que erra 10 pacientes por dia é excelente para um hospital de 500 "
        "atendimentos é péssima para um de 30. E um modelo que erra pouco quase sempre, mas "
        "erra feio uma vez por mês, pode ser melhor ou pior do que outro que erra médio todo "
        "dia &mdash; <b>dependendo do que custa cada tipo de erro na sua operação</b>.")

    abas = st.tabs(["As três métricas", "Quando a métrica troca o vencedor",
                    "Os defeitos do MAPE", "Onde medir", "Custo assimétrico"])

    campo = comum.campo_de_jogo()

    # ── As três métricas ───────────────────────────────────────────────────────
    with abas[0]:
        real = np.array([120, 135, 128, 142, 150, 138, 145], dtype=float)
        previsto = np.array([125, 130, 131, 138, 155, 134, 148], dtype=float)
        erro = real - previsto

        tabela = pd.DataFrame({
            "dia": DIAS, "real": real.astype(int), "previsto": previsto.astype(int),
            "erro (real - previsto)": erro.astype(int),
            "erro absoluto": np.abs(erro).astype(int),
            "erro ao quadrado": (erro ** 2).astype(int),
            "erro percentual (%)": (100 * np.abs(erro) / real).round(2)})
        st.dataframe(tabela, width="stretch", hide_index=True)

        mae, rmse, mape = A.metricas(real, previsto)
        wmape = A.wmape(real, previsto)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            kpi(num(erro.mean()), "média simples dos erros", "danger")
        with c2:
            kpi(num(mae), "MAE")
        with c3:
            kpi(num(rmse), "RMSE", "info")
        with c4:
            kpi(num(mape) + "%", "MAPE", "warning")
        with c5:
            kpi(num(wmape) + "%", "WMAPE", "info")

        # As fórmulas vão em st.latex, uma por linha: bloco $$...$$ dentro de
        # markdown não é renderizado como matemática e sai como texto cru.
        with st.expander("ℹ️ As fórmulas"):
            st.latex(r"\text{MAE} = \frac{1}{n}\sum_i \left| y_i - \hat y_i \right|")
            st.latex(r"\text{RMSE} = \sqrt{\frac{1}{n}\sum_i \left( y_i - \hat y_i \right)^2}")
            st.latex(r"\text{MAPE} = \frac{100}{n}\sum_i "
                     r"\frac{\left| y_i - \hat y_i \right|}{y_i}")
            st.latex(r"\text{WMAPE} = 100 \cdot "
                     r"\frac{\sum_i \left| y_i - \hat y_i \right|}{\sum_i y_i}")
            st.markdown("""
| Métrica | Como remove o sinal | O que isso significa na prática |
| --- | --- | --- |
| **MAE** | valor absoluto | trata todos os erros com o mesmo peso |
| **RMSE** | eleva ao quadrado | **pune erros grandes** com muito mais severidade |
| **MAPE** | divide pelo real, **dia a dia** | erro em proporção ao tamanho de cada dia |
| **WMAPE** | divide pelo real **uma vez só, no fim** | erro do período em proporção ao volume do período |
""")
        comum.leitura(f"""
A média simples dos erros deu <b>{num(erro.mean())}</b>. Olhando só esse número,
concluiríamos que o modelo é praticamente perfeito. <b>E ele não é:</b> os erros diários são
{', '.join(f'{int(e):+d}' for e in erro)} &mdash; errou <b>todos os dias</b>, entre 3 e 5
ligações. Os erros para mais cancelaram os erros para menos.<br><br>
E por isso que existem MAE, RMSE e MAPE: as três impedem que erros de sinais opostos se
cancelem. Repare que <b>o RMSE ({num(rmse)}) é maior que o MAE ({num(mae)})</b>, e isso não
é coincidência: <b>o RMSE é sempre maior ou igual ao MAE</b>, e eles só ficam iguais quando
todos os erros têm exatamente o mesmo tamanho. Aqui a razão é
<b>{num(rmse / mae)}</b>, bem perto de 1, sinal de erros parecidos entre si.<br><br>
Isso da um diagnóstico de graça: <b>RMSE/MAE próximo de 1</b> significa erros homogêneos;
<b>muito acima de 1</b> denuncia poucos dias com erro enorme.
""")

        # ── WMAPE ──────────────────────────────────────────────────────────────
        st.markdown("##### WMAPE: a porcentagem que aguenta a operação real")
        st.markdown("""
O MAPE calcula **uma porcentagem por dia e tira a média delas** — cada dia pesa igual, tenha
ele 900 ligações ou 9. O WMAPE inverte a ordem das contas: **soma todos os erros, soma todos
os reais e divide uma vez só, no fim**. Cada dia passa a pesar pelo seu próprio tamanho.
""")
        st.latex(r"\underbrace{\text{MAPE} = \frac{100}{n}\sum_i "
                 r"\frac{\left| y_i - \hat y_i \right|}{y_i}}_{\text{média das porcentagens}}"
                 r"\qquad\qquad"
                 r"\underbrace{\text{WMAPE} = 100 \cdot \frac{\sum_i "
                 r"\left| y_i - \hat y_i \right|}{\sum_i y_i}}_{\text{porcentagem do total}}")

        soma_erros = float(np.abs(erro).sum())
        soma_real = float(real.sum())
        comum.leitura(f"""
Na semana da tabela acima, os erros somam <b>{num(soma_erros, 0)} ligações</b> sobre um volume
de <b>{num(soma_real, 0)} ligações</b> atendidas. O WMAPE é essa divisão:
{num(soma_erros, 0)} ÷ {num(soma_real, 0)} = <b>{num(wmape)}%</b>. A frase que ele produz é
direta: <i>"o erro da semana equivale a {num(wmape)}% de tudo o que a central recebeu"</i>.<br><br>
Repare em uma identidade útil: <b>WMAPE = MAE ÷ média dos reais</b> &mdash;
{num(mae)} ÷ {num(soma_real / len(real))} = {num(wmape)}%. Ou seja, ele é <b>o MAE traduzido
em porcentagem da operação</b>, e por isso herda a virtude do MAE: não quebra, não explode e
não muda de escala.<br><br>
Aqui MAPE ({num(mape)}%) e WMAPE ({num(wmape)}%) quase empatam, porque os sete dias têm
volumes parecidos. <b>Eles se separam quando o volume varia muito</b> &mdash; e é exatamente o
caso da série horária desta central, que vai de 2 ligações às 4h a mais de
60 no pico. Nas horas vazias, errar 2 ligações vira 100% de erro percentual, e a média
do MAPE passa a ser dominada justamente pelas horas em que <b>quase nada acontece</b>.<br><br>
<b>Quando usar.</b> Como métrica percentual padrão em contagens com volume baixo ou com zeros
— é a recomendação do módulo. Reporte-a ao lado do MAE, nunca sozinha: como a divisão acontece
no fim, <b>um dia catastrófico se dilui no total</b>, e é o RMSE que denuncia esse dia.
""")

    # ── Vencedor ───────────────────────────────────────────────────────────────
    with abas[1]:
        st.markdown("""
Imagine dois candidatos para prever chegadas, avaliados na mesma semana:

- **Modelo A, preciso e frágil.** Acerta quase na mosca seis dias, errando 1 paciente por dia.
  No sétimo, não enxerga um evento e erra 20.
- **Modelo B, mediano e constante.** Erra 5 pacientes todos os dias, sem exceção e sem surpresa.
""")
        erros_A = np.array([1, 1, 1, 1, 1, 1, 20], dtype=float)
        erros_B = np.full(7, 5.0)
        mae_A, rmse_A = np.mean(erros_A), np.sqrt(np.mean(erros_A ** 2))
        mae_B, rmse_B = np.mean(erros_B), np.sqrt(np.mean(erros_B ** 2))

        fig = G.barras(DIAS, erros_A, "Erro diário", "Erro (pacientes)", cores=G.AZUL2)
        fig.add_bar(x=DIAS, y=erros_B, name="Modelo B", marker_color=G.LARANJA)
        fig.data[0].name = "Modelo A"
        fig.update_layout(barmode="group", showlegend=True)
        st.plotly_chart(fig, width="stretch")

        st.dataframe(pd.DataFrame([
            {"modelo": "A (preciso, falha feio um dia)", "MAE": round(mae_A, 2),
             "RMSE": round(rmse_A, 2), "maior erro": int(erros_A.max()),
             "vence no": "MAE"},
            {"modelo": "B (erra médio, nunca falha feio)", "MAE": round(mae_B, 2),
             "RMSE": round(rmse_B, 2), "maior erro": int(erros_B.max()),
             "vence no": "RMSE"}]), width="stretch", hide_index=True)

        st.markdown("**Na sua operação, qual você levaria para produção?**")
        e, d = st.columns(2)
        if e.button("Modelo A — quero o menor erro típico", width="stretch"):
            st.success("""
**Você escolheu o MAE como critério.** Isso é uma afirmação sobre o negócio: o custo do erro
é **proporcional ao tamanho dele**. Faz todo sentido quando o que importa é o total de horas
de atendente contratadas no mês, porque um dia ruim se compensa com um dia bom.
""")
        if d.button("Modelo B — não posso ter um dia catastrófico", width="stretch"):
            st.success("""
**Você escolheu o RMSE como critério.** Também é uma afirmação sobre o negócio: o custo
**cresce mais rápido que o erro**. Um dia com 20 pacientes a mais significa fila, desvio de
ambulância e risco assistencial &mdash; aquele dia sozinho custa mais do que os seis dias
tranquilos juntos.
""")
        comum.leitura(f"""
<b>O modelo A vence no MAE ({num(mae_A)} contra {num(mae_B)}). O modelo B vence no RMSE
({num(rmse_B)} contra {num(rmse_A)}).</b> Mesmos dados, mesma semana, dois vencedores
diferentes. Não há erro de cálculo aqui, e nem uma métrica melhor que a outra: há duas
perguntas diferentes sendo respondidas.<br><br>
O <b>MAE</b> responde <i>"quanto eu erro em um dia típico?"</i>. O <b>RMSE</b> responde
<i>"quão ruim é quando dá errado?"</i>. A escolha entre elas <b>não é estatística, é
operacional</b>, e precisa ser feita <b>antes</b> de treinar &mdash; métrica escolhida depois
dos resultados vira justificativa.
""")

    # ── MAPE ───────────────────────────────────────────────────────────────────
    with abas[2]:
        st.markdown("##### Defeito 1: divide por zero")
        real_m = np.array([3, 1, 0, 2, 0, 4], dtype=float)
        prev_m = np.array([2, 2, 1, 2, 1, 3], dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            pct = np.abs((real_m - prev_m) / np.where(real_m == 0, np.nan, real_m))
        st.dataframe(pd.DataFrame({"hora": ["2h", "3h", "4h", "5h", "6h", "7h"],
                                   "real": real_m.astype(int), "previsto": prev_m.astype(int),
                                   "erro %": np.where(np.isnan(pct), np.inf, pct * 100).round(1)}),
                     width="stretch", hide_index=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            kpi("∞", "MAPE — a métrica quebrou", "danger")
        with c2:
            kpi(num(np.mean(np.abs(real_m - prev_m))), "MAE — continua funcionando")
        with c3:
            kpi(num(A.wmape(real_m, prev_m), 1) + "%", "WMAPE — alto mas verdadeiro", "info")

        st.markdown("##### Defeito 2: é assimétrico")
        st.dataframe(pd.DataFrame([
            {"situação": "Previu a METADE (50)", "real": 100, "previsto": 50,
             "erro absoluto": 50, "MAPE": "50%"},
            {"situação": "Previu o DOBRO (200)", "real": 100, "previsto": 200,
             "erro absoluto": 100, "MAPE": "100%"},
            {"situação": "Previu ZERO", "real": 100, "previsto": 0,
             "erro absoluto": 100, "MAPE": "100%  ← o teto para quem subestima"},
            {"situação": "Previu o TRIPLO (300)", "real": 100, "previsto": 300,
             "erro absoluto": 200, "MAPE": "200%"}]), width="stretch", hide_index=True)

        with st.expander("ℹ️ As duas alternativas"):
            st.markdown("**WMAPE** (MAD/Mean ratio): divide a **soma** dos erros pela "
                        "**soma** dos reais.")
            st.latex(r"\text{WMAPE} = 100 \cdot "
                     r"\frac{\sum_i \left| y_i - \hat y_i \right|}{\sum_i y_i}")
            st.markdown(
                "Como a divisão acontece uma vez só, no fim, **um zero isolado não quebra "
                "nada** — ele entra no denominador da soma e pronto. É a métrica percentual "
                "recomendada como padrão em séries com valores pequenos ou com zeros. "
                "Na tabela do defeito 1, enquanto o MAPE virou infinito, o WMAPE devolveu "
                f"**{num(A.wmape(real_m, prev_m), 1)}%** — um número alto, porque o modelo "
                "erra mesmo, mas um número que existe.")

            st.markdown("**MASE**: divide o MAE do modelo pelo MAE de uma previsão ingênua.")
            st.latex(r"\text{MASE} = \frac{\text{MAE}_{\text{modelo}}}"
                     r"{\text{MAE}_{\text{ingênuo}}}")
            st.markdown("Leitura imediata: **abaixo de 1, o modelo é melhor do que a regra "
                        "boba.**")
        comum.leitura("""
<b>Divisão por zero.</b> Naquelas horas de madrugada, duas tiveram zero chegadas. O MAPE
virou <b>infinito</b> e deixou de existir como número, enquanto o MAE seguiu funcionando.
E a saída comum &mdash; "vou ignorar as horas com zero" &mdash; é pior do que parece: você
passa a avaliar o modelo <b>apenas nas horas movimentadas</b>, é o número que sai não
representa a operação inteira.<br><br>
<b>Assimetria.</b> Quem subestima <b>nunca ultrapassa 100%</b> de MAPE, porque o pior caso é
prever zero. Quem superestima não tem limite. Consequência prática: um processo de seleção
que otimize MAPE vai, sistematicamente, <b>preferir o modelo mais tímido</b>. Em saúde isso é
grave, porque subdimensionar escala costuma custar mais caro do que sobredimensionar.
""")

    # ── Onde medir ─────────────────────────────────────────────────────────────
    with abas[3]:
        st.markdown("##### O erro que mais engana: dividir os dados de forma aleatória")
        mae_aleatorio, mae_temporal = _aleatorio_versus_temporal()
        c1, c2, c3 = st.columns(3)
        with c1:
            kpi(num(mae_aleatorio), "MAE com divisão ALEATORIA", "danger")
        with c2:
            kpi(num(mae_temporal), "MAE com divisão cronológica")
        with c3:
            kpi(f"{num(100 * (mae_temporal - mae_aleatorio) / mae_temporal, 0)}%",
                "de otimismo indevido", "warning")

        comum.leitura(f"""
O mesmo modelo, os mesmos dados, duas formas de dividir. A divisão aleatória fez o modelo
parecer <b>{num(100 * (mae_temporal - mae_aleatorio) / mae_temporal, 0)}% melhor do que ele
é</b>.<br><br>
O motivo é simples de enxergar: ao sortear linhas, o dia 15 de março cai no treino e o dia
16 cai no teste. O modelo aprende com o dia 15 e é avaliado no 16, que é o vizinho e se
parece muito com ele. Em produção nada disso acontece: você treina com <b>todo o passado</b>
e prevê um futuro que <b>ninguém viu</b>.<br><br>
A regra é curta e absoluta: <b>em série temporal, a divisão é sempre cronológica.</b>
Treino no passado, teste no futuro, e nunca o contrário.
""")

        st.markdown("---")
        st.markdown("##### Walk-forward: um holdout só pode enganar")
        st.code("janela 1:  [====== treino ======][teste]\n"
                "janela 2:  [======== treino ========][teste]\n"
                "janela 3:  [========== treino ==========][teste]")
        wf = _walk_forward()
        st.plotly_chart(G.barras(wf["janela"], wf["MAE"],
                                 "MAE do MESMO modelo em 8 janelas consecutivas de 30 dias",
                                 "MAE (ligações/dia)", "Janela",
                                 texto=[f"{v:.1f}" for v in wf["MAE"]]), width="stretch")
        st.dataframe(wf, width="stretch", hide_index=True)

        comum.leitura(f"""
O <b>mesmo modelo</b>, avaliado em oito períodos consecutivos, produziu MAEs bem diferentes
entre si: a média fica em <b>{num(wf['MAE'].mean())}</b>, a melhor janela marca
<b>{num(wf['MAE'].min())}</b> e a pior chega a <b>{num(wf['MAE'].max())}</b> &mdash; uma
diferença de <b>{num(100 * (wf['MAE'].max() - wf['MAE'].min()) / wf['MAE'].min(), 0)}%</b>
entre as duas.<br><br>
Pense no que isso significa. Se o seu relatório tivesse caido por acaso na melhor janela,
você reportaria {num(wf['MAE'].min())}. Se tivesse caido na pior, {num(wf['MAE'].max())}.
O mesmo modelo, o mesmo código, e quase o dobro na conclusão.<br><br>
<b>Um único holdout não é um número, é um sorteio.</b> Reporte sempre a média <b>e a
dispersão</b> entre janelas &mdash; a dispersão é uma informação tão valiosa quanto a média,
porque ela diz o quanto você pode confiar no próximo mês.
""")

    # ── Custo assimétrico ──────────────────────────────────────────────────────
    with abas[4]:
        st.markdown("""
Todas as métricas até aqui são **simétricas**: errar 10 para mais e 10 para menos contam
exatamente o mesmo. Em quase nenhuma operação de saúde isso é verdade.

Faltar um atendente significa fila, tempo de espera, reclamação e risco de perder o SLA
regulatório. Sobrar um atendente significa uma hora paga sem produção. São dois custos reais
e **de tamanhos bem diferentes**.
""")
        e, d = st.columns(2)
        custo_falta = e.slider("Custo de FALTAR (por ligação não atendida)", 1.0, 8.0, 3.0, 0.5)
        custo_sobra = d.slider("Custo de SOBRAR (por ligação a mais dimensionada)",
                               0.5, 3.0, 1.0, 0.5)

        previsao = st.session_state.get("previsao_teste")
        if previsao is None:
            previsao = comum.referencias()["Média dos 4 últimos mesmos dias"]
            st.caption("Usando a referência simples porque nenhum campeão foi definido "
                       "na etapa 3.")

        curva = A.curva_margem(campo["y_teste"], previsao, custo_falta, custo_sobra)
        fig = G.curva_dupla(curva["margem_%"], curva["MAE"], curva["custo"],
                            "MAE (simétrico)", "Custo real da operação",
                            "O MAE elege margem zero; o custo elege outra coisa",
                            "", "Margem de segurança aplicada à previsão")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(curva.drop(columns=["margem"]), width="stretch", hide_index=True)

        melhor_custo = curva.loc[curva["custo"].idxmin()]
        melhor_mae = curva.loc[curva["MAE"].idxmin()]
        with st.expander("ℹ️ A fórmula"):
            st.latex(r"\text{Custo} = c_{\text{falta}} \cdot "
                     r"\overline{\max(y - \hat y,\, 0)} \;+\; c_{\text{sobra}} \cdot "
                     r"\overline{\max(\hat y - y,\, 0)}")
            st.markdown("Não exige matemática nova: basta separar a parte do erro em que "
                        "**faltou** da parte em que **sobrou** e dar pesos diferentes a "
                        "cada uma.")
        comum.leitura(f"""
Conforme a margem sobe, a <b>falta média despenca</b> (de
{num(curva['falta média'].iloc[0])} para {num(curva['falta média'].iloc[-1])}) e a
<b>sobra cresce sem parar</b>. O MAE, que soma as duas sem distinguir, só piora &mdash; e
por isso ele elege a margem <b>{melhor_mae['margem_%']}</b>.<br><br>
Com o custo de faltar valendo {num(custo_falta, 1)}x o de sobrar, o custo total <b>cai</b> ao
sair da margem zero e atinge o mínimo em <b>{melhor_custo['margem_%']}</b>. Ou seja: pelo
MAE, a melhor decisão é a previsão mais precisa possível; <b>pelo custo real da operação, a
melhor decisão é prever um pouco a mais</b>.<br><br>
Este é o fecho da etapa, porque mostra que a métrica não é um detalhe técnico do fim do
projeto: <b>ela é a tradução do custo do negócio para a linguagem do modelo</b>. Escolher o
MAE é afirmar que faltar e sobrar custam igual.
""")

        if st.button(f"✅ Adotar margem de {melhor_custo['margem_%']} nas etapas 6 e 7",
                     type="primary"):
            st.session_state["margem_seguranca"] = float(melhor_custo["margem"])
            st.session_state["custo_falta"] = custo_falta
            st.session_state["custo_sobra"] = custo_sobra
            st.success(f"Margem de {melhor_custo['margem_%']} registrada. "
                       "O gêmeo digital vai dimensionar a escala com ela.")
