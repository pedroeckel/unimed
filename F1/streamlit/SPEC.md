# SPEC — Aplicação Streamlit: Gêmeo Digital da Operadora, Ponta a Ponta

**Módulo F1 | Previsão de Demanda na Gestão de Planos de Saúde**
Prof. Pedro · UNIMED SP
Versão da spec: 1.4 · Status: **implementada** — ver §14, §15 e §16

---

## 1. Objetivo

Construir uma aplicação Streamlit **simples e didática** que mostre, em uma única narrativa
contínua, como as nove aulas do módulo F1 se encaixam em um **projeto real de ponta a ponta**:

```
dados brutos → diagnóstico → engenharia de variáveis → modelos → avaliação honesta
            → previsão operacional → GÊMEO DIGITAL (simulação) → decisão de capacidade
```

O aluno hoje vê nove notebooks excelentes, mas **desconectados**: cada um tem a sua própria série
sintética, o seu próprio conjunto de teste e o seu próprio placar. A aplicação existe para
responder à pergunta que nenhum notebook responde sozinho:

> *"Tudo bem, o MAE caiu de 5,03 para 4,21. **E daí?** O que muda na operação?"*

A resposta é o gêmeo digital: a previsão vira **entrada** de uma simulação de capacidade, e a
simulação traduz erro de previsão em **fila, SLA e custo**. É aí que a aula fecha.

### 1.1 Público

1. **Alunos do módulo F1** (gestores, analistas de operadora, profissionais de saúde com
   Python básico). Usam a app como laboratório guiado, sem escrever código.
2. **Prof. Pedro em aula**, projetando a tela e mexendo nos controles ao vivo.

### 1.2 O que a aplicação **não** é (não-objetivos)

- Não é um sistema de produção nem um substituto dos notebooks — é a **camada de síntese** deles.
- Não usa dados reais de beneficiário. Toda a base é **sintética e gerada em memória**,
  com semente fixa (mesma decisão didática dos notebooks: sabemos o que plantamos, então
  podemos verificar se o modelo achou).
- Não repete o painel do D10 (`D10/streamlit/app_gemeo_digital.py`), que é o gêmeo do
  **Pronto Atendimento**. Aqui o sistema simulado é a **operadora** (central de atendimento e
  autorização prévia). Ver §3.3 sobre a relação entre os dois.
- **Não inclui redes neurais.** Perceptron, MLP, RNN e LSTM (F1_06) ficam fora do escopo por
  decisão de projeto (§13.5). As lições operacionais daquela aula continuam presentes, mas por
  outros meios (§6, página 3).
- Não treina modelos pesados por padrão. O Prophet fica atrás de botão explícito (§8).

---

## 2. Fio condutor: o caso da operadora

Um único caso atravessa todas as páginas, exatamente como os notebooks F1_01, F1_02, F1_04,
F1_06 e F1_09 já fazem:

> **A central de atendimento da operadora.** Volume de ligações hora a hora. Prever essa demanda
> é o que permite dimensionar a escala de atendentes, cumprir o SLA de atendimento e controlar o
> custo operacional.

Três casos **secundários** aparecem em páginas específicas, como demonstrações pontuais, porque
carregam lições que a central não carrega:

| Caso secundário | Notebook | Lição exclusiva que ele traz |
| --- | --- | --- |
| Chegadas ao Pronto Atendimento | F1_07 | variáveis externas com **defasagem a descobrir** (clima, epidemia) |
| Autorização prévia por especialidade | F1_08 | painel, agregações por entidade, **LGPD** e pipeline em produção |
| Carteira de vidas por contrato | F1_05 | boosting em painel, **ablação de blocos**, oráculo, viés no agregado |
| Teleconsultas (3 anos) | F1_03 | Prophet: changepoints, sazonalidade anual, feriados |

A série da central usada em toda a app é a do **F1_06** (2 anos, hora a hora, com ondas
epidemiológicas latentes e a coluna `sinal` guardada para o oráculo). Ou seja: o F1_06 entra como
**gerador de dados e como problema**, embora as suas arquiteturas de rede tenham ficado fora
do escopo (§13.5).

**Regra de projeto:** o aluno nunca fica perdido sobre "de que série estamos falando". Toda página
mostra, no topo, um selo com o caso ativo e o notebook de origem.

---

## 3. Arquitetura

### 3.1 Estrutura de arquivos

