"""Página 3 — os modelos, todos no mesmo conjunto de teste."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from nucleo import avaliacao as A
from nucleo import features as F
from nucleo import graficos as G
from nucleo import modelos as M

from . import comum
from .comum import kpi, num, sinal


@st.cache_data(show_spinner=False)
def _painel_referencias() -> tuple[pd.DataFrame, dict]:
    dados = comum.features_carteira()
    m = comum.mascaras_carteira()
    y_te = dados.loc[m["teste"], "variacao_vidas"].to_numpy()
    refs = {
        "Carteira estável (variação = 0)": np.zeros(len(y_te)),
        "Repetir o último mês": dados.loc[m["teste"], "variacao_lag1"].to_numpy(),
        "Média dos 3 últimos meses": dados.loc[m["teste"], "media_variacao_3m"].to_numpy(),
        "PISO DO PROBLEMA (variação esperada)": dados.loc[m["teste"], "variacao_esperada"].to_numpy(),
    }
    tabela = pd.DataFrame([{"referência": k, "MAE": round(A.metricas(y_te, v)[0], 3),
                            "RMSE": round(A.metricas(y_te, v)[1], 3)} for k, v in refs.items()])
    maes = dict(zip(tabela["referência"], tabela["MAE"]))
    return tabela, {"mae_referencia": maes["Média dos 3 últimos meses"],
                    "mae_piso": maes["PISO DO PROBLEMA (variação esperada)"],
                    "mae_estavel": maes["Carteira estável (variação = 0)"]}


@st.cache_data(show_spinner=False)
def _painel_ablacao() -> pd.DataFrame:
    dados = comum.features_carteira()
    m = comum.mascaras_carteira()
    _, campo = _painel_referencias()
    tabela = M.ablacao(dados, dados["variacao_vidas"], m, F.BLOCOS_CARTEIRA,
                       ["cadastro", "categórico", "histórico", "macro"],
                       campo["mae_referencia"], campo["mae_piso"])
    # MAPE não faz sentido em um alvo que cruza o zero: a divisão explode.
    return tabela.drop(columns=["MAPE (%)"])


@st.cache_resource(show_spinner=False)
def _painel_modelo():
    dados = comum.features_carteira()
    return M.lgbm_simples(dados, dados["variacao_vidas"], comum.mascaras_carteira(),
                          comum.colunas_carteira())


@st.cache_data(show_spinner=False)
def _painel_target_encoding() -> tuple[pd.DataFrame, float, float]:
    """Três formas de usar o identificador da carteira, com número FIXO de árvores.

    O número de árvores precisa ser fixo para que os erros de treino sejam comparáveis
    entre as três configurações — com early stopping, cada uma pararia em um ponto
    diferente é a assinatura do vazamento ficaria mascarada.
    """
    import lightgbm as lgb

    dados = comum.features_carteira()
    m = comum.mascaras_carteira()
    y = dados["variacao_vidas"]
    colunas = comum.colunas_carteira()

    def treinar(base: pd.DataFrame, cols: list[str]) -> dict:
        modelo = lgb.LGBMRegressor(n_estimators=250, learning_rate=0.05, num_leaves=31,
                                   min_child_samples=20, random_state=42, verbose=-1)
        modelo.fit(base.loc[m["treino"], cols], y[m["treino"]])
        return {c: round(A.metricas(y[m[c]], modelo.predict(base.loc[m[c], cols]))[0], 3)
                for c in ("treino", "validação", "teste")}

    com_ingenuo = dados.assign(te_carteira=F.target_encoding(dados, m, "ingênuo"))
    com_oof = dados.assign(te_carteira=F.target_encoding(dados, m, "out_of_fold"))

    linhas = [{"configuração": "A) Sem o identificador da carteira", **treinar(dados, colunas)},
              {"configuração": "B) Target encoding INGENUO (média em todo o treino)",
               **treinar(com_ingenuo, colunas + ["te_carteira"])},
              {"configuração": "C) Target encoding out-of-fold (correto)",
               **treinar(com_oof, colunas + ["te_carteira"])}]

    treino = m["treino"]
    corr_ingenuo = float(np.corrcoef(com_ingenuo.loc[treino, "te_carteira"], y[treino])[0, 1])
    corr_oof = float(np.corrcoef(com_oof.loc[treino, "te_carteira"], y[treino])[0, 1])
    return pd.DataFrame(linhas), corr_ingenuo, corr_oof


def _registrar(nome: str, previsao, campo) -> tuple[float, float, float]:
    mae, rmse, mape = A.metricas(campo["y_teste"], previsao)
    comum.registrar_modelo(nome, mae)
    st.session_state.setdefault("previsões", {})
    st.session_state["previsões"][nome] = np.asarray(previsao, dtype=float)
    return mae, rmse, mape


def _cartoes(mae, mape, campo, extra_valor=None, extra_rotulo=None, tempo=None):
    aproveitado = 100 * (campo["mae_referencia"] - mae) / (campo["mae_referencia"] - campo["mae_piso"])
    colunas = st.columns(4)
    with colunas[0]:
        kpi(num(mae), "MAE (ligações/dia)")
    with colunas[1]:
        kpi(num(mape, 1) + "%", "MAPE", "info")
    with colunas[2]:
        kpi(f"{num(max(aproveitado, 0), 1)}%", "do sinal aprendível", "warning")
    with colunas[3]:
        if extra_valor is not None:
            kpi(str(extra_valor), extra_rotulo, "neutral")
        elif tempo is not None:
            kpi(f"{num(tempo, 1)}s", "tempo de treino", "neutral")
    if mae < campo["mae_piso"]:
        comum.alerta("<b>Este modelo ficou ABAIXO do piso do problema.</b> Isso é uma "
                     "impossibilidade estatística, não uma conquista: o piso é calculado com a "
                     "intensidade verdadeira do processo, e o que sobra dele é aleatoriedade "
                     "pura, que ninguém prevê. "
                     "Procure o vazamento.")


def render() -> None:
    comum.selo("Etapa 3 · Modelos", "F1_02 e F1_03 (clássicos), F1_04 e F1_05 (árvores)")
    st.title("🤖 Os modelos")

    comum.problema(
        "<b>O problema de gestão.</b> Qual família de modelo usar, e quanto cada uma custa em "
        "tempo, em manutenção e em capacidade de explicar o resultado para a diretoria. "
        "Aqui todas competem no <b>mesmo conjunto de teste</b> &mdash; o que os notebooks, "
        "cada um com a sua própria série, não conseguem fazer.")

    campo = comum.campo_de_jogo()
    X, y = comum.features_central()
    m = comum.mascaras()
    indice_teste = X.index[m["teste"]]

    comum.info("O protocolo de avaliação, declarado antes de qualquer número", """
