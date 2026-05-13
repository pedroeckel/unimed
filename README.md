# Simulação em Serviços de Saúde — UNIMED SP
### Material prático do curso — Prof. Pedro

> **Instituição:** UNIMED SP  
> **Disciplina:** Simulação em Serviços de Saúde  
> **Professor:** Prof. Dr. Pedro (Mestrado e Doutorado em Simulação)  
> **Módulo:** D9 — Integração com Sistemas Corporativos (ERP, HIS)

---

## Visão Geral

Este repositório contém o **material prático** da aula D9, que demonstra como extrair, limpar e transformar dados reais de sistemas hospitalares (HIS via HL7 FHIR R4 e ERP) em **inputs prontos para modelos de simulação de eventos discretos (DES)**.

O pipeline percorre sete etapas — da conexão à API FHIR até a exportação dos parâmetros calibrados em CSV —, cobrindo os principais conceitos de integração de dados em saúde: interoperabilidade, qualidade de dados, KPIs operacionais e conformidade com a LGPD.

```
HIS (HL7 FHIR R4)         ERP (SQL / batch)
        │                          │
        ▼                          ▼
  GET /Encounter           Escala de pessoal
  (dados de PA)            Disponibilidade de leitos
        │                          │
        └──────────┬───────────────┘
                   ▼
          Limpeza (IQR)
          Análise de completude
                   │
                   ▼
          KPIs operacionais
          λ por hora · μ por risco
                   │
                   ▼
          inputs_*.csv  ──▶  Modelo SimPy (D10)
```

---

## Estrutura do Repositório

```
code/
├── README.md                          ← este arquivo
└── D9/
    ├── D9_Pratica_Integracao_ERP_HIS.ipynb   ← notebook principal (33 células)
    │
    ├── inputs_chegada_pa.csv          ← taxa λ de chegada por faixa horária
    ├── inputs_servico_pa.csv          ← parâmetros μ e σ por nível Manchester
    ├── inputs_escala_erp.csv          ← escala de médicos por turno (ERP)
    ├── inputs_leitos_erp.csv          ← taxa de ocupação de leitos por ala
    │
    ├── fig1_outliers.png              ← histograma antes × depois da limpeza
    ├── fig2_taxa_chegada.png          ← taxa de chegada λ por hora do dia
    ├── fig3_volume_dia.png            ← volume de atendimentos por dia da semana
    ├── fig4_espera_risco.png          ← tempo de espera por nível Manchester
    └── fig5_heatmap.png               ← heatmap hora × dia da semana
```

---

## Notebook — D9_Pratica_Integracao_ERP_HIS.ipynb

O notebook está estruturado em **10 partes didáticas** — cada uma começa com explicação teórica e termina com interpretação dos resultados.

| Parte | Conteúdo | Células |
|-------|----------|---------|
| 1 | Configuração e bibliotecas | 2 |
| 2 | Conexão à API FHIR R4 (HAPI sandbox) | 2 |
| 3 | Extração de Encounters (atendimentos de PA) | 2 |
| 4 | Dataset sintético realista (30 dias · ~5.000 atendimentos) | 2 |
| 5 | Análise de qualidade: completude + outliers (método IQR) | 4 |
| 6 | KPIs: λ/hora, volume/dia, μ/risco Manchester, heatmap | 4 |
| 7 | Integração ERP: escala de pessoal + ocupação de leitos | 3 |
| 8 | Conformidade LGPD: classificação de sensibilidade dos campos | 1 |
| 9 | Tabela de inputs para o simulador SimPy | 3 |
| 10 | Resumo do pipeline e próximos passos | 1 |

### Execução offline

O notebook detecta automaticamente se o servidor FHIR público (`hapi.fhir.org/baseR4`) está disponível. Em caso de falha de rede, ativa um **modo offline** com dataset sintético estatisticamente equivalente — garantindo que todas as células executem sem erros em qualquer ambiente.

```python
def fhir_get(path, params=None):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json(), True          # ✅ servidor disponível
    except Exception:
        return None, False                # ⚠️ fallback sintético ativado
```