```
F1/streamlit/
├── SPEC.md                            ← este documento
├── README.md                          ← como rodar, mapa das páginas
├── requirements.txt
├── app.py                             ← entrypoint: config, CSS, sidebar, roteamento
├── nucleo/
│   ├── __init__.py
│   ├── dados.py       (~250 l.)  geradores sintéticos, semente fixa, @st.cache_data
│   ├── features.py    (~200 l.)  pipeline ÚNICO de features (treino == produção)
│   ├── modelos.py     (~280 l.)  baselines, SARIMA, Prophet, RF, LGBM/XGB/Cat
│   ├── avaliacao.py   (~150 l.)  MAE/RMSE/MAPE/WMAPE/MASE, walk-forward, custo assimétrico
│   ├── gemeo.py       (~250 l.)  SimPy M/M/c por turno, Erlang C, KPIs, cenários
│   ├── graficos.py    (~300 l.)  figuras Plotly reutilizáveis
│   └── textos.py      (~250 l.)  blocos didáticos em Markdown, separados do código
├── paginas/
│   ├── p0_visao_geral.py
│   ├── p1_dados.py
│   ├── p2_features.py
│   ├── p3_modelos.py
│   ├── p4_avaliacao.py
│   ├── p5_previsao.py
│   ├── p6_gemeo.py
│   ├── p7_cenarios.py
│   └── p8_sintese.py
└── testes/
    └── test_nucleo.py                 ← pytest, roda sem Streamlit (§10)
```

Total estimado: **~2.000 linhas**, sendo ~700 de texto didático.

### 3.2 Decisões técnicas

| Decisão | Escolha | Motivo |
| --- | --- | --- |
| Navegação | `st.radio` na sidebar (como o app do D10) | consistência visual com o painel já existente; menos mágica para o aluno ler o código |
| Gráficos | **Plotly** | interatividade (hover com o número exato), igual ao D10 |
| Dados | sintéticos, gerados em memória, `@st.cache_data` | zero dependência de arquivo; reprodutível; sabemos a verdade |
| Modelos rápidos | treinados ao vivo, `@st.cache_resource` | LightGBM/RF/SARIMA-diário custam < 3 s |
| Modelo lento | Prophet atrás de botão + cache | ~10 s de ajuste |
| Estado entre páginas | `st.session_state` para a previsão escolhida | a página 6 (gêmeo) **consome** o que a página 5 produziu |
| Paleta e CSS | reaproveitados de `D10/streamlit/app_gemeo_digital.py` | identidade única do curso |

### 3.3 Relação com o painel D10

Os dois painéis são **complementares e explicitamente ligados**:

| | D10 (existente) | F1 (esta spec) |
| --- | --- | --- |
| Sistema simulado | Pronto Atendimento (Manchester, médicos) | Operadora (central de atendimento, atendentes) |
| Foco | **simulação**: a demanda é um dado de entrada | **previsão**: como se produz aquele dado de entrada |
| Pergunta | "com esta demanda, quantos médicos?" | "qual será a demanda, e com que erro?" |

A página 0 e a página 8 trazem um cartão apontando para o outro painel, fechando o arco
**F1 (prever) → D9 (integrar dados) → D10 (simular)**.

---

## 4. Modelo de dados

Tudo em `nucleo/dados.py`, funções puras, semente fixa, retorno `pandas`.
As funções são **transcrições diretas** dos geradores dos notebooks, para que o aluno reconheça
os números.

| Função | Origem | Saída | Efeitos plantados |
| --- | --- | --- | --- |
| `gerar_central_horaria(dias=730)` | F1_06 | 17.520 h | perfil horário, semanal, feriados, sazonalidade anual, **ondas epidemiológicas latentes**, ruído; coluna `sinal` guardada para o **oráculo** |
| `gerar_pa_horario(dias=730)` | F1_07 | 17.520 h + tabela diária de externas | clima, gripe, dengue com defasagens verdadeiras 3/4/7 dias; `intensidade` guardada |
| `gerar_autorizacoes(dias=730)` | F1_08 | painel 730 × 8 especialidades | dia da semana dominante, campanhas, vencimento, fim de trimestre, onda clínica |
| `gerar_carteiras(meses=48)` | F1_05 | painel 260 × 48 | setor, porte, reajuste × porte, crise macro, momento comercial latente |
| `gerar_teleconsultas()` | F1_03 | 1.096 dias | changepoint, sazonalidade anual, feriados BR |

**Contrato obrigatório:** toda função devolve, junto com a série observada, a **intensidade /
sinal verdadeiro**. Sem isso não há oráculo, e sem oráculo não há piso — e o piso é a espinha
dorsal didática do módulo inteiro (§7.5).

---

## 5. Identidade visual e padrões de página

Reaproveitados do D10: paleta (`VERDE #1A5E3A`, `AZUL #1F4E79`, `LARANJA #E65100`), cartões KPI,
helper `info(titulo, markdown)` em expander.

**Cada página segue o mesmo esqueleto de 5 blocos** — essa repetição é proposital, é o que
torna a app previsível para quem está aprendendo:

1. **Título + selo de origem** — `Etapa 3 · baseado em F1_04 e F1_05`
2. **O problema de gestão** (2–4 linhas) — por que um gestor de operadora se importa
3. **A ideia** — caixa `ℹ️` com a definição e a fórmula em LaTeX
4. **O laboratório** — controles + gráfico + tabela, recalculado ao vivo
5. **📖 Lendo o resultado** — caixa de leitura guiada, **gerada com os números da execução atual**
   (não texto fixo: usa f-strings sobre as métricas calculadas, no estilo dos notebooks)

O bloco 5 é o diferencial pedagógico. Um gráfico sem leitura guiada é decoração.

---

## 6. Especificação página a página