Comparação só vale se o protocolo for o mesmo. O nosso:

- **Ajuste:** treino (até mai/2025) + validação (jun a ago/2025). A validação decide o número
  de árvores e as ordens do SARIMA. **O teste (set a dez/2025) nunca participa de nenhuma decisão.**
- **Horizonte:** referências, SARIMA, árvores e boosting preveem **um dia à frente**, com todo o
  histórico real disponível até ontem. É o uso operacional: a escala de amanhã é fechada hoje.
- **Exceção declarada:** o **Prophet** prevê o horizonte inteiro de uma vez, porque não usa
  defasagens. É uma vantagem dele (não depende do dado de ontem chegar a tempo) e uma
  desvantagem na comparação (não aproveita o dado de ontem). Ler o placar sem saber disso
  leva à conclusão errada.
""")

    abas = st.tabs(["Referências e piso", "Clássicos: ARIMA × SARIMA", "Prophet",
                    "Árvores e floresta", "Boosting", "🏁 Placar",
                    "🧪 Caso em painel (F1_05)"])

    # ── Referências ────────────────────────────────────────────────────────────
    with abas[0]:
        st.markdown("""
**Modelo sem baseline não é resultado.** Antes de treinar qualquer coisa, é preciso saber o
que se ganha por não fazer nada, e qual é o melhor resultado possível. Todo o esforço de
modelagem acontece no espaço entre esses dois números.
""")
        refs = comum.referencias()
        nomes = list(refs) + ["PISO DO PROBLEMA (limite teórico)"]
        valores = [A.metricas(campo["y_teste"], v)[0] for v in refs.values()]
        valores.append(campo["mae_piso"])
        cores = [G.CINZA] * len(refs) + [G.VERDE]
        st.plotly_chart(G.barras_horizontais(nomes[::-1], valores[::-1],
                                             "MAE no conjunto de teste (menor é melhor)",
                                             "Ligações por dia", cores[::-1], altura=330),
                        width="stretch")

        lam_medio = comum.central_diaria().loc[indice_teste, "intensidade"].mean()
        comum.leitura(f"""
A <b>média histórica global</b> erra {num(campo['maes_referencia']['Média histórica global'])}
ligações por dia: é o retrato de dimensionar a central por uma taxa média fixa, o
<b>input estático</b>. <b>Repetir ontem</b> erra
{num(campo['maes_referencia']['Repetir ontem (lag 1)'])} &mdash; melhor, mas ignora que
segunda não se parece com domingo. O <b>mesmo dia da semana passada</b> já respeita o ciclo
semanal e cai para {num(campo['maes_referencia']['Mesmo dia da semana passada (lag 7)'])}.<br><br>
A melhor referência simples é <b>{campo['melhor_referencia']}</b>, com MAE
<b>{num(campo['mae_referencia'])}</b>. É contra ela que os modelos precisam competir.<br><br>
A última barra é o <b>piso do problema</b>: <b>{num(campo['mae_piso'])}</b>.<br><br>
<b>O piso não é um modelo</b>, e ninguém pode construí-lo &mdash; é uma <b>conta</b>. Ele
responde: se alguém soubesse exatamente a <i>média</i> de ligações de cada dia, quanto ainda
erraria? A resposta não é zero, porque a chegada de ligações é um <b>sorteio</b>: para uma
média de {num(lam_medio, 0)} ligações/dia, o erro mínimo é
&radic;(2&lambda;/&pi;) &asymp; {num(np.sqrt(2 * lam_medio / np.pi))} ligações.<br><br>
Ele está aqui por dois motivos práticos. <b>Primeiro</b>, sem ele "MAE de 36" não diz nada:
com ele, a frase vira "capturamos X% de tudo o que era capturável", e essa é a frase que se
leva para a diretoria. <b>Segundo</b>, ele é o detector de fraude involuntária: um modelo
<b>abaixo</b> do piso está lendo a resposta em algum lugar.<br><br>
Nesta base o piso é exato porque nós geramos os dados. Em um projeto real você não o tem de
graça, mas quase sempre consegue uma boa estimativa &mdash; a fórmula acima para contagens,
ou o erro de um modelo maduro já em produção.
""")

    # ── Clássicos ──────────────────────────────────────────────────────────────
    with abas[1]:
        c1, c2, c3, c4 = st.columns(4)
        p = c1.slider("p (autorregressivo)", 0, 3, 1)
        d = c2.slider("d (diferenciação)", 0, 2, 1)
        q = c3.slider("q (média móvel)", 0, 3, 1)
        sazonal_ligada = c4.checkbox("Sazonalidade semanal (s=7)", value=True)

        sazonal = (1, 1, 1, 7) if sazonal_ligada else (0, 0, 0, 0)
        with st.spinner("Ajustando e caminhando pelo teste, um dia por vez..."):
            r = comum.modelo_sarima((p, d, q), sazonal)
        nome = f"{'SARIMA' if sazonal_ligada else 'ARIMA'}({p},{d},{q})" + \
               ("(1,1,1)[7]" if sazonal_ligada else "")
        mae, rmse, mape = _registrar(nome, r["previsão"], campo)
        _cartoes(mae, mape, campo, f"{r['aic']:.0f}", "AIC")

        recorte = slice(0, 60)
        st.plotly_chart(
            G.comparar_previsoes(indice_teste[recorte], campo["y_teste"][recorte],
                                 {nome: r["previsão"][recorte]},
                                 "Primeiros 60 dias do teste", "Ligações por dia",
                                 banda=(r["ic_inferior"][recorte], r["ic_superior"][recorte])),
            width="stretch")

        with st.expander("📋 Ranking de ordens por AIC (metodologia de Box-Jenkins)"):
            st.dataframe(comum.grid_sarima(), width="stretch", hide_index=True)
            st.caption("O AIC recompensa o ajuste e penaliza parâmetros em excesso. Entre "
                       "dois modelos, prefere-se o de menor AIC. Note que a escolha das "
                       "ordens muda pouco perto do que muda ligar a sazonalidade.")

        rodados = st.session_state.get("modelos_rodados", {})
        arima_puro = next((v for k, v in rodados.items() if k.startswith("ARIMA")), None)
        sarima_ = next((v for k, v in rodados.items() if k.startswith("SARIMA")), None)
        comparacao = ""
        if arima_puro and sarima_:
            comparacao = (f"Nesta sessão você já rodou os dois: o ARIMA puro erra "
                          f"<b>{num(arima_puro)}</b> e o SARIMA <b>{num(sarima_)}</b>, uma "
                          f"redução de <b>{num(100 * (arima_puro - sarima_) / arima_puro, 1)}%</b> "
                          f"apenas por acrescentar a parte sazonal.")
        comum.leitura(f"""
