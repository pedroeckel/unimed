"""Página 0 — o mapa da viagem."""

from __future__ import annotations

import streamlit as st

from nucleo import avaliacao as A

from . import comum
from .comum import kpi, num

ETAPAS = [
    ("📈", "1. Dados", "Diagnóstico da série", "F1_01 · F1_02"),
    ("🧱", "2. Variáveis", "Feature engineering", "F1_07 · F1_08"),
    ("🤖", "3. Modelos", "Clássicos, árvores, boosting", "F1_02 a F1_05"),
    ("📏", "4. Avaliação", "MAE, RMSE, MAPE e custo", "F1_09"),
    ("🔮", "5. Previsão", "D+1 a D+14, hora a hora", "F1_07"),
    ("🏥", "6. Gêmeo", "Simulação de capacidade", "D9 · D10"),
    ("🎯", "7. Decisão", "Cenários e prescrição", "E4"),
]


def render() -> None:
    st.title("🗺️ Gêmeo Digital da Operadora — ponta a ponta")
    st.caption("Módulo F1 · Previsão de Demanda na Gestão de Planos de Saúde · "
               "Prof. Pedro | UNIMED SP")

    st.markdown("""
As nove aulas do módulo são excelentes e **desconectadas**: cada uma tem a sua própria
série, o seu próprio conjunto de teste e o seu próprio placar. Esta aplicação existe para
responder à pergunta que nenhuma delas responde sozinha:

> *"Tudo bem, o erro caiu de 80 para 36 ligações por dia. **E daí?** O que muda na operação?"*

A resposta está na etapa 6. A previsão vira **entrada** de uma simulação de capacidade, e a
simulação traduz erro de previsão em **fila, nível de serviço e custo**. É aí que a aula fecha.
""")

    st.markdown("### O percurso")
    colunas = st.columns(len(ETAPAS))
    for coluna, (icone, titulo, descricao, origem) in zip(colunas, ETAPAS):
        with coluna:
            st.markdown(
                f"<div style='text-align:center;border:1px solid #CFE0D5;border-radius:10px;"
                f"padding:.6rem .35rem;height:150px'>"
                f"<div style='font-size:1.5rem'>{icone}</div>"
                f"<div style='font-weight:700;font-size:.82rem;margin-top:.2rem'>{titulo}</div>"
                f"<div style='font-size:.72rem;color:#555;margin-top:.25rem'>{descricao}</div>"
                f"<div style='font-size:.65rem;color:#1A5E3A;margin-top:.4rem'>{origem}</div>"
                f"</div>", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("### Onde a sessão está agora")

    campo = comum.campo_de_jogo()
    rodados = st.session_state.get("modelos_rodados", {})
    campeao = st.session_state.get("campeão")
    mae_campeao = rodados.get(campeao) if campeao else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Central de atendimento", "Caso ativo", "info")
    with c2:
        kpi(campeao or "—", "Modelo campeão", "neutral" if not campeao else "")
    with c3:
        kpi(num(mae_campeao) if mae_campeao else "—", "MAE no teste (ligações/dia)",
            "neutral" if not mae_campeao else "")
    with c4:
        if mae_campeao:
            aproveitado = 100 * (campo["mae_referencia"] - mae_campeao) / \
                          (campo["mae_referencia"] - campo["mae_piso"])
            kpi(f"{num(max(aproveitado, 0), 1)}%", "do sinal aprendível capturado", "warning")
        else:
            kpi("—", "do sinal aprendível capturado", "neutral")

    if not campeao:
        st.caption("Os cartões se preenchem conforme você percorre as etapas 3 e 4.")

    st.markdown("")
    esq, dir_ = st.columns([3, 2])

    with esq:
        comum.info("O que é um gêmeo digital de operadora", """
Um **gêmeo digital** é uma réplica computacional de um sistema real que:

1. **aprende** com o histórico do sistema (aqui, o registro de ligações da central);
2. **prevê** a demanda futura (etapas 1 a 5 desta aplicação);
3. **simula** o comportamento da operação sob aquela demanda (etapa 6, com SimPy);
4. **recomenda** a ação — quantos atendentes escalar em cada turno (etapa 7).

O ponto que costuma se perder: as etapas 1 a 5 não são o produto. Elas produzem o
**input** do passo 3. Um gêmeo alimentado por uma taxa média fixa é um gêmeo que responde
com precisão a uma pergunta errada.
""")

        comum.info("Por que a base é sintética", """
Toda a base é gerada em memória, com semente fixa. A decisão é didática e vem dos
notebooks: como somos nos que plantamos cada efeito dentro dos dados (o ciclo diário, o
feriado, a janela de vencimento, a onda epidemiológica), sabemos exatamente o que o modelo
**deveria** descobrir, e podemos verificar se ele descobriu.

Mais importante: guardamos a **intensidade verdadeira** de cada hora — a média do processo
que gera as ligações. Com ela calculamos o **piso do problema**: o erro de quem soubesse essa
média exata e ainda assim errasse, porque a chegada de ligações é um sorteio.

**Para que serve o piso.** Sem ele, "MAE de 36" não diz se o modelo é bom ou ruim. Com ele, a
frase vira "o modelo capturou 74% de tudo o que era possível capturar". E ele também é o
detector de vazamento: se um modelo fica **abaixo** do piso, ele está lendo a resposta em
algum lugar. Na vida real o piso não vem de graça, mas quase sempre dá para estimá-lo —
para contagens, √(2λ/π) é uma boa aproximação.
""")

    with dir_:
        st.markdown("##### O campo de jogo desta base")
        st.markdown(f"""
| Referência | MAE (ligações/dia) |
| --- | ---: |
| Média histórica global | {num(campo['maes_referencia']['Média histórica global'])} |
| Repetir ontem (lag 1) | {num(campo['maes_referencia']['Repetir ontem (lag 1)'])} |
| Mesmo dia da semana passada | {num(campo['maes_referencia']['Mesmo dia da semana passada (lag 7)'])} |
| **Melhor referência simples** | **{num(campo['mae_referencia'])}** |
| **PISO do problema** (o melhor resultado possível) | **{num(campo['mae_piso'])}** |
""")
        st.caption(f"Todo o espaço disputável está entre "
                   f"{num(campo['mae_referencia'])} e {num(campo['mae_piso'])}, ou seja, "
                   f"{num(campo['mae_referencia'] - campo['mae_piso'])} ligações por dia. "
                   "E essa margem que a modelagem vai brigar para capturar.")

    st.markdown("---")
    st.markdown("""
##### Onde esta aplicação se encaixa no curso

| Painel | Sistema | Pergunta que responde |
| --- | --- | --- |
| **Este (F1)** | Operadora: central de atendimento | *qual será a demanda, e com que erro?* |
| **D9** | Integração ERP/HIS | *como os dados chegam limpos até aqui?* |
| **D10** | Pronto Atendimento (Manchester, médicos) | *com esta demanda, quantos médicos?* |

O arco completo do curso é **prever (F1) → integrar (D9) → simular (D10)**. O painel do D10
recebe a demanda como um dado de entrada; esta aplicação mostra de onde aquele dado vem.
""")
