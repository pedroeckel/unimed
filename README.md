# Simulação e Previsão em Serviços de Saúde — UNIMED SP
### Material prático do curso — Prof. Pedro Eckel

> **Instituição:** UNIMED SP
> **Disciplinas:** Simulação em Serviços de Saúde · Previsão de Demanda na Gestão de Planos de Saúde
> **Módulos neste repositório:** D9 · D10 · E3 · E4 · F1

---

## Visão Geral

Este repositório reúne o **material prático** de cinco módulos do curso. Cada módulo é um passo
de uma mesma cadeia: os dados saem dos sistemas corporativos, viram parâmetros, alimentam um
modelo de simulação, e o modelo vira decisão de escala.

```
F1  prever          →  D9  integrar        →  D10  simular       →  E3/E4  decidir
séries temporais       ERP + HIS (FHIR)       gêmeo digital          rigor estatístico
e machine learning     limpeza e KPIs         SimPy ponta a ponta    e análise de decisão
```

O arco completo é: **prever a demanda (F1) → trazer o dado limpo do HIS/ERP (D9) → simular a
operação com esse dado (D10) → coletar resultado com rigor (E3) → transformar simulação em
decisão (E4)**.

Três aplicações interativas fecham a narrativa: dois painéis Streamlit (F1 e D10) e um frontend
Next.js que apresenta o gêmeo digital da central de atendimento em formato de produto.

---

## Mapa dos Módulos

| Módulo | Tema | Artefatos | Onde |
|--------|------|-----------|------|
| **D9** | Integração com sistemas corporativos (ERP, HIS) | 1 notebook · 6 CSVs · 6 figuras | [`D9/`](D9) |
| **D10** | Gêmeo digital com SimPy | 1 notebook integrador · 6 notebooks de trilha · 6 scripts · 1 painel | [`D10/`](D10) |
| **E3** | Warm-up e regime permanente | 1 notebook | [`E3/`](E3) |
| **E4** | Análises de cenário, sensibilidade, risco e otimização | 1 notebook · 4 figuras · 1 relatório modelo | [`E4/`](E4) |
| **F1** | Previsão de demanda: séries temporais e ML | 9 notebooks · 1 app Streamlit (9 páginas, 22 testes) · 1 frontend Next.js | [`F1/`](F1) |

---

## Estrutura do Repositório

```
code/
├── README.md                    ← este arquivo
├── requirements.txt             ← ambiente único do repositório (Python 3.14)
│
├── D9/                          INTEGRAÇÃO ERP/HIS
│   ├── D9_Pratica_Integracao_ERP_HIS.ipynb
│   ├── historico_pa_clean.csv           base limpa (2.128 atendimentos · 30 dias)
│   ├── inputs_chegada_pa.csv            λ por faixa de 6h
│   ├── inputs_servico_pa.csv            lognormal por risco Manchester
│   ├── inputs_escala_erp.csv            escala por turno (ERP)
│   ├── inputs_leitos_erp.csv            ocupação de leitos por ala
│   ├── taxa_hora_pa.csv                 λ hora a hora (24 linhas)
│   └── fig*.png                         figuras da aula
│
├── D10/                         GÊMEO DIGITAL
│   ├── D10_GemeDigital_PontaAPonta.ipynb        ← versão de referência (41 células)
│   ├── notebooks/
│   │   ├── D10_GemeDigital_PontaAPonta.ipynb    ← cópia sem a Etapa 5C (ver nota abaixo)
│   │   └── d10_fig1..7_*.png
│   ├── simpy_exemplos/
│   │   ├── 00_fundamentos_simpy.ipynb … 05_despacho_ambulancias_filterstore.ipynb
│   │   ├── ex01..ex05_*.py · executar_todos.py   versões script de apoio
│   │   └── README.md                             guia da trilha didática
│   └── streamlit/
│       └── app_gemeo_digital.py                  painel do PA
│
├── E3/  E3_Warmup_Regime_Permanente.ipynb
├── E4/  E4_Propostas_Analises_Decisao.ipynb · e4_fig1..4_*.png · Relatorio_Final_Exemplo_E4.docx
│
├── F1/                          PREVISÃO DE DEMANDA
│   ├── F1_01..F1_09_*.ipynb                      nove aulas
│   ├── pipeline_features_autorizacao.json        contrato do pipeline de variáveis
│   ├── streamlit/                                laboratório (9 páginas + testes)
│   └── frontend/                                 painel executivo Next.js
│
├── docs/
│   └── simpy.md                 base teórica de SimPy 4.1.1 (apoio à D10)
└── .claude/launch.json          configurações de dev server das três aplicações
```