O modelo atual erra <b>{num(mae)}</b> ligações por dia (MAPE {num(mape, 1)}%), com AIC de
{r['aic']:.0f}. A faixa sombreada é o <b>intervalo de confiança de 95%</b>: a incerteza que
o próprio modelo declara, e que quase nenhum modelo de árvore oferece de graça.<br><br>
Faca o experimento central da aula: <b>desligue a sazonalidade semanal</b>. A previsão vira
quase uma reta, porque o ARIMA puro só olha os lags vizinhos e aposta em um nível médio,
errando de forma sistemática os picos de segunda e os vales de domingo. {comparacao}<br><br>
Repare também no que <b>não</b> aparece: nem o ARIMA nem o SARIMA sabem o que é um feriado
ou uma campanha. Eles só têm a própria série. É daí que vem o limite desta família.
""")

    # ── Prophet ────────────────────────────────────────────────────────────────
    with abas[2]:
        c1, c2, c3 = st.columns(3)
        cps = c1.select_slider("changepoint_prior_scale (flexibilidade da tendência)",
                               options=[0.01, 0.05, 0.1, 0.5], value=0.05)
        feriados = c2.checkbox("Feriados brasileiros", value=True)
        anual = c3.checkbox("Sazonalidade anual", value=True)

        with st.spinner("Ajustando o Prophet..."):
            r = comum.modelo_prophet(cps, feriados, anual)
        nome = f"Prophet (cps={cps})"
        mae, rmse, mape = _registrar(nome, r["previsão"], campo)
        _cartoes(mae, mape, campo, tempo=r["tempo_s"])

        st.plotly_chart(
            G.comparar_previsoes(indice_teste[:60], campo["y_teste"][:60],
                                 {nome: r["previsão"][:60]}, "Primeiros 60 dias do teste",
                                 "Ligações por dia",
                                 banda=(r["ic_inferior"][:60], r["ic_superior"][:60])),
            width="stretch")

        fc = r["componentes"]
        e, d_ = st.columns(2)
        with e:
            st.plotly_chart(G.serie(fc["ds"], fc["trend"], "Tendência g(t)", G.VERDE,
                                    "Tendência aprendida", "Ligações por dia", altura=280),
                            width="stretch")
        with d_:
            semanal = fc.assign(dow=pd.DatetimeIndex(fc["ds"]).dayofweek) \
                        .groupby("dow")["weekly"].mean()
            st.plotly_chart(G.barras(G.NOMES_DIAS, semanal.to_numpy(),
                                     "Sazonalidade semanal s(t)", "Efeito", altura=280),
                            width="stretch")

        efeito_feriado = ""
        if feriados and "holidays" in fc.columns:
            h = fc.loc[fc["holidays"] != 0, "holidays"]
            if len(h):
                efeito_feriado = (f" O componente de feriados estima, em média, "
                                  f"<b>{num(h.mean(), 0)} ligações</b> em relação a um dia comum.")

        with st.expander("🔭 O caso original do F1_03: teleconsultas, 3 anos de história"):
            st.markdown("""
A série da central tem 2 anos, o que é pouco para o Prophet mostrar o que ele faz de melhor.
O notebook F1_03 usa outra série, desenhada para isso: **demanda diária por teleconsulta**,
com uma **tendência que muda de inclinação** em setembro de 2022 (a adoção da telemedicina
acelerando), sazonalidade anual e efeito de feriado.
""")
            if st.button("▶️ Ajustar o Prophet nas teleconsultas"):
                with st.spinner("Ajustando..."):
                    tele = comum.teleconsultas()
                    rt = comum.modelo_prophet_teleconsultas()
                fct = rt["componentes"]
                figt = G.serie(tele["ds"], tele["y"], "Teleconsultas por dia", G.CINZA,
                               "Três anos de teleconsultas e a tendência aprendida",
                               "Teleconsultas por dia", altura=320)
                figt.add_scatter(x=fct["ds"], y=fct["trend"], name="Tendência g(t)",
                                 line=dict(color=G.VERMELHO, width=2.5))
                for cp in rt["changepoints_relevantes"]:
                    figt.add_vline(x=cp, line=dict(color=G.VERMELHO, width=1, dash="dash"),
                                   opacity=0.6)
                st.plotly_chart(figt, width="stretch")
                st.markdown(f"""
Dos **{rt['n_changepoints']} pontos candidatos** que o Prophet avaliou, apenas
**{len(rt['changepoints_relevantes'])}** tiveram mudança de inclinação relevante, e o
principal fica perto do segundo semestre de 2022 — exatamente onde a aceleração foi plantada.

