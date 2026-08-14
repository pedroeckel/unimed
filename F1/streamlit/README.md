# Gêmeo Digital da Operadora — ponta a ponta

**Módulo F1 | Previsão de Demanda na Gestão de Planos de Saúde** · Prof. Pedro · UNIMED SP

Aplicação Streamlit que amarra as nove aulas do módulo F1 em uma única narrativa, do dado
bruto até a decisão de escala:

```
dados → diagnóstico → engenharia de variáveis → modelos → avaliação honesta
      → previsão operacional → GÊMEO DIGITAL (SimPy) → cenários e prescrição
```

Os notebooks são excelentes e desconectados: cada um tem a sua própria série, o seu próprio
conjunto de teste e o seu próprio placar. Esta aplicação existe para responder à pergunta que
nenhum deles responde sozinho: **"o erro caiu de 80 para 36 ligações por dia — e daí?"**

A resposta está na etapa 6. A previsão vira **entrada** de uma simulação de capacidade, e a
simulação traduz erro de previsão em **fila, nível de serviço e custo**.

---

## Como rodar

```bash
cd "<raiz do projeto>"
.venv/bin/streamlit run F1/streamlit/app.py
```

Ou, em um ambiente novo:

```bash
python -m venv .venv && .venv/bin/pip install -r F1/streamlit/requirements.txt
.venv/bin/streamlit run F1/streamlit/app.py
```

Não há nenhum arquivo de dados a baixar: **toda a base e sintética e gerada em memória**, com
semente fixa. A decisão é didática — como somos nos que plantamos cada efeito (ciclo diário,
feriado, janela de vencimento, onda epidemiológica), sabemos o que o modelo **deveria**
descobrir e podemos verificar se ele descobriu. E, principalmente, guardamos a **intensidade
verdadeira** de cada hora, o que da ao problema um **piso exato** de erro.

## Testes

```bash
cd F1/streamlit && python -m pytest testes -q
```

Os testes rodam sem subir o Streamlit. Cada um é um **invariante didático**, não uma
recomendação: se um deles quebrar, a aplicação passou a ensinar algo errado.

| Teste | O que protege |
| --- | --- |
| `test_split_e_cronologico` | treino no passado, teste no futuro, sem sobreposicao |
| `test_features_nao_usam_o_futuro` | a linha de hoje e identica com e sem os dados de amanhã |
| `test_pipeline_treino_igual_producao` | o teste que a 1ª versão do notebook F1_08 reprovou |
| `test_rolling_sempre_precedido_de_shift` | varredura estática de janelas móveis sem `shift` |
| `test_ninguem_bate_o_oraculo` | modelo abaixo do piso = vazamento, não conquista |
| `test_painel_ninguem_bate_o_piso` | o mesmo invariante no caso em painel |
| `test_modelo_supera_a_melhor_referencia` | sem bater o baseline, o projeto não se justifica |
| `test_gemeo_concorda_com_erlang_em_regime_estavel` | simulação contra teoria |
| `test_prescricao_atinge_a_meta` | a escala recomendada entrega o SLA pedido |
| `test_painel_features_nao_usam_o_futuro` | em painel, o `shift` tem que ser dentro do grupo |
| `test_target_encoding_ingenuo_vaza` | a assinatura do vazamento por média do alvo |
| `test_historico_e_o_bloco_mais_valioso` | o momento comercial latente só aparece nas defasagens |

## Mapa das páginas

