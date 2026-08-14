"""Página 8 — síntese."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from nucleo import avaliacao as A

from . import comum
from .comum import num

AULAS = [
    ("F1_01", "Fundamentos de séries temporais",
     "tendência, sazonalidade, estacionariedade, ACF/PACF", "Etapa 1"),
    ("F1_02", "ARIMA e SARIMA",
     "ignorar a sazonalidade custa caro", "Etapa 3, aba Clássicos"),
    ("F1_03", "Prophet",
     "ajuste de curva com componentes inspecionáveis", "Etapa 3, aba Prophet"),
    ("F1_04", "Árvores e Random Forest",
     "a série vira tabela; bagging cancela ruído", "Etapa 3, aba Árvores"),
    ("F1_05", "XGBoost, LightGBM e CatBoost",
     "boosting corrige o resíduo; as três bibliotecas empatam", "Etapa 3, aba Boosting"),
    ("F1_06", "Perceptron, RNN e LSTM",
     "redes neurais — FORA DO ESCOPO desta aplicação", "só no notebook"),
    ("F1_07", "Feature engineering: chegadas hospitalares",
     "defasagem correta; estratégia de duas etapas", "Etapas 2 e 5"),
    ("F1_08", "Feature engineering: operadora e LGPD",
     "agregações em painel, vazamento, minimização", "Etapa 2, abas 2 e 4"),
    ("F1_09", "Avaliação: MAE, RMSE e MAPE",
     "a métrica traduz o custo do negócio", "Etapa 4"),
]

ERROS = [
    ("Dividir treino e teste de forma aleatória",
     "O modelo aprende com o dia 15 e é avaliado no dia 16, que é o vizinho. O erro medido "
     "fica otimista e não representa nada da operação real.",
     "Divisão sempre cronológica: treino no passado, teste no futuro."),
    ("`rolling` sem `shift`",
     "A média móvel termina no próprio dia que queremos prever, então a resposta está dentro "
     "da pergunta. Em produção a feature não existe, porque o dia ainda não terminou.",
     "Toda janela móvel começa com shift. Em painel, o shift é dentro do groupby."),
    ("Target encoding ingênuo",
     "A média do alvo por categoria inclui a própria linha. O erro de treino cai, a validação "
     "piora, e quem olhar só o treino comemora.",
     "Calcular fora da amostra (out-of-fold), ou deixar o CatBoost fazer com estatísticas ordenadas."),
    ("Avaliar o modelo no treino",
     "Uma árvore sem poda chega a erro zero no treino sem ter aprendido nada que sirva para "
     "amanhã.",
     "Avaliação fora da amostra, sempre. E walk-forward, porque um holdout único é um sorteio."),
    ("Otimizar métrica simétrica quando o custo é assimétrico",
     "Escolher o MAE é afirmar que faltar e sobrar custam igual. Em saúde, quase nunca custam.",
     "Escolher a métrica ANTES de treinar, conversando com quem sofre o erro."),
]


def render() -> None:
    comum.selo("Etapa 8 · Síntese", "as nove aulas do módulo F1")
    st.title("📚 O que fica")

    campo = comum.campo_de_jogo()
    rodados = st.session_state.get("modelos_rodados", {})
    campeao = st.session_state.get("campeão")

    st.markdown("### A cadeia inteira, nos números desta sessão")
    linhas = [
        {"etapa": "Não fazer nada (média histórica)",
         "MAE (ligações/dia)": round(campo["maes_referencia"]["Média histórica global"], 2),
         "leitura": "o custo de não ter modelo"},
        {"etapa": "Melhor referência simples",
         "MAE (ligações/dia)": round(campo["mae_referencia"], 2),
         "leitura": f"{campo['melhor_referencia']} — o número a ser batido"},
    ]
    if campeao and campeao in rodados:
        linhas.append({"etapa": f"Modelo campeão ({campeao})",
                       "MAE (ligações/dia)": round(rodados[campeao], 2),
                       "leitura": "o que a modelagem entregou"})
    linhas.append({"etapa": "Piso do problema (limite teórico)",
                   "MAE (ligações/dia)": round(campo["mae_piso"], 2),
                   "leitura": "aleatoriedade de Poisson: ninguém vai abaixo"})
    st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)

    if campeao and campeao in rodados:
        aproveitado = 100 * (campo["mae_referencia"] - rodados[campeao]) / \
                      (campo["mae_referencia"] - campo["mae_piso"])
        st.progress(min(max(aproveitado / 100, 0.0), 1.0))
        st.caption(f"O modelo capturou {num(max(aproveitado, 0), 1)}% do sinal aprendível "
                   "que existia entre a melhor referência simples é o piso do problema.")
    else:
        st.caption("Defina um campeão na etapa 3 para completar esta tabela.")

    st.markdown("---")
    st.markdown("### Cada aula é onde ela vive nesta aplicação")
    st.dataframe(pd.DataFrame([
        {"notebook": a, "assunto": b, "o que resolveu": c, "onde esta aqui": d}
        for a, b, c, d in AULAS]), width="stretch", hide_index=True)

    st.info("""