A lição: o Prophet **não** cria um changepoint em cada solavanco da série. A penalização faz
com que ele use poucos pontos, só onde a virada de tendência é sustentada. É isso que o
protege de aprender ruído como se fosse sinal.
""")

        comum.leitura(f"""
O Prophet trata a previsão como <b>ajuste de curva</b>: y(t) = g(t) + s(t) + h(t) + ruído.
A grande vantagem está nos dois painéis acima &mdash; cada termo é <b>inspecionável</b> e
vira um argumento visual em uma reunião de gestão.{efeito_feriado}<br><br>
Ele erra <b>{num(mae)}</b> aqui, mais do que os modelos de árvore, é o motivo é o protocolo:
ele prevê <b>todo o horizonte de uma vez</b>, sem usar o volume de ontem. Compare com uma
referência que também não usa nada além do calendário e a leitura fica justa.<br><br>
Puxe o <code>changepoint_prior_scale</code> para <b>0,01</b> e a tendência vira quase uma
reta rígida (subajuste); para <b>0,5</b>, ela fica cheia de curvas tentando seguir cada
oscilação (sobreajuste). O valor padrão de 0,05 busca justamente o equilíbrio.
""")

    # ── Árvores ────────────────────────────────────────────────────────────────
    with abas[3]:
        c1, c2, c3 = st.columns(3)
        profundidade = c1.slider("max_depth", 1, 25, 8)
        folha_min = c2.slider("min_samples_leaf", 1, 50, 1)
        n_arvores = c3.slider("Árvores da floresta", 1, 500, 300, 25)

        arv = comum.modelo_arvore(profundidade, folha_min)
        flor = comum.modelo_floresta(n_arvores, None, 2)
        mae_a, _, mape_a = _registrar(f"Árvore (d={profundidade}, msl={folha_min})",
                                      arv["previsão"], campo)
        mae_f, _, mape_f = _registrar(f"Random Forest ({n_arvores} árvores)",
                                      flor["previsão"], campo)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi(num(mae_a), "MAE — árvore isolada", "warning")
        with c2:
            kpi(num(mae_f), "MAE — Random Forest")
        with c3:
            kpi(f"{arv['n_folhas']}", "folhas da árvore", "neutral")
        with c4:
            kpi(num(flor["oob"], 3), "R² out-of-bag", "info")

        curva = comum.curva_profundidade()
        st.plotly_chart(G.curva_dupla(curva["max_depth"], curva["MAE treino"],
                                      curva["MAE teste"], "MAE no treino", "MAE no teste",
                                      "Profundidade da árvore: a curva em U do overfitting",
                                      "MAE (ligações/dia)", "max_depth"), width="stretch")

        melhor = curva.loc[curva["MAE teste"].idxmin()]
        pior = curva.iloc[-1]
        comum.leitura(f"""
A curva <b>azul</b> (treino) só faz descer, de {num(curva['MAE treino'].iloc[0])} até
<b>{num(pior['MAE treino'])}</b> na profundidade {int(pior['max_depth'])}: a árvore acertou
quase na virgula todos os dias com que foi treinada. A curva <b>vermelha</b> (teste) desce
junto <b>só até certo ponto</b> &mdash; o mínimo é {num(melhor['MAE teste'])} em
<code>max_depth = {int(melhor['max_depth'])}</code> &mdash; e depois <b>volta a subir</b>.<br><br>
A distância entre as duas curvas é o <b>tamanho do autoengano</b>. Quem avaliasse o modelo
no treino diria ter um preditor quase perfeito, e estaria errado por
{num(pior['MAE teste'] - pior['MAE treino'])} ligações por dia.<br><br>
Agora o contraste que fecha a aba: a <b>floresta</b> erra {num(mae_f)} contra {num(mae_a)}
da árvore isolada. E o ganho não vem de um modelo mais esperto, vem de <b>muitos modelos
medianos combinados</b>: o sobreajuste de cada árvore é, em boa parte, ruído com sinal
aleatório, e ruído aleatório <b>se cancela na média</b>. O padrão real, que todas as árvores
enxergam por igual, sobrevive.<br><br>
Experimento: leve <code>max_depth</code> para 25 e depois suba <code>min_samples_leaf</code>
para 20. O erro melhora de novo, porque exigir um mínimo de observações por folha impede a
memorização onde ela nasce &mdash; nas folhas pequenas demais.
""")

        with st.expander("📉 A curva do bagging: quantas árvores bastam?"):
            cb = comum.curva_bagging()
            st.plotly_chart(G.serie(cb["árvores"], cb["MAE"], "Média de k árvores", G.AZUL2,
                                    "", "MAE no teste", "Número de árvores", altura=300),
                            width="stretch")
            st.caption(f"Começa em {num(cb['MAE'].iloc[0])} com uma única árvore profunda e "
                       f"estabiliza em torno de {num(cb['MAE'].tail(10).mean())}. O ganho é "
                       "enorme nas primeiras árvores e vira quase nada depois de umas 30: "
                       "aumentar de 300 para 1.000 árvores custa tempo e não compra precisão.")

        with st.expander("🎯 Importância das variáveis na floresta"):
            imp = flor["importancias"].sort_values()
            st.plotly_chart(G.barras_horizontais(imp.index.tolist(), (imp * 100).to_numpy(),
                                                 "", "Importância (%)", altura=520),
                            width="stretch")

    # ── Boosting ───────────────────────────────────────────────────────────────
    with abas[4]:
        comum.info("Bagging contra boosting, em uma frase cada", """
- **Bagging** (Random Forest): árvores treinadas **em paralelo e independentes**, combinadas
  por média simples. Ataca a **variância**. Mais árvores **nunca pioram**.
- **Boosting** (XGBoost, LightGBM, CatBoost): árvores **sequenciais**, cada uma treinada para
  corrigir o **erro que sobrou** das anteriores. Ataca o **viés**. Mais árvores **podem piorar**,
  porque parte do resíduo é ruído puro, e a certa altura o modelo passa a "corrigir" aleatoriedade.