| Página | O que mostra | Origem |
| --- | --- | --- |
| 🗺️ Visão geral | o percurso, o campo de jogo (referências e piso) | — |
| 📈 1. Dados | decomposição, perfis, ADF, ACF/PACF, laboratório | F1_01, F1_02 |
| 🧱 2. Variáveis | blocos e ablação, defasagem, vazamento, LGPD | F1_04, F1_07, F1_08 |
| 🤖 3. Modelos | referências, ARIMA×SARIMA, Prophet, árvores, boosting, **caso em painel** | F1_02 a F1_05 |
| 📏 4. Avaliação | MAE/RMSE/MAPE/WMAPE/MASE, walk-forward, custo assimétrico | F1_09 |
| 🔮 5. Previsão | D+1 a D+14, duas etapas, erro por horizonte | F1_07 |
| 🏥 6. Gêmeo | SimPy + Erlang C, erro de previsão → KPI | D9, D10 |
| 🎯 7. Cenários | surto, campanha, carteira; fronteira custo × serviço | E4 |
| 📚 8. Síntese | a cadeia em números, os cinco erros, checklist | todas |

O estado flui entre as páginas: o **campeão** escolhido na 3 e a **margem de segurança**
adotada na 4 alimentam a previsão da 5, que alimenta o gêmeo da 6 e os cenários da 7.

## Estrutura

```
F1/streamlit/
├── app.py                  entrypoint: config, CSS, sidebar, roteamento
├── nucleo/                 código puro, SEM Streamlit — é o que os testes exercitam
│   ├── dados.py            geradores sintéticos (semente fixa, intensidade guardada)
│   ├── features.py         pipeline único de variáveis (treino == produção)
│   ├── modelos.py          referências, SARIMA, Prophet, árvores, boosting
│   ├── avaliacao.py        métricas, walk-forward, custo assimétrico
│   ├── gemeo.py            SimPy (fila M/G/c por turno) + Erlang C
│   └── graficos.py         figuras Plotly com a identidade do curso
├── paginas/                uma página por etapa; `comum.py` concentra CSS e cache
└── testes/test_nucleo.py
```

**`nucleo/` não importa Streamlit em lugar nenhum.** Todo o cache mora em `paginas/comum.py`.
É por isso que os testes rodam em segundos, sem servidor.

## Sobre o "piso do problema"

Aparece em quase todas as páginas, e vale saber o que e antes de encontra-lo: **o piso não é um
modelo**, e ninguém pode construi-lo. É uma **conta** que responde "se alguém soubesse
exatamente a média de ligações de cada dia, quanto ainda erraria?". A resposta não é zero,
porque a chegada de ligações e um sorteio.

Ele está na aplicação por três motivos:

1. **Da escala ao erro.** Sem piso, "MAE de 36" não diz se o modelo é bom. Com ele, vira
   "capturamos 74% de tudo o que era capturavel" — a frase que se leva para a diretoria.
2. **Detecta vazamento.** Um modelo abaixo do piso está lendo a resposta em algum lugar.
3. **Marca o teto do ganho.** Na etapa 6, a escala dimensionada por uma previsão perfeita
   mostra quanto ainda há para ganhar melhorando o modelo.

Nesta base o piso é exato porque nós geramos os dados. Em projeto real ele se **estima** —
para contagens, √(2λ/π) e uma boa aproximação. Na literatura, o termo técnico é *oráculo*.

## Escopo

As arquiteturas de rede neural do **F1_06** (perceptron, MLP, RNN, LSTM) ficaram **fora do
escopo**, por decisão de projeto (ver `SPEC.md`, §13.5). Três coisas daquele notebook, porém,
seguem aqui: a **série da central com estado latente epidemiológico** é a base de tudo; o
**piso de erro** dele é a régua de todas as páginas; e a **acumulação de erro em previsão
multi-passo** e medida na etapa 5, com o modelo tabular. A página 8 diz isso ao aluno.

## Relação com os outros painéis

| Painel | Sistema | Pergunta |
| --- | --- | --- |
| **F1** (este) | central de atendimento da operadora | qual será a demanda, e com que erro? |
| **D9** | integração ERP/HIS | como o dado chega limpo até aqui? |
| **D10** | Pronto Atendimento (Manchester) | com esta demanda, quantos médicos? |

O arco do curso é **prever (F1) → integrar (D9) → simular (D10)**.