### Página 0 — 🗺️ Visão Geral: o mapa da viagem

**Objetivo:** em 30 segundos, o aluno entende o percurso e onde cada aula entra.

- Diagrama do pipeline (7 caixas encadeadas), com o número da aula em cada etapa.
- Quatro cartões KPI do estado atual da sessão: caso ativo, modelo campeão, MAE no teste,
  % do sinal aprendível capturado. Ficam com "—" até o aluno rodar as etapas.
- Caixa `ℹ️` **"O que é um gêmeo digital de operadora"**: réplica computacional que
  (1) aprende do histórico, (2) prevê a demanda, (3) simula a capacidade, (4) recomenda a escala.
- Cartão de ligação com o painel D10 e com os notebooks D9/E3/E4.

### Página 1 — 📈 Etapa 1: os dados e o que eles escondem *(F1_01, F1_02)*

**Problema de gestão:** antes de prever, entender o ritmo da operação.

Controles: caso (central / PA / autorização), período de zoom, granularidade (hora ou dia).

Conteúdo:
1. Série completa + zoom de 2 semanas (dois painéis).
2. **Decomposição** aditiva (`seasonal_decompose`, period=24 ou 7): observado, tendência,
   sazonalidade, resíduo.
3. Perfis médios: por hora do dia e por dia da semana — "o mapa de escala do gestor".
4. **Estacionariedade**: teste ADF na série e na 1ª diferença, com o veredito em destaque
   (p ≥ 0,05 → não estacionária). Slider de nº de diferenças.
5. **ACF e PACF** com marcação automática dos picos sazonais (lag 24/48 no horário, 7/14 no diário).
6. Laboratório dos 4 componentes: sliders de tendência, amplitude diária, amplitude semanal e
   ruído, redesenhando a série (réplica direta do laboratório do F1_01).

*Lendo o resultado* (gerado): correlação lag-1, p-valor do ADF antes e depois, amplitude
da sazonalidade, e a frase-ponte: *"o pico está às 10h e a segunda é o dia mais cheio; guarde
isso, porque é o que o modelo vai ter que reproduzir"*.

### Página 2 — 🧱 Etapa 2: engenharia de variáveis *(F1_07, F1_08, F1_04)*

**Problema de gestão:** trocar de algoritmo rende 0,04; construir variáveis rende 1,16.
Esta é a página que mais rende e a que menos aparece nos cursos.

Quatro abas:

**2.1 Da série para a tabela.** Mostra lado a lado a série (uma coluna + índice) e a matriz X
(10+ colunas). Mensagem: *a árvore não sabe o que é tempo; toda informação temporal vira coluna*.

**2.2 Blocos e ablação.** Checkboxes por bloco — temporais / cíclicas / calendário / operacionais /
histórico / clima / epidemia / perfil do beneficiário. A cada mudança, retreina o LightGBM e
atualiza: MAE, ganho do bloco, e a barra **"% do espaço aproveitável capturado"** entre a melhor
referência ingênua e o oráculo. Tabela de ablação acumulada, na ordem de trabalho real
(começa pelo que é de graça, termina pelo que custa integração).

**2.3 Defasagem: a correlação que engana.** Só para o caso PA. Dois painéis lado a lado:
correlação cruzada **bruta** (erra as 4 defasagens e inverte o sinal da temperatura) versus
correlação **dos resíduos** após remover tendência + harmônicos anuais + dia da semana
(acerta 3/0/4/7). Botão "revelar as defasagens verdadeiras".

**2.4 Vazamento e LGPD.** Duas demonstrações:
- `rolling(7)` sem `shift` — tabela linha a linha mostrando o alvo dentro da feature, e a
  correlação subindo de 0,565 para 0,794.
- **Custo da proteção**: três níveis de granularidade de dado de beneficiário
  (0 = nenhum, 1 = anonimizado em faixas, 2 = detalhado), com o MAE de cada um e a leitura:
  *o bloco sensível vale ~2,5% do erro; a minimização da LGPD deixou de ser opinião jurídica e
  virou número de acurácia*.
- Visualizador do **contrato de features** (`F1/pipeline_features_autorizacao.json`): versão,
  lista de colunas, estatísticas de referência do treino.

### Página 3 — 🤖 Etapa 3: os modelos *(F1_02 a F1_05)*

**Problema de gestão:** qual família usar, e quanto cada uma custa.

Uma aba por família, todas avaliadas **no mesmo conjunto de teste** — o que os notebooks,
sozinhos, não conseguem fazer:

| Aba | Modelo | Controles | Gráfico principal |
| --- | --- | --- | --- |
| Referências | média histórica, lag-1, lag-7, média-7, **oráculo** | — | barras de MAE com o piso destacado |
| Clássicos | ARIMA × SARIMA | p, d, q, ligar/desligar sazonalidade | previsão + IC 95% sobre o real |
| Prophet | Prophet com feriados BR | `changepoint_prior_scale`, feriados on/off | `plot_components` reconstruído em Plotly |
| Árvores | Árvore, Random Forest | `max_depth`, `min_samples_leaf`, `n_estimators` | curva treino×teste em U (overfitting ao vivo) |
| Boosting | XGBoost, LightGBM, CatBoost | `learning_rate`, `num_leaves`, early stopping | curva de validação com o vale marcado |