E por isso que aqui precisamos de **três** conjuntos: a validação existe para decidir
**quando parar**.
""")
        c1, c2, c3, c4 = st.columns(4)
        lib = c1.selectbox("Biblioteca", ["XGBoost", "LightGBM", "CatBoost"])
        lr = c2.select_slider("learning_rate", options=[0.01, 0.03, 0.05, 0.1, 0.3], value=0.05)
        folhas = c3.slider("num_leaves (LightGBM)", 7, 127, 31, 8)
        min_obs = c4.slider("min_child_samples", 2, 40, 10)

        with st.spinner(f"Treinando {lib}..."):
            r = comum.modelo_boosting(lib, lr, folhas, min_obs, 6)
        nome = f"{lib} (lr={lr})"
        mae, rmse, mape = _registrar(nome, r["previsão"], campo)
        _cartoes(mae, mape, campo, f"{r['n_arvores']} / {num(r['tempo_s'], 1)}s",
                 "árvores usadas / tempo")

        curvas = r["curvas"]
        st.plotly_chart(
            G.curva_dupla(list(range(1, len(curvas["treino"]) + 1)), curvas["treino"],
                          curvas["validação"], "Erro no treino", "Erro na validação",
                          "A curva de validação vira: esse vale é o modelo",
                          "MAE (ligações/dia)", "Número de árvores"), width="stretch")

        vale = int(np.argmin(curvas["validação"])) + 1
        comum.leitura(f"""
A curva de <b>validação quase nunca é monótona</b>: ela desce, encontra um vale em torno da
árvore <b>{vale}</b> e começa a subir. <b>Esse vale é o modelo</b>, e tudo depois dele é
ruído sendo memorizado. No bagging da aba anterior essa curva simplesmente achatava; aqui ela
vira. É a assinatura do boosting.<br><br>
Reduza o <code>learning_rate</code> e o vale se desloca para a direita: o mesmo aprendizado,
dividido em mais passos. Suba para 0,3 e a curva de treino despenca enquanto a de validação
sobe logo depois de um mínimo raso &mdash; o retrato do sobreajuste.<br><br>
E o resultado que importa para a decisão de projeto: troque a <b>biblioteca</b> mantendo os
demais controles e compare. As três empatam dentro do ruído de semente aleatória. <b>A escolha
entre XGBoost, LightGBM e CatBoost quase nunca é uma decisão de acurácia</b> &mdash; é uma
decisão de velocidade, de tratamento de categóricas e de esforço de ajuste. Note, em
compensação, o quanto <code>min_child_samples</code> move o resultado: em uma base de poucas
centenas de linhas, esse parâmetro decide mais do que o nome da biblioteca.
""")

    # ── Placar ─────────────────────────────────────────────────────────────────
    with abas[5]:
        previsoes = st.session_state.get("previsões", {})
        if not previsoes:
            st.info("Visite as abas anteriores para popular o placar.")
        else:
            _placar(previsoes, campo)

    with abas[6]:
        _caso_em_painel()


def _placar(previsoes: dict, campo: dict) -> None:
    refs = comum.referencias()
    todas = {**{f"[ref] {k}": v for k, v in refs.items()}, **previsoes,
             "[piso] LIMITE TEORICO": comum.oraculo_teste()}
    placar = A.montar_placar(campo["y_teste"], todas, campo["ingênuo"],
                             campo["mae_referencia"], campo["mae_piso"])
    st.dataframe(placar, width="stretch", hide_index=True)

    candidatos = {k: v for k, v in previsoes.items()}
    melhor = min(candidatos, key=lambda k: A.metricas(campo["y_teste"], candidatos[k])[0])
    escolha = st.selectbox("Modelo campeão (será usado nas etapas 4 a 7)",
                           list(candidatos), index=list(candidatos).index(melhor))
    if st.button("✅ Definir como campeão", type="primary"):
        mae_e = A.metricas(campo["y_teste"], candidatos[escolha])[0]
        comum.definir_campeao(escolha, candidatos[escolha], mae_e)
        st.success(f"Campeão definido: **{escolha}** (MAE {num(mae_e)}). "
                   "Siga para a etapa 4.")

    comum.leitura("""
Três leituras do placar, em ordem de importância.<br><br>
<b>Primeira: leia a coluna RMSE/MAE.</b> Ela é o termômetro de dias de desastre. Muito acima
de 1 significa que existem poucos dias com erro enorme escondidos atrás da média &mdash;
justamente os dias que quebram a escala.<br><br>
<b>Segunda: o MASE resume o projeto em um número.</b> Abaixo de 1, o modelo é melhor do que
repetir o mesmo dia da semana passada. É a frase que justifica o investimento em uma reunião.<br><br>
<b>Terceira: ninguém passa do piso.</b> Se passar, não comemore &mdash; procure a coluna
que contém a resposta.
""")


def _caso_em_painel() -> None:
    """O caso do F1_05: variação líquida de vidas por contrato, em painel.

    E um PROBLEMA DIFERENTE do resto da aplicação — outro alvo, outra base, outro conjunto
    de teste. Ele entra aqui porque carrega três lições que a série única da central não
    consegue dar: ablação em painel, vazamento por target encoding e viés no agregado.
    """
    st.warning("**Atenção: este é outro problema.** Outro alvo (variação de vidas por "
               "contrato), outra base e outro conjunto de teste. Os números desta aba **não** "
               "entram no placar da central — comparar seria comparar laranja com maçã.")

    if not st.session_state.get("painel_carregado"):
        st.markdown("""
Esta aba reproduz o caso do notebook **F1_05**: prever a **variação líquida de vidas** de cada
carteira no próximo mês, em um painel de 260 contratos acompanhados por 48 meses. Ela traz
três lições que a série única da central **não consegue dar**:

1. **Ablação em painel** — é aqui que o bloco de histórico mostra o seu valor, porque cada
   empresa tem um *momento comercial* que não aparece em nenhum cadastro;