> **Nota sobre a duplicata da D10.** Existem dois arquivos com o mesmo nome:
> `D10/D10_GemeDigital_PontaAPonta.ipynb` (41 células, inclui a **Etapa 5C — recalibrar a
> baseline**) e `D10/notebooks/D10_GemeDigital_PontaAPonta.ipynb` (39 células, sem essa etapa).
> O da raiz da D10 é o mais completo; o de `notebooks/` é o que acompanha as figuras exportadas.
> Antes da próxima aula, vale consolidar em um só.

---

## Ambiente

### Pré-requisitos

- Python ≥ 3.11 (o ambiente do projeto usa **3.14.2**)
- Node.js ≥ 20 — apenas para o frontend da F1
- Jupyter Notebook, JupyterLab ou VS Code para abrir os notebooks

### Instalação

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

O `requirements.txt` da raiz cobre **todos os módulos** com as versões efetivamente usadas.
Cada aplicação também tem um arquivo próprio, menor, para deploy isolado:
`F1/streamlit/requirements.txt` e `D10/streamlit/requirements.txt`.

Se for abrir os notebooks fora do VS Code, registre o kernel:

```bash
.venv/bin/python -m ipykernel install --user --name sim-saude --display-name "Python (sim-saude)"
```

---

## D9 — Integração com Sistemas Corporativos (ERP, HIS)

[`D9/D9_Pratica_Integracao_ERP_HIS.ipynb`](D9/D9_Pratica_Integracao_ERP_HIS.ipynb) — 35 células,
organizado em **10 partes**, cada uma abrindo com teoria e fechando com interpretação.

| Parte | Conteúdo |
|-------|----------|
| 1 | Configuração do ambiente |
| 2 | Conexão ao HIS via HL7 FHIR R4 (sandbox HAPI) |
| 3 | Extração de atendimentos (recurso `Encounter`) |
| 4 | Dataset sintético realista do PA |
| 5 | Análise de qualidade: completude e outliers (IQR) |
| 6 | KPIs operacionais: λ/hora, volume/dia, μ por risco, heatmap |
| 7 | Integração com ERP: escala e leitos |
| 8 | Conformidade com a LGPD |
| 9 | Tabela de inputs para o simulador |
| 10 | Resumo do pipeline de integração |

**Geração dos dados.** A base sintética não é amostrada diretamente de distribuições calibradas
às metas Manchester — ela sai de uma **simulação SimPy M/G/c com fila de prioridade**, para que
os tempos de espera sejam consequência da capacidade do ERP e não de um alvo imposto. É isso que
faz a D10 conseguir reproduzir a D9 dentro do intervalo de confiança.

**Execução offline.** O notebook detecta se `hapi.fhir.org/baseR4` está disponível; em caso de
falha de rede, entra em modo offline com dataset sintético equivalente, sem quebrar nenhuma
célula.

```python
def fhir_get(path, params=None):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json(), True          # servidor disponível
    except Exception:
        return None, False                # fallback sintético ativado
```

```bash
.venv/bin/jupyter notebook D9/D9_Pratica_Integracao_ERP_HIS.ipynb
```

### Artefatos gerados (inputs do simulador)

**`inputs_chegada_pa.csv`** — taxa de chegada por faixa de 6h.

| Coluna | Descrição |
|--------|-----------|
| `faixa_6h` | Bloco de 6 horas (`00h-06h`, `06h-12h`, …) |
| `total_30_dias` | Chegadas no período |
| `lambda_hora` | Chegadas por hora |
| `intervalo_medio_min` | Intervalo médio entre chegadas (min) |

```
00h-06h   λ = 0,76 pac/h      06h-12h   λ = 3,47 pac/h
12h-18h   λ = 4,89 pac/h  ← pico       18h-24h   λ = 2,69 pac/h
```

**`inputs_servico_pa.csv`** — tempo de atendimento por nível Manchester.

| Coluna | Descrição |
|--------|-----------|
| `risco_manchester` | Vermelho / Laranja / Amarelo / Verde / Azul |
| `n_atendimentos` | Volume observado no nível |
| `media_min` · `mediana_min` · `desvio_min` | Estatísticas descritivas |
| `mu_lognormal` · `sigma_lognormal` | Parâmetros ajustados da Lognormal |
| `P10_min` · `P90_min` | Percentis 10 e 90 |

