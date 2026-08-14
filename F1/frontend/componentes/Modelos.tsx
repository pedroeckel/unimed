import { BarrasHorizontais, COR } from "@/componentes/graficos";
import { Cartao, Kpi, Leitura, Secao } from "@/componentes/ui";
import { num, pct } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

const COR_FAMILIA: Record<string, string> = {
  Boosting: COR.verde,
  Árvores: COR.azul,
  Clássico: COR.roxo,
  "Referência simples": "#3b4f66",
};

export function Modelos({ dados }: { dados: Operacao }) {
  const { placar, campo, campeao, parametros } = dados;
  const maximo = Math.max(...placar.map((p) => p.mae)) * 1.12;

  return (
    <Secao
      id="modelos"
      etapa="A disputa"
      titulo="Quem previu melhor — e quanto disso era possível"
      chamada={
        <>
          Um MAE isolado não informa nada. Ele só vira resultado entre duas linhas: a{" "}
          <strong className="text-texto">melhor referência simples</strong>, que qualquer planilha
          entrega sem modelo nenhum, e o <strong className="text-texto">piso do problema</strong> —
          o erro de quem soubesse a média exata de cada dia e ainda assim erraria, porque a chegada
          de ligações é um sorteio. Todo o espaço disputável está entre as duas.
        </>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi
          valor={num(campo.mae_referencia, 1)}
          rotulo="Melhor referência simples"
          tom="vermelho"
          nota={campo.melhor_referencia}
        />
        <Kpi valor={num(campeao.mae, 1)} rotulo={`Modelo campeão (${campeao.nome})`} tom="verde" nota="erro no conjunto de teste" />
        <Kpi
          valor={num(campo.mae_piso, 1)}
          rotulo="Piso do problema"
          tom="azul"
          nota="ninguém vai abaixo sem vazamento"
        />
        <Kpi
          valor={pct(campeao.aproveitado / 100, 1)}
          rotulo="Do sinal aprendível, capturado"
          tom="roxo"
          nota={`${num(campeao.ganho_sobre_referencia, 1)}% de erro a menos que a referência`}
        />
      </div>

      <div className="mt-4">
        <Cartao
          titulo="Erro médio absoluto no conjunto de teste"
          descricao={`ligações por dia · ${parametros.n_dias_teste} dias de teste, a partir de ${parametros.corte_teste}`}
        >
          <BarrasHorizontais
            itens={placar.map((p) => ({
              rotulo: p.modelo,
              valor: p.mae,
              cor: COR_FAMILIA[p.familia] ?? "#3b4f66",
            }))}
            maximo={maximo}
            marcos={[
              { valor: campo.mae_piso, rotulo: "piso", cor: COR.azul },
              { valor: campo.mae_referencia, rotulo: "referência", cor: COR.vermelho },
            ]}
            formatar={(v) => num(v, 1)}
          />
        </Cartao>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Cartao titulo="O placar completo" descricao="todos avaliados no mesmo conjunto de teste, sem exceção">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-sm">
              <thead>
                <tr className="border-b border-borda text-left text-[0.7rem] uppercase tracking-wider text-tenue">
                  <th className="pb-2 font-medium">Modelo</th>
                  <th className="pb-2 text-right font-medium">MAE</th>
                  <th className="pb-2 text-right font-medium">RMSE</th>
                  <th className="pb-2 text-right font-medium">MAPE</th>
                  <th className="pb-2 text-right font-medium">RMSE/MAE</th>
                  <th className="pb-2 text-right font-medium">% aproveitável</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borda/60">
                {placar.map((p, i) => (
                  <tr key={p.modelo} className={i === 0 ? "bg-verde/[0.06]" : undefined}>
                    <td className="py-1.5">
                      <span className={i === 0 ? "font-medium text-verde" : "text-suave"}>
                        {p.modelo}
                      </span>
                      <span className="ml-2 text-[0.68rem] text-tenue">{p.familia}</span>
                    </td>
                    <td className="numero py-1.5 text-right text-texto">{num(p.mae, 1)}</td>
                    <td className="numero py-1.5 text-right text-suave">{num(p.rmse, 1)}</td>
                    <td className="numero py-1.5 text-right text-suave">{num(p.mape, 1)}%</td>
                    <td className="numero py-1.5 text-right text-suave">{num(p.rmse_mae, 2)}</td>
                    <td className="numero py-1.5 text-right text-texto">
                      {p.aproveitado === null ? "—" : `${num(p.aproveitado, 1)}%`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Leitura>
            As três bibliotecas de <strong className="text-texto">boosting empatam</strong> — a
            diferença entre elas é menor do que a incerteza do próprio teste, e escolher entre uma e
            outra é decisão de engenharia, não de acurácia. O salto real está antes: das referências
            simples (~{num(campo.mae_referencia, 0)}) para as árvores e o boosting (~
            {num(campeao.mae, 0)}). O <strong className="text-texto">Prophet fica para trás</strong>{" "}
            aqui por um motivo declarado: ele prevê o horizonte inteiro de uma vez, sem usar o volume
            de ontem, enquanto os demais preveem um dia à frente com o histórico completo — que é
            como a escala de amanhã é fechada de verdade.
          </Leitura>
        </Cartao>

        <Cartao
          titulo="O que o modelo olha"
          descricao={`importância relativa das variáveis dentro do ${campeao.nome}`}
        >
          <div className="space-y-2">
            {campeao.importancias.map((v) => (
              <div key={v.variavel} className="flex items-center gap-3">
                <span className="w-32 shrink-0 truncate text-xs text-suave" title={v.variavel}>
                  {v.variavel}
                </span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-painel2">
                  <div
                    className="h-full rounded-full bg-verde"
                    style={{ width: `${(v.peso / campeao.importancias[0].peso) * 100}%` }}
                  />
                </div>
                <span className="numero w-12 text-right text-[0.7rem] text-tenue">
                  {num(v.peso * 100, 1)}%
                </span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs leading-relaxed text-tenue">
            O calendário e o histórico recente dominam. Não é acidente: a base tem uma{" "}
            <strong className="text-suave">onda epidemiológica latente</strong> que nenhuma coluna de
            calendário captura — nenhum modelo adivinha quando um surto começa, mas um bom modelo
            percebe que ele <em>já</em> começou, e para isso precisa olhar as defasagens da própria
            série.
          </p>
        </Cartao>
      </div>
    </Secao>
  );
}