Elementos didáticos obrigatórios:
- Aviso em toda aba de boosting: *no bagging mais árvores nunca pioram; no boosting, pioram* —
  com a curva de validação virando para cima depois do vale.
- Coluna de **tempo de treino** ao lado do MAE. A aula é que precisão não é o único eixo:
  CatBoost é ~20× mais lento que o XGBoost nesta base para um empate técnico de 0,04.
- **Onde foram parar as lições do F1_06.** Como as redes ficaram fora do escopo, as três lições
  daquela aula que sobrevivem à decisão aparecem em outros lugares, e a app diz isso ao aluno
  numa caixa `ℹ️` ao pé da página:
  - *estado latente*: nenhuma coluna de calendário captura a onda epidemiológica — só o
    **histórico recente** percebe que o surto já começou (demonstrado na ablação da página 2,
    desligando o bloco de histórico);
  - *acumulação de erro em multi-passo*: agora medida com o modelo tabular campeão (página 5);
  - *o piso do problema*: o oráculo do F1_06 continua sendo a régua de todas as páginas.

### Página 4 — 📏 Etapa 4: avaliação honesta *(F1_09)*

**Problema de gestão:** o número que você reporta decide se o projeto continua.

1. **A média dos erros mente** — os 7 dias, os erros ±3 a ±5, a média -0,43.
2. **MAE, RMSE, MAPE calculados na mão**, conferidos com o scikit-learn.
3. **O caso em que a métrica troca o vencedor**: modelo A (erra 1 seis dias, erra 20 no sétimo)
   vence no MAE; modelo B (erra 5 todo dia) vence no RMSE. Pergunta ao aluno, com dois botões:
   *"na sua operação, qual você levaria?"* — cada resposta abre a justificativa correspondente.
4. **Defeitos do MAPE**: divisão por zero na madrugada (vira infinito) e assimetria
   (teto de 100% para quem subestima). **WMAPE** e **MASE** como alternativas.
5. **Divisão aleatória × cronológica**: o mesmo modelo parece 47% melhor com divisão aleatória.
   Gráfico com os dias de teste espalhados versus em bloco no fim.
6. **Walk-forward** com 8 janelas de 30 dias: a média, a melhor (13,77) e a pior (25,38).
   Mensagem: *um holdout não é um número, é um sorteio*.
7. **Custo assimétrico**: sliders `custo_falta` e `custo_sobra`; a curva de custo em função da
   margem de segurança. O MAE elege margem zero; o custo elege ~2%. **A margem escolhida aqui é
   guardada em `session_state` e usada na página 6.**

### Página 5 — 🔮 Etapa 5: a previsão operacional

**Problema de gestão:** a escala é fechada por hora e por turno, não por dia.

- O aluno escolhe o modelo campeão (padrão: o de menor MAE na página 4).
- Previsão para **D+1 a D+14**, com banda de incerteza (quantis dos resíduos do walk-forward).
- **Estratégia de duas etapas** (F1_07): total do dia × perfil intradiário por dia da semana,
  estimado só no treino. Comparação lado a lado com o modelo horário direto — a diferença é
  ~0,015 chegada/hora, ou seja, **nenhuma**, e um modelo é mais fácil de explicar do que dois.
- **Previsão recursiva multi-passo** (lição do F1_06, agora com o modelo tabular campeão):
  realimenta a própria previsão nas features de defasagem e mede a curva de erro por horizonte
  (1 h → 24 h). O que o aluno precisa ver é o crescimento **e a saturação**: o modelo não entra
  em espiral porque as colunas de calendário continuam sendo alimentadas com valores reais.
- Saída: `st.session_state["previsao_horaria"]` = DataFrame com `datetime`, `previsto`,
  `lo`, `hi`, `real` (quando existir). **É o contrato de entrada da página 6.**

### Página 6 — 🏥 Etapa 6: o gêmeo digital

**Problema de gestão:** previsão não é decisão. Quantos atendentes escalar em cada turno?

Esta é a página que só existe porque as cinco anteriores existem.

**Motor:** SimPy, fila M/G/c com capacidade variável por turno, alimentada pela previsão da
página 5 (λ por hora) e por uma distribuição de tempo de atendimento (lognormal, TMA configurável).
Réplicas independentes com IC 95%, warm-up e janela de coleta — mesmas convenções do D10.

**Benchmark analítico:** Erlang C calculado em paralelo. Se a simulação e a fórmula divergirem
muito em regime estável, há bug no modelo — é o teste de sanidade que o aluno aprende a fazer.

Controles: atendentes por turno (4 turnos), TMA médio, paciência do beneficiário (abandono),
nº de réplicas, semente.

KPIs em cartões: **tempo médio de espera**, **% atendido em ≤ 20 s (nível de serviço)**,
**taxa de abandono**, **utilização ρ por turno**, **custo de escala**.