---

## Arquivos de Saída (inputs para o simulador)

### `inputs_chegada_pa.csv`
Taxa de chegada λ (pacientes/hora) por faixa horária de 6h. Alimenta o módulo de chegadas do SimPy.

| Coluna | Descrição |
|--------|-----------|
| `faixa_horaria` | Bloco de 6h (ex.: `06h–12h`) |
| `total_30_dias` | Total de chegadas no período |
| `lambda_hora` | Taxa média de chegadas por hora (pacientes/h) |

### `inputs_servico_pa.csv`
Parâmetros da distribuição Lognormal por nível de risco Manchester. Alimenta o módulo de atendimento.

| Coluna | Descrição |
|--------|-----------|
| `risco_manchester` | Nível de triagem (Vermelho / Laranja / Amarelo / Verde / Azul) |
| `media_atend_min` | Tempo médio de atendimento (minutos) |
| `dp_atend_min` | Desvio-padrão do tempo de atendimento |
| `media_espera_min` | Tempo médio de espera pelo médico |
| `proporcao` | Número absoluto de atendimentos neste nível |

### `inputs_escala_erp.csv`
Número de médicos disponíveis por turno e dia da semana. Define a capacidade do recurso no SimPy.

| Coluna | Descrição |
|--------|-----------|
| `dia_semana` | Dia da semana |
| `turno` | Plantão (Noturno / Diurno / Vespertino) |
| `hora_inicio` / `hora_fim` | Intervalo do turno |
| `n_medicos` | Médicos escalados neste turno |

### `inputs_leitos_erp.csv`
Disponibilidade de leitos por ala hospitalar. Modela restrições de internação (boarding).

| Coluna | Descrição |
|--------|-----------|
| `ala` | Ala hospitalar (PA Observação, UTI, Clínica Médica...) |
| `leitos_total` | Capacidade total de leitos |
| `leitos_ocupados` | Leitos ocupados no período |
| `taxa_ocupacao_pct` | Taxa de ocupação (%) |

---

## Modelos Estatísticos Utilizados

### Processo de Poisson — chegadas de pacientes
```
P(X = k) = (λᵏ · e⁻λ) / k!

λ varia por hora do dia:
  Madrugada (0h–6h):   λ ≈ 0,71 pac/h
  Manhã     (6h–12h):  λ ≈ 5,61 pac/h
  Tarde     (12h–18h): λ ≈ 6,67 pac/h  ← pico
  Noite     (18h–24h): λ ≈ 5,94 pac/h
```

### Distribuição Lognormal — tempos de atendimento
```
T ~ Lognormal(μ, σ²)
E[T] = e^(μ + σ²/2)

Parâmetros calibrados por nível Manchester:
  Vermelho: μ = 3,0 · σ = 0,3  → E[T] ≈ 20 min
  Laranja:  μ = 3,5 · σ = 0,4  → E[T] ≈ 33 min
  Amarelo:  μ = 4,2 · σ = 0,5  → E[T] ≈ 67 min
  Verde:    μ = 4,8 · σ = 0,6  → E[T] ≈ 121 min
  Azul:     μ = 3,8 · σ = 0,4  → E[T] ≈ 45 min
```

### Detecção de outliers — Método IQR (Tukey, 1977)
```python
IQR = Q3 - Q1
limite_inferior = Q1 - 1.5 * IQR
limite_superior = Q3 + 1.5 * IQR
```

---

## Instalação

### Pré-requisitos
- Python ≥ 3.9
- Jupyter Notebook ou JupyterLab

### Dependências

```bash
pip install requests pandas numpy matplotlib seaborn scipy
```

Ou com conda:

```bash
conda install requests pandas numpy matplotlib seaborn scipy
```

### Executar o notebook

```bash
cd D9/
jupyter notebook D9_Pratica_Integracao_ERP_HIS.ipynb
```

Execute as células em ordem, de cima para baixo. O tempo total de execução é de aproximadamente **30 segundos** (modo offline) a **2 minutos** (com conexão ao servidor FHIR).