```
Vermelho  μ = 2,998 · σ = 0,309  →  E[T] ≈ 21,0 min
Laranja   μ = 3,356 · σ = 0,302  →  E[T] ≈ 30,0 min
Amarelo   μ = 3,067 · σ = 0,384  →  E[T] ≈ 23,1 min
Verde     μ = 2,758 · σ = 0,485  →  E[T] ≈ 17,7 min
Azul      μ = 2,665 · σ = 0,309  →  E[T] ≈ 15,1 min
```

**`inputs_escala_erp.csv`** — capacidade por turno, direto do ERP.

| Coluna | Descrição |
|--------|-----------|
| `turno` | Noturno-1 · Matutino · Vespertino · Noturno-2 |
| `n_medicos_pa` · `n_enfermeiros` · `n_tecnicos` | Equipe escalada |
| `salas_atend` | Salas disponíveis |
| `lambda_turno` · `pac_medico_turno` | Demanda e carga por médico no turno |

**`inputs_leitos_erp.csv`** — restrição de internação (boarding).

| Coluna | Descrição |
|--------|-----------|
| `ala` | PA Adulto, Observação PA, UTI Geral, Clínica Médica, Cirurgia Geral, Maternidade |
| `capacidade` · `leitos_ocup` · `leitos_livres` | Contagem de leitos |
| `taxa_ocup` | Taxa de ocupação (0–1) |

**`taxa_hora_pa.csv`** — λ hora a hora (24 linhas), usado pelo gêmeo digital para reproduzir o
perfil intradiário. **`historico_pa_clean.csv`** — base limpa, um atendimento por linha.

---

## D10 — Gêmeo Digital com SimPy

A D10 tem três blocos complementares: uma **trilha didática**, um **notebook integrador** e um
**painel**.

### 1. Trilha didática — [`D10/simpy_exemplos/`](D10/simpy_exemplos)

Seis notebooks em ordem de dificuldade, cada um com público, pré-requisitos e objetivos de
aprendizagem explícitos:

1. [`00_fundamentos_simpy.ipynb`](D10/simpy_exemplos/00_fundamentos_simpy.ipynb) — `Environment`, `Process`, `Event`, `timeout`
2. [`01_triagem_classificacao_risco.ipynb`](D10/simpy_exemplos/01_triagem_classificacao_risco.ipynb) — `Resource` e `PriorityResource` em fila clínica
3. [`02_leitos_uti_timeout.ipynb`](D10/simpy_exemplos/02_leitos_uti_timeout.ipynb) — `Store` para leitos nomeados e espera com prazo
4. [`03_fluxo_cadastro_alta.ipynb`](D10/simpy_exemplos/03_fluxo_cadastro_alta.ipynb) — fluxo multietapas e gargalo no retrabalho
5. [`04_escala_enfermagem_container.ipynb`](D10/simpy_exemplos/04_escala_enfermagem_container.ipynb) — `Container` e `start_delayed()`
6. [`05_despacho_ambulancias_filterstore.ipynb`](D10/simpy_exemplos/05_despacho_ambulancias_filterstore.ipynb) — `FilterStore` para seleção por compatibilidade

Os arquivos `ex0*.py` da mesma pasta são as versões script, úteis para execução rápida fora do
Jupyter. `executar_todos.py` roda todas de uma vez.

### 2. Notebook integrador — [`D10/D10_GemeDigital_PontaAPonta.ipynb`](D10/D10_GemeDigital_PontaAPonta.ipynb)

A aula final, em oito etapas: compreender o sistema real → transformar dados em parâmetros →
construir o modelo → executar com rigor estatístico → **validar contra a realidade** (e
diagnosticar quando a validação falha, na Etapa 5B, e recalibrar, na 5C) → atualizar com novos
dados → explorar cenários e prever demanda com Prophet → prescrever a escala ótima com
Pyomo + HiGHS.

```bash
.venv/bin/jupyter notebook D10/D10_GemeDigital_PontaAPonta.ipynb
```

**Consistência D9 ↔ D10.** Os dois modelos compartilham os mesmos parâmetros — perfil horário de
chegadas, escala do ERP por turno (2 / 5 / 4 / 3 médicos), overhead de documentação de 15 min por
atendimento, warm-up de 4 h e janela de coleta de 24 h dentro de um horizonte de 30 h. Se um lado
mudar `TAXA_CHEGADA` ou `ERP_TURNOS`, **o outro precisa mudar junto**, ou a validação estatística
deixa de fechar.