Três painéis:
1. λ previsto × capacidade escalada, hora a hora — onde ρ passa de 0,85, a fila explode.
2. Distribuição do tempo de espera (histograma + P90), por réplica.
3. **O painel-chave: erro de previsão → KPI.** Roda o gêmeo três vezes — com a demanda **real**,
   com a **previsão do modelo** e com a **média histórica** (o input estático). A tabela mostra
   quanto de SLA se perde por usar o input estático. *Este é o número que justifica o módulo F1
   inteiro.*

### Página 7 — 🎯 Etapa 7: cenários e decisão

**Problema de gestão:** planejar o que ainda não aconteceu.

Cenários pré-configurados, cada um com um botão e uma explicação de origem:

| Cenário | Como entra no modelo | Origem |
| --- | --- | --- |
| Onda epidemiológica | ×λ de 1,0 a 2,0 sobre a previsão | estado latente do F1_06 |
| Campanha de comunicação | +45,6% por 5 dias | efeito medido no F1_08 |
| Feriado + dia seguinte | −26,4% e depois +7,7% | efeitos medidos no F1_07 |
| Crescimento da carteira | ×(1 + variação prevista) | modelo de carteira do F1_05 |

Para cada cenário: KPIs do gêmeo, e a **prescrição** — a menor escala por turno que mantém o
SLA acima da meta, encontrada por busca incremental. Tabela comparativa final:
cenário × escala recomendada × custo × SLA atingido.

Fecho com a **fronteira custo × serviço**: cada ponto é uma configuração de escala; a curva
mostra o trade-off e onde está o joelho. É a tela que vai para a diretoria.

### Página 8 — 📚 Síntese

- Tabela única: **cada aula → o que ela resolveu → o número que ela produziu nesta sessão**.
  A linha do **F1_06** aparece marcada como *"coberta no notebook, fora do escopo da app"*, com
  um cartão explicando o que se ganha lendo aquele material (§13.5). O aluno não deve descobrir
  a ausência sozinho.
- Os cinco erros que o módulo ensina a não cometer (divisão aleatória, `rolling` sem `shift`,
  target encoding ingênuo, avaliar no treino, otimizar métrica simétrica quando o custo é assimétrico).
- Checklist imprimível de projeto de previsão.
- Ligações para os notebooks, para o painel D10 e para a bibliografia
  (Breiman 2001; Chen & Guestrin 2016; Ke et al. 2017; Prokhorenkova et al. 2018;
  Taylor & Letham 2018; Hochreiter & Schmidhuber 1997; Hastie et al. 2009).

---

## 7. Invariantes didáticos (regras que o código deve garantir)

Estas não são recomendações, são **restrições de implementação**. Cada uma vira um teste (§10).

1. **Separação sempre cronológica.** Nenhum `train_test_split` aleatório em lugar nenhum.
2. **Três conjuntos quando há early stopping**: treino / validação / teste.
3. **Toda janela móvel começa com `shift`**, e em painel o `shift` é dentro do `groupby`.
4. **Uma única função de features**, usada no treino e na simulação de produção. Teste de
   equivalência com tolerância 1e-9 (o teste que reprovou a primeira versão do F1_08).
5. **Ninguém bate o oráculo.** Se um modelo ficar abaixo do piso, a app exibe um alerta
   vermelho: *"isto é impossível — procure o vazamento"*, e não um troféu.
6. **Toda comparação inclui as referências ingênuas.** Modelo sem baseline não é resultado.
7. **MAE e RMSE sempre juntos**, com a razão RMSE/MAE exibida como termômetro de dias de desastre.
8. **Números do texto vêm da execução.** Nada de constante escrita à mão na narrativa.

---

## 8. Desempenho

| Operação | Alvo | Estratégia |
| --- | --- | --- |
| Primeira carga (página 0) | < 3 s | só gera a série da central |
| Troca de página com cache quente | < 1 s | `@st.cache_data` nos dados, `@st.cache_resource` nos modelos |
| Retreino de LightGBM (ablação) | < 2 s | 730 linhas no caso diário |
| Random Forest 300 árvores | < 3 s | `n_jobs=-1` |
| SARIMA diário | < 3 s | série diária (não horária), grid de ordens pré-calculado |
| Prophet | ~10 s | `cache_resource` + spinner com aviso |
| Gêmeo, 10 réplicas × 30 h simuladas | < 5 s | SimPy puro, sem I/O |

**Medido na implementação** (MacBook do professor, cache frio na primeira visita de cada página,
quente nas seguintes):

| Página | 1ª visita | Visitas seguintes |
| --- | ---: | ---: |
| Visão geral / Avaliação / Síntese | < 0,3 s | instantâneo |
| 1. Dados | 0,6 s | 0,13 s |
| 2. Variáveis | **12,6 s** | 0,05 s |
| 3. Modelos | 6,7 s | 0,04 s |
| 5. Previsão | 2,9 s | 0,68 s |
| 6. Gêmeo | 1,0 s | 0,16 s |
| 7. Cenários | 0,6 s | 0,60 s |

