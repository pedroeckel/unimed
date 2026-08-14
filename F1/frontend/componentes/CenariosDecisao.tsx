import { Fronteira } from "@/componentes/graficos";
import { Cartao, Leitura, Secao, Selo } from "@/componentes/ui";
import { num, pct, reais } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

export function CenariosDecisao({ dados }: { dados: Operacao }) {
  const { cenarios, fronteira, parametros } = dados;
  const base = cenarios.find((c) => c.fator === 1) ?? cenarios[0];
  const pior = [...cenarios].sort((a, b) => b.custo - a.custo)[0];
  const meta = fronteira.find((p) => p.delta === 0)!;
  const maisUm = fronteira.find((p) => p.delta === 1)!;
  const menosUm = fronteira.find((p) => p.delta === -1)!;

  return (
    <Secao
      id="cenarios"
      etapa="Decisão"
      titulo="O que levar para a diretoria"
      chamada={
        <>
          A previsão cobre o esperado. A gestão precisa saber o que fazer quando o inesperado
          chegar — e quanto custa estar preparado. Cada cenário multiplica a demanda prevista, a
          escala é <strong className="text-texto">redimensionada</strong> e o gêmeo mede o
          resultado.
        </>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {cenarios.map((c) => {
          const variacao = c.custo / base.custo - 1;
          return (
            <div
              key={c.nome}
              className={`rounded-2xl border p-4 ${
                c.fator === 1 ? "border-verde/40 bg-verde/[0.06]" : "border-borda bg-painel/70"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold leading-tight text-texto">{c.nome}</h3>
                <span className="numero shrink-0 rounded-md border border-borda2 px-1.5 py-0.5 text-[0.68rem] text-suave">
                  ×{num(c.fator, 2)}
                </span>
              </div>
              <p className="mt-2 text-[0.72rem] leading-relaxed text-tenue">{c.descricao}</p>

              <div className="mt-4 space-y-1.5 border-t border-borda pt-3 text-xs">
                <Linha rotulo="Demanda do dia" valor={`${num(c.demanda)} lig.`} />
                <Linha rotulo="Atendentes-hora" valor={num(c.atendentes_hora)} />
                <Linha rotulo="Pico de escala" valor={`${c.pico_atendentes} pessoas`} />
                <Linha rotulo="Nível de serviço" valor={pct(c.nivel_servico, 1)} />
                <Linha rotulo="Custo do dia" valor={reais(c.custo)} />
              </div>

              <div
                className={`mt-3 rounded-lg px-2 py-1.5 text-center text-[0.72rem] ${
                  variacao > 0.1
                    ? "bg-vermelho/10 text-vermelho"
                    : variacao < -0.1
                      ? "bg-azul/10 text-azul"
                      : "bg-painel2 text-tenue"
                }`}
              >
                {variacao === 0
                  ? "linha de base"
                  : `${variacao > 0 ? "+" : ""}${num(variacao * 100, 0)}% de custo`}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4">
        <Leitura>
          Repare no que <strong className="text-texto">não</strong> aconteceu: o nível de serviço
          ficou parecido em todos os cenários. É o resultado esperado, porque a escala foi
          redimensionada em cada um. A pergunta de gestão não é{" "}
          <em>&ldquo;o que acontece com a fila se vier um surto&rdquo;</em> — é{" "}
          <strong className="text-texto">
            &ldquo;quanto custa manter o SLA se vier um surto, e eu consigo mobilizar essa gente a
            tempo?&rdquo;
          </strong>{" "}
          No pior cenário selecionado ({pior.nome}), a escala vai de {num(base.atendentes_hora)} para{" "}
          {num(pior.atendentes_hora)} atendentes-hora — {num((pior.custo / base.custo - 1) * 100, 0)}% de custo a mais. O gêmeo responde a primeira parte; a segunda é uma conversa com o RH, e
          ela precisa acontecer <strong className="text-texto">antes</strong> do surto.
        </Leitura>
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Cartao
          titulo="Fronteira custo × serviço"
          descricao="a escala da meta, varrida de três atendentes a menos a três a mais em cada hora"
        >
          <Fronteira pontos={fronteira} meta={parametros.meta_nivel_servico} />
        </Cartao>

        <div className="space-y-4">
          <Cartao titulo="A curva é côncava — e é isso que importa">
            <p className="text-[0.88rem] leading-relaxed text-suave">
              Sair da escala mais enxuta para a seguinte compra{" "}
              <strong className="text-texto">muitos pontos de serviço por pouco dinheiro</strong>:
              de {pct(menosUm.nivel_servico, 0)} para {pct(meta.nivel_servico, 0)} custa{" "}
              {reais(meta.custo - menosUm.custo)}. O passo seguinte compra menos:{" "}
              {reais(maisUm.custo - meta.custo)} pelos{" "}
              {num((maisUm.nivel_servico - meta.nivel_servico) * 100, 1)} pontos que faltam para{" "}
              {pct(maisUm.nivel_servico, 0)}. Depois disso, cada real adicional compra quase nada.
            </p>
            <p className="mt-3 text-[0.88rem] leading-relaxed text-suave">
              Essa é a tela que vai para a diretoria: ela não pede uma decisão técnica, pede{" "}
              <strong className="text-texto">uma escolha de posição na curva</strong>. E vale dizer o
              que a curva não mostra — o custo de perder o beneficiário que abandonou a ligação e o
              custo regulatório de estourar prazo. Com eles na conta, o ponto ótimo se desloca para a
              direita.
            </p>
          </Cartao>

          <Cartao titulo="A rotina que sai daqui">
            <ol className="space-y-2.5 text-[0.85rem] leading-relaxed text-suave">
              {[
                ["D-14", "feche a escala base pelo calendário — feriado, campanha, janela de vencimento."],
                ["D-1", "ajuste o fino com o modelo completo, que já viu o volume de ontem e percebeu se há onda em curso."],
                ["No dia", "monitore ocupação por hora. Acima de 0,85, acione contingência antes que a fila apareça."],
                ["Sempre", "reporte espera e abandono juntos. Espera sozinha premia quem perde beneficiário no caminho."],
              ].map(([quando, oque]) => (
                <li key={quando} className="flex gap-3">
                  <Selo tom="neutro">{quando}</Selo>
                  <span className="pt-0.5">{oque}</span>
                </li>
              ))}
            </ol>
          </Cartao>
        </div>
      </div>
    </Secao>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <span className="text-tenue">{rotulo}</span>
      <span className="numero text-texto">{valor}</span>
    </div>
  );
}