### 3. Painel — [`D10/streamlit/app_gemeo_digital.py`](D10/streamlit/app_gemeo_digital.py)

```bash
.venv/bin/streamlit run D10/streamlit/app_gemeo_digital.py --server.port 8502
```

Sobe mesmo sem os CSVs da D9 no caminho esperado, usando fallback sintético para demonstração.

---

## E3 — Warm-up e Regime Permanente

[`E3/E3_Warmup_Regime_Permanente.ipynb`](E3/E3_Warmup_Regime_Permanente.ipynb) — 55 células.
Responde às duas perguntas que toda simulação estocástica precisa responder antes de reportar
qualquer número: **quando começar a coletar** e **quantas replicações rodar**.

| Seção | Conteúdo |
|-------|----------|
| 1–2 | Por que a análise de saída importa · fila de autorização como exemplo mínimo |
| 3 | Múltiplas replicações: por que uma só não basta |
| 4 | **Método de Welch** para identificar o fim do transiente |
| 5 | Média com e sem warm-up: o tamanho do viés |
| 6 | Intervalo de confiança de 95% e por que a distribuição *t* de Student |
| 7 | Quantas replicações são necessárias — com verificação prática |
| 8 | Horizonte finito × regime permanente × regime cíclico |
| 9–10 | Exercício guiado e armadilhas comuns |

Só depende de `numpy`, `pandas`, `scipy` e `matplotlib`.

---

## E4 — Análises para Apoiar a Decisão

[`E4/E4_Propostas_Analises_Decisao.ipynb`](E4/E4_Propostas_Analises_Decisao.ipynb) — 33 células.
Modela a jornada do beneficiário na rede credenciada e roda os quatro tipos de análise da
apostila sobre esse mesmo modelo-base:

| Etapa | Análise | Pergunta de negócio |
|-------|---------|---------------------|
| 2 | **Cenário** | Com 35% mais vidas, a rede mantém o nível de serviço? |
| 3 | **Sensibilidade** | Contratar mais especialistas ou agilizar a central de autorização? (gráfico tornado) |
| 4 | **Risco** | Qual a chance de a rede sair de controle em regime normal — e quanto custa? |
| 5 | **Otimização** | Quantos especialistas *e* quantas vagas de exame extras? |
| 6 | Relatório | Do resultado da simulação ao relatório gerencial |

Execução de ~30–60 s. [`Relatorio_Final_Exemplo_E4.docx`](E4/Relatorio_Final_Exemplo_E4.docx) é o
modelo de entrega esperado dos alunos.

---

## F1 — Previsão de Demanda na Gestão de Planos de Saúde

Nove notebooks com um **estudo de caso condutor único** — o volume de ligações na central de
atendimento da operadora — para que os modelos sejam comparáveis entre si.

| # | Notebook | Conteúdo |
|---|----------|----------|
| 01 | [Fundamentos de Séries Temporais](F1/F1_01_Fundamentos_Series_Temporais.ipynb) | tendência, sazonalidade, estacionariedade, ADF, ACF/PACF |
| 02 | [ARIMA e SARIMA](F1/F1_02_ARIMA_SARIMA.ipynb) | o modelo clássico e sua versão sazonal |
| 03 | [Prophet](F1/F1_03_Prophet.ipynb) | previsão com o "analista no loop" (Taylor & Letham, 2018) |
| 04 | [Árvores de Decisão e Random Forest](F1/F1_04_Arvores_Decisao_Random_Forest.ipynb) | bagging: do tempo para a tabela |
| 05 | [XGBoost, LightGBM e CatBoost](F1/F1_05_XGBoost_LightGBM_CatBoost.ipynb) | boosting e o que ele reduz que o bagging não reduz |
| 06 | [Perceptron, RNN e LSTM](F1/F1_06_Perceptron_RNN_LSTM.ipynb) | redes implementadas em NumPy puro, sem framework |
| 07 | [Feature Engineering — chegadas hospitalares](F1/F1_07_Feature_Engineering_Chegadas_Hospitalares.ipynb) | clima, epidemia, calendário e a busca da defasagem certa |
| 08 | [Feature Engineering — operadora e LGPD](F1/F1_08_Feature_Engineering_Operadora_LGPD.ipynb) | variáveis dirigidas pelo produto, com limites legais |
| 09 | [Avaliação: MAE, RMSE e MAPE](F1/F1_09_Avaliacao_MAE_RMSE_MAPE.ipynb) | parar de usar as métricas e passar a entendê-las |