A página 2 é a mais cara porque treina **sete** modelos (um por bloco da ablação, mais o da
seleção do aluno, mais o da importância por permutação). É custo único por sessão, com spinner
nomeando o que está rodando. O Prophet, na prática, ficou em ~1 s nesta base, então dispensou o
botão previsto na spec. Ficaram atrás de botão as três operações realmente caras: o custo da
proteção (LGPD, 3 modelos em painel), a curva de erro por horizonte (~4 s, 980 reconstruções de
features) e o ajuste do Prophet nas teleconsultas.

Se algum alvo estourar, a saída é **reduzir a amostra, nunca esconder o cálculo** — o aluno
precisa ver o custo computacional, que é parte da lição (CatBoost é ~20× mais lento que o
XGBoost nesta base, para um empate de 0,04 no MAE).

---

## 9. Dependências

`requirements.txt` (versões idênticas às já instaladas no `.venv` do projeto):

```
streamlit==1.57.0
pandas==3.0.3
numpy==2.4.4
scipy==1.17.1
plotly==6.7.0
statsmodels==0.14.6
scikit-learn==1.9.0
lightgbm==4.7.0
xgboost==3.3.0
catboost==1.2.10
prophet==1.3.0
simpy==4.1.1
```

Não há dependência nova em relação ao que o ambiente já tem. `matplotlib` não é usado (Plotly) e
não entra nenhuma biblioteca de deep learning, porque as redes ficaram fora do escopo (§13.5).

---

## 10. Critérios de aceite

A implementação está pronta quando:

**Funcional**
- [ ] `streamlit run F1/streamlit/app.py` sobe sem erro em ambiente limpo criado a partir do `requirements.txt`.
- [ ] As 9 páginas renderizam sem exceção, com todos os controles em qualquer combinação.
- [ ] A previsão gerada na página 5 alimenta de fato o gêmeo na página 6 (contrato do `session_state`).
- [ ] Toda página tem os 5 blocos do §5, incluindo o "📖 Lendo o resultado" com números vivos.

**Metodológico** — `pytest F1/streamlit/testes/`
- [ ] `test_split_e_cronologico`: `max(indice_treino) < min(indice_teste)` em todos os casos.
- [ ] `test_pipeline_treino_igual_producao`: diferença máxima < 1e-9.
- [ ] `test_ninguem_bate_o_oraculo`: para cada modelo, `MAE_modelo >= MAE_oraculo`.
- [ ] `test_rolling_tem_shift`: varredura estática do `features.py` — nenhum `.rolling(` sem
      `.shift(` antes na mesma expressão.
- [ ] `test_gemeo_bate_erlang`: em regime estável (ρ < 0,8), simulação e Erlang C dentro de 15%.
- [ ] `test_reprodutibilidade`: duas execuções com a mesma semente dão o mesmo MAE.

**Desempenho**
- [ ] Nenhuma interação sem botão explícito passa de 5 s no MacBook do professor.

**Didático**
- [ ] Um aluno que nunca viu os notebooks consegue percorrer as 9 páginas em ~35 min e explicar,
      no fim, por que o SARIMA ganha do ARIMA, por que o histórico é o bloco mais valioso e
      por que o modelo com MAE 2,39 estava trapaceando.

---

## 11. Plano de implementação

| Fase | Entrega | Páginas | Esforço |
| --- | --- | --- | --- |
| **1. Esqueleto** | app.py, CSS, sidebar, `dados.py`, `graficos.py` | 0, 1 | ~25% |
| **2. Núcleo analítico** | `features.py`, `modelos.py`, `avaliacao.py` | 2, 3, 4 | ~40% |
| **3. Gêmeo** | `gemeo.py`, integração via `session_state` | 5, 6, 7 | ~25% |
| **4. Acabamento** | textos didáticos, testes, README, revisão de desempenho | 8 + tudo | ~10% |

Cada fase termina com a app **rodando** — nunca há um estado intermediário quebrado.
Sugestão: revisão sua ao fim da Fase 2, que é onde as decisões pedagógicas ficam travadas.

---

## 12. Riscos

| Risco | Impacto | Mitigação |
| --- | --- | --- |
| App vira "9 notebooks empilhados" e perde o fio | alto | o gêmeo (pág. 6) como destino declarado desde a pág. 0; contrato de `session_state` entre 5 e 6 |
| Excesso de controles paralisa o aluno | médio | no máximo 4 controles por laboratório; padrões sempre em um estado interessante |
| Prophet trava a aula | baixo | atrás de botão, com aviso de tempo estimado |
| F1_06 ficar órfão no percurso | médio | a app declara onde as lições daquela aula foram parar (pág. 3) e usa a série dela como base; a pág. 8 aponta o notebook para quem quiser as arquiteturas |
| Números divergirem dos notebooks | baixo | mesmas sementes e geradores; a spec avisa que a app **recalcula**, e valores dos notebooks entram como faixa esperada, não como verdade fixa |
| Duplicar o painel D10 | médio | escopo separado (§3.3) e ligação cruzada explícita |

---

## 13. Decisões de escopo

