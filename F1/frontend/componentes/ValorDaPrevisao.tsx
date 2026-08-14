import { GraficoLinhas } from "@/componentes/graficos";
import { Cartao, Legenda, Leitura, Secao, Selo } from "@/componentes/ui";
import { dataCurta, num, pct, reais, segundos } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

export function ValorDaPrevisao({ dados }: { dados: Operacao }) {
  const [estatico, modelo, perfeita] = dados.comparacao_fontes;
  const { mes, dia, parametros } = dados;
  const ganhoSl = (modelo.nivel_servico - estatico.nivel_servico) * 100;
  const custoExtra = modelo.custo - estatico.custo;

  return (
    <Secao
      id="valor"
      etapa="O experimento que justifica o projeto"
      titulo="E daí que o erro caiu?"
      chamada={
        <>
          O gestor dimensiona a escala a partir de uma <strong className="text-texto">fonte de
          demanda</strong>. Depois o dia acontece de verdade. Aqui o gêmeo roda três vezes, sempre
          com a <strong className="text-texto">demanda real</strong> — muda só quem recomendou a
          escala. A diferença entre as colunas é o valor operacional da previsão, medido em fila e
          em serviço, não em MAE.
        </>
      }
    >
      <div className="grid gap-3 lg:grid-cols-3">
        <ColunaFonte
          titulo="Média histórica"
          subtitulo="a operação sem modelo: uma taxa média fixa aplicada a todo dia"
          fonte={estatico}
          meta={parametros.meta_nivel_servico}
          tom="vermelho"
        />
        <ColunaFonte
          titulo={`Previsão do modelo`}
          subtitulo={`${dados.campeao.nome} × perfil intradiário — o que está no ar`}
          fonte={modelo}
          meta={parametros.meta_nivel_servico}
          tom="verde"
          destaque
        />
        <ColunaFonte
          titulo="Previsão perfeita"
          subtitulo="conhecer a demanda real de antemão: impossível, e é o teto do ganho"
          fonte={perfeita}
          meta={parametros.meta_nivel_servico}
          tom="azul"
        />
      </div>

      <div className="mt-4">
        <Leitura>
          Neste dia chegaram <strong className="text-texto">{num(dia.total_real)} ligações</strong>{" "}
          contra {num(dia.total_previsto)} previstas e apenas {num(dia.total_estatico)} que a média
          histórica esperava. Dimensionando pela média, o dia fecharia com{" "}
          {pct(estatico.nivel_servico, 1)} de nível de serviço e{" "}
          <strong className="text-texto">{pct(estatico.abandono, 1)} de abandono</strong>.
          Dimensionando pela previsão, o serviço sobe{" "}
          <strong className="text-texto">{num(ganhoSl, 1)} pontos</strong> e o abandono cai para{" "}
          {pct(modelo.abandono, 1)}, ao custo de {reais(custoExtra)} a mais em escala —{" "}
          {num(modelo.atendentes_hora - estatico.atendentes_hora)} atendentes-hora.
          <br />
          <br />A coluna da <strong className="text-texto">previsão perfeita</strong> é o limite
          teórico: a distância entre ela e o modelo é tudo o que ainda há para ganhar melhorando a
          previsão; a distância entre o modelo e a média histórica é o que já foi ganho.
        </Leitura>
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Cartao
          titulo={`E no mês inteiro? ${mes.resumo.dias_simulados} dias de operação simulados`}
          descricao="a mesma comparação repetida dia a dia, com a escala redimensionada em cada um"
        >
          <GraficoLinhas
            series={[
              {
                nome: "modelo",
                valores: mes.dias.map((d) => d.modelo_sl),
                cor: "#00995d",
              },
              {
                nome: "média histórica",
                valores: mes.dias.map((d) => d.estatico_sl),
                cor: "#ed1651",
                tracejada: true,
              },
            ]}
            rotulosX={mes.dias.map((d) => dataCurta(d.data))}
            altura={240}
            minimoY={0.4}
            formatarY={(v) => `${Math.round(v * 100)}%`}
            marcoY={{ valor: parametros.meta_nivel_servico, rotulo: "meta", cor: "#004e4c" }}
          />
          <div className="mt-3">
            <Legenda
              itens={[
                { cor: "#00995d", texto: "escala dimensionada pelo modelo" },
                { cor: "#ed1651", texto: "escala pela média histórica", tracejada: true },
              ]}
            />
          </div>
        </Cartao>

        <div className="space-y-3">
          <Cartao titulo="O mês em números" descricao={`${num(mes.resumo.chamadas)} ligações simuladas`}>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-borda text-left text-[0.7rem] uppercase tracking-wider text-tenue">
                  <th className="pb-2 font-medium">&nbsp;</th>
                  <th className="pb-2 text-right font-medium text-verde">Modelo</th>
                  <th className="pb-2 text-right font-medium text-vermelho">Média hist.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borda/60">
                <LinhaMes
                  rotulo="Nível de serviço"
                  a={pct(mes.resumo.modelo_sl, 1)}
                  b={pct(mes.resumo.estatico_sl, 1)}
                />
                <LinhaMes
                  rotulo="Espera média"
                  a={segundos(mes.resumo.modelo_espera_s, 1)}
                  b={segundos(mes.resumo.estatico_espera_s, 1)}
                />
                <LinhaMes
                  rotulo="Abandono"
                  a={pct(mes.resumo.modelo_abandono, 1)}
                  b={pct(mes.resumo.estatico_abandono, 1)}
                />
                <LinhaMes
                  rotulo="Atendentes-hora"
                  a={num(mes.resumo.modelo_atendentes_hora)}
                  b={num(mes.resumo.estatico_atendentes_hora)}
                />
                <LinhaMes
                  rotulo="Custo de escala"
                  a={reais(mes.resumo.modelo_custo)}
                  b={reais(mes.resumo.estatico_custo)}
                />
              </tbody>
            </table>
          </Cartao>

          <Cartao>
            <p className="text-[0.88rem] leading-relaxed text-suave">
              <strong className="text-texto">Leia a tabela com honestidade.</strong> No mês típico as
              duas fontes entregam praticamente o mesmo serviço — a média histórica até fica{" "}
              {num((mes.resumo.estatico_sl - mes.resumo.modelo_sl) * 100, 1)} ponto acima — mas
              gastando{" "}
              <strong className="text-texto">
                {reais(mes.resumo.estatico_custo - mes.resumo.modelo_custo)}
              </strong>{" "}
              a mais. O ganho da previsão não aparece na média dos dias:{" "}
              <strong className="text-texto">ele aparece nos dias atípicos</strong>, quando a média
              histórica erra a mão e o serviço desaba — como no dia da simulação, {num(ganhoSl, 1)}{" "}
              pontos abaixo. Em operação, é isso que se compra com um modelo: menos gordura no dia
              comum e proteção no dia ruim.
            </p>
          </Cartao>
        </div>
      </div>
    </Secao>
  );
}