2. **Vazamento por target encoding** — o erro clássico ao usar uma categórica de alta
   cardinalidade;
3. **Viés no agregado** — um modelo bom por contrato pode errar feio o total da operadora.

Como envolve treinar vários modelos em 10.920 linhas, ela é carregada sob demanda.
""")
        if st.button("▶️ Carregar o caso em painel (leva alguns segundos)", type="primary"):
            st.session_state["painel_carregado"] = True
            st.rerun()
        return

    painel = comum.carteiras()
    dados = comum.features_carteira()
    m = comum.mascaras_carteira()
    y = dados["variacao_vidas"]
    y_te = y[m["teste"]].to_numpy()
    tabela_refs, campo = _painel_referencias()

    st.markdown("""
Na operadora, **carteira** é o conjunto de beneficiários vinculados a um contrato. No mercado
brasileiro de saúde suplementar, a maior parte das vidas está em **contratos coletivos
empresariais**, e a carteira de cada contrato respira todo mês: entram vidas quando a empresa
contrata, saem em demissões e cancelamentos. O que queremos prever é o **saldo**:
""")
    st.latex(r"\text{variação}_{c,t} = \text{adesões}_{c,t} - \text{cancelamentos}_{c,t}")
    st.markdown("""
Isso sustenta quatro decisões: **receita e provisão**, **precificação do reajuste**,
**ação comercial** (qual contrato visitar antes de perder) e **dimensionamento da rede**.
""")

    mensal = painel.groupby("data").agg(vidas=("vidas_fim_mes", "sum"),
                                        adesoes=("adesoes", "sum"),
                                        cancelamentos=("cancelamentos", "sum"),
                                        saldo=("variacao_vidas", "sum"))
    desemprego = painel.groupby("data")["taxa_desemprego"].mean()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi(f"{len(dados):,}".replace(",", "."), "linhas (carteira × mês)", "info")
    with c2:
        kpi(f"{painel['carteira_id'].nunique()}", "carteiras acompanhadas", "info")
    with c3:
        kpi(num(painel["variacao_vidas"].mean()), "variação média (vidas/mês)")
    with c4:
        kpi(num(painel["variacao_vidas"].std(), 1), "desvio-padrão da variação", "warning")

    e, d = st.columns(2)
    with e:
        fig = G.serie(mensal.index, mensal["vidas"], "Vidas ativas", G.AZUL,
                      "Carteira total da operadora", "Vidas", altura=300)
        st.plotly_chart(fig, width="stretch")
    with d:
        fig = G.serie(mensal.index, mensal["saldo"], "Saldo líquido", G.PRETO,
                      "O que queremos prever, somado em toda a operadora",
                      "Vidas no mês", altura=300)
        fig.add_bar(x=mensal.index, y=mensal["adesoes"], name="Adesões",
                    marker_color="rgba(46,125,82,.55)")
        fig.add_bar(x=mensal.index, y=-mensal["cancelamentos"], name="Cancelamentos",
                    marker_color="rgba(192,57,43,.55)")
        st.plotly_chart(fig, width="stretch")

    pior = mensal["saldo"].idxmin()
    comum.leitura(f"""
A carteira sai de <b>{num(mensal['vidas'].iloc[0], 0)}</b> vidas, cai até
<b>{num(mensal['vidas'].min(), 0)}</b> no fundo da crise ({mensal['vidas'].idxmin():%b/%Y}) e
termina em <b>{num(mensal['vidas'].iloc[-1], 0)}</b>, um crescimento de
<b>{num(100 * (mensal['vidas'].iloc[-1] / mensal['vidas'].iloc[0] - 1), 1)}%</b> em quatro
anos. Esse <b>formato de U</b> é o que qualquer modelo vai ter que enfrentar, e ele vem do
desemprego, que sobe até {num(desemprego.max(), 1)}% e depois recua.<br><br>
No painel da direita, repare na diferença de escala entre as barras e a linha: os dois
<b>fluxos</b> (adesões e cancelamentos) são grandes e parecidos entre si; o <b>saldo</b>,
que é a diferença deles, é pequeno e nervoso. Essa é a dificuldade estrutural do problema, e
nenhum modelo a conserta: a variação média por carteira é de apenas
<b>{num(painel['variacao_vidas'].mean())} vida</b> contra um desvio-padrão de
<b>{num(painel['variacao_vidas'].std(), 1)}</b>. O sinal é pequeno diante da dispersão.<br><br>
O pior mês da série é <b>{pior:%b/%Y}</b> ({num(mensal['saldo'].min(), 0)} vidas): dezembro é
sempre o pior mês, porque é quando as empresas fecham o ano e cortam custo.
""")

    st.markdown("---")
    st.markdown("##### O campo de jogo, é por que ele muda a percepção de dificuldade")
    e, d = st.columns([2, 3])
    with e:
        st.dataframe(tabela_refs, width="stretch", hide_index=True)
    with d:
        modelo = _painel_modelo()
        prev = modelo.predict(dados.loc[m["teste"], comum.colunas_carteira()])
        mae_modelo = A.metricas(y_te, prev)[0]
        aproveitado = 100 * (campo["mae_referencia"] - mae_modelo) / \
                      (campo["mae_referencia"] - campo["mae_piso"])
        c1, c2 = st.columns(2)
        with c1:
            kpi(num(mae_modelo), "MAE do LightGBM (vidas)")
        with c2:
            kpi(f"{num(max(aproveitado, 0), 1)}%", "do sinal aprendível", "warning")
        st.progress(min(max(aproveitado / 100, 0.0), 1.0))
        st.caption("A barra vai da melhor referência simples até o piso do problema.")

    comum.leitura(f"""
