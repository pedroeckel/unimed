"""Página 2 — engenharia de variáveis."""

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

ORDEM_BLOCOS = ["temporais", "calendário", "operacionais", "histórico", "cíclicas"]


@st.cache_data(show_spinner=False)
def _ablacao_central() -> pd.DataFrame:
    X, y = comum.features_central()
    campo = comum.campo_de_jogo()
    return M.ablacao(X, y, D.separar(X.index), F.BLOCOS_CENTRAL, ORDEM_BLOCOS,
                     campo["mae_referencia"], campo["mae_piso"])


@st.cache_data(show_spinner=False)
def _modelo_por_blocos(chave: tuple[str, ...]) -> tuple[float, float, float, int]:
    X, y = comum.features_central()
    colunas = [c for bloco in chave for c in F.BLOCOS_CENTRAL[bloco]]
    m = D.separar(X.index)
    modelo = M.lgbm_simples(X, y, m, colunas)
    mae, rmse, mape = A.metricas(y[m["teste"]], modelo.predict(X.loc[m["teste"], colunas]))
    return mae, rmse, mape, len(colunas)


@st.cache_data(show_spinner=False)
def _importancia_permutacao() -> pd.Series:
    X, y = comum.features_central()
    m = D.separar(X.index)
    modelo = M.lgbm_simples(X, y, m, list(X.columns))
    return M.importancia_permutacao(modelo, X[m["teste"]], y[m["teste"]])


@st.cache_data(show_spinner=False)
def _defasagens():
    chegadas, externas = comum.pa_diario()
    return F.descobrir_defasagens(chegadas, externas)


@st.cache_data(show_spinner=False)
def _lgpd() -> pd.DataFrame:
    """O custo de proteger: mesmo modelo, três níveis de granularidade de dado pessoal."""
    painel = comum.autorizacoes()
    dados = F.construir_features_autorizacao(painel)
    m = D.separar(pd.DatetimeIndex(dados["data"]))
    y = dados["solicitacoes"]

    sem_perfil = (F.BLOCOS_AUTORIZACAO["especialidade"] + F.BLOCOS_AUTORIZACAO["calendário"]
                  + F.BLOCOS_AUTORIZACAO["operacionais"] + F.BLOCOS_AUTORIZACAO["agregadas"]
                  + F.BLOCOS_AUTORIZACAO["histórico"])
    niveis = {
        "Nível 0 — nenhum dado de beneficiário": sem_perfil,
        "Nível 1 — proporção 60+ em faixas (anonimizado)":
            sem_perfil + F.BLOCOS_AUTORIZACAO["perfil_anonimo"],
        "Nível 2 — perfil detalhado (idade, crônicos, complexidade)":
            sem_perfil + F.BLOCOS_AUTORIZACAO["perfil_anonimo"]
            + F.BLOCOS_AUTORIZACAO["perfil_detalhado"],
    }
    linhas = []
    for nome, colunas in niveis.items():
        modelo = M.lgbm_simples(dados, y, m, colunas)
        mae, rmse, _ = A.metricas(y[m["teste"]], modelo.predict(dados.loc[m["teste"], colunas]))
        linhas.append({"nível de granularidade": nome, "variáveis": len(colunas),
                       "MAE": round(mae, 3), "RMSE": round(rmse, 3)})
    return pd.DataFrame(linhas)