| # | Decisão | Escolha | Status |
| --- | --- | --- | --- |
| 1 | **Fio condutor** | Central de atendimento da operadora; PA, autorização, carteira e teleconsultas como demonstrações pontuais | ✅ confirmado |
| 2 | **Motor do gêmeo** | SimPy (fila M/G/c por turno) + Erlang C como benchmark analítico de sanidade | ✅ confirmado |
| 3 | **Local** | `F1/streamlit/`, app independente do painel do D10, com ligação cruzada | ✅ confirmado |
| 4 | **Idioma** | Interface em português; identificadores de código sem acento, como nos notebooks | ✅ confirmado |
| 5 | **Redes neurais** | **Fora do escopo.** Sem perceptron, MLP, RNN ou LSTM | ✅ confirmado |

### 13.5 Consequências do corte das redes neurais

Registro explícito do que se perde e do que se mantém, para a decisão poder ser revisitada depois
sem arqueologia:

**Perde-se** (continua disponível no notebook `F1_06`, para quem quiser ir além):
- a demonstração da janela embaralhada, que prova que a rede densa não sabe que existe ordem;
- a tarefa de memória (RNN cai para 52% de acerto em 34 passos, LSTM mantém 100%);
- os mapas de calor dos portões da LSTM e o perfil de sensibilidade por defasagem;
- o argumento de eficiência por parâmetro (LSTM: 1,79 de MAE com 3.001 parâmetros, contra
  1,83 do MLP com 9.281).

**Mantém-se**, por outros meios:
- a série da central com **estado latente epidemiológico** continua sendo a base da app;
- o **oráculo** do F1_06 (MAE de 1,24) continua sendo o piso de referência;
- a **acumulação de erro em multi-passo** migra para a página 5, com o modelo tabular;
- a lição de que *nenhuma coluna de calendário captura o surto* aparece na ablação da página 2.

**Ganha-se**: ~30 s de treino a menos por sessão, ~150 linhas a menos, nenhuma dependência de
deep learning, e uma página 3 mais curta e mais focada na comparação que interessa para dados
tabulares — clássicos × árvores × boosting.

---

## 14. Estado da implementação

Implementada e verificada. `streamlit run F1/streamlit/app.py`, testes em
`F1/streamlit/testes/` (`python -m pytest testes -q` → **17 passam**).

### 14.1 O que existe

| Entregue | Onde |
| --- | --- |
| 9 páginas com o esqueleto de 5 blocos e leitura guiada com números vivos | `paginas/p0…p8` |
| Núcleo sem Streamlit (dados, features, modelos, avaliação, gêmeo, gráficos) | `nucleo/` |
| Contrato de estado entre páginas (campeão → margem → previsão horária → gêmeo) | `paginas/comum.py` |
| SimPy (fila M/G/c por turno, abandono) + Erlang C como benchmark | `nucleo/gemeo.py` |
| 17 testes de invariante didático | `testes/test_nucleo.py` |
| README com mapa das páginas e instruções | `README.md` |

### 14.2 Números que a base produz (semente 42)

O campo de jogo da série da central, em ligações por dia no conjunto de teste:

| Marco | MAE |
| --- | ---: |
| Média histórica global (input estático) | 104,8 |
| Mesmo dia da semana passada (lag 7) | 87,0 |
| **Melhor referência simples** (média dos últimos 7 dias) | **80,7** |
| Prophet (horizonte completo) | 78,4 |
| SARIMA(1,1,1)(1,1,1)[7] | 59,2 |
| Random Forest / CatBoost | ~36,5 / ~40,6 |
| **XGBoost / LightGBM** | **~36,2 / ~36,9** |
| **Oráculo (piso de Poisson)** | **20,5** |

O melhor modelo captura ~74% do espaço entre a melhor referência e o piso. ARIMA sem a parte
sazonal erra 81,1 contra 59,2 do SARIMA — a demonstração do F1_02 sobrevive intacta.

### 14.3 Diferenças em relação à spec, e por quê

1. ~~Painel de carteiras (F1_05) não foi gerado.~~ **Implementado na v1.3** (§15): o painel de
   260 contratos × 48 meses entrou como uma sétima aba da página 3, carregada sob demanda.
2. **Prophet avaliado na série da central**, com protocolo de horizonte completo declarado no
   próprio app, para que todos os modelos compartilhem o mesmo conjunto de teste. O caso
   original das teleconsultas (3 anos, changepoints) entra como demonstração à parte, atrás de
   botão, na própria aba do Prophet.
3. **Monitoramento de drift entrou** (não estava detalhado na spec): a página 2 cruza PSI com
   importância por permutação e nomeia o falso alarme das variáveis de calendário, que sempre
   acusam PSI altíssimo em separação temporal. O contrato de features do F1_08
   (`pipeline_features_autorizacao.json`) é exibido junto.
4. **Nível de serviço medido sobre chamadas oferecidas**, não sobre atendidas. Medir só entre
   as atendidas premia a operação que perde beneficiário no meio do caminho — e o app usa isso
   como lição explícita ao lado da taxa de abandono.
