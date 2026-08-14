# Gêmeo Digital — previsão de demanda e escala

Aplicação **Next.js** montada como um produto SaaS: barra lateral, workspace, barra superior com
sincronização e avisos, e três telas.

| Rota | Para quem | O que mostra |
| --- | --- | --- |
| `/` | **gestão** | Operação de hoje: rotina diária do sistema, a central em tempo real, escala publicada e horas de atenção. |
| `/semana` | **gestão / RH** | Os sete dias seguintes já dimensionados, com faixa provável, equipe, custo, motivo — e exportação em CSV. |
| `/simulador` | **gestão / planejamento** | O "e se": mexe na demanda e no tamanho da equipe e o gêmeo simula o dia inteiro na hora. |
| `/tecnico` | time técnico e sala de aula | Qualidade da previsão: modelos, erro medido, gêmeo digital, Erlang C, cenários e procedência. |

A separação é proposital. O gestor decide **escala**, não hiperparâmetro: as telas dele falam de
ligações, fila, gente e custo — nenhuma palavra sobre modelo. A aplicação Streamlit
(`../streamlit`) continua sendo o laboratório onde se mexe em tudo.

---

## Identidade visual

As cores saem dos tokens institucionais publicados no site da Unimed FESP (`--cdm-*`) e estão
todas em `app/globals.css`:

| Papel no produto | Token institucional | Valor |
| --- | --- | --- |
| Barra lateral | verde escuro | `#004e4c` |
| Primária, positivo | verde | `#00995d` |
| Destaques, marca | verde cítrico | `#b1d34b` |
| Atenção | laranja | `#f47920` |
| Crítico | vermelho | `#ed1651` |
| Fundo / cartões | cinza claro / branco | `#f1f4f2` / `#ffffff` |

**A marca.** Solte o arquivo oficial em `public/marca.svg` e ele aparece no topo da barra
lateral (a existência é checada no build, em `app/layout.tsx`). Sem o arquivo, entra o texto
"Unimed FESP". O logotipo não foi reproduzido aqui de propósito: use o arquivo oficial da
central de marca.

---

## Como rodar

```bash
npm --prefix "F1/frontend" install
npm --prefix "F1/frontend" run dev
```

Abre em <http://localhost:3010>. Também registrado em `.claude/launch.json` como
`f1-torre-de-controle`.

Versão estática (uma pasta que abre em qualquer lugar, sem Node):

```bash
npm --prefix "F1/frontend" run exportar-estatico
```

Resultado em `F1/frontend/out/`.

---

## De onde vêm os números

**Nenhum número foi digitado à mão.** Todos saem de `scripts/exportar_operacao.py`, que importa
o mesmo núcleo dos notebooks e da aplicação Streamlit (`F1/streamlit/nucleo`) e grava
`dados/operacao.json`:

```bash
.venv/bin/python "F1/frontend/scripts/exportar_operacao.py"
# ou, de dentro do frontend:
npm run dados
```

| Etapa | O que calcula | Origem |
| --- | --- | --- |
| Base sintética | 2 anos de volume horário da central, com semente fixa | `nucleo/dados.py` |
| Campo de jogo | referências ingênuas e o piso do problema | `nucleo/avaliacao.py` |
| Modelos | SARIMA, Prophet, árvore, Random Forest, XGBoost, LightGBM, CatBoost | `nucleo/modelos.py` |
| Previsão operacional | previsão diária × perfil intradiário; erro por horizonte | `nucleo/features.py` |
| Gêmeo digital | replicações SimPy + Erlang C, escala prescrita, comparação de fontes | `nucleo/gemeo.py` |
| Dia da operação | traço minuto a minuto + uma linha por ligação (chegada, início, fim) | `nucleo/gemeo.py` |
| Próximos 7 dias | previsão, faixa provável, escala e custo — com o motivo de cada dia | `nucleo/dados.py` |

Roda em cerca de 20 segundos. Mudou TMA, meta de SLA ou custo do atendente-hora? Ajuste o topo
do script, rode de novo e as três telas se refazem.

### O fluxo animado, e por que ele é honesto

