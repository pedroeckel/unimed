# Guia das páginas — como apresentar esta aplicação

**Módulo F1 · Gêmeo Digital da Operadora** · Prof. Pedro | UNIMED SP

Este documento é o **roteiro de apresentação**. Ele explica, página por página: o que cada uma
mostra, o que clicar ao vivo, a frase que fecha a ideia e quanto tempo gastar. Se você só tem
cinco minutos antes da aula, leia as três primeiras seções e pule para o roteiro.

---

## 1. A aplicação em uma frase

> Os nove notebooks do módulo são bons e **desconectados**. Esta aplicação é a **camada de
> síntese**: ela pega tudo o que foi ensinado e leva até a única pergunta que interessa ao
> gestor — **quantos atendentes escalar amanhã?**

A pergunta que a aula inteira responde:

> *"O erro caiu de 80 para 36 ligações por dia. **E daí?** O que muda na operação?"*

A resposta está na **etapa 6**: a previsão vira **entrada** de uma simulação de capacidade, e a
simulação traduz erro de previsão em **fila, nível de serviço e custo**.

O caso é sempre o mesmo: a **central de atendimento** da operadora, ligação por ligação, hora a
hora, dois anos de história. Toda a base é **sintética, gerada em memória, com semente fixa** —
não há arquivo para baixar e o resultado é sempre o mesmo em qualquer máquina.

---

## 2. Como rodar

```bash
cd "/Users/pedroeckel/gestao_quanti/projects/unimed sp/code" && .venv/bin/streamlit run F1/streamlit/app.py
```

Abra **antes da aula** e passe uma vez por todas as páginas: os modelos ficam em cache e, na
apresentação, tudo responde na hora. Se algo travar, o botão **♻️ Limpar cache e recomeçar**
(no rodapé da barra lateral) devolve a aplicação ao estado inicial.

---

## 3. As três palavras que se repetem em todas as páginas

Explique estas três **uma vez, no começo**. Depois disso, todas as páginas ficam fáceis.

| Termo | O que é | Por que existe |
| --- | --- | --- |
| **Referência** (baseline) | o erro de uma regra boba — "repetir ontem", "mesmo dia da semana passada" | é o número que o modelo precisa **bater**. Sem baseline, modelo nenhum é resultado |
| **Piso do problema** | o erro de quem soubesse a **média exata** de ligações de cada dia e ainda assim errasse | é o **melhor resultado possível**. Ninguém vai abaixo dele |
| **% do sinal aprendível** | onde o modelo está entre a referência e o piso | transforma "MAE de 36" em "capturamos 74% de tudo o que era capturável" |

**O piso não é um modelo, é uma conta.** Ele responde: se a chegada de ligações é um sorteio,
quanto erra quem conhece a média do sorteio? A resposta não é zero — para contagens, é
aproximadamente √(2λ/π).

Ele serve para três coisas, e vale dizer isso em voz alta:

1. **dá escala ao erro** — "36" não significa nada sozinho;
2. **detecta vazamento** — modelo abaixo do piso está lendo a resposta em algum lugar;
3. **marca o teto do ganho** — na etapa 6, mostra quanto ainda há para ganhar melhorando o modelo.

Nesta base o piso é **exato**, porque nós geramos os dados e guardamos a intensidade verdadeira
de cada hora. É por isso que a base é sintética.

---

## 4. O fio que costura as páginas (o mais importante)

As páginas **não são independentes**. Três decisões suas viajam de uma para a outra:

```
Página 3  →  você escolhe o MODELO CAMPEÃO       (botão "✅ Definir como campeão")
                        ↓
Página 4  →  você adota a MARGEM DE SEGURANÇA    (botão "✅ Adotar margem de X%")
                        ↓
Página 5  →  você envia a PREVISÃO HORÁRIA       (botão "💾 Enviar para o gêmeo digital")
                        ↓
Páginas 6 e 7  →  o gêmeo simula a operação com tudo isso
```

