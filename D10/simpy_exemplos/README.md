# Exemplos Didáticos de SimPy para a Aula D10

Este material transforma os exemplos de [docs/simpy.md](/Users/pedroeckel/gestao_quanti/projects/unimed%20sp/code/docs/simpy.md) em **notebooks Jupyter didáticos**, pensados para aula passo a passo.

## Trilha principal da aula

1. `00_fundamentos_simpy.ipynb`
2. `01_triagem_classificacao_risco.ipynb`
3. `02_leitos_uti_timeout.ipynb`
4. `03_fluxo_cadastro_alta.ipynb`
5. `04_escala_enfermagem_container.ipynb`
6. `05_despacho_ambulancias_filterstore.ipynb`

## O que existe em cada notebook

- `00_fundamentos_simpy.ipynb`: introduz `Environment`, `Process`, `timeout`, `Resource`, `Store`, `FilterStore` e `Container`.
- `01_triagem_classificacao_risco.ipynb`: mostra `Resource` e `PriorityResource` em fila clínica.
- `02_leitos_uti_timeout.ipynb`: mostra `Store` e espera com prazo máximo.
- `03_fluxo_cadastro_alta.ipynb`: mostra fluxo multietapas com retorno ao médico.
- `04_escala_enfermagem_container.ipynb`: mostra capacidade agregada com `Container` e `start_delayed()`.
- `05_despacho_ambulancias_filterstore.ipynb`: mostra seleção de objetos compatíveis com `FilterStore`.

## Material de apoio

Os arquivos `.py` continuam na pasta como apoio para:
- execução rápida fora do Jupyter;
- comparação entre versão notebook e versão script;
- reaproveitamento em demos automatizadas.

## Ambiente

Use o ambiente virtual do projeto, porque o Python global não tem `simpy` instalado.

Se quiser abrir os notebooks localmente, o kernel deve apontar para:

```bash
./.venv/bin/python
```

## Observação didática importante

No notebook de escala (`04_escala_enfermagem_container.ipynb`), a simulação roda até esgotar os eventos do dia. Isso evita cortar a última mensagem exatamente no limite do horizonte, um detalhe importante de `env.run(until=...)` no SimPy.