def render() -> None:
    comum.selo("Etapa 2 · Engenharia de variáveis",
               "F1_07 (chegadas ao PA) e F1_08 (operadora e LGPD)")
    st.title("🧱 Engenharia de variáveis")

    comum.problema(
        "<b>O problema de gestão.</b> Nos notebooks, a diferença entre XGBoost, LightGBM e "
        "CatBoost foi de <b>0,04</b>; a diferença entre um conjunto pobre e um conjunto bem "
        "construido de variáveis foi de <b>1,16</b>, quase trinta vezes maior. Trocar de "
        "algoritmo rende pouco. Construir variáveis melhores rende muito &mdash; e depende de "
        "conhecimento do negócio, não de biblioteca.")

    abas = st.tabs(["Da série para a tabela", "Blocos e ablação",
                    "Defasagem: a correlação que engana", "Vazamento e LGPD"])

    X, y = comum.features_central()
    diaria = comum.central_diaria()
    m = comum.mascaras()

    # ── 2.1 ────────────────────────────────────────────────────────────────────
    with abas[0]:
        st.markdown("""
Um modelo de árvore recebe uma matriz $X$ de variáveis e um vetor $y$ com o alvo, e aprende
$\\hat{y} = f(X)$. **Não existe noção de ordem temporal dentro do modelo**: se embaralhássemos
as linhas, o treinamento daria o mesmo resultado. Toda a informação de tempo tem que ser
**escrita como coluna**.
""")
        e, d = st.columns([1, 3])
        with e:
            st.markdown("**Antes** — uma coluna e um índice")
            st.dataframe(diaria[["n_ligacoes"]].tail(6).round(0), width="stretch")
        with d:
            st.markdown("**Depois** — a linha se descreve sozinha")
            st.dataframe(X.tail(6)[["dia_semana", "dia_mes", "eh_feriado", "janela_vencimento",
                                    "campanha", "lag1", "lag7", "media7", "media28"]].round(1),
                         width="stretch")

        c1, c2, c3 = st.columns(3)
        with c1:
            kpi(f"{X.shape[0]}", "linhas (dias)", "info")
        with c2:
            kpi(f"{X.shape[1]}", "colunas de variáveis", "info")
        with c3:
            kpi(f"{len(diaria) - len(X)}", "dias perdidos no aquecimento", "warning")

        comum.leitura(f"""
A série virou uma matriz de <b>{X.shape[0]} linhas por {X.shape[1]} colunas</b>. A partir
daqui o modelo não precisa mais do índice de tempo: ele pergunta coisas como
"<i>dia_semana &le; 4,5?</i>" e "<i>eh_feriado = 1?</i>".<br><br>
Repare no custo que ninguém menciona: perdemos <b>{len(diaria) - len(X)} dias</b> no início
da série, porque a média móvel de 28 dias precisa de 28 dias de história para existir. E um
custo real da engenharia de variáveis, e é o motivo de a apostila recomendar coletar doze
meses ou mais de histórico antes de começar.
""")

    # ── 2.2 ────────────────────────────────────────────────────────────────────
    with abas[1]:
        campo = comum.campo_de_jogo()
        st.markdown("Ligue e desligue blocos. O modelo é retreinado a cada mudança.")

        colunas_ui = st.columns(5)
        escolhidos = []
        padroes = {"temporais": True, "calendário": True, "operacionais": True,
                   "histórico": True, "cíclicas": False}
        for coluna, bloco in zip(colunas_ui, ORDEM_BLOCOS):
            if coluna.checkbox(F.ROTULO_BLOCO[bloco].split(" (")[0], value=padroes[bloco],
                               key=f"bloco_{bloco}"):
                escolhidos.append(bloco)

        if not escolhidos:
            st.warning("Selecione ao menos um bloco.")
        else:
            with st.spinner("Retreinando com os blocos selecionados..."):
                mae, rmse, mape, n_col = _modelo_por_blocos(tuple(escolhidos))
            aproveitado = 100 * (campo["mae_referencia"] - mae) / \
                          (campo["mae_referencia"] - campo["mae_piso"])
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                kpi(num(mae), "MAE no teste")
            with c2:
                kpi(num(mape, 1) + "%", "MAPE", "info")
            with c3:
                kpi(f"{n_col}", "variáveis usadas", "neutral")
            with c4:
                kpi(f"{num(max(aproveitado, 0), 1)}%", "do aproveitável", "warning")
            st.progress(min(max(aproveitado / 100, 0.0), 1.0))
            st.caption(f"A barra vai da melhor referência simples "
                       f"({num(campo['mae_referencia'])}) até o piso do problema "
                       f"({num(campo['mae_piso'])}).")

        st.markdown("##### Ablação: quanto vale cada bloco, na ordem em que um projeto os constrói")
        with st.spinner("Treinando um modelo por bloco acrescentado..."):
            tabela = _ablacao_central()
        st.dataframe(tabela, width="stretch", hide_index=True)

        melhor_bloco = tabela.loc[tabela["ganho do bloco"].idxmax()] \
            if tabela["ganho do bloco"].notna().any() else None
        hist = tabela[tabela["bloco acrescentado"] == "histórico"].iloc[0]
        ciclicas = tabela[tabela["bloco acrescentado"] == "cíclicas"].iloc[0]
        comum.leitura(f"""
A sequência começa pelo que sai <b>de graça do índice de tempo</b> e termina pelo que
custa integração de dados. O maior ganho é do bloco
<b>{melhor_bloco['bloco acrescentado'] if melhor_bloco is not None else 'histórico'}</b>
({num(melhor_bloco['ganho do bloco']) if melhor_bloco is not None else '—'} ligações),
e ele também é de <b>custo zero</b>: a informação já estava dentro da própria base.
Depois de acrescenta-lo, o modelo chega a MAE {num(hist['MAE'])} e captura
{num(hist['% do aproveitável'], 1)}% do espaço disputável.<br><br>
As <b>cíclicas</b> acrescentam {num(ciclicas['ganho do bloco'])}, praticamente nada. É o
resultado esperado: para uma <b>árvore</b>, seno e cosseno são redundantes, porque ela pode
cortar <code>dia_semana &le; 4,5</code> e reconstruir qualquer formato sozinha. Elas valem
muito em modelo linear e quase nada aqui. <b>Variável redundante não é variável útil.</b><br><br>
É a lição central: o bloco de <b>histórico</b> é o único que enxerga a onda epidemiológica.
Nenhuma coluna de calendário sabe que um surto começou; <code>lag1</code> e
<code>media7</code> sabem.
""")

        with st.expander("🔎 Importância por permutação (embaralha uma coluna e mede a piora)"):
            with st.spinner("Embaralhando cada coluna e medindo a piora..."):
                imp = _importancia_permutacao()
            cores = [G.VERMELHO if v < 0 else G.AZUL2 for v in imp.to_numpy()]
            st.plotly_chart(G.barras_horizontais(imp.index.tolist(), imp.to_numpy(),
                                                 "Aumento do MAE ao embaralhar a variável",
                                                 "Ligações por dia", cores, altura=560),
                            width="stretch")
            with st.container():
                st.markdown("**Monitoramento: desvio de distribuição (PSI) × importância**")
                psi_tabela = pd.DataFrame([
                    {"variável": c,
                     "PSI treino → teste": round(A.psi(X.loc[m["treino"], c],
                                                       X.loc[m["teste"], c]), 3),
                     "situação": A.classificar_psi(A.psi(X.loc[m["treino"], c],
                                                         X.loc[m["teste"], c])),
                     "importância": round(float(imp.get(c, 0.0)), 3)}
                    for c in X.columns]).sort_values("importância", ascending=False)
                st.dataframe(psi_tabela, width="stretch", hide_index=True, height=260)
                calendario = ["mês", "dia_do_ano", "doy_sin", "doy_cos", "dia_mes",
                              "semana_mes", "dias_restantes_mes"]
                criticas = psi_tabela[(psi_tabela["PSI treino → teste"] >= 0.25)
                                      & (psi_tabela["importância"] > 0)
                                      & (~psi_tabela["variável"].isin(calendario))]
                nomes = ", ".join(f"`{v}`" for v in criticas["variável"].head(3))
                st.markdown(f"""
Um modelo em produção envelhece: a rede credenciada muda, a carteira envelhece, um protocolo
novo altera a indicação. Nada disso gera erro de execução — o modelo continua devolvendo
números, cada vez piores.

**Primeiro, o falso alarme.** Em uma separação temporal, as variáveis de calendário (`mês`,
`dia_do_ano`, `doy_sin`) sempre acusam PSI altíssimo: o teste cobre setembro a dezembro e o
treino não tinha esses meses. Isso é **esperado por construção**, não é desvio de população,
e um painel que dispara alerta aí ensina a equipe a ignorar alertas.

**Depois, o alarme de verdade.** {'As variáveis ' + nomes + ' combinam desvio relevante com importância positiva — são médias móveis, que se deslocam junto com o nível crescente da série. Esse é o mesmo problema de extrapolação das árvores, agora visível na monitoração.' if len(criticas) else 'Nenhuma variável não-calendário combinou desvio relevante com importância positiva nesta base.'}

**A regra que sai daqui: ordene o monitoramento por importância, não por PSI.** Um desvio
enorme em uma variável fraca faz barulho e não muda nada; um desvio moderado em uma variável
forte estraga o modelo em silêncio.
""")

            negativas = imp[imp < 0]
            st.markdown(f"""
É medida **fora da amostra** e **na métrica que interessa**, o que a torna mais confiável do
que a importância interna do modelo. As variáveis no topo são as que sustentam o resultado.

{'As **' + str(len(negativas)) + ' variáveis com importância negativa** merecem atenção: embaralha-las **melhorou** o modelo, ou seja, elas estavam atrapalhando. São candidatas naturais a remoção &mdash; menos colunas, menos manutenção, menos chance de drift.' if len(negativas) else 'Nenhuma variável teve importância negativa nesta execução.'}
""")

    # ── 2.3 ────────────────────────────────────────────────────────────────────
    with abas[2]:
        st.markdown("""
Este é o ponto mais técnico da etapa, é o que separa uma engenharia de variáveis amadora de
uma profissional. Trocamos de caso para mostra-lo: **chegadas ao pronto atendimento**, com
clima e alertas epidemiológicos.

Temperatura, chuva e alerta afetam a chegada ao PA, mas **não no mesmo dia**. Uma frente fria
não enche o PA na hora em que chega: ela adoece a população, os quadros evoluem, e a procura
aparece dias depois. A pergunta correta é **qual defasagem usar**.
""")
        tabela = _defasagens()
        rotulos = {"temp_media": "Temperatura", "chuva_mm": "Chuva",
                   "alerta_gripe": "Alerta de gripe", "alerta_dengue": "Alerta de dengue"}

        colunas_fig = st.columns(2)
        for i, linha in tabela.iterrows():
            with colunas_fig[i % 2]:
                st.plotly_chart(
                    G.dispersao_lags(linha["curva_bruta"], linha["curva_residual"],
                                     linha["lag_verdadeiro"], rotulos[linha["variável"]]),
                    width="stretch")

        exibir = tabela[["variável", "lag_verdadeiro", "lag_bruto", "corr_bruta",
                         "lag_residual", "corr_residual"]].copy()
        exibir["variável"] = exibir["variável"].map(rotulos)
        st.dataframe(exibir, width="stretch", hide_index=True)

        acertos_bruto = int(tabela["acertou_bruto"].sum())
        acertos_res = int(tabela["acertou_residual"].sum())
        temp = tabela[tabela["variável"] == "temp_media"].iloc[0]
        comum.leitura(f"""
O método ingênuo &mdash; correlacionar a série bruta com a variável bruta &mdash; acerta
<b>{acertos_bruto} de 4</b> defasagens. O método correto, que correlaciona os
<b>resíduos</b> depois de remover tendência, harmônicos anuais e dia da semana, acerta
<b>{acertos_res} de 4</b>.<br><br>
O caso da <b>temperatura</b> é o mais eloquente: a correlação bruta da
<b>{num(temp['corr_bruta'], 3)}</b> no lag {temp['lag_bruto']}, um valor próximo de zero
que sugere "a temperatura não importa". Ela importa, e muito &mdash; é a variável externa
mais valiosa do modelo, com efeito <b>negativo</b> (frio três dias atrás significa mais
chegadas hoje) que só aparece quando olhamos o resíduo.<br><br>
A causa é a <b>sazonalidade compartilhada</b>: todas essas séries sobem e descem juntas ao
longo do ano. No verão faz calor <b>e</b> há dengue; no inverno faz frio <b>e</b> há gripe.
Como todas oscilam com o mesmo ciclo anual, todas correlacionam com todas, e a correlação
bruta mede principalmente essa sazonalidade &mdash; não a relação causal.<br><br>
A pergunta que o método dos resíduos responde é a certa: <b>quando esta variável se afasta
do seu próprio padrão sazonal, em quantos dias as chegadas se afastam do delas?</b>
""")

    # ── 2.4 ────────────────────────────────────────────────────────────────────
    with abas[3]:
        st.markdown("##### A armadilha do `rolling` sem `shift`")
        st.code('X["media7"] = s.rolling(7).mean()          # ERRADO: inclui o próprio dia alvo\n'
                'X["media7"] = s.shift(1).rolling(7).mean() # CERTO: só até o dia anterior',
                language="python")

        demo, corr_errada, corr_correta = F.demonstrar_vazamento(diaria["n_ligacoes"])
        e, d = st.columns([3, 2])
        e.dataframe(demo, width="stretch")
        with d:
            kpi(num(corr_errada, 3), "correlação com o alvo — versão ERRADA", "danger")
            kpi(num(corr_correta, 3), "correlação com o alvo — versão correta")

        comum.leitura(f"""
Compare a coluna <code>media3_ERRADA</code> com <code>valor</code> na mesma linha: a média
de três dias <b>termina no próprio dia</b>, então um terço do valor que queremos prever já
está dentro da pergunta.<br><br>
A correlação com o alvo mostra o tamanho do problema: <b>{num(corr_errada, 3)}</b> na versão
errada contra <b>{num(corr_correta, 3)}</b> na correta. Aquela diferença de
{num(corr_errada - corr_correta, 3)} é <b>puro vazamento</b>, e o modelo vai persegui-la com
entusiasmo &mdash; a avaliação fica ótima e, em produção, a feature simplesmente não existe,
porque no momento da previsão o dia ainda não terminou.
""")

        st.markdown("---")
        st.markdown("##### O teste que separa notebook de sistema")
        st.markdown("""
Em produção as features são construídas **todo dia, de novo, exatamente do mesmo jeito**, com
dados que chegam aos poucos. O erro clássico é ter **duas implementações**: uma no notebook de
treino e outra no serviço. Elas começam iguais e divergem na primeira correção feita em apenas
um dos lados. O sintoma é cruel: desempenho excelente na avaliação e medíocre em produção,
**sem nenhuma mensagem de erro**.
""")
        if st.button("▶️ Rodar o teste treino × produção"):
            painel = comum.autorizacoes()
            r = F.verificar_treino_producao(painel, pd.Timestamp("2025-10-15"), "Ortopedia")
            if r["ok"]:
                st.success(f"✅ Passou. Diferença máxima entre as duas rotas: "
                           f"**{r['diferenca_maxima']:.10f}** em {r['n_colunas']} variáveis.")
            else:
                st.error(f"❌ Reprovou. Diferença de {r['diferenca_maxima']:.4f} "
                         f"na coluna `{r['coluna_pior']}`.")
            st.caption("Constrói o vetor de features de duas rotas — o painel inteiro e o "
                       "painel recortado até a véspera, como o sistema faria às 6h — e "
                       "compara número a número. Parece um teste bobo, e não é: a primeira "
                       "versão do notebook F1_08 REPROVOU nele, com diferença de 28,86 em uma "
                       "média móvel que atravessava a fronteira do grupo.")

        contrato = comum.contrato_de_features()
        if contrato:
            with st.expander("📄 O contrato de features versionado (gerado pelo notebook F1_08)"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    kpi(contrato.get("versao", "—"), "versão do pipeline", "info")
                    kpi(f"{len(contrato.get('colunas', []))}", "colunas no contrato", "neutral")
                with c2:
                    st.markdown("**Colunas declaradas**")
                    st.code(", ".join(contrato.get("colunas", [])), language=None)
                estat = contrato.get("estatísticas", {})
                if estat:
                    st.markdown("**Faixas de referência aprendidas no treino** — são elas que "
                                "permitem detectar desvio de distribuição (drift) depois.")
                    st.dataframe(pd.DataFrame([
                        {"variável": k, "média do treino": round(v["media"], 3),
                         "desvio-padrão": round(v["desvio"], 3),
                         "min": round(v["quantis"][0], 2), "max": round(v["quantis"][-1], 2)}
                        for k, v in estat.items()]), width="stretch", hide_index=True,
                        height=240)
                st.caption("Em produção, o que se versiona não é só o modelo: é o par "
                           "modelo + contrato de features. Modelo novo com contrato antigo é "
                           "uma das formas mais silenciosas de quebrar um sistema.")

        st.markdown("---")
        st.markdown("##### Quanto custa proteger o dado do beneficiário (LGPD)")
        st.markdown("""
Idade, condição crônica e histórico de procedimento são **dados pessoais**, e os que revelam
condição de saúde são **dados pessoais sensíveis** (LGPD, art. 5º, II). A pergunta que o
jurídico faz é sempre a mesma: *de quanto abrimos mão se não usarmos esses dados?*

Aqui ela deixa de ser opinião e vira número. Mesmo modelo, mesma base de autorizações prévia,
três níveis de granularidade.
""")
        if st.button("▶️ Medir o custo da proteção"):
            with st.spinner("Treinando os três níveis..."):
                tabela = _lgpd()
            st.dataframe(tabela, width="stretch", hide_index=True)
            n0, n1, n2 = tabela["MAE"].tolist()
            comum.leitura(f"""
<b>Nível 0</b>, sem nenhum dado de beneficiário: MAE de <b>{num(n0, 3)}</b>.<br>
<b>Nível 1</b>, só a proporção de 60+ agregada em faixas: <b>{num(n1, 3)}</b>.<br>
<b>Nível 2</b>, com o perfil detalhado: <b>{num(n2, 3)}</b>.<br><br>
Todo o ganho de sair do desenho protegido para o desenho invasivo é de
<b>{num(n0 - n2, 3)} solicitação por dia e especialidade</b>, ou
<b>{num(100 * (n0 - n2) / n0, 1)}%</b> do erro. Não é zero, e também não é o que costuma ser
prometido quando se pede acesso a dados individuais.<br><br>
E o argumento que fecha a conversa com o encarregado de dados: o princípio de
<b>minimização</b> (art. 6º, III) exige justificar a necessidade de cada variável.
"Pode ser útil" não é justificativa. A ablação por bloco é o instrumento que transforma essa
exigência em <b>evidência</b>: se um bloco não melhora o modelo, ele não é necessário, e não
deve ser coletado.
""")