A **barra lateral mostra o estado** o tempo todo (campeão escolhido, modelos rodados, previsão
pronta ou pendente). Use isso na aula: aponte para a barra lateral depois de cada botão e diga
*"olhem, a decisão que acabamos de tomar já está valendo para as próximas páginas"*.

**Se você pular esses botões, nada quebra** — as páginas 5, 6 e 7 caem em um modelo padrão e
avisam na tela. Mas aí a demonstração perde a graça, porque o aluno não vê a própria escolha
mudando o resultado final.

---

## 5. Página por página

### 🗺️ Página 0 — Visão geral
**O que é:** o mapa da viagem. Sete cartões com as etapas, os KPIs da sessão (ainda vazios) e a
tabela do **campo de jogo** — as referências e o piso.

**Ao vivo:** só mostre a tabela do campo de jogo à direita. É onde você explica a seção 3 deste
guia.

**A frase:** *"todo o espaço disputável está entre a melhor referência simples e o piso. É essa
margem que a modelagem vai brigar para capturar — nada além dela existe."*

**Tempo:** 5 min.

---

### 📈 Página 1 — Dados e diagnóstico *(F1_01, F1_02)*
**O que é:** o diagnóstico da série antes de modelar qualquer coisa. Seis abas.

| Aba | O que mostra |
| --- | --- |
| A série | dois anos de ligações por dia + zoom de duas semanas hora a hora |
| Decomposição | tendência, sazonalidade, resíduo (diária s=7 ou horária s=24) |
| Perfis | o **mapa de escala**: média por hora do dia e por dia da semana |
| Estacionariedade | teste ADF com um slider de diferenciações (d = 0, 1, 2) |
| ACF e PACF | os correlogramas que justificam o s do SARIMA |
| Laboratório | três sliders que montam a série componente por componente |

**Ao vivo:**
1. Na aba **Estacionariedade**, mexa o slider de `d` de 0 para 1. O p-valor despenca abaixo de
   0,05. *"Pronto: acabamos de descobrir o d = 1 que o SARIMA vai usar na etapa 3."*
2. Na aba **Laboratório**, zere a amplitude diária, depois a semanal, depois suba a onda
   epidemiológica. É o momento mais visual da página.

**A frase que precisa ficar:** existem dois tipos de padrão na série. **Sazonalidade** (ciclo de
24h e de 7 dias) tem período fixo e qualquer coluna de calendário captura. A **onda
epidemiológica** não tem período fixo, começa em data arbitrária e **nenhum calendário
enxerga** — só o histórico recente. Essa distinção organiza o módulo inteiro e volta na etapa 2.

**Tempo:** 10 min (abas 1, 3 e 6; as demais são apoio).

---

### 🧱 Página 2 — Engenharia de variáveis *(F1_07, F1_08)*
**O que é:** a página que mostra que **variável boa vale mais que algoritmo novo**. Quatro abas.

| Aba | O que mostra |
| --- | --- |
| Da série para a tabela | o "antes e depois": uma coluna vira uma matriz de variáveis |
| Blocos e ablação | **cinco checkboxes** que ligam/desligam blocos e retreinam o modelo |
| Defasagem | por que correlacionar séries brutas engana (caso do PA, com clima) |
| Vazamento e LGPD | `rolling` sem `shift`, teste treino × produção, custo da LGPD |

**Ao vivo:**
1. **Aba 2, os checkboxes.** Desligue **histórico** e veja o MAE piorar e a barra de "% do
   aproveitável" encolher. Religue. Depois ligue **cíclicas** e mostre que quase nada muda.
   *"Seno e cosseno valem muito em modelo linear e quase nada em árvore — variável redundante
   não é variável útil."*
2. **Aba 4, o botão `▶️ Rodar o teste treino × produção`.** Ele constrói as features por duas
   rotas e compara número a número. Conte a história: *"a primeira versão do notebook F1_08
   REPROVOU neste teste, com diferença de 28,86 em uma média móvel que atravessava a fronteira
   do grupo."*