**Sobre o F1_06.** As arquiteturas de rede neural (perceptron, MLP, RNN e LSTM) ficaram
**fora do escopo** desta aplicação, por decisão de projeto. Três coisas daquele notebook,
porém, estão aqui: a **série da central com estado latente epidemiológico** é a base de tudo
o que você viu; o **piso de erro** dele é a régua de todas as páginas; e a **acumulação de erro em
previsão multi-passo** foi medida na etapa 5, com o modelo tabular.

O que fica só no notebook é o argumento de por que a LSTM existe: a demonstração da janela
embaralhada (a rede densa não sabe que existe ordem no tempo) e a tarefa de memória, em que a
RNN simples desaba para 52% de acerto em 34 passos enquanto a LSTM mantem 100%. Vale a
leitura para quem for trabalhar com sequências longas.
""")

    st.markdown("---")
    st.markdown("### Os cinco erros que este módulo ensina a não cometer")
    for i, (titulo, porque, defesa) in enumerate(ERROS, start=1):
        with st.expander(f"**{i}. {titulo}**"):
            st.markdown(f"**Por que engana.** {porque}\n\n**A defesa.** {defesa}")

    st.markdown("---")
    st.markdown("### Checklist de um projeto de previsão de demanda")
    st.markdown("""
**Antes de modelar**
- [ ] Escolher a métrica **conversando com quem sofre o erro**. Métrica escolhida depois dos
      resultados vira justificativa.
- [ ] Calcular o **piso do problema**. Para contagens, √(2λ/π) é uma boa aproximação.
- [ ] Estabelecer as **referências ingênuas**. Sem baseline, nenhum número significa nada.

**Ao construir variáveis**
- [ ] Começar pelo que sai **de graça do índice de tempo**, depois calendário, depois o
      **histórico da própria série** — é só então buscar dado externo, que custa integração.
- [ ] Toda janela móvel com `shift`. Em painel, `shift` dentro do `groupby`.
- [ ] Justificar cada variável de dado pessoal com **ablação**, não com "pode ser útil".
- [ ] Uma **única função** de features, com teste de equivalência treino × produção.

**Ao avaliar**
- [ ] Divisão **cronológica**. Três conjuntos quando houver early stopping.
- [ ] Reportar **MAE e RMSE juntos**, com a razão entre eles.
- [ ] **Walk-forward**: reportar média e dispersão, nunca um holdout único.
- [ ] Conferir contra o piso. **Ficou abaixo dele? Há vazamento, não há terceira explicação.**

**Ao entregar**
- [ ] Traduzir o erro em **decisão**: escala, fila, SLA, custo.
- [ ] Declarar a **incerteza** (faixa provável), não só o ponto.
- [ ] Definir a rotina de **monitoramento**, ordenada por importância da variável — não por
      tamanho do desvio.
""")

    st.markdown("---")
    e, d = st.columns(2)
    with e:
        st.markdown("""
##### O arco do curso

| Painel | Sistema | Pergunta |
| --- | --- | --- |
| **F1** (este) | central da operadora | qual será a demanda? |
| **D9** | integração ERP/HIS | como o dado chega limpo? |
| **D10** | Pronto Atendimento | com esta demanda, quantos médicos? |
| **E3** | warm-up e regime permanente | quando a simulação pode ser lida? |
| **E4** | análise de decisão | qual cenário levar para a diretoria? |
""")
    with d:
        st.markdown("""
##### Bibliografia citada nas aulas

- Breiman (2001) — *Random Forests*
- Chen & Guestrin (2016) — *XGBoost*
- Ke et al. (2017) — *LightGBM*
- Prokhorenkova et al. (2018) — *CatBoost*
- Taylor & Letham (2018) — *Forecasting at Scale* (Prophet)
- Hochreiter & Schmidhuber (1997) — *Long Short-Term Memory*
- Hastie, Tibshirani & Friedman (2009) — *The Elements of Statistical Learning*
- Box & Jenkins — metodologia de identificação ARIMA
""")

    st.caption("Módulo F1 · Previsão de Demanda na Gestão de Planos de Saúde · "
               "Prof. Pedro | UNIMED SP · base sintética com semente fixa")