function LinhaMes({ rotulo, a, b }: { rotulo: string; a: string; b: string }) {
  return (
    <tr>
      <td className="py-2 text-suave">{rotulo}</td>
      <td className="numero py-2 text-right text-texto">{a}</td>
      <td className="numero py-2 text-right text-suave">{b}</td>
    </tr>
  );
}

function ColunaFonte({
  titulo,
  subtitulo,
  fonte,
  meta,
  tom,
  destaque = false,
}: {
  titulo: string;
  subtitulo: string;
  fonte: Operacao["comparacao_fontes"][number];
  meta: number;
  tom: "verde" | "vermelho" | "azul";
  destaque?: boolean;
}) {
  const cores = {
    verde: { texto: "text-verde", barra: "#00995d", borda: "border-verde/40" },
    vermelho: { texto: "text-vermelho", barra: "#ed1651", borda: "border-vermelho/30" },
    azul: { texto: "text-azul", barra: "#004e4c", borda: "border-azul/30" },
  }[tom];

  return (
    <div
      className={`rounded-2xl border bg-painel/70 p-5 ${destaque ? `${cores.borda} ring-1 ring-verde/20` : "border-borda"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-texto">{titulo}</h3>
        {destaque ? <Selo tom="verde">em produção</Selo> : null}
      </div>
      <p className="mt-1 text-xs leading-relaxed text-tenue">{subtitulo}</p>

      <div className={`numero mt-5 text-4xl font-semibold tracking-tight ${cores.texto}`}>
        {pct(fonte.nivel_servico, 1)}
      </div>
      <div className="text-[0.7rem] uppercase tracking-wider text-tenue">
        atendidas em até 20 segundos
      </div>

      <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-painel2">
        <div
          className="h-full rounded-full"
          style={{ width: `${fonte.nivel_servico * 100}%`, background: cores.barra }}
        />
      </div>
      <div className="mt-1.5 text-[0.7rem] text-tenue">
        meta contratada: {pct(meta, 0)}
        {fonte.nivel_servico >= meta ? " · atingida" : " · não atingida"}
      </div>

      <dl className="mt-5 space-y-2 border-t border-borda pt-4 text-sm">
        <Linha rotulo="Espera média" valor={segundos(fonte.espera_s, 1)} />
        <Linha rotulo="Espera no P90" valor={segundos(fonte.espera_p90_s, 1)} />
        <Linha rotulo="Abandono" valor={pct(fonte.abandono, 1)} />
        <Linha rotulo="Atendentes-hora" valor={num(fonte.atendentes_hora)} />
        <Linha rotulo="Custo do dia" valor={reais(fonte.custo)} />
      </dl>
    </div>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-xs text-tenue">{rotulo}</dt>
      <dd className="numero text-sm text-texto">{valor}</dd>
    </div>
  );
}