3. **Aba 4, o botão `▶️ Medir o custo da proteção` (LGPD).** Três níveis de granularidade de
   dado pessoal, o mesmo modelo. O ganho de sair do desenho protegido para o invasivo é pequeno.

**As duas frases:** (a) *"trocar de algoritmo rendeu 0,04; trocar o conjunto de variáveis rendeu
1,16 — trinta vezes mais"*; (b) *"a ablação é o instrumento que transforma o princípio de
minimização da LGPD em evidência: se o bloco não melhora o modelo, ele não é necessário, e não
deve ser coletado."*

**Tempo:** 12 min.

---

### 🤖 Página 3 — Os modelos *(F1_02 a F1_05)*
**O que é:** a página mais densa da aplicação — **sete abas** —, e é aqui que todas as famílias
competem **no mesmo conjunto de teste**, o que os notebooks não conseguem fazer.

| Aba | O que mostra |
| --- | --- |
| Referências e piso | as barras do campo de jogo, com o piso destacado em verde |
| Clássicos | sliders de p, d, q + checkbox de sazonalidade semanal |
| Prophet | changepoint_prior_scale, feriados, sazonalidade anual, componentes |
| Árvores e floresta | max_depth, min_samples_leaf, nº de árvores, a curva em U |
| Boosting | XGBoost / LightGBM / CatBoost, learning_rate, a curva de validação |
| 🏁 Placar | a tabela com tudo o que você rodou + **o botão do campeão** |
| 🧪 Caso em painel | outro problema: variação de vidas por contrato (carregado sob demanda) |

**Regra da apresentação:** só entra no placar o que você **visitou**. Passe pelas abas na ordem.

**Ao vivo (escolha dois destes quatro momentos):**
1. **Clássicos:** desligue a sazonalidade semanal. A previsão vira quase uma reta e o erro
   explode. *"Isso é o custo de ignorar a sazonalidade, em uma tela."*
2. **Árvores:** leve `max_depth` para 25. O erro de treino vai a quase zero e o de teste sobe —
   a curva em U do overfitting. Depois suba `min_samples_leaf` para 20 e o teste melhora de novo.
3. **Boosting:** troque a biblioteca entre XGBoost, LightGBM e CatBoost mantendo o resto. **As
   três empatam.** *"A escolha entre elas quase nunca é decisão de acurácia — é de velocidade,
   de tratamento de categóricas e de esforço de ajuste."* Repare que `min_child_samples` move
   mais o resultado do que o nome da biblioteca.
4. **Placar:** leia a coluna **RMSE/MAE** (termômetro de dias de desastre) e o **MASE** (abaixo
   de 1, o modelo bate a regra boba). E: **ninguém passa do piso**.

**⚠️ Não esqueça:** na aba **🏁 Placar**, clique em **`✅ Definir como campeão`**. Sem isso, as
etapas 5 a 7 usam um modelo padrão.

**Sobre a aba 🧪 Caso em painel:** é **outro problema** (outro alvo, outra base, outro teste) e a
própria tela avisa isso em amarelo. Ela carrega sob demanda e leva alguns segundos. **Numa aula
de tempo apertado, pule.** Se sobrar tempo, ela tem três lições que a série única não dá:
o vazamento por *target encoding*, a curva de reajuste × porte (a saída que vai para a mesa de
precificação) e o **problema do agregado** — um modelo bom por contrato pode errar feio o total
da operadora, porque árvores não extrapolam.

**Tempo:** 20 min (sem o painel), 30 min (com).

---

### 📏 Página 4 — Avaliação honesta *(F1_09)*
**O que é:** o número que você reporta decide se o projeto continua. Cinco abas.

| Aba | O que mostra |
| --- | --- |
| As três métricas | uma semana de exemplo, MAE × RMSE × MAPE lado a lado |
| Quando a métrica troca o vencedor | dois modelos, dois vencedores diferentes |
| Os defeitos do MAPE | divisão por zero e assimetria; WMAPE e MASE como saída |
| Onde medir | divisão aleatória × cronológica, e o walk-forward |
| Custo assimétrico | dois sliders de custo + **o botão da margem de segurança** |