5. **A curva de erro por horizonte usa dias de partida consecutivos** em número múltiplo de 7.
   Com partidas espaçadas, cada horizonte caía sobre uma mistura diferente de dias da semana e
   a curva ficava serrilhada por artefato de amostragem, não pelo fenômeno.

---

## 15. v1.3 — o caso em painel e o vocabulário do piso

Duas mudanças depois da primeira entrega.

### 15.1 O painel de carteiras (F1_05) entrou

Era a única aula com cobertura parcial. Agora existe `dados.gerar_carteiras()` — 260 contratos
coletivos × 48 meses, com **momento comercial latente** (AR(1) por carteira), **interação
reajuste × porte** e **crise macro** com sensibilidade por setor — e
`features.construir_features_carteira()`, com todo o histórico defasado **dentro do grupo**.

Vive na sétima aba da página 3, **carregada sob demanda por botão** (a página 3 continua em
~8 s; a aba custa mais ~8 s quando aberta). Ela é marcada em destaque como **outro problema**:
outro alvo, outra base, outro conjunto de teste — os números não entram no placar da central.

Traz as três lições que a série única não consegue dar:

| Lição | O que a app mostra |
| --- | --- |
| **Ablação em painel** | histórico é o maior ganho (+0,44), porque o momento comercial não está em cadastro nenhum; macro não acrescenta nada, e a ablação é o que autoriza não integrar aquela fonte |
| **Vazamento por target encoding** | ingênuo × out-of-fold × sem o identificador, com nº de árvores **fixo** para os erros de treino serem comparáveis; a correlação com o alvo no treino mede o vazamento diretamente |
| **Viés no agregado** | a soma das previsões acerta a *forma* (correlação ~0,9) e erra o *nível*, porque árvores não extrapolam — e erros pequenos na mesma direção se somam em vez de se cancelar |

Mais o **efeito parcial do reajuste por porte**, a saída que vai para a mesa de precificação: o
modelo recupera sozinho a hierarquia plantada (Micro é o porte mais sensível ao preço).

Números da base (semente 42, teste = jul–dez/2025, em vidas por carteira-mês): carteira estável
5,25 · repetir o último mês 4,79 · **média dos 3 últimos meses 4,22** (melhor referência) ·
**LightGBM 3,86** · **piso 2,98**. A carteira total faz o U do notebook — 120,8 mil vidas, fundo
de 116,5 mil na crise, 130,3 mil no fim (+7,9%).

### 15.2 "Oráculo" virou "piso do problema"

O termo vinha dos notebooks, mas na interface ele sugere um *modelo* que o aluno deveria
construir, e não um limite teórico. Todos os rótulos e textos passaram a dizer **piso do
problema** (ou "limite teórico"), com uma explicação no primeiro contato em cada página:

> O piso **não é um modelo**, e ninguém pode construí-lo — é uma **conta**. Ele responde: se
> alguém soubesse exatamente a *média* de ligações de cada dia, quanto ainda erraria?

Os nomes internos (`oraculo_teste()`, `test_ninguem_bate_o_oraculo`) continuam como estão: são
código, não interface, e "oráculo" é o termo corrente na literatura.

O conceito **não** foi removido, porque três coisas da aplicação dependem dele: a métrica
"% do sinal aprendível" (que traduz MAE em algo que uma diretoria entende), o alarme de
vazamento e o experimento da página 6, onde a previsão perfeita marca o teto do que ainda há
para ganhar melhorando o modelo.

---

## 16. v1.4 — revisão do português

A interface tinha sido escrita **sem acentos**. A regra da §13.4 ("identificadores de código
sem acento, como nos notebooks") acabou aplicada também ao texto que o aluno lê, o que estava
errado: nos notebooks só os identificadores são ASCII; a prosa em markdown é acentuada.

Corrigido em ~2.700 palavras, com uma separação explícita entre as duas camadas:

| Camada | Regra | Exemplo |
| --- | --- | --- |
| **Texto que o aluno lê** | português correto, com acento | `"Piso do problema"`, `"A validação decide…"` |
| **Identificadores de código** | ASCII, como nos notebooks | `def construir_features_central`, `mae_referencia` |
| **Nomes de coluna e chaves de dicionário** | ASCII | `"variacao_vidas"`, `"fracao"`, `"media"` |

A terceira linha é a que exige disciplina e não é óbvia: uma chave acentuada quebra em silêncio
quando o outro lado da comparação é um identificador — `df.agg(adesoes=("adesões", "sum"))` cria
a coluna `adesoes`, e `mensal["adesões"]` estoura. Chave de dicionário e nome de coluna são
código, não texto.

A troca foi feita apenas dentro de literais de string e comentários (via `tokenize`), nunca no
código, e a revisão de `e` → `é` foi conferida caso a caso — regra automática erra nos dois
sentidos, e algumas trocas indevidas precisaram ser desfeitas à mão.

**Guarda contra regressão:** `test_prosa_esta_acentuada` varre todo literal de string com mais
de 60 caracteres e espaço (ou seja, prosa, não chave interna) procurando ~60 palavras que só
aparecem sem acento por descuido. São 22 testes no total agora.