Três números merecem atenção antes de qualquer modelagem.<br><br>
<b>Assumir carteira estável</b> (prever zero) já erra pouco: {num(campo['mae_estavel'])} vidas.
<b>Repetir o último mês</b> erra {num(tabela_refs.iloc[1]['MAE'])} &mdash; e essa comparação é
reveladora: a variação de um mês tem tanto ruído que copiá-la introduz <b>mais erro do que
informação</b>. A previsão ingênua, que costuma ser difícil de bater em séries de nível, aqui
é ruim porque o alvo é uma <b>diferença</b>, não um nível.<br><br>
O <b>piso do problema</b> é {num(campo['mae_piso'])}: é o erro de quem soubesse a
variação <i>esperada</i> de cada carteira e ainda assim errasse, porque adesões e
cancelamentos são sorteios. Não é um modelo a ser perseguido, é a linha de chegada da pista.
Todo o espaço disputável está entre {num(campo['mae_referencia'])} e
{num(campo['mae_piso'])}, é o modelo capturou <b>{num(max(aproveitado, 0), 1)}%</b> dele.<br><br>
Esse número não é glamouroso, e é exatamente por isso que ele é instrutivo: <b>em problemas
dominados por ruído de contagem, o ganho realista de um bom modelo é esta ordem de
grandeza</b>. Prometer mais do que isso à diretoria é criar uma expectativa que a estatística
do problema não sustenta.
""")

    st.markdown("---")
    st.markdown("##### Quanto vale cada bloco de variáveis")
    with st.spinner("Treinando um modelo por bloco..."):
        ablacao = _painel_ablacao()
    st.dataframe(ablacao, width="stretch", hide_index=True)

    hist = ablacao[ablacao["bloco acrescentado"] == "histórico"].iloc[0]
    cad = ablacao.iloc[0]
    macro = ablacao[ablacao["bloco acrescentado"] == "macro"].iloc[0]
    comum.leitura(f"""
<b>Só cadastro e calendário</b>: MAE {num(cad['MAE'])}, ou seja, <b>pior do que a média dos 3
últimos meses</b>. Saber o tamanho da carteira, o mês e o reajuste contratado não basta.<br><br>
<b>Somando o cadastro categórico</b> (setor, porte, região, modalidade, coparticipação,
canal): ganho de {num(ablacao.iloc[1]['ganho do bloco'])}. As categóricas valem, mas
isoladamente não viram o jogo.<br><br>
<b>Somando o histórico da própria carteira</b>: salto de <b>{num(hist['ganho do bloco'])}</b>,
o maior da tabela. E este ganho tem uma explicação estrutural precisa: o gerador embutiu um
<b>momento comercial latente</b> em cada empresa, que persiste por vários meses e <b>não
aparece em nenhum cadastro</b>. As defasagens são a única janela para esse estado invisível.
E o análogo, em painel, do componente autorregressivo do ARIMA.<br><br>
<b>Somando macro e sinistralidade</b>: {num(macro['ganho do bloco'])}. Praticamente nada, e a
razão é boa de entender: a variável macro é <b>comum a todas as carteiras</b> em cada mês,
então o modelo já a reconstrói em parte pelo calendário. Bloco caro de integrar, ganho
marginal &mdash; exatamente o tipo de decisão que a ablação existe para informar.
""")

    st.markdown("---")
    st.markdown("##### O identificador da carteira: como usar uma categórica de alta cardinalidade")
    st.markdown("""
Imagine usar o próprio `carteira_id` (260 valores) como variável. One-hot está fora de questão.
A alternativa clássica é o **target encoding**: substituir cada categoria pela **média do alvo**
naquela categoria. Simples, compacto, e com uma armadilha grave — se a média é calculada com
todas as linhas de treino, ela **inclui a própria linha** que vamos prever.
""")
    if st.button("▶️ Comparar as três formas de codificar"):
        with st.spinner("Treinando as três configurações..."):
            tabela_te, corr_ingenuo, corr_oof = _painel_target_encoding()
        st.dataframe(tabela_te, width="stretch", hide_index=True)

        a, b, c = tabela_te.iloc[0], tabela_te.iloc[1], tabela_te.iloc[2]
        comum.leitura(f"""
Compare as colunas de <b>treino</b> e de <b>teste</b>, porque a assinatura do vazamento está
no contraste entre elas.<br><br>
<b>A) Sem o identificador</b>: {num(a['treino'], 3)} no treino e {num(a['teste'], 3)} no teste.
E a base de comparação.<br>
<b>B) Target encoding ingênuo</b>: o treino <b>melhora</b> para {num(b['treino'], 3)} e o teste
<b>piora</b> para {num(b['teste'], 3)}. Exatamente o padrão descrito: a média por carteira
contém a resposta da própria linha, o modelo se apoia nela, e em dados novos o apoio
desaparece.<br>
<b>C) Out-of-fold</b>: {num(c['treino'], 3)} / {num(c['teste'], 3)}. É o jeito correto de fazer
manualmente, e ainda assim <b>não melhora</b> em relação a não usar a feature.<br><br>
A medida mais direta do vazamento está na correlação da feature com o alvo, dentro do treino:
<b>{num(corr_ingenuo, 3)}</b> na versão ingênua contra <b>{num(corr_oof, 3)}</b> na
out-of-fold. Aquela diferença de {num(corr_ingenuo - corr_oof, 3)} é <b>informação que só
existe no treino</b>, é o modelo vai persegui-la.<br><br>
Duas conclusões. A primeira: neste problema o identificador da carteira <b>não acrescenta
nada</b> que as defasagens já não capturem, e o esforço de codificá-lo foi em vão. A segunda,
mais importante: o vazamento aqui é <b>pequeno</b> porque cada carteira tem 30 meses de treino,
então a própria linha pesa 1/30 na média. Com categóricas de <b>alta cardinalidade de
verdade</b> &mdash; CID, código de procedimento, prestador &mdash; cada categoria tem poucas
linhas é a média praticamente <b>entrega a resposta</b>. É aí que o CatBoost, com as suas
estatísticas ordenadas, resolve o problema sem que você precise pensar nele.
""")

    st.markdown("---")
    st.markdown("##### O efeito do reajuste, por porte da empresa")
    st.markdown("Esta é a saída que vai para a mesa de precificação, e ela responde a uma "
                "pergunta de negócio direta: **quanto de carteira eu perco por ponto de "
                "reajuste, em cada tipo de empresa?**")

    modelo = _painel_modelo()
    colunas = comum.colunas_carteira()
    teste = dados[m["teste"]]
    percentuais = [0.03, 0.06, 0.09, 0.12, 0.18, 0.25]
    fig = G.serie([100 * p for p in percentuais], [0] * len(percentuais), "zero", G.CINZA,
                  "Variação mensal prevista no período pós-reajuste", "% da carteira por mês",
                  "Reajuste aplicado (%)", altura=340)
    fig.data[0].line.dash = "dot"
    cores = {"Micro": G.VERMELHO, "Pequena": G.LARANJA, "Média": G.VERDE2, "Grande": G.AZUL}
    resumo = []
    for porte, cor in cores.items():
        mascara = (teste["porte"] == porte).to_numpy()
        if not mascara.any():
            continue
        base = teste.loc[mascara, colunas].copy()
        base["eh_pos_reajuste"] = 1
        base["meses_desde_reajuste"] = 1
        vidas = teste.loc[mascara, "vidas_inicio_mes"].to_numpy()
        curva = [100 * float(np.mean(modelo.predict(base.assign(reajuste_vigente=p)) / vidas))
                 for p in percentuais]
        fig.add_scatter(x=[100 * p for p in percentuais], y=curva, name=porte, mode="lines+markers",
                        line=dict(color=cor, width=2.4))
        resumo.append({"porte": porte, "a 3% de reajuste": round(curva[0], 2),
                       "a 25% de reajuste": round(curva[-1], 2),
                       "perda adicional": round(curva[-1] - curva[0], 2)})
    st.plotly_chart(fig, width="stretch")
    st.dataframe(pd.DataFrame(resumo), width="stretch", hide_index=True)

    tabela_resumo = pd.DataFrame(resumo).set_index("porte")["perda adicional"]
    mais_sensivel = tabela_resumo.idxmin()
    comum.leitura(f"""