**Ao vivo:**
1. **Aba 2** tem dois botões de opinião — *"Modelo A"* e *"Modelo B"*. **Pergunte à turma antes
   de clicar.** Modelo A vence no MAE, modelo B vence no RMSE, mesmos dados. *"Não é erro de
   conta e não há métrica melhor: são duas perguntas diferentes. A escolha não é estatística, é
   operacional — e precisa ser feita antes de treinar."*
2. **Aba 4** mostra o mesmo modelo avaliado em 8 janelas consecutivas, com MAEs bem diferentes.
   *"Um único holdout não é um número, é um sorteio."*
3. **Aba 5**, o fecho: suba o custo de faltar. O MAE elege sempre a margem zero; o **custo real
   da operação elege outra coisa**. Clique em **`✅ Adotar margem de X%`** — essa margem vai
   valer nas etapas 6 e 7.

**A frase:** *"escolher o MAE é afirmar que faltar e sobrar custam igual. Em saúde, quase nunca
custam."*

**Tempo:** 12 min.

---

### 🔮 Página 5 — Previsão operacional *(F1_07)*
**O que é:** o modelo entrega um número **por dia**; a escala é montada **por hora**. Esta página
faz a ponte. Três abas.

| Aba | O que mostra |
| --- | --- |
| Próximos 14 dias | a janela operacional com faixa provável (quantis dos resíduos) |
| Duas etapas | previsão diária × perfil intradiário = previsão horária |
| Até onde dá para prever | erro por horizonte, de D+1 a D+14 (botão) |

**Ao vivo:**
1. **Aba 2** é o coração da página. A tabela compara quatro abordagens: input estático, **duas
   etapas**, modelo horário direto (treinado em 17.520 linhas) e o piso horário. As duas etapas
   empatam com o modelo direto. *"Um modelo em vez de dois, muito mais fácil de explicar e de
   manter — 'prevemos 620 ligações amanhã, e historicamente 7% delas chegam entre 10h e 11h' é
   uma frase que qualquer gestor audita."*
2. **Clique em `💾 Enviar esta previsão horária para o gêmeo digital`.** É o que alimenta a
   etapa 6.
3. **Aba 3**, se houver tempo: o botão mede o erro de D+1 a D+14. A curva **satura em vez de
   explodir**, porque o calendário do futuro é conhecido. Daí sai a rotina: **escala base em
   D-14 com o calendário, ajuste fino em D-1 com o modelo completo.**

**Tempo:** 10 min.

---

### 🏥 Página 6 — O gêmeo digital *(D9, D10)*
**O que é: a página que justifica o módulo inteiro.** É onde "erro de previsão" vira "fila,
SLA e custo". Se você tiver que cortar tudo, **guarde esta**.

Motor: **SimPy** (eventos discretos, chegadas de Poisson não homogêneo, abandono por impaciência,
escala que muda por turno) com a fórmula de **Erlang C** rodando em paralelo como teste de
sanidade. Controles no topo: dia da operação, TMA, paciência, meta de nível de serviço,
replicações.

| Aba | O que mostra |
| --- | --- |
| A operação do dia | espera, SLA, abandono, custo, escala × demanda, histograma de espera |
| **Erro de previsão → KPI** | **o experimento central** |
| Simulação × Erlang C | o teste de sanidade do simulador |

**Ao vivo — a aba 2 é a aula inteira em uma tabela.** O gêmeo roda **três vezes com a demanda
real**, mudando apenas **quem recomendou a escala**:

| Fonte da escala | Leitura |
| --- | --- |
| Média histórica (input estático) | é assim que se dimensiona sem modelo |
| **Previsão do modelo** | o que ganhamos |
| Demanda real (previsão perfeita, impossível) | o limite: **quanto ainda há para ganhar** |