---

## Tecnologias e Padrões

| Tecnologia / Padrão | Versão | Uso neste projeto |
|---------------------|--------|-------------------|
| HL7 FHIR | R4 (2019) | Protocolo de extração de dados do HIS |
| HAPI FHIR Server | Público | Sandbox de testes (`hapi.fhir.org/baseR4`) |
| Python | ≥ 3.9 | Linguagem principal |
| pandas | ≥ 1.5 | Manipulação de DataFrames |
| NumPy | ≥ 1.23 | Geração de números aleatórios e cálculos |
| SciPy | ≥ 1.9 | Ajuste de distribuições (Lognormal) |
| Matplotlib / Seaborn | latest | Visualizações (5 figuras) |
| SimPy | ≥ 4.0 | Motor de simulação DES (próxima aula — D10) |
| LGPD | Lei 13.709/2018 | Conformidade no tratamento de dados de saúde |
| Protocolo Manchester | — | Sistema de triagem e classificação de risco |

---

## Conformidade LGPD

Os dados sintéticos gerados neste notebook **não contêm dados pessoais reais**. O campo `id_anonimizado` é um pseudônimo técnico gerado programaticamente (ex.: `PA00001`), sem vínculo com qualquer paciente real. As datas são fictícias e os parâmetros estatísticos são derivados de literatura científica publicada, não de prontuários individuais.

Para uso com dados reais de produção, consulte a Seção 8.6 da apostila D9 (Governança e LGPD no Data Lake) para orientações sobre classificação de campos, pseudonimização e controle de acesso.

---

## Próximos Passos — Aula D10

Os quatro arquivos CSV gerados por este notebook são os **inputs diretos** do modelo SimPy que será construído na aula D10:

```python
# Exemplo de uso no modelo SimPy (D10)
import simpy, pandas as pd, numpy as np

chegadas   = pd.read_csv("inputs_chegada_pa.csv")
servico    = pd.read_csv("inputs_servico_pa.csv")
escala     = pd.read_csv("inputs_escala_erp.csv")
leitos     = pd.read_csv("inputs_leitos_erp.csv")

# λ da faixa horária atual
lambda_hora = chegadas.loc[chegadas.faixa_horaria == "06h–12h", "lambda_hora"].values[0]

# Tempo de serviço por nível de risco
mu_amarelo    = servico.loc[servico.risco_manchester == "Amarelo", "media_atend_min"].values[0]
sigma_amarelo = servico.loc[servico.risco_manchester == "Amarelo", "dp_atend_min"].values[0]
```

---

## Referências

- DIXON, J. *Pentaho, Hadoop, and Data Lakes*. Pentaho Blog, 2010.
- HL7 INTERNATIONAL. *FHIR R4 Specification*. 2019. Disponível em: https://hl7.org/fhir/R4/
- ZAHARIA, M. et al. Apache Spark: a unified engine for big data processing. *Communications of the ACM*, v. 59, n. 11, p. 56-65, 2016.
- ARMBRUST, M. et al. Delta Lake: high-performance ACID table storage over cloud object stores. *VLDB Endowment*, v. 13, n. 12, 2020.
- OHDSI. *The Book of OHDSI*. 2021. Disponível em: https://ohdsi.github.io/TheBookOfOhdsi/
- TUKEY, J. W. *Exploratory Data Analysis*. Addison-Wesley, 1977.
- BRASIL. *Lei n.º 13.709/2018* — Lei Geral de Proteção de Dados Pessoais (LGPD).
- DATASUS/MS. *RNDS — Rede Nacional de Dados em Saúde*. 2020. Disponível em: https://rnds.saude.gov.br

---

## Licença

Material didático de uso exclusivo para fins acadêmicos no contexto do curso UNIMED SP — Simulação em Serviços de Saúde. Reprodução permitida com citação da fonte.

---

*Dúvidas ou sugestões? Abra uma issue ou entre em contato pelo e-mail do curso.*