**A tese do módulo**, medida no notebook 05: trocar de algoritmo mudou o resultado em **0,04 vida
por carteira**; trocar um conjunto pobre de variáveis por um bem construído mudou em **1,16 vidas**
— quase trinta vezes mais. É por isso que dois dos nove notebooks são de engenharia de variáveis.

Todos usam `ipywidgets` para os controles interativos.

### Aplicação Streamlit — o laboratório

[`F1/streamlit/`](F1/streamlit) amarra as nove aulas em uma narrativa única, do dado bruto à
decisão de escala, em nove páginas: visão geral → dados → variáveis → modelos → avaliação →
previsão → **gêmeo digital** → cenários → síntese. O estado flui entre as páginas: o campeão
escolhido na página 3 alimenta a previsão da 5, que alimenta o gêmeo da 6.

```bash
.venv/bin/streamlit run F1/streamlit/app.py
```

O `nucleo/` não importa Streamlit em lugar nenhum — é código puro, e é o que os testes exercitam:

```bash
cd F1/streamlit && ../../.venv/bin/python -m pytest testes -q
# 22 passed
```

Cada teste é um **invariante didático**: `test_features_nao_usam_o_futuro`,
`test_ninguem_bate_o_oraculo`, `test_gemeo_concorda_com_erlang_em_regime_estavel`. Se um deles
quebra, a aplicação passou a ensinar algo errado. Detalhes em
[`F1/streamlit/README.md`](F1/streamlit/README.md), com o roteiro de apresentação em
[`GUIA_DAS_PAGINAS.md`](F1/streamlit/GUIA_DAS_PAGINAS.md) e a referência tela a tela em
[`TELAS_E_ANALISES.md`](F1/streamlit/TELAS_E_ANALISES.md).

### Frontend Next.js — o produto

[`F1/frontend/`](F1/frontend) apresenta o mesmo gêmeo digital como um produto SaaS, com quatro
telas separadas por público: `/` (operação de hoje), `/semana` (sete dias dimensionados),
`/simulador` (o "e se") e `/tecnico` (qualidade da previsão). O gestor decide escala, não
hiperparâmetro — as telas dele não mencionam modelo.

```bash
npm --prefix F1/frontend install
npm --prefix F1/frontend run dev        # http://localhost:3010
```

Nenhum número é digitado à mão: todos saem de `scripts/exportar_operacao.py`, que importa o mesmo
`F1/streamlit/nucleo` e grava `dados/operacao.json` (versionado).

```bash
.venv/bin/python F1/frontend/scripts/exportar_operacao.py     # ~20 s
```

Ver [`F1/frontend/README.md`](F1/frontend/README.md) para identidade visual, arquitetura de
componentes e a explicação do fluxo animado da central.

---

## Aplicações Interativas

| Aplicação | Comando | Porta | Sistema modelado |
|-----------|---------|-------|------------------|
| **F1 · laboratório** | `.venv/bin/streamlit run F1/streamlit/app.py` | 8501 | Central de atendimento da operadora |
| **F1 · torre de controle** | `npm --prefix F1/frontend run dev` | 3010 | Central de atendimento (visão gestor) |
| **D10 · gêmeo do PA** | `.venv/bin/streamlit run D10/streamlit/app_gemeo_digital.py --server.port 8502` | 8502 | Pronto Atendimento (Manchester) |

As três estão registradas em [`.claude/launch.json`](.claude/launch.json).

---

## Modelos Estatísticos Utilizados

**Processo de Poisson — chegadas**

```
P(X = k) = (λᵏ · e⁻λ) / k!      com λ variando por hora do dia
```

**Distribuição Lognormal — tempos de atendimento**

```
T ~ Lognormal(μ, σ²)      E[T] = e^(μ + σ²/2)
```

**Fila M/G/c com prioridade** — capacidade variável por turno, disciplina de prioridade Manchester,
sem preempção de consulta já iniciada (D9, D10, E4, F1/nucleo/gemeo.py).

**Erlang C** — dimensionamento analítico usado na F1 como contraprova do gêmeo digital: em regime
estável, simulação e teoria têm de concordar (é um dos testes automatizados).

**Método IQR (Tukey, 1977) — outliers**

```python
IQR = Q3 - Q1
limite_inferior = Q1 - 1.5 * IQR
limite_superior = Q3 + 1.5 * IQR
```

**Método de Welch** — identificação do fim do transiente (E3).

---

## Tecnologias

