# Telas e análises — documentação de referência

**Módulo F1 · Gêmeo Digital da Operadora** · Prof. Pedro | UNIMED SP

Documento de referência da aplicação Streamlit, tela a tela. Para cada página: o que ela
responde, quais controles existem (com faixas e padrões), o que aparece na tela, **quais
análises dá para fazer** e o que roda por baixo.

> Documento irmão: [GUIA_DAS_PAGINAS.md](GUIA_DAS_PAGINAS.md) é o roteiro de apresentação
> (o que falar, o que clicar, quanto tempo). Este aqui é o manual de referência.

---

## Sumário

- [Parte I — O que você precisa saber antes](#parte-i--o-que-você-precisa-saber-antes)
  - [1. Arquitetura](#1-arquitetura)
  - [2. A base sintética: o que foi plantado](#2-a-base-sintética-o-que-foi-plantado)
  - [3. Os cortes temporais](#3-os-cortes-temporais)
  - [4. O vocabulário: referência, piso, % do aproveitável](#4-o-vocabulário-referência-piso--do-aproveitável)
  - [5. O estado compartilhado](#5-o-estado-compartilhado-entre-telas)
- [Parte II — Tela a tela](#parte-ii--tela-a-tela)
  - [Tela 0 — Visão geral](#tela-0--visão-geral)
  - [Tela 1 — Dados e diagnóstico](#tela-1--dados-e-diagnóstico)
  - [Tela 2 — Engenharia de variáveis](#tela-2--engenharia-de-variáveis)
  - [Tela 3 — Modelos](#tela-3--modelos)
  - [Tela 4 — Avaliação honesta](#tela-4--avaliação-honesta)
  - [Tela 5 — Previsão operacional](#tela-5--previsão-operacional)
  - [Tela 6 — Gêmeo digital](#tela-6--gêmeo-digital)
  - [Tela 7 — Cenários e decisão](#tela-7--cenários-e-decisão)
  - [Tela 8 — Síntese](#tela-8--síntese)
- [Parte III — Referência rápida](#parte-iii--referência-rápida)

---

# Parte I — O que você precisa saber antes

## 1. Arquitetura

```
F1/streamlit/
├── app.py            entrypoint: config, CSS, barra lateral, roteamento das 9 páginas
├── nucleo/           código puro, SEM Streamlit — é o que os testes exercitam
│   ├── dados.py      geradores sintéticos (semente 42, intensidade verdadeira guardada)
│   ├── features.py   pipeline único de variáveis (a mesma função no treino e em produção)
│   ├── modelos.py    referências, SARIMA, Prophet, árvores, boosting, ablação
│   ├── avaliacao.py  métricas, walk-forward, PSI, custo assimétrico
│   ├── gemeo.py      SimPy (fila M/G/c por turno) + Erlang C
│   └── graficos.py   figuras Plotly
├── paginas/          uma página por etapa; comum.py concentra CSS, cache e estado
└── testes/           12 invariantes didáticos, rodam sem subir o Streamlit
```

**Duas consequências práticas:**

1. `nucleo/` **não importa Streamlit em lugar nenhum**. Todo o cache mora em
   `paginas/comum.py`. É por isso que `python -m pytest testes -q` roda em segundos.
2. Modelos ficam em `@st.cache_resource` e tabelas em `@st.cache_data`. **A primeira visita a
   cada aba é lenta; as seguintes são instantâneas.** Mudar um slider gera uma chave de cache
   nova — voltar ao valor anterior é instantâneo.

**Barra lateral:** navegação entre as 9 páginas, o estado da sessão (campeão, nº de modelos
rodados, previsão horária pronta/pendente) e o botão **♻️ Limpar cache e recomeçar**, que zera
os dois caches e todas as chaves de estado.

## 2. A base sintética: o que foi plantado

Nada é lido de disco. Tudo é gerado em memória com **semente fixa (42)** — o resultado é
idêntico em qualquer máquina. O contrato dos geradores: **toda função devolve, junto com a
série observada, a intensidade verdadeira** (o sinal antes do sorteio). Sem ela não existe piso.

### 2.1 Caso principal — central de atendimento (730 dias × 24h)

A intensidade horária é **multiplicativa**:

```
λ(t) = 22 × tendência × fator_hora × fator_semana × fator_feriado
       × (1 + onda_anual + surto) × fator_vencimento × fator_campanha
n_ligacoes(t) ~ Poisson(λ(t))
```

| Efeito plantado | Magnitude | Quem captura |
| --- | --- | --- |
| Nível base | 22 ligações/hora | — |
| **Ciclo diário** | de −9 (madrugada) a +9 (10h) sobre a base | `hora`, cíclicas |
| **Ciclo semanal** | segunda +3 … domingo −3 | `dia_semana` |
| **Tendência** | +0,022% ao dia (≈ +16% em 2 anos) | `dia_do_ano`, médias móveis |
| **Onda anual** | ±12%, pico no dia 196 (meados de julho) | `mês`, `doy_sin/cos` |
| **Onda epidemiológica** | surtos de +18% a +42%, meia-vida 12 dias, ~1%/dia de chance | **só o histórico** (`lag1`, `media7`) |
| **Feriado** | ×0,45 (−55%) | `eh_feriado` |
| **Janela de vencimento** | ×1,18 nos dias 5–9, **só das 8h às 18h** | `janela_vencimento` |
| **Campanha de SMS** | ×1,25, 5 campanhas de 5 dias | `campanha` |

A **onda epidemiológica é o coração didático da base**: ela não tem período fixo, começa em data
arbitrária e **nenhuma coluna de calendário a captura**. É ela que separa um modelo bom de um
modelo médio, e é por isso que o bloco `histórico` domina a ablação da tela 2.

Repare também na **interação vencimento × hora**: o efeito do boleto só existe no horário
comercial. Um modelo que trate `janela_vencimento` como efeito aditivo constante erra as
madrugadas dos dias 5 a 9.

### 2.2 Casos secundários

| Caso | Onde aparece | O que carrega de único |
| --- | --- | --- |
| **Pronto atendimento** (730 dias + clima/epidemia) | tela 2, aba 3 | defasagens verdadeiras: temperatura **3** dias, chuva **0**, gripe **4**, dengue **7**. O efeito da temperatura entra como `graus_frio = max(0, 19 − temp)` — ou seja, **frio de 3 dias atrás gera chegada hoje** |
| **Autorizações prévias** (730 dias × 8 especialidades) | tela 2, aba 4 | painel; colunas de perfil do beneficiário (idade, % 60+, % crônico) para a discussão de LGPD; campanha vale **+45,6%** aqui |
| **Carteiras** (260 contratos × 48 meses) | tela 3, aba 🧪 | **momento comercial latente** AR(1) (coef. 0,86) que não está em nenhum cadastro; interação **reajuste × porte**; crise macro com sensibilidade por setor; dezembro sempre pior (×1,30 no cancelamento) |
| **Teleconsultas** (3 anos) | tela 3, aba Prophet | **changepoint de tendência** plantado em set/2022 |

## 3. Os cortes temporais

**Sempre cronológicos. Nunca aleatórios.**

| Conjunto | Central (diária/horária) | Carteiras (mensal) | Para que serve |
| --- | --- | --- | --- |
| **Treino** | até 31/mai/2025 | até dez/2024 | ajustar parâmetros |
| **Validação** | jun–ago/2025 | jan–jun/2025 | decidir nº de árvores (early stopping) e ordens do SARIMA |
| **Teste** | set–dez/2025 | jul–dez/2025 | **nunca participa de nenhuma decisão** |

O **perfil intradiário** da tela 5 também é estimado **apenas até o fim do treino** — sem esse
recorte ele conteria informação do futuro e toda a avaliação ficaria otimista.

### O protocolo de previsão (importante para ler o placar)

- **Referências, SARIMA, árvores e boosting** preveem **um dia à frente**, com todo o histórico
  real disponível até ontem. É o uso operacional: a escala de amanhã é fechada hoje.
- **Prophet** prevê **o horizonte inteiro de uma vez**, porque não usa defasagens. É uma
  vantagem dele (não depende do dado de ontem chegar a tempo) e uma desvantagem na comparação.
  **Ler o placar sem saber disso leva à conclusão errada.**

## 4. O vocabulário: referência, piso, % do aproveitável

| Termo | Definição | Como é calculado aqui |
| --- | --- | --- |
| **Referências ingênuas** | regras bobas que qualquer um implementaria | média histórica, repetir ontem (lag 1), mesmo dia da semana passada (lag 7), média dos últimos 7 dias, média dos 4 últimos mesmos dias |
| **Melhor referência simples** | a menor MAE entre elas | é o número que o modelo **precisa bater** |
| **Piso do problema** | o erro de quem soubesse a **intensidade verdadeira** e ainda assim errasse | MAE entre `n_ligacoes` e `intensidade` no teste |
| **% do aproveitável** | `100 × (MAE_ref − MAE_modelo) / (MAE_ref − MAE_piso)` | onde o modelo está entre os dois |

**O piso não é um modelo — é uma conta.** Para contagens de Poisson, o erro mínimo esperado é
**√(2λ/π)**. Ele existe na aplicação por três razões:

1. **dá escala ao erro** — "MAE de 36" vira "capturamos 74% do que era capturável";
2. **detecta vazamento** — modelo abaixo do piso está lendo a resposta em algum lugar (a tela 3
   dispara um alerta vermelho automaticamente quando isso acontece);
3. **marca o teto do ganho** — na tela 6, a linha da "previsão perfeita" mostra quanto ainda há
   para ganhar melhorando o modelo.

**Nota metodológica:** aqui o piso é *exato* porque nós geramos os dados. Em projeto real ele se
**estima** — √(2λ/π) para contagens, ou o erro de um modelo maduro já em produção.

## 5. O estado compartilhado entre telas

Três decisões viajam entre as páginas via `st.session_state`:

| Chave | Onde nasce | Onde é consumida | Se você não definir |
| --- | --- | --- | --- |
| `campeão` + `previsao_teste` | tela 3, aba 🏁 Placar | telas 5, 6, 7 | usa "Média dos 4 últimos mesmos dias" e avisa na tela |
| `margem_seguranca` | tela 4, aba Custo assimétrico | telas 5, 6, 7 | fica em 0% (previsão crua) |
| `previsao_horaria` | tela 5, aba Duas etapas | telas 6 e 7 | as telas montam uma versão padrão sozinhas |
| `modelos_rodados` | toda aba de modelo da tela 3 | barra lateral, telas 0 e 8 | placar vazio |

**Nada quebra se você pular etapas** — mas a cadeia perde o sentido, porque o aluno não vê a
própria escolha mudando o KPI final.

---

# Parte II — Tela a tela

---

## Tela 0 — Visão geral

🗺️ **Pergunta:** onde estamos e qual é o campo de jogo?

### O que a tela mostra
- **Sete cartões** com o percurso (etapas 1 a 7) e o notebook de origem de cada uma.
- **Quatro KPIs de sessão**: caso ativo, modelo campeão, MAE no teste, % do sinal capturado.
  Começam vazios e se preenchem conforme você percorre as telas 3 e 4.
- **Dois blocos explicativos** (expanders): o que é um gêmeo digital; por que a base é sintética.
- **A tabela do campo de jogo**: as três referências principais + o piso.

### Análises possíveis

**A1 — Ler o espaço disputável.** A tabela dá os dois extremos. A diferença entre a melhor
referência simples e o piso é *todo* o espaço em que a modelagem pode operar. Qualquer promessa
de ganho acima disso é impossível por construção.

**A2 — Ranquear as próprias referências.** A ordem entre "média histórica global", "repetir
ontem" e "mesmo dia da semana passada" já é um diagnóstico: se o lag 7 bate o lag 1, a
sazonalidade semanal é forte. Se a média histórica não é a pior de todas, a série tem pouca
estrutura de curto prazo.

**A3 — Acompanhar a sessão.** Volte a esta tela depois das telas 3 e 4: os cartões passam a
mostrar o campeão e o % capturado. É o "placar do jogo" em uma tela só.

### Por baixo
`comum.campo_de_jogo()` calcula as referências no teste, escolhe a melhor por MAE e mede o piso
com `oraculo_teste()` — a coluna `intensidade` do gerador, agregada por dia.

---

## Tela 1 — Dados e diagnóstico
📈 *F1_01 (fundamentos) e F1_02 (estacionariedade)* · **6 abas**

**Pergunta de gestão:** em que horas o telefone toca, que dias são cheios, o que o calendário
explica e o que ele não explica.

### KPIs do topo
horas de operação · ligações/hora (média) · ligações/dia (média) · menor e maior dia.

### Aba 1 — A série

| Controle | Faixa | Padrão |
| --- | --- | --- |
| Semana para o zoom | qualquer início a cada 7 dias na série | 02/jun/2025 |

Mostra o total diário com média móvel de 14 dias e **linhas verticais vermelhas nos feriados**,
mais um zoom de duas semanas hora a hora.

**Análises possíveis:**
- **A1 — Separar sazonalidade de ciclo.** A média móvel de 14 dias **não é plana nem
  puramente sazonal**: tem platôs e corcovas que duram semanas. Essas são as ondas
  epidemiológicas. A tela informa em quantos dias houve onda ativa e o pico em %.
- **A2 — Verificar o efeito do feriado visualmente.** As linhas vermelhas caem quase sempre
  sobre os vales mais fundos. É a confirmação visual do ×0,45 plantado.
- **A3 — Passear pelo zoom.** Mova o slider para uma semana com campanha (abr e set/2024,
  mar, ago e out/2025) e compare com uma semana comum. O degrau de +25% é visível a olho nu.
- **A4 — Ver os dois ciclos simultâneos.** No zoom, o ciclo de 24h se repete dia após dia; o de
  7 dias aparece como diferença de altura entre dias úteis e fim de semana.

### Aba 2 — Decomposição

| Controle | Opções | Padrão |
| --- | --- | --- |
| Granularidade | Diária (s=7) / Horária (s=24) | Diária |

Roda `seasonal_decompose` aditivo e mostra as quatro faixas (série, tendência, sazonalidade,
resíduo), com a leitura já calculada: variação da tendência em %, amplitude da sazonalidade,
desvio-padrão do resíduo.

**Análises possíveis:**
- **A1 — Quantificar a tendência.** A tela informa de quanto para quanto a tendência foi e o
  crescimento percentual. Compare com o +16% plantado.
- **A2 — Trocar a granularidade.** Em s=24 a amplitude sazonal domina tudo; em s=7 ela é bem
  menor. É a demonstração de que "sazonalidade" depende da escala em que você olha.
- **A3 — Olhar o que sobrou no resíduo.** O resíduo **não é só ruído**: parte dele é a onda
  epidemiológica, que a decomposição clássica **não sabe isolar** porque ela não tem período
  fixo. Esse é o limite do método, e é o argumento de por que precisamos de modelos com
  defasagem.

### Aba 3 — Perfis (o mapa de escala)

Média de ligações por hora do dia e por dia da semana, com a razão pico/vale calculada.

**Análises possíveis:**
- **A1 — Ler o retrato do call center.** Vale de madrugada, subida pela manhã, pico às 10h,
  queda no almoço, segundo platô à tarde. A tela informa a razão pico/vale.
- **A2 — Identificar o dia mais cheio e o mais calmo.** Sai direto do gráfico da direita.
- **A3 — Reconhecer a tabela que volta na tela 5.** Este perfil, normalizado em fração do dia,
  **é exatamente o que desce a previsão diária para a hora** na estratégia de duas etapas.

### Aba 4 — Estacionariedade

| Controle | Faixa | Padrão |
| --- | --- | --- |
| Número de diferenciações (d) | 0 a 2 | 0 |

Teste ADF (H₀: a série **não** é estacionária) com estatística, p-valor e veredito em cartões
que mudam de cor.

**Análises possíveis:**
- **A1 — Descobrir o `d` do SARIMA experimentalmente.** Em d=0 o p-valor fica acima de 0,05
  (não estacionária). Em d=1 ele despenca. **Esse é o d=1 que a tela 3 vai usar.**
- **A2 — Ver o custo da diferenciação.** Com d≥1 a série passa a oscilar em torno de zero: a
  diferenciação **remove o nível, e com ele a informação de escala**. Modelos de árvore não
  precisam disso — não têm pressuposto de estacionariedade.
- **A3 — Testar a sobrediferenciação.** Vá para d=2. O p-valor continua baixo, mas a série fica
  visivelmente mais ruidosa. Diferenciar demais injeta ruído sem ganho.

### Aba 5 — ACF e PACF

| Controle | Opções | Padrão |
| --- | --- | --- |
| Série | Diária (lags em dias) / Horária (lags em horas) | Diária |

Correlogramas com banda de confiança (±1,96/√n) e destaque nos múltiplos do ciclo (7, 14, 21, 28
na diária; 24 e 48 na horária).

**Análises possíveis:**
- **A1 — Justificar o `s` do SARIMA.** Os picos da ACF nos múltiplos de 7 (ou 24) são a
  assinatura da sazonalidade. É a evidência formal para `s=7`.
- **A2 — Orientar `p` e `q`.** Regra prática: a **ACF orienta o q**, a **PACF orienta o p**. Na
  PACF as barras despencam depois dos primeiros lags → componente autorregressivo de ordem baixa
  já basta.
- **A3 — Comparar as duas granularidades.** Na horária, o pico em 24 e 48 é muito mais marcado
  que qualquer coisa na diária. Quanto mais forte a sazonalidade, mais o modelo perde ao ignorá-la.

### Aba 6 — Laboratório dos componentes

| Controle | Faixa | Padrão |
| --- | --- | --- |
| Amplitude do ciclo diário | 0,0 a 2,0 | 1,0 |
| Amplitude do ciclo semanal | 0,0 a 3,0 | 1,0 |
| Força da onda epidemiológica | 0,0 a 3,0 | 1,0 |

Monta uma série sintética ao vivo e sobrepõe à série real (3 semanas).

**Análises possíveis:**
- **A1 — Isolar cada componente.** Zere a amplitude diária: as ondas de 24h somem e sobra o
  degrau semana/fim de semana. Zere a semanal: todos os dias ficam iguais.
- **A2 — Ver a assinatura da onda epidemiológica.** Suba a força para 3,0: aparecem corcovas de
  várias semanas que **não seguem nenhum calendário** — começam em datas arbitrárias e decaem
  devagar. É a distinção **sazonalidade × ciclo** em uma tela.
- **A3 — Ajustar a olho.** Tente reproduzir a série real mexendo nos três controles. Você vai
  chegar perto, mas nunca em cima — o que sobra é o ruído de Poisson, ou seja, **o piso**.

---

## Tela 2 — Engenharia de variáveis
🧱 *F1_07 (chegadas ao PA) e F1_08 (operadora e LGPD)* · **4 abas**

**Premissa:** nos notebooks, a diferença entre XGBoost, LightGBM e CatBoost foi de **0,04**; a
diferença entre um conjunto pobre e um conjunto bem construído de variáveis foi de **1,16** —
quase trinta vezes maior.

### Aba 1 — Da série para a tabela

Mostra o "antes" (uma coluna + índice) e o "depois" (a linha se descreve sozinha), com três
KPIs: linhas, colunas e **dias perdidos no aquecimento**.

**Análises possíveis:**
- **A1 — Medir o custo do aquecimento.** A `media28` precisa de 28 dias de história para
  existir. A tela informa quantos dias foram perdidos no início da série. **É um custo real da
  engenharia de variáveis**, e é o motivo de se recomendar 12+ meses de histórico antes de começar.
- **A2 — Entender por que a ordem temporal precisa virar coluna.** Uma árvore não tem noção de
  tempo: se você embaralhasse as linhas, o treinamento daria o mesmo resultado.

**Os cinco blocos disponíveis:**

| Bloco | Colunas | Custo de obter |
| --- | --- | --- |
| `temporais` | dia_semana, mês, dia_mes, semana_mes, eh_fim_semana, dia_do_ano | zero (saem do índice) |
| `cíclicas` | dsem_sin/cos, doy_sin/cos | zero |
| `calendário` | eh_feriado, eh_vespera, eh_pos_feriado, ferias_escolares | baixo (tabela de feriados) |
| `operacionais` | janela_vencimento, fim_trimestre, campanha, dias_restantes_mes | médio (conhecimento do negócio) |
| `histórico` | lag1, lag7, lag14, media7, media28, desvio7, tendencia_7_28 | zero (já está na base) |

### Aba 2 — Blocos e ablação

| Controle | Padrão |
| --- | --- |
| 5 checkboxes de bloco | temporais, calendário, operacionais, histórico ligados; **cíclicas desligado** |

Ao mudar qualquer checkbox, um LightGBM é retreinado e a tela mostra MAE, MAPE, nº de variáveis,
% do aproveitável e uma **barra de progresso** que vai da melhor referência até o piso. Abaixo,
a **tabela de ablação**: um modelo por bloco acrescentado, na ordem em que um projeto real os
constrói.

**Análises possíveis:**
- **A1 — Medir o valor de cada bloco isoladamente.** Desligue `histórico` e observe o MAE piorar
  e a barra encolher. É o bloco de maior ganho **e de custo zero**: a informação já estava na
  própria base.
- **A2 — Demonstrar que redundância não é utilidade.** Ligue `cíclicas`. O ganho é praticamente
  nulo. Motivo: para uma **árvore**, seno e cosseno são redundantes — ela corta
  `dia_semana ≤ 4,5` e reconstrói qualquer formato sozinha. As cíclicas valem muito em modelo
  **linear** e quase nada aqui.
- **A3 — Simular um projeto com dados pobres.** Deixe só `temporais` ligado. O modelo fica perto
  (ou pior) da referência simples — é o retrato de quem só tem o índice de tempo.
- **A4 — Ordenar o roadmap de integração de dados.** A coluna "ganho do bloco" responde
  diretamente: vale a pena integrar essa fonte? Bloco caro com ganho marginal não entra.
- **A5 — Confirmar a lição central.** O bloco `histórico` é **o único que enxerga a onda
  epidemiológica**. Nenhuma coluna de calendário sabe que um surto começou; `lag1` e `media7` sabem.

**Expander: importância por permutação + PSI**

Embaralha cada coluna 8 vezes e mede quanto o MAE piora — medido **fora da amostra** e **na
métrica que interessa**, o que é mais confiável que a importância interna do modelo.

**Análises possíveis:**
- **A6 — Encontrar variáveis que atrapalham.** Importância **negativa** significa que embaralhar
  a coluna **melhorou** o modelo. São candidatas naturais a remoção: menos colunas, menos
  manutenção, menos chance de drift.
- **A7 — Ler o PSI corretamente (monitoramento).** A tabela cruza **PSI treino→teste** com
  **importância**. Duas leituras opostas:
  - **Falso alarme:** em separação temporal, `mês`, `dia_do_ano` e `doy_sin` **sempre** acusam
    PSI altíssimo — o teste cobre set–dez e o treino não tinha esses meses. É **esperado por
    construção**. Um painel que dispara alerta aí ensina a equipe a ignorar alertas.
  - **Alarme de verdade:** variáveis não-calendário com PSI ≥ 0,25 **e** importância positiva.
    Costumam ser as médias móveis, que se deslocam junto com o nível crescente da série.
  - **A regra:** ordene o monitoramento **por importância, não por PSI**. Desvio enorme em
    variável fraca faz barulho e não muda nada; desvio moderado em variável forte estraga o
    modelo em silêncio.

### Aba 3 — Defasagem: a correlação que engana

Troca de caso: **chegadas ao pronto atendimento**, com temperatura, chuva, alerta de gripe e
alerta de dengue. As defasagens verdadeiras são **3, 0, 4 e 7 dias**, e a tela tenta descobri-las
por dois métodos, mostrando as duas curvas de correlação cruzada para cada variável.

| Método | Como funciona | Acertos típicos |
| --- | --- | --- |
| **Ingênuo** | correlaciona a série bruta com a variável bruta | erra quase todas |
| **Correto** | correlaciona os **resíduos** depois de remover tendência, 3 harmônicos anuais e dia da semana | acerta |

**Análises possíveis:**
- **A1 — Ver a correlação bruta mentir.** O caso da **temperatura** é o mais eloquente: a
  correlação bruta é próxima de zero, o que sugere "a temperatura não importa". Ela importa, e
  muito — é a variável externa mais valiosa, com efeito **negativo** (frio três dias atrás →
  mais chegadas hoje) que só aparece no resíduo.
- **A2 — Entender a causa: sazonalidade compartilhada.** Todas as séries sobem e descem juntas
  ao longo do ano. No verão faz calor **e** há dengue; no inverno faz frio **e** há gripe. Como
  todas oscilam com o mesmo ciclo anual, todas correlacionam com todas, e a correlação bruta mede
  **principalmente essa sazonalidade** — não a relação causal.
- **A3 — Formular a pergunta certa.** O método dos resíduos responde: *"quando esta variável se
  afasta do seu próprio padrão sazonal, em quantos dias as chegadas se afastam do delas?"*
- **A4 — Comparar o formato das duas curvas.** Na curva bruta o máximo costuma ser raso e
  deslocado; na residual há um pico nítido no lag correto. O formato é tão informativo quanto o valor.

### Aba 4 — Vazamento e LGPD

Quatro blocos independentes.

**(a) A armadilha do `rolling` sem `shift`** — tabela linha a linha com `media3_ERRADA` (termina
no próprio dia) contra `media3_CORRETA`, mais as duas correlações com o alvo.

- **A1 — Medir o tamanho do vazamento.** A diferença entre as duas correlações é **puro
  vazamento**. O modelo vai persegui-la com entusiasmo: a avaliação fica ótima e, em produção, a
  feature **simplesmente não existe**, porque no momento da previsão o dia ainda não terminou.

**(b) O teste treino × produção** (botão `▶️ Rodar o teste`) — constrói o vetor de features por
duas rotas (painel inteiro vs. painel recortado até a véspera, como o sistema faria às 6h) e
compara número a número em todas as colunas.

- **A2 — Detectar *training-serving skew*.** O erro clássico é ter **duas implementações**, uma
  no notebook e outra no serviço. Elas começam iguais e divergem na primeira correção feita em
  apenas um dos lados. O sintoma é cruel: desempenho excelente na avaliação e medíocre em
  produção, **sem nenhuma mensagem de erro**. *A primeira versão do notebook F1_08 reprovou neste
  teste, com diferença de 28,86 em uma média móvel que atravessava a fronteira do grupo.*

**(c) O contrato de features versionado** (expander, se `pipeline_features_autorizacao.json`
existir) — versão do pipeline, colunas declaradas e faixas de referência aprendidas no treino.

- **A3 — Entender o que se versiona em produção.** Não é só o modelo: é o par **modelo +
  contrato de features**. Modelo novo com contrato antigo é uma das formas mais silenciosas de
  quebrar um sistema. As estatísticas do contrato são o que permite detectar drift depois.

**(d) O custo da proteção (LGPD)** (botão `▶️ Medir o custo da proteção`) — o mesmo modelo, a
mesma base de autorizações, **três níveis de granularidade de dado pessoal**:

| Nível | O que usa |
| --- | --- |
| 0 | nenhum dado de beneficiário |
| 1 | proporção 60+ agregada em faixas de 5 p.p. (anonimizado) |
| 2 | perfil detalhado: idade média, % crônico, % alta complexidade, taxa de negativa |

- **A4 — Transformar uma discussão jurídica em número.** A pergunta do jurídico é sempre "de
  quanto abrimos mão se não usarmos esses dados?". A tela responde em solicitações/dia e em % do
  erro. Não é zero — e também não é o que costuma ser prometido quando se pede acesso a dados
  individuais.
- **A5 — Instrumentar o princípio da minimização** (LGPD art. 6º, III). Ele exige justificar a
  necessidade de **cada** variável, e "pode ser útil" não é justificativa. **A ablação por bloco
  é o instrumento que transforma essa exigência em evidência:** se um bloco não melhora o modelo,
  ele não é necessário, e não deve ser coletado.

---

## Tela 3 — Modelos
🤖 *F1_02 e F1_03 (clássicos), F1_04 e F1_05 (árvores)* · **7 abas**

**O que esta tela faz que os notebooks não fazem:** coloca todas as famílias competindo no
**mesmo conjunto de teste**, sob um protocolo declarado antes de qualquer número.

> ⚠️ **Só entra no placar o que você visitou.** Cada aba registra o modelo em `modelos_rodados`
> ao ser renderizada.

### Aba 1 — Referências e piso

Gráfico de barras horizontais com as 5 referências + o piso (destacado em verde), e a
decomposição da conta √(2λ/π) com o λ médio do teste.

**Análises possíveis:**
- **A1 — Quantificar o "input estático".** A média histórica global é literalmente o que
  acontece quando se dimensiona a central por uma taxa média fixa. Guarde esse número: ele volta
  como uma **linha vermelha pontilhada** na tela 6.
- **A2 — Ver a sazonalidade valer pontos.** "Repetir ontem" bate a média global, mas ignora que
  segunda não se parece com domingo. "Mesmo dia da semana passada" respeita o ciclo e melhora de novo.
- **A3 — Conferir a fórmula do piso.** A tela mostra o λ médio e o √(2λ/π) correspondente,
  batendo com o piso medido. É a demonstração numérica de que o piso não é arbitrário.

### Aba 2 — Clássicos: ARIMA × SARIMA

| Controle | Faixa | Padrão |
| --- | --- | --- |
| p (autorregressivo) | 0 a 3 | 1 |
| d (diferenciação) | 0 a 2 | 1 |
| q (média móvel) | 0 a 3 | 1 |
| Sazonalidade semanal (s=7) | ligado/desligado | **ligado** |

Ajusta em treino+validação e **caminha pelo teste um dia por vez** (`append` sem refit — é assim
que o modelo roda em produção). Mostra previsão, **intervalo de confiança de 95%** e AIC.
Expander com o **ranking de ordens por AIC** (metodologia de Box-Jenkins).

**Análises possíveis:**
- **A1 — O experimento central: desligue a sazonalidade.** A previsão vira quase uma reta,
  porque o ARIMA puro só olha os lags vizinhos e aposta em um nível médio, errando
  sistematicamente os picos de segunda e os vales de domingo. Ao rodar os dois na mesma sessão,
  a tela calcula automaticamente a **redução percentual** que a parte sazonal trouxe.
- **A2 — Comparar ordens por AIC.** O AIC recompensa o ajuste e penaliza parâmetros em excesso.
  Note no ranking que **mudar p e q move muito pouco perto do que move ligar a sazonalidade**.
- **A3 — Usar o intervalo de confiança.** É a incerteza que o próprio modelo declara — e que
  **quase nenhum modelo de árvore oferece de graça**. Se a decisão exige faixa e não ponto, isso
  é um argumento real a favor da família clássica.
- **A4 — Reconhecer o limite da família.** Nem ARIMA nem SARIMA sabem o que é feriado ou
  campanha. Eles só têm a própria série. Compare o MAE deles com o do boosting na aba 5: a
  diferença **é o valor das variáveis exógenas**.
- **A5 — Testar a sobredifferenciação em modelo.** Suba `d` para 2 e observe o AIC piorar.

### Aba 3 — Prophet

| Controle | Opções | Padrão |
| --- | --- | --- |
| changepoint_prior_scale | 0,01 / 0,05 / 0,1 / 0,5 | 0,05 |
| Feriados brasileiros | sim/não | sim |
| Sazonalidade anual | sim/não | sim |

Mostra previsão com IC, **tendência g(t)** e **sazonalidade semanal s(t)** em painéis separados,
mais o efeito médio do componente de feriados. Expander com o **caso das teleconsultas** (3 anos,
changepoint plantado em set/2022).

**Análises possíveis:**
- **A1 — Explorar o trade-off viés/variância na tendência.** Com `cps = 0,01` a tendência vira
  quase uma reta rígida (**subajuste**); com `0,5` ela fica cheia de curvas seguindo cada
  oscilação (**sobreajuste**). O padrão 0,05 busca o equilíbrio.
- **A2 — Usar a decomposição como argumento de reunião.** Cada termo é **inspecionável**:
  "a tendência cresce X%", "sexta tem +Y ligações", "feriado custa −Z". É a grande vantagem
  prática do Prophet sobre as árvores.
- **A3 — Ler o placar com justiça.** Ele erra mais que as árvores **por causa do protocolo**:
  prevê todo o horizonte de uma vez, sem usar o volume de ontem. Compare-o com uma referência que
  também só usa calendário, e a leitura fica justa.
- **A4 — Ver a penalização de changepoints funcionando** (caso teleconsultas). Dos ~25 pontos
  candidatos, poucos têm mudança de inclinação relevante, e o principal cai perto de set/2022 —
  exatamente onde a aceleração foi plantada. **O Prophet não cria um changepoint em cada
  solavanco**, e é isso que o protege de aprender ruído como sinal.
- **A5 — Isolar o valor do bloco de feriados.** Desligue "Feriados brasileiros" e compare o MAE.

### Aba 4 — Árvores e floresta

| Controle | Faixa | Padrão |
| --- | --- | --- |
| max_depth | 1 a 25 | 8 |
| min_samples_leaf | 1 a 50 | 1 |
| Árvores da floresta | 1 a 500 (passo 25) | 300 |

Roda uma **árvore isolada** e uma **Random Forest** ao mesmo tempo, mostrando MAE de cada,
número de folhas e **R² out-of-bag**. Abaixo, a **curva em U** (MAE de treino e de teste por
profundidade, de 1 a 20). Dois expanders: a **curva do bagging** (MAE por número de árvores) e a
importância das variáveis na floresta.

**Análises possíveis:**
- **A1 — Ver o overfitting acontecer.** Leve `max_depth` a 25: a curva de treino desce até quase
  zero enquanto a de teste **volta a subir**. A distância entre as curvas é o **tamanho do
  autoengano** de quem avalia no treino.
- **A2 — Regularizar por outro caminho.** Com `max_depth = 25`, suba `min_samples_leaf` para 20.
  O erro de teste melhora de novo: exigir um mínimo de observações por folha **impede a
  memorização onde ela nasce** — nas folhas pequenas demais.
- **A3 — Entender por que bagging funciona.** A floresta erra bem menos que a árvore isolada, e
  o ganho **não vem de um modelo mais esperto**: vem de muitos modelos medianos combinados. O
  sobreajuste de cada árvore é ruído com sinal aleatório, e **ruído aleatório se cancela na
  média**. O padrão real, que todas as árvores enxergam, sobrevive.
- **A4 — Dimensionar o número de árvores.** A curva do bagging cai muito nas primeiras árvores e
  **estabiliza depois de ~30**. Ir de 300 para 1.000 custa tempo e não compra precisão. É uma
  decisão de infraestrutura, não de acurácia.
- **A5 — Usar o R² out-of-bag.** Ele é uma estimativa de generalização obtida **de graça**,
  sem separar dados — cada árvore é avaliada nas linhas que o bootstrap deixou de fora.

### Aba 5 — Boosting

| Controle | Opções | Padrão |
| --- | --- | --- |
| Biblioteca | XGBoost / LightGBM / CatBoost | XGBoost |
| learning_rate | 0,01 / 0,03 / 0,05 / 0,1 / 0,3 | 0,05 |
| num_leaves (LightGBM) | 7 a 127 (passo 8) | 31 |
| min_child_samples | 2 a 40 | 10 |

Treina com **early stopping de 100 rodadas na validação**, reajusta o modelo final em
treino+validação com o número de árvores escolhido, e plota as **curvas de erro de treino e de
validação** por número de árvores.

**Análises possíveis:**
- **A1 — Encontrar o vale.** A curva de validação **quase nunca é monótona**: desce, encontra um
  vale e começa a subir. **Esse vale é o modelo**, e tudo depois dele é ruído sendo memorizado.
  No bagging da aba anterior essa curva simplesmente achatava; aqui ela **vira**. É a assinatura
  do boosting, e a razão de precisarmos de **três** conjuntos — a validação existe para decidir
  quando parar.
- **A2 — Deslocar o vale com o learning rate.** Reduza `lr` e o vale se move para a direita: o
  mesmo aprendizado, dividido em mais passos. Suba para 0,3 e a curva de treino despenca enquanto
  a de validação sobe logo depois de um mínimo raso — o retrato do sobreajuste.
- **A3 — O resultado que muda decisão de projeto: troque a biblioteca.** Mantendo os demais
  controles, **as três empatam dentro do ruído de semente**. A escolha entre XGBoost, LightGBM e
  CatBoost **quase nunca é decisão de acurácia** — é de velocidade, tratamento de categóricas e
  esforço de ajuste.
- **A4 — Comparar com o efeito de um hiperparâmetro.** Agora mexa em `min_child_samples`. Em uma
  base de poucas centenas de linhas, **esse parâmetro decide mais do que o nome da biblioteca**.
- **A5 — Cronometrar.** O cartão de tempo de treino permite comparar o custo computacional das
  três bibliotecas na mesma base.

### Aba 6 — 🏁 Placar

Tabela com todos os modelos rodados + as referências + o piso, ordenada por MAE, com as colunas
**MAE, RMSE, MAPE, WMAPE, RMSE/MAE, MASE e % do aproveitável**. Abaixo, o seletor e o botão
**`✅ Definir como campeão`**.

**Análises possíveis:**
- **A1 — Diagnosticar dias de desastre pelo RMSE/MAE.** Próximo de 1 → erros homogêneos. Muito
  acima de 1 → existem poucos dias com erro enorme escondidos atrás da média, **justamente os
  dias que quebram a escala**.
- **A2 — Resumir o projeto em um número com o MASE.** Abaixo de 1, o modelo é melhor do que
  repetir o mesmo dia da semana passada. É a frase que justifica o investimento numa reunião.
- **A3 — Comparar MAPE e WMAPE.** Onde eles divergem, há valores pequenos inflando o MAPE.
- **A4 — Auditar o piso.** Se **qualquer** modelo aparecer abaixo do piso, não comemore: procure
  a coluna que contém a resposta. A tela dispara um alerta vermelho automático nesse caso.
- **A5 — Escolher o campeão e propagar.** Note que o campeão **não precisa ser o de menor MAE**:
  se a sua operação sofre com dias catastróficos, escolha pelo RMSE. Essa decisão vale para as
  telas 5, 6 e 7.

### Aba 7 — 🧪 Caso em painel (F1_05)

> ⚠️ **Outro problema.** Outro alvo (variação líquida de vidas por contrato), outra base, outro
> conjunto de teste. **Os números desta aba não entram no placar da central.** Carregada sob
> demanda por botão, porque treina vários modelos em ~10.900 linhas.

O alvo: `variação = adesões − cancelamentos`, por carteira, no próximo mês. Sustenta quatro
decisões: receita/provisão, precificação do reajuste, ação comercial e dimensionamento de rede.

**Blocos disponíveis:** `cadastro`, `categórico`, `histórico`, `macro`.

**Análises possíveis:**

- **A1 — Reconhecer um problema estruturalmente difícil.** Os dois **fluxos** (adesões,
  cancelamentos) são grandes e parecidos; o **saldo**, que é a diferença deles, é pequeno e
  nervoso. A variação média por carteira é de ~1 vida contra um desvio-padrão muito maior.
  **Nenhum modelo conserta isso.**
- **A2 — Ver a previsão ingênua falhar.** "Repetir o último mês" erra **mais** do que assumir
  carteira estável: a variação de um mês tem tanto ruído que copiá-la **introduz mais erro do que
  informação**. A previsão ingênua, difícil de bater em séries de nível, é ruim aqui porque o
  alvo é uma **diferença**.
- **A3 — Calibrar expectativa.** O % do aproveitável capturado não é glamouroso — e é
  exatamente por isso que é instrutivo: **em problemas dominados por ruído de contagem, esse é o
  ganho realista de um bom modelo**. Prometer mais à diretoria é criar expectativa que a
  estatística do problema não sustenta.
- **A4 — Ablação em painel.** Só cadastro e calendário fica **pior que a média dos 3 últimos
  meses**. O bloco `histórico` dá o maior salto da tabela, e a explicação é estrutural: o gerador
  embutiu um **momento comercial latente** (AR(1)) em cada empresa, que persiste por meses e
  **não aparece em nenhum cadastro**. As defasagens são a única janela para esse estado invisível
  — o análogo, em painel, do componente autorregressivo do ARIMA.
- **A5 — Descobrir por que o bloco `macro` rende quase nada.** A variável macro é **comum a todas
  as carteiras** em cada mês, então o modelo já a reconstrói em parte pelo calendário. Bloco caro
  de integrar, ganho marginal — exatamente o tipo de decisão que a ablação existe para informar.
- **A6 — Medir vazamento por target encoding** (botão). Três configurações com **número fixo de
  árvores** (250) para que os erros de treino sejam comparáveis:

  | Configuração | Assinatura |
  | --- | --- |
  | A) sem o identificador | base de comparação |
  | B) target encoding **ingênuo** | treino **melhora**, teste **piora** ← a assinatura do vazamento |
  | C) out-of-fold | correto, e ainda assim **não melhora** sobre A |

  A medida mais direta é a **correlação da feature com o alvo dentro do treino**: a diferença
  entre as duas versões é **informação que só existe no treino**. Duas conclusões: (i) aqui o
  identificador não acrescenta nada que as defasagens já não capturem; (ii) o vazamento é
  **pequeno** porque cada carteira tem 30 meses de treino (a própria linha pesa 1/30 na média) —
  **com alta cardinalidade de verdade** (CID, código de procedimento, prestador) cada categoria
  tem poucas linhas e a média praticamente **entrega a resposta**. É aí que o CatBoost, com
  estatísticas ordenadas, resolve o problema sem que você precise pensar nele.
- **A7 — Extrair uma curva de precificação.** O gráfico de **variação prevista × reajuste, por
  porte**, responde a uma pergunta de negócio direta: *quanto de carteira eu perco por ponto de
  reajuste, em cada tipo de empresa?* O modelo aprendeu a interação **reajuste × porte** que foi
  plantada, **sem que ninguém tenha escrito a regra**. ⚠️ Ressalva de honestidade: reajustes acima
  de 18% são **raros na base**, então aquela parte da curva se apoia em poucas observações.
- **A8 — Diagnosticar viés no agregado.** Do contrato para a operadora: a **correlação** entre
  real e previsto é alta (o modelo acerta quais meses são bons e quais são ruins), mas o **nível**
  tem viés sistemático. A linha do piso, que acerta o agregado, prova que **o problema não é
  ruído**. A causa: modelos de árvore **não extrapolam** — treinados majoritariamente em período
  de crise, nunca viram os níveis de crescimento do fim da série. Erros pequenos e **na mesma
  direção**, espalhados por 260 carteiras, **se somam em vez de se cancelar**.
  **A lição:** um modelo bom por unidade não é automaticamente bom no agregado. Se a pergunta da
  diretoria é o total, corrija o viés explicitamente e **meça o agregado como um KPI próprio**.

---

## Tela 4 — Avaliação honesta
📏 *F1_09 (MAE, RMSE, MAPE)* · **5 abas**

**Premissa:** o número que você reporta decide se o projeto continua.

### Aba 1 — As três métricas

Uma semana de exemplo com todas as colunas intermediárias (erro, erro absoluto, erro ao
quadrado, erro percentual) e quatro cartões: média simples dos erros, MAE, RMSE, MAPE.

**Análises possíveis:**
- **A1 — Ver por que a média simples não serve.** Ela dá quase zero, sugerindo modelo perfeito.
  E ele **errou todos os dias** — os erros para mais cancelaram os para menos. É por isso que as
  três métricas removem o sinal.
- **A2 — Extrair um diagnóstico de graça da razão RMSE/MAE.** O RMSE é **sempre ≥** o MAE, e eles
  só ficam iguais quando todos os erros têm exatamente o mesmo tamanho. Próximo de 1 → erros
  homogêneos. Muito acima de 1 → poucos dias com erro enorme.

### Aba 2 — Quando a métrica troca o vencedor

Dois candidatos: **A** (acerta quase na mosca seis dias, erra 20 no sétimo) e **B** (erra 5 todos
os dias). Dois botões de opinião que revelam o que a escolha significa.

**Análises possíveis:**
- **A1 — Provar que a métrica é uma afirmação sobre o negócio.** A vence no MAE, B vence no RMSE.
  Mesmos dados, mesma semana, dois vencedores. Não há erro de cálculo nem métrica melhor: há
  **duas perguntas diferentes**. MAE = *"quanto eu erro num dia típico?"*; RMSE = *"quão ruim é
  quando dá errado?"*
- **A2 — Aplicar ao próprio contexto.** Escolher MAE = o custo do erro é **proporcional** ao
  tamanho dele (faz sentido quando o que importa é o total de horas contratadas no mês).
  Escolher RMSE = o custo **cresce mais rápido** que o erro (um dia com 20 pacientes a mais
  significa fila, desvio de ambulância e risco assistencial).
- **A3 — Fixar o momento da escolha.** A métrica precisa ser escolhida **antes** de treinar.
  Métrica escolhida depois dos resultados vira justificativa.

### Aba 3 — Os defeitos do MAPE

**Análises possíveis:**
- **A1 — Quebrar a métrica com um zero.** Nas horas de madrugada com zero chegadas o MAPE vira
  **infinito** e deixa de existir como número, enquanto o MAE segue funcionando. E a saída comum
  — "vou ignorar as horas com zero" — é pior do que parece: você passa a avaliar o modelo
  **apenas nas horas movimentadas**, e o número que sai não representa a operação.
- **A2 — Medir a assimetria.** Quem subestima **nunca ultrapassa 100%** de MAPE (o pior caso é
  prever zero); quem superestima não tem limite. **Consequência prática: um processo de seleção
  que otimize MAPE prefere sistematicamente o modelo mais tímido.** Em saúde isso é grave, porque
  subdimensionar costuma custar mais caro que sobredimensionar.
- **A3 — Escolher a alternativa certa.** **WMAPE** (divide a soma dos erros pela soma dos reais,
  uma única divisão no fim) é o padrão recomendado em séries com zeros ou valores pequenos.
  **MASE** (MAE do modelo ÷ MAE do ingênuo) tem leitura imediata: abaixo de 1, o modelo vence a
  regra boba.

### Aba 4 — Onde medir

**(a) Divisão aleatória × cronológica** — o mesmo modelo, os mesmos dados, duas formas de dividir.

- **A1 — Quantificar o otimismo indevido.** A tela calcula em % o quanto a divisão aleatória fez
  o modelo **parecer melhor do que ele é**. Motivo: ao sortear linhas, o dia 15 cai no treino e o
  16 no teste — o modelo aprende com um dia e é avaliado no vizinho. Em produção nada disso
  acontece. **Regra curta e absoluta: em série temporal, a divisão é sempre cronológica.**

**(b) Walk-forward** — o mesmo modelo avaliado em 8 janelas consecutivas de 30 dias, cada uma
treinando com tudo que existia até aquele momento.

- **A2 — Medir a dispersão entre janelas.** A tela informa média, melhor e pior janela, e a
  diferença percentual entre elas. **Se o seu relatório tivesse caído por acaso na melhor janela,
  você reportaria metade do erro da pior.** Um único holdout não é um número, é um sorteio.
- **A3 — Reportar dispersão junto com média.** A dispersão é uma informação tão valiosa quanto a
  média: ela diz **o quanto você pode confiar no próximo mês**.

### Aba 5 — Custo assimétrico

| Controle | Faixa | Padrão |
| --- | --- | --- |
| Custo de FALTAR (por ligação não atendida) | 1,0 a 8,0 | 3,0 |
| Custo de SOBRAR (por ligação a mais dimensionada) | 0,5 a 3,0 | 1,0 |

Varre margens de segurança (0, 2, 4, 6, 8, 12, 16, 20%) aplicadas à previsão e plota **MAE** e
**custo real** na mesma tela.

```
Custo = c_falta · média(max(y − ŷ, 0)) + c_sobra · média(max(ŷ − y, 0))
```

**Análises possíveis:**
- **A1 — Ver as duas curvas divergirem.** Conforme a margem sobe, a **falta média despenca** e a
  **sobra cresce sem parar**. O MAE, que soma as duas sem distinguir, **só piora** — e por isso
  elege sempre a margem 0%. O custo real **cai** ao sair de zero e tem mínimo em outro ponto.
- **A2 — Encontrar a margem ótima da sua operação.** Mexa nos dois sliders e veja o mínimo da
  curva de custo se deslocar. Com faltar valendo 8× sobrar, a margem ótima sobe bastante; com os
  dois custos iguais, ela volta para zero — o que é a **prova de que o MAE é o caso particular
  em que faltar e sobrar custam igual**.
- **A3 — Propagar a decisão.** O botão `✅ Adotar margem de X%` grava a margem, que passa a
  multiplicar a previsão nas telas 5, 6 e 7. É a tradução do custo do negócio para dentro do modelo.

---

## Tela 5 — Previsão operacional
🔮 *F1_07 (estratégia de duas etapas)* · **3 abas**

**Problema:** o modelo entrega um número por dia; a escala é montada por turno e por hora.

**KPIs do topo:** modelo em uso · MAE diário · MAPE diário · margem de segurança aplicada.

### Aba 1 — Próximos 14 dias

Janela operacional das duas últimas semanas do teste, com **faixa provável** construída a partir
dos **quantis 10% e 90% dos resíduos** observados no período de teste anterior à janela — não de
nenhuma hipótese de normalidade. Tabela com data, dia da semana, previsto, faixa, real e erro.

**Análises possíveis:**
- **A1 — Declarar incerteza sem intervalo paramétrico.** É a forma mais honesta de declarar
  incerteza quando o modelo não produz intervalo por conta própria — **o caso de todos os modelos
  de árvore**.
- **A2 — Encontrar os dias que quebram a escala.** Ordene mentalmente pela coluna `erro`: os dias
  em que ele cresce são os de **calendário atípico**, e é exatamente neles que a escala quebra.
- **A3 — Ver a margem em ação.** Se você adotou margem na tela 4, a previsão está deliberadamente
  um pouco alta, e a tela diz isso explicitamente.

### Aba 2 — Duas etapas: descendo para a hora

```
ŷ(hora) = ŷ(dia) × p(hora | dia da semana)
```

O perfil `p` é a fração média das chegadas do dia que acontece em cada hora, estimada **apenas no
treino** e separada por dia da semana. Tabela comparando **quatro abordagens**:

| Abordagem | O que é |
| --- | --- |
| Input estático | média histórica × perfil único (sem dia da semana) |
| **Duas etapas** | modelo diário × perfil por dia da semana |
| Modelo horário direto | LightGBM treinado nas 17.520 linhas horárias, com lags de 24h e 168h |
| Piso horário | intensidade verdadeira |

Abaixo, um seletor de dia para inspecionar hora a hora.

**Análises possíveis:**
- **A1 — Comparar duas etapas com o modelo horário direto.** Eles empatam — a diferença é
  irrelevante para decisão de escala. Consequências práticas: **um modelo em vez de dois** (730
  observações em vez de 17.520); **muito mais fácil de explicar** ("prevemos 620 ligações amanhã,
  e historicamente 7% delas chegam entre 10h e 11h" é uma frase que qualquer gestor audita);
  **mais fácil de manter** (o perfil é uma tabela).
- **A2 — Medir o custo do input estático.** Ele erra várias vezes mais. No gráfico do dia, aparece
  como uma curva de **altura sempre igual**, que não sabe se é segunda ou domingo, nem se há
  campanha. É assim que a central é dimensionada quando não existe modelo.
- **A3 — Inspecionar um dia atípico.** Escolha um feriado ou um dia de campanha no seletor e
  compare as duas curvas hora a hora. É onde a distância entre elas explode.
- **A4 — Situar tudo contra o piso horário.** A última linha da tabela dá o limite no nível da hora.

**Saída:** o botão `💾 Enviar esta previsão horária para o gêmeo digital` grava
`previsao_horaria` com quatro colunas — previsto, estático, real e intensidade — que é
exatamente o insumo do experimento central da tela 6.

### Aba 3 — Até onde dá para prever

Botão que roda **previsão recursiva** (prever amanhã, inserir a própria previsão no lugar do dado
observado, repetir) de D+1 a D+14, a partir de 70 dias de início consecutivos.

> Detalhe metodológico: os pontos de partida são **consecutivos e em número múltiplo de 7**. Sem
> isso, cada horizonte cairia sobre uma mistura diferente de dias da semana e a curva ficaria
> serrilhada por artefato de amostragem, não pelo fenômeno.

**Análises possíveis:**
- **A1 — Medir a acumulação de erro.** A partir do segundo passo, o modelo está olhando para os
  próprios erros. A tela dá o MAE em D+1, D+7 e D+14.
- **A2 — Notar que a curva satura em vez de explodir.** O modelo não entra em espiral porque as
  colunas de **calendário continuam sendo alimentadas com valores reais** — a hora, o dia da
  semana e o feriado do futuro são conhecidos. No horizonte longo o modelo degrada para algo
  próximo de "prever o perfil típico daquele dia", que é o que a melhor referência simples faz
  (a linha cinza tracejada no gráfico).
- **A3 — Derivar a rotina operacional.** Daqui sai a recomendação: **feche a escala base com 14
  dias usando o calendário, e ajuste o fino em D-1 com o modelo completo.**

---

## Tela 6 — Gêmeo digital
🏥 *SimPy (D9/D10) + Erlang C* · **3 abas**

**A página que justifica o módulo inteiro.** O gestor não pergunta "qual será o MAE?"; ele
pergunta **quantos atendentes escalar em cada turno**, e o que acontece com a fila se ele errar.

### Controles

| Controle | Faixa | Padrão |
| --- | --- | --- |
| Dia da operação | qualquer dia do teste | **o dia em que o input estático mais erra** |
| TMA (tempo médio de atendimento) | 2,0 a 10,0 min | 5,0 |
| Paciência | 0,5 a 10,0 min | 3,0 |
| Meta de nível de serviço | 0,50 a 0,95 | 0,80 |
| Replicações | 3 a 20 | 8 |

> O dia padrão não é aleatório: é aquele em que a demanda real mais se afasta do input estático.
> **É nos dias atípicos que a operação quebra; na média dos dias, tanto faz.**

### Como o motor funciona

| Peça | Detalhe |
| --- | --- |
| **Chegadas** | processo de Poisson **não homogêneo** — a taxa muda a cada hora, vinda da previsão |
| **Atendimento** | **lognormal** em torno do TMA (σ_log = 0,5) |
| **Abandono** | paciência exponencial; se a espera passa da paciência, o beneficiário desiste |
| **Capacidade** | muda por turno; a redução de escala **só vale quando o atendente em curso termina a ligação** — como na vida real |
| **Nível de serviço** | atendidas em até **20 s**, sobre as chamadas **oferecidas** (quem abandonou conta como não atendido) |
| **Prescrição de escala** | busca incremental sobre **Erlang C**: menor `c` por hora que atinge a meta (teto de 40) |
| **Replicações** | média entre rodadas independentes, com IC de 95% |
| **Custo** | R$ 38,00 por atendente-hora (padrão) |

### Aba 1 — A operação do dia

Cinco KPIs (espera média com IC, % atendidas em 20 s, abandono, atendentes-hora, custo do dia),
o gráfico **escala × demanda** com a linha de ocupação, o **histograma do tempo de espera** com
o P90 marcado, e a tabela de escala por turno.

**Análises possíveis:**
- **A1 — Ver a escala acompanhar a demanda.** As barras (chamadas/hora) e a linha em degraus
  (atendentes) sobem e descem juntas. É a diferença entre escala dimensionada por modelo e tabela fixa.
- **A2 — Explorar a não linearidade da ocupação.** A relação entre ocupação e fila **não é
  linear**: sair de 0,70 para 0,80 custa pouco; sair de 0,85 para 0,92 **multiplica** a espera.
  **É por isso que dimensionar "pela média" falha** — a média esconde as horas em que a ocupação
  passa do joelho da curva.
- **A3 — Ler a cauda, não a média.** A distribuição da espera é **fortemente assimétrica**: a
  maioria é atendida quase na hora e uma cauda espera muito mais. Compare o P90 com a média.
  **Reportar só a média esconde a cauda, e é a cauda que gera reclamação.**
- **A4 — Testar sensibilidade ao TMA.** Suba o TMA de 5 para 7 min sem mudar mais nada: a
  intensidade de tráfego sobe 40% e a escala prescrita cresce. É o experimento que responde
  "o que acontece se o novo script de atendimento ficar mais longo?".
- **A5 — Testar sensibilidade à paciência.** Reduza a paciência para 1 min: o abandono dispara e
  a espera média **cai** (ver A3 da aba 3).
- **A6 — Calibrar a meta de SLA.** Suba a meta de 0,80 para 0,90 e observe o custo do dia. É a
  conversão direta de política de atendimento em folha de pagamento.

### Aba 2 — Erro de previsão → KPI ⭐ **o experimento central**

O gêmeo roda **três vezes com a demanda real**, mudando apenas **quem recomendou a escala**:

| Fonte usada para dimensionar | O que representa |
| --- | --- |
| Média histórica (input estático) | como se dimensiona sem modelo |
| **Previsão do modelo** | o que ganhamos |
| Demanda real (previsão perfeita, impossível) | o limite teórico |

Cada linha traz atendentes-hora, custo do dia, espera média, espera P90, nível de serviço e
abandono. O gráfico sobrepõe as escalas prescritas por cada fonte.

**Análises possíveis:**
- **A1 — Traduzir MAE em KPI operacional.** Esta é a resposta ao "e daí?". A diferença de nível de
  serviço entre o input estático e a previsão é **o valor operacional do modelo**, medido em
  pontos de SLA e em reais — **não em MAE**.
- **A2 — Medir o que já foi ganho e o que falta ganhar.** A distância entre o input estático e a
  previsão é **o que já foi ganho**. A distância entre a previsão e a linha impossível é **tudo o
  que ainda há para ganhar melhorando o modelo**. Se essa segunda distância for pequena, **parar
  de investir em modelagem é a decisão certa** — e essa é uma conclusão de gestão que nenhuma
  métrica de erro entrega sozinha.
- **A3 — Diagnosticar a forma certa com o nível errado.** No gráfico, a escala do input estático
  (vermelha pontilhada) tem **a forma certa e o nível errado**: ela não sabe que dia da semana é
  hoje nem que há campanha em curso. É assim que se escala gente demais num domingo e gente de
  menos numa segunda de pico.
- **A4 — Separar custo de serviço.** Compare as colunas de custo e de SLA juntas. Às vezes a
  previsão entrega **mais serviço por menos dinheiro** (porque redistribui, não porque adiciona);
  às vezes ela custa mais e entrega muito mais. As duas leituras são resultados legítimos.
- **A5 — Repetir em outro dia.** Troque o dia no seletor do topo. Em dias típicos as três linhas
  ficam parecidas; **é nos atípicos que a previsão paga o próprio custo.**

### Aba 3 — Simulação × Erlang C

Roda a simulação **nas mesmas hipóteses da fórmula** (sem abandono) e depois **com abandono**,
comparando as três com a fórmula analítica. Mostra também a tabela por replicação.

**Análises possíveis:**
- **A1 — Validar o simulador (teste de sanidade).** Erlang C e SimPy sem abandono precisam ficar
  na mesma ordem de grandeza. Se divergirem muito em regime estável, **o bug é da simulação**.
  Aprender a checar uma simulação contra a teoria é parte da aula.
- **A2 — Isolar o efeito de cada hipótese.** A diferença que resta é explicável: Erlang C assume
  atendimento **exponencial** (CV = 1); o nosso é **lognormal** com dispersão menor. **Menos
  variabilidade no atendimento significa fila menor**, então a fórmula tende a ser
  **conservadora** aqui. Em dimensionamento, errar para o lado conservador é aceitável; o
  perigoso é o contrário.
- **A3 — A armadilha do abandono.** Ligando o abandono, a espera média **melhora**. Cuidado:
  **melhorou porque parte dos beneficiários desistiu** — quem abandona não entra na conta da
  espera. **Nunca reporte tempo de espera sem reportar taxa de abandono ao lado**; sozinho, ele
  premia a operação que perde clientes.
- **A4 — Dimensionar o número de replicações.** A tabela por replicação mostra a variabilidade
  entre rodadas. Suba o controle de replicações e observe o IC encolher. **Um único dia simulado
  não é um resultado; a média entre replicações, com o IC, é.**

---

## Tela 7 — Cenários e decisão
🎯 *E4 (análise de decisão) + o gêmeo da etapa 6* · **3 abas**

**Problema:** planejar o que ainda não aconteceu. A previsão cobre o esperado; a gestão precisa
saber o que fazer quando o inesperado chegar — e quanto custa estar preparado.

### Controles

| Controle | Faixa | Padrão |
| --- | --- | --- |
| Dia de referência | qualquer dia do teste | **o dia de maior demanda prevista** |
| TMA | 2,0 a 10,0 min | 5,0 |
| Meta de nível de serviço | 0,50 a 0,95 | 0,80 |
| Custo do atendente-hora | R$ 20 a R$ 120 | R$ 38 |

### Aba 1 — Cenários

Cada cenário multiplica a demanda prevista; a escala é **redimensionada** para cada um e o gêmeo
mede o resultado.

| Cenário | Fator | Origem do número |
| --- | --- | --- |
| Operação normal | ×1,00 | linha de base |
| **Onda epidemiológica** | ×1,40 | estado latente medido na própria base (F1_06) |
| **Campanha de comunicação** | ×1,25 | efeito de +45,6% medido em autorizações (F1_08) |
| Crescimento da carteira | ×1,08 | modelo de variação de carteira (F1_05) |
| Feriado | ×0,45 | efeito medido na base (−55%) do F1_07 |

**Análises possíveis:**
- **A1 — Precificar a resiliência.** No cenário mais pesado, a tela informa o acréscimo
  percentual de custo para manter o mesmo SLA. **Essa é a pergunta certa de gestão**: não "o que
  acontece com a fila se vier um surto", mas **"quanto custa manter o SLA se vier um surto, e eu
  consigo mobilizar essa gente a tempo?"**. O gêmeo responde a primeira parte; a segunda é uma
  conversa com o RH, e precisa acontecer **antes** do surto.
- **A2 — Verificar que o nível de serviço fica parecido entre cenários.** Isso é o **resultado
  esperado**, porque a escala foi redimensionada em cada um. O que varia é o **custo**, não o serviço.
- **A3 — Rastrear a origem de cada fator.** A tabela "De onde vem cada cenário" mostra que
  nenhum fator é chute: todos foram medidos em algum notebook do módulo. É o que separa um cenário
  defensável de um exercício de imaginação.
- **A4 — Testar a capacidade máxima.** Selecione onda + campanha e observe o **pico de
  atendentes**. Se ele passar do que a operação consegue mobilizar, a conclusão não é "o modelo
  errou" — é que **existe um teto físico** e o plano precisa ser outro (transbordo, URA, callback).

### Aba 2 — Fronteira custo × serviço

Varre sete configurações de escala (−3 a +3 atendentes por hora sobre a escala da meta) e plota
custo contra nível de serviço.

**Análises possíveis:**
- **A1 — Ler a concavidade.** A curva é **côncava**, e essa forma é a coisa mais importante da
  tela: sair da escala mais enxuta para a próxima compra muitos pontos de serviço por pouco
  dinheiro; depois de certo ponto, **cada real adicional compra quase nada**.
- **A2 — Localizar o joelho.** A tela calcula o ganho marginal de serviço por real e aponta o
  joelho. À esquerda dele, cortar custo destrói serviço de forma desproporcional; à direita,
  gastar mais é desperdício.
- **A3 — Transformar em decisão executiva.** Esta é a tela que vai para a diretoria: ela **não
  pede uma decisão técnica, pede uma escolha de posição na curva**.
- **A4 — Reconhecer o que a curva não mostra.** Ela não inclui o custo de perder o beneficiário
  que abandonou nem o custo regulatório de estourar prazo. Quando esses entram na conta, **o ponto
  ótimo se desloca para a direita** — que é exatamente o que a tela 4 mediu com o custo assimétrico.

### Aba 3 — A prescrição

A escala recomendada com quatro KPIs, a tabela por turno com custo, e o detalhamento hora a hora
(chamadas previstas, atendentes, ocupação).

**Análises possíveis:**
- **A1 — Auditar a cadeia inteira.** O número final vem da previsão do modelo (telas 3 e 5),
  distribuída pelo perfil intradiário, ajustada pela margem do custo assimétrico (tela 4),
  dimensionada por Erlang C e validada por simulação (tela 6). **Cada elo pode ser auditado
  separadamente, e é isso que diferencia um número defensável de um chute bem apresentado.**
- **A2 — Encontrar as horas de risco.** Ordene o detalhamento pela coluna `ocupacao`: qualquer
  hora acima de 0,85 é candidata a fila.
- **A3 — Converter em jornada real.** A tabela por turno é o que se leva para o RH. Compare o
  pico com a média dentro de cada turno — a diferença é o que exige turno partido, hora extra ou
  banco de horas.
- **A4 — Seguir a rotina prescrita:** **D-14** escala base pelo calendário · **D-1** ajuste fino
  com o modelo completo · **no dia** monitorar ocupação (acima de 0,85, acionar contingência
  **antes** que a fila apareça) · **sempre** reportar espera **e** abandono juntos.

---

## Tela 8 — Síntese
📚 *as nove aulas do módulo* · sem abas

### O que a tela mostra
- **A cadeia inteira nos números da sua sessão**: não fazer nada → melhor referência → **seu
  campeão** → piso, com a barra de % capturado.
- **Mapa notebook → etapa**: onde cada aula do módulo vive na aplicação.
- **Nota sobre o F1_06** (redes neurais fora do escopo, e o que daquele notebook sobreviveu aqui).
- **Os cinco erros** que o módulo ensina a não cometer, em expanders com "por que engana" e "a defesa".
- **Checklist** de um projeto de previsão de demanda, em quatro fases.
- **Bibliografia** e o arco do curso.

### Os cinco erros

| # | Erro | A defesa |
| --- | --- | --- |
| 1 | dividir treino e teste de forma **aleatória** | divisão sempre cronológica |
| 2 | `rolling` sem `shift` | toda janela móvel começa com shift; em painel, dentro do `groupby` |
| 3 | **target encoding** ingênuo | out-of-fold, ou CatBoost com estatísticas ordenadas |
| 4 | avaliar o modelo **no treino** | fora da amostra, sempre — e walk-forward |
| 5 | métrica **simétrica** com custo **assimétrico** | escolher a métrica **antes** de treinar |

### Análises possíveis
- **A1 — Fechar o loop numericamente.** A tabela do topo usa **os números que você produziu**,
  não valores fixos. Rodar a aplicação com um campeão diferente muda a tabela.
- **A2 — Usar o checklist como auditoria.** Ele funciona como lista de verificação para qualquer
  projeto de previsão de demanda, dentro ou fora deste curso.
- **A3 — Situar no arco do curso.** F1 (prever) → D9 (integrar) → D10 (simular). O painel do D10
  recebe a demanda como dado de entrada; esta aplicação mostra de onde aquele dado vem.

---

# Parte III — Referência rápida

## Todos os controles, em uma tabela

| Tela | Controle | Faixa / opções | Padrão |
| --- | --- | --- | --- |
| 1 | Semana do zoom | passo de 7 dias | 02/jun/2025 |
| 1 | Granularidade da decomposição | Diária (s=7) / Horária (s=24) | Diária |
| 1 | Diferenciações (d) | 0–2 | 0 |
| 1 | Série do correlograma | Diária / Horária | Diária |
| 1 | Amplitude diária / semanal / onda | 0–2 / 0–3 / 0–3 | 1 / 1 / 1 |
| 2 | 5 checkboxes de bloco | ligado/desligado | cíclicas desligado, resto ligado |
| 3 | p / d / q | 0–3 / 0–2 / 0–3 | 1 / 1 / 1 |
| 3 | Sazonalidade semanal | ligado/desligado | ligado |
| 3 | changepoint_prior_scale | 0,01 / 0,05 / 0,1 / 0,5 | 0,05 |
| 3 | max_depth / min_samples_leaf | 1–25 / 1–50 | 8 / 1 |
| 3 | Árvores da floresta | 1–500 | 300 |
| 3 | Biblioteca de boosting | XGB / LGBM / CatBoost | XGBoost |
| 3 | learning_rate | 0,01–0,3 | 0,05 |
| 3 | num_leaves / min_child_samples | 7–127 / 2–40 | 31 / 10 |
| 4 | Custo de faltar / sobrar | 1–8 / 0,5–3 | 3 / 1 |
| 5 | Dia para inspeção horária | dias do teste | penúltima semana |
| 6 | TMA / Paciência | 2–10 min / 0,5–10 min | 5 / 3 |
| 6 | Meta de SLA / Replicações | 0,50–0,95 / 3–20 | 0,80 / 8 |
| 7 | Custo do atendente-hora | R$ 20–120 | R$ 38 |
| 7 | Cenários | 5 opções | normal + onda + campanha |

## Botões que mudam o estado da sessão

| Tela | Botão | Efeito |
| --- | --- | --- |
| 3 | `✅ Definir como campeão` | grava `campeão` e `previsao_teste` → telas 5, 6, 7 |
| 4 | `✅ Adotar margem de X%` | grava `margem_seguranca` → telas 5, 6, 7 |
| 5 | `💾 Enviar previsão horária` | grava `previsao_horaria` → telas 6 e 7 |
| lateral | `♻️ Limpar cache e recomeçar` | zera os dois caches e todo o estado |

## Botões de cálculo sob demanda (não mudam estado)

| Tela | Botão | Custo aproximado |
| --- | --- | --- |
| 2 | Rodar o teste treino × produção | segundos |
| 2 | Medir o custo da proteção (LGPD) | ~3 modelos |
| 3 | Ajustar o Prophet nas teleconsultas | Prophet em 3 anos |
| 3 | Carregar o caso em painel | vários modelos em ~10.900 linhas |
| 3 | Comparar as três formas de codificar | 3 modelos com 250 árvores |
| 5 | Medir o erro por horizonte | 70 × 14 previsões recursivas |

## Os 12 testes (`cd F1/streamlit && python -m pytest testes -q`)

Cada um é um **invariante didático**, não uma recomendação: se um deles quebrar, a aplicação
passou a ensinar algo errado.

| Teste | O que protege |
| --- | --- |
| `test_split_e_cronologico` | treino no passado, teste no futuro, sem sobreposição |
| `test_features_nao_usam_o_futuro` | a linha de hoje é idêntica com e sem os dados de amanhã |
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

## Limitações declaradas

| Limitação | Onde aparece | Por quê |
| --- | --- | --- |
| Base sintética | todas | permite conhecer o piso exato e verificar o que o modelo deveria descobrir |
| Redes neurais fora do escopo | tela 8 | decisão de projeto (SPEC §13.5); o que sobrevive do F1_06 é a série, o piso e a acumulação de erro |
| Prophet desfavorecido pelo protocolo | tela 3 | prevê o horizonte inteiro sem usar o dado de ontem |
| Caso em painel não entra no placar | tela 3, aba 🧪 | outro alvo, outra base, outro conjunto de teste |
| Curva de reajuste acima de 18% | tela 3, aba 🧪 | poucas observações na base |
| Árvores não extrapolam | tela 3, aba 🧪 | viés no agregado que não vem de ruído |
| Erlang C é conservador aqui | tela 6, aba 3 | assume atendimento exponencial; o nosso é lognormal com menos dispersão |
| Teto de 40 atendentes/hora | tela 6 e 7 | limite da busca em `prescrever_escala` |