*"A distância entre o input estático e a previsão é o que já foi ganho. A distância entre a
previsão e a linha impossível é tudo o que ainda há para ganhar melhorando o modelo. Agora
'MAE de 36' tem uma tradução: tantos pontos de nível de serviço, tantos reais por dia."*

Repare no gráfico: a escala do input estático tem **a forma certa e o nível errado** — ela não
sabe que dia da semana é hoje.

**Mais dois pontos que valem ouro na aba 1 e na 3:**
- A **ocupação** não é linear. Sair de 0,70 para 0,80 custa pouco; de 0,85 para 0,92 multiplica
  a espera. É por isso que dimensionar "pela média" falha.
- Ligando o abandono, a espera média **melhora** — porque quem desistiu não entra na conta.
  *"Nunca reporte tempo de espera sem reportar taxa de abandono ao lado."*

**Tempo:** 15 min. É a página em que você pode gastar mais.

---

### 🎯 Página 7 — Cenários e decisão *(E4)*
**O que é:** planejar o que ainda não aconteceu. Três abas.

| Aba | O que mostra |
| --- | --- |
| Cenários | 5 cenários (onda epidemiológica, campanha, crescimento de carteira, feriado) |
| Fronteira custo × serviço | quanto de serviço se compra com cada real a mais |
| A prescrição | a escala recomendada, por turno e por hora, com custo |

**Ao vivo:**
1. **Aba 1:** cada cenário multiplica a demanda e a escala é **redimensionada** para cada um.
   O nível de serviço fica parecido entre eles — e isso é o resultado. *"A pergunta de gestão
   não é 'o que acontece com a fila se vier um surto'. É 'quanto custa manter o SLA se vier um
   surto — e eu consigo mobilizar essa gente a tempo?'. O gêmeo responde a primeira parte; a
   segunda é uma conversa com o RH, e precisa acontecer antes do surto."* A tabela **"De onde vem
   cada cenário"** mostra que cada fator veio de um notebook, não de um chute.
2. **Aba 2:** a curva é **côncava**. Tem um joelho. *"Esta é a tela que vai para a diretoria:
   ela não pede uma decisão técnica, pede uma escolha de posição na curva."*
3. **Aba 3:** a prescrição final e **a rotina D-14 / D-1 / no dia / sempre**. Mostre que o número
   final é rastreável até a etapa 3. *"Cada elo pode ser auditado separadamente, e é isso que
   diferencia um número defensável de um chute bem apresentado."*

**Tempo:** 10 min.

---

### 📚 Página 8 — Síntese
**O que é:** o fechamento. A cadeia inteira em números **da sessão que você acabou de rodar**,
o mapa de cada notebook para cada etapa, **os cinco erros** que o módulo ensina a não cometer
(em expanders) e o checklist de um projeto de previsão de demanda.

**Ao vivo:** abra os cinco erros um a um. Eles são o resumo executivo do módulo:

1. dividir treino e teste de forma **aleatória**;
2. `rolling` sem `shift`;
3. *target encoding* ingênuo;
4. avaliar o modelo **no treino**;
5. otimizar métrica **simétrica** quando o custo é **assimétrico**.

Termine na tabela do topo: não fazer nada → melhor referência → **seu campeão** → piso.

**Tempo:** 8 min.

---

## 6. Roteiro sugerido

### Aula completa (~100 min)
| Tempo | Página | Foco |
| --- | --- | --- |
| 5 min | 0 | referência, piso, % capturado |
| 10 min | 1 | sazonalidade × onda epidemiológica |
| 12 min | 2 | ablação por bloco; LGPD |
| 20 min | 3 | overfitting, boosting, **definir o campeão** |
| 12 min | 4 | métrica é decisão de negócio; **adotar a margem** |
| 10 min | 5 | duas etapas; **enviar ao gêmeo** |
| 15 min | 6 | **erro de previsão → KPI** |
| 10 min | 7 | cenários e prescrição |
| 8 min | 8 | os cinco erros |