| Tecnologia / Padrão | Versão | Uso |
|---------------------|--------|-----|
| Python | 3.14.2 | Linguagem principal |
| HL7 FHIR | R4 (2019) | Protocolo de extração do HIS |
| HAPI FHIR Server | público | Sandbox (`hapi.fhir.org/baseR4`) |
| SimPy | 4.1.1 | Motor de simulação de eventos discretos |
| pandas · NumPy · SciPy | 3.0.3 · 2.4.4 · 1.17.1 | Dados, aleatoriedade e ajuste de distribuições |
| Matplotlib · Seaborn · Plotly | 3.10.9 · 0.13.2 · 6.7.0 | Visualizações |
| statsmodels | 0.14.6 | ARIMA / SARIMA, testes de estacionariedade |
| Prophet · holidays | 1.3.0 · 0.96 | Previsão com sazonalidade e feriados |
| scikit-learn | 1.9.0 | Árvores, Random Forest, métricas |
| XGBoost · LightGBM · CatBoost | 3.3.0 · 4.7.0 · 1.2.10 | Boosting |
| Pyomo + HiGHS | 6.10.0 · 1.14.0 | Otimização prescritiva da escala |
| Streamlit | 1.57.0 | Painéis F1 e D10 |
| Next.js · React | 16.3.0 · 19.2.8 | Frontend F1 (Tailwind 4, TypeScript 5) |
| pytest | 9.1.1 | Invariantes didáticos da F1 |
| LGPD | Lei 13.709/2018 | Conformidade no tratamento de dados de saúde |
| Protocolo Manchester | — | Triagem e classificação de risco |

---

## Conformidade LGPD

**Todos os dados deste repositório são sintéticos.** Não há dado de paciente ou beneficiário real
em nenhum módulo. Identificadores como `PA00001` são pseudônimos técnicos gerados
programaticamente, datas são fictícias e os parâmetros estatísticos vêm de literatura publicada,
não de prontuários individuais. Nenhum número descreve a operação real de qualquer operadora.

A escolha por dados sintéticos também é **didática**: como somos nós que plantamos cada efeito
dentro dos dados — ciclo diário, feriado, janela de vencimento, onda epidemiológica — sabemos o
que o modelo *deveria* descobrir, e conseguimos calcular o **piso exato de erro** do problema. Um
modelo que fica abaixo desse piso não é bom: está lendo a resposta em algum lugar.

O tratamento do tema aparece explicitamente em dois lugares: a Parte 8 da D9 (classificação de
sensibilidade dos campos) e o notebook F1_08 (quais variáveis a operadora **pode** usar para
prever demanda, e quais não). Para uso com dados de produção, consulte a Seção 8.6 da apostila D9
sobre pseudonimização e controle de acesso.

---

## Referências

- BRASIL. *Lei n.º 13.709/2018* — Lei Geral de Proteção de Dados Pessoais (LGPD).
- ANS. *Resolução Normativa n.º 566/2022* — prazos máximos para garantia de atendimento.
- ARMBRUST, M. et al. Delta Lake: high-performance ACID table storage over cloud object stores. *VLDB Endowment*, v. 13, n. 12, 2020.
- DIXON, J. *Pentaho, Hadoop, and Data Lakes*. Pentaho Blog, 2010.
- HL7 INTERNATIONAL. *FHIR R4 Specification*. 2019. https://hl7.org/fhir/R4/
- OHDSI. *The Book of OHDSI*. 2021. https://ohdsi.github.io/TheBookOfOhdsi/
- TAYLOR, S. J.; LETHAM, B. Forecasting at scale. *The American Statistician*, v. 72, n. 1, 2018.
- TUKEY, J. W. *Exploratory Data Analysis*. Addison-Wesley, 1977.
- WELCH, P. D. The statistical analysis of simulation results. In: *Computer Performance Modeling Handbook*. Academic Press, 1983.
- ZAHARIA, M. et al. Apache Spark: a unified engine for big data processing. *Communications of the ACM*, v. 59, n. 11, 2016.
- DATASUS/MS. *RNDS — Rede Nacional de Dados em Saúde*. 2020. https://rnds.saude.gov.br

Cada notebook traz a sua própria lista de referências ao final — a da E4, em particular, reúne a
bibliografia de análise de decisão em simulação hospitalar.

---

## Licença

Material didático de uso exclusivo para fins acadêmicos no contexto do curso UNIMED SP.
Reprodução permitida com citação da fonte.

---

*Dúvidas ou sugestões? Abra uma issue ou entre em contato pelo e-mail do curso.*