A seção **A central agora** não simula nada no navegador. O exportador grava, além do traço
minuto a minuto, **uma linha por ligação** do dia — quando chegou, quando foi atendida e quando
a chamada terminou (`gemeo.simular_dia_detalhado()`, a mesma máquina de `simular_dia()` com um
processo observador acoplado).

Com isso, o painel reconstrói o fluxo inteiro: a ligação aparece na faixa **chegando** no
instante exato em que chegou, entra na **fila** se não houver atendente livre (com o cronômetro
da espera correndo), ocupa um **posto** pelo tempo exato da conversa — barra de progresso e
tudo — e sai como **atendida**, ou desiste no meio da espera. O relógio caminha em tempo
contínuo (soma o tempo real decorrido a cada quadro), o que permite acelerar de 1 min/s até
1 h/s sem que nada perca o sincronismo.

A única coisa decidida no navegador é **qual posto** recebe cada ligação, porque a simulação
registra o tempo, não a cadeira: `lib/fluxo.ts` distribui pelo primeiro posto livre, uma vez
para o dia inteiro. Os cartões de indicadores leem exatamente esse mesmo retrato — o número em
"na fila agora" é, por construção, a quantidade de pastilhas desenhadas na fila.

É por isso que o aviso de *"nas últimas 3 horas chegaram 51% mais ligações do que o esperado"* é
uma comparação de verdade entre realizado e previsto, e não um texto fixo. Os avisos do sino, na
barra superior, são os mesmos marcos calculados sobre esse registro.

---

## Estrutura

```
F1/frontend/
├── app/
│   ├── layout.tsx          o shell do produto (sidebar + topbar)
│   ├── page.tsx            Operação de hoje
│   ├── semana/page.tsx     Escala da semana
│   ├── simulador/page.tsx  Simulador de cenários
│   ├── tecnico/page.tsx    Qualidade da previsão
│   └── globals.css         tokens da aplicação (tema escuro neutro)
├── componentes/
│   ├── Shell.tsx           barra lateral, workspace, avisos, sincronização
│   ├── StatusSistema.tsx   a rotina diária do sistema
│   ├── PainelOperacao.tsx  o dia acontecendo (cliente)
│   ├── FluxoAtendimento.tsx  chegada → fila → postos → desfecho, animado
│   ├── RecomendacaoAgora.tsx projeção de fechamento e reforço recomendado
│   ├── PlanoDoDia.tsx      escala por turno e horas de atenção
│   ├── ProximaSemana.tsx   os sete dias já dimensionados
│   ├── Simulador.tsx       a tela do "e se" (cliente)
│   ├── BotaoExportar.tsx   exportação da escala em CSV
│   ├── graficos.tsx        todos os gráficos, em SVG puro — sem biblioteca
│   ├── ui.tsx              cabeçalho de página, blocos, cartões, KPIs
│   └── (Hero, ResultadoDoDia, ValorDaPrevisao, Modelos,
│        PrevisaoOperacional, CenariosDecisao, Cadeia) → tela técnica
├── lib/
│   ├── gemeo.ts            o gêmeo digital em TS — fila M/G/c com abandono
│   ├── erlang.ts           Erlang C em TS — a recomendação do meio do dia
│   ├── fluxo.ts            retrato da central em um instante (fila, postos, saídas)
│   ├── tipos.ts            o contrato com o JSON do exportador
│   ├── dados.ts            carga do JSON
│   └── formato.ts          formatação pt-BR (número, %, R$, tempo, data)
├── dados/operacao.json     ← gerado pelo Python, versionado
└── scripts/exportar_operacao.py
```

Só `Shell`, `PainelOperacao`, `Simulador` e `BotaoExportar` são componentes de cliente; o resto é renderizado
no servidor. Não há biblioteca de gráficos: as figuras são SVG escrito à mão.

---

## Sobre os dados

Toda a base é **sintética e gerada em memória**, com semente fixa. Nenhum dado de beneficiário
real é usado e nenhum número descreve a operação real de qualquer operadora — o nome do produto
e o workspace são fictícios, de demonstração. A decisão é didática: como somos nós que plantamos
cada efeito dentro dos dados, sabemos o que o modelo deveria descobrir — e podemos calcular o
piso exato do problema.