### Versão curta (~25 min)
Página **0** (o campo de jogo) → página **3, aba Placar** (defina o campeão) → página **5, aba 2**
(duas etapas, envie ao gêmeo) → página **6, aba 2** (o experimento central) → página **8**
(os cinco erros).

Essa sequência sozinha já conta a história inteira.

---

## 7. Perguntas que a turma vai fazer

**"Os dados são reais?"**
Não, e é de propósito. Como nós plantamos cada efeito (ciclo diário, feriado, janela de
vencimento, onda epidemiológica), sabemos o que o modelo **deveria** descobrir e podemos
verificar se descobriu. E, principalmente, guardamos a intensidade verdadeira de cada hora — é
ela que dá o **piso exato**. Com dado real, o piso teria que ser estimado.

**"Por que o modelo não chega perto de zero de erro?"**
Porque não existe erro zero. A chegada de ligações é um sorteio. O piso é o erro de quem conhece
a média do sorteio, e ninguém vai abaixo dele — quem vai, está com vazamento.

**"O Prophet é pior que as árvores?"**
Neste placar sim, **mas o protocolo o desfavorece**: ele prevê o horizonte inteiro de uma vez,
sem usar o volume de ontem. É uma vantagem operacional (não depende do dado de ontem chegar a
tempo) que aparece como desvantagem na comparação. A página 3 declara isso antes de mostrar
qualquer número.

**"E as redes neurais (LSTM)?"**
Fora do escopo desta aplicação, por decisão de projeto. Três coisas do F1_06 continuam aqui: a
série da central com estado latente epidemiológico é a base de tudo, o piso de erro dele é a
régua de todas as páginas, e a acumulação de erro em previsão multi-passo é medida na etapa 5
com o modelo tabular. O que fica só no notebook é o argumento de **por que** a LSTM existe.

**"Isso roda com dado de verdade?"**
A camada `nucleo/` é código puro, sem Streamlit, e os testes (`python -m pytest testes -q`)
verificam **invariantes didáticos**: split cronológico, features que não usam o futuro,
equivalência treino × produção, ninguém abaixo do piso. É o esqueleto de um sistema, não um
sistema — mas o esqueleto é o certo.

---

## 8. Se algo der errado

| Sintoma | O que fazer |
| --- | --- |
| Página lenta na primeira visita | é o cache aquecendo — rode tudo uma vez antes da aula |
| Números estranhos / estado confuso | **♻️ Limpar cache e recomeçar**, na barra lateral |
| Pulou a página 3 ou a 5 | não quebra: as páginas seguintes avisam e usam o modelo padrão |
| Caso em painel travando o tempo | pule a aba 🧪 — ela é um problema à parte |
| Sem tempo | vá direto para a versão curta da seção 6 |

---

## 9. Onde cada aula do módulo vive aqui

| Notebook | Assunto | Onde está |
| --- | --- | --- |
| F1_01 | fundamentos de séries temporais | Etapa 1 |
| F1_02 | ARIMA e SARIMA | Etapa 3, aba Clássicos |
| F1_03 | Prophet | Etapa 3, aba Prophet |
| F1_04 | árvores e Random Forest | Etapa 3, aba Árvores |
| F1_05 | XGBoost, LightGBM, CatBoost | Etapa 3, abas Boosting e 🧪 Painel |
| F1_06 | perceptron, RNN, LSTM | fora do escopo (ver seção 7) |
| F1_07 | feature engineering: chegadas hospitalares | Etapas 2 e 5 |
| F1_08 | feature engineering: operadora e LGPD | Etapa 2, abas 2 e 4 |
| F1_09 | avaliação: MAE, RMSE, MAPE | Etapa 4 |
| D9 · D10 · E4 | integração, simulação, decisão | Etapas 6 e 7 |

E o arco do curso, que fecha a apresentação:

> **prever (F1) → integrar (D9) → simular (D10)**