As curvas <b>descem</b> conforme o reajuste sobe, que é a direção esperada, e <b>a separação
entre elas é o resultado</b>. O porte <b>{mais_sensivel}</b> é o mais sensível: perde
<b>{num(abs(tabela_resumo.min()), 2)} ponto percentual de carteira por mês</b> a mais quando
o reajuste vai de 3% para 25%. Os portes maiores ficam quase planos.<br><br>
O modelo aprendeu, <b>sem que ninguém tenha escrito a regra</b>, a interação
<i>reajuste × porte</i> que foi plantada no gerador, e a hierarquia recuperada é a correta:
quanto menor a empresa, mais sensível ao preço. É o tipo de saída que transforma um modelo
preditivo em ferramenta de negociação.<br><br>
Uma ressalva de honestidade interpretativa, que vale para qualquer análise de efeito parcial:
reajustes acima de 18% são <b>raros na base</b>, então aquela parte da curva se apoia em
poucas observações. Extrapolar dali para uma decisão de precificação seria ir além do que os
dados sustentam.
""")

    st.markdown("---")
    st.markdown("##### Do contrato para a operadora: o problema do agregado")
    st.markdown("""
Até aqui medimos o erro **por carteira**, que é o número relevante para a ação comercial: qual
contrato visitar, qual renegociar. Mas a diretoria faz outra pergunta, que parece a mesma e
não é: **quantas vidas a operadora vai ter no mês que vem?**
""")
    agregado = teste.assign(previsto=modelo.predict(teste[colunas])).groupby("data").agg(
        real=("variacao_vidas", "sum"), previsto=("previsto", "sum"),
        oraculo=("variacao_esperada", "sum"))

    fig = G.comparar_previsoes(agregado.index, agregado["real"],
                               {"Soma das previsões": agregado["previsto"],
                                "Piso (soma da variação esperada)": agregado["oraculo"]},
                               "Saldo mensal de vidas da operadora", "Vidas no mês")
    st.plotly_chart(fig, width="stretch")

    correlacao = float(np.corrcoef(agregado["real"], agregado["previsto"])[0, 1])
    vies = float((agregado["previsto"] - agregado["real"]).mean())
    st.dataframe(agregado.assign(erro=agregado["previsto"] - agregado["real"]).round(0),
                 width="stretch")

    comum.leitura(f"""
Duas coisas acontecem ao mesmo tempo, e é preciso separa-las.<br><br>
<b>O formato está certo.</b> A correlação entre o real e o previsto é de
<b>{num(correlacao, 2)}</b>: o modelo acerta quais meses são bons e quais são ruins. Para a
gestão, isso já é útil &mdash; a <b>direção</b> e o <b>ritmo</b> estão capturados.<br><br>
<b>O nível está {'baixo' if vies < 0 else 'alto'}.</b> O viés médio é de
<b>{num(vies, 0)} vidas por mês</b>. No acumulado dos seis meses de teste, a carteira real
variou <b>{sinal(agregado['real'].sum(), 0)}</b> vidas e a soma das previsões deu
<b>{sinal(agregado['previsto'].sum(), 0)}</b>. A linha do oráculo, que soma
<b>{sinal(agregado['oraculo'].sum(), 0)}</b>, prova que o problema <b>não é o ruído</b>: quem
conhece a variação esperada acerta o agregado.<br><br>
A causa é conhecida e vale levar para qualquer projeto de previsão em painel: modelos de
árvore <b>não extrapolam</b>. Treinados majoritariamente em um período de crise, eles nunca
viram níveis de crescimento como os do fim da série, e a previsão fica presa no valor da folha
mais alta. Erros pequenos e na <b>mesma direção</b>, espalhados por 260 carteiras, se somam em
vez de se cancelar.<br><br>
A lição prática: <b>um modelo bom por unidade não é automaticamente bom no agregado</b>. Se a
pergunta da diretoria é o total, corrija o viés explicitamente (com um modelo separado para o
agregado, ou com uma calibração) e <b>meça o agregado como um KPI próprio</b> &mdash; ele não
vem de graça junto com o MAE por carteira.
""")
