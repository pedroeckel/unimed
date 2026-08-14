import { Selo } from "@/componentes/ui";
import { dataLonga, num, pct, reais } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

export function Hero({ dados }: { dados: Operacao }) {
  const { campo, campeao, dia, resultado_dia, mes, parametros } = dados;
  const economiaMes = mes.resumo.estatico_custo - mes.resumo.modelo_custo;
  const modelo = dados.comparacao_fontes[1];
  const estatico = dados.comparacao_fontes[0];

  return (
    <section id="topo" className="relative overflow-hidden">
      <div className="px-5 pb-8 pt-8 sm:px-7">
        <div className="flex flex-wrap items-center gap-2">
          <Selo tom="verde">Módulo F1 · Previsão de demanda em planos de saúde</Selo>
          <Selo tom="neutro">UNIMED SP</Selo>
          <Selo tom="azul">gêmeo digital · SimPy + Erlang C</Selo>
        </div>

        <h2 className="mt-5 max-w-3xl text-2xl font-semibold leading-tight tracking-tight text-texto">
          Um dia inteiro de operação,
          <span className="text-verde"> do dado bruto até a escala do turno</span>
        </h2>

        <p className="mt-3 max-w-3xl text-[0.95rem] leading-relaxed text-suave">
          Esta é a central de atendimento de uma operadora de saúde vista de cima: a demanda
          prevista com {parametros.n_dias_base} dias de histórico, a escala dimensionada por essa
          previsão e o dia acontecendo — ligação a ligação, minuto a minuto — dentro de um gêmeo
          digital. A pergunta que a tela responde não é <em>&ldquo;qual foi o erro do modelo?&rdquo;</em>,
          é <em>&ldquo;o que muda na operação?&rdquo;</em>
        </p>

        <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <CartaoHero
            valor={num(campeao.mae, 1)}
            unidade="ligações/dia"
            rotulo="Erro do modelo campeão"
            detalhe={`${campeao.nome} · ${pct(campeao.aproveitado / 100, 0)} de tudo o que era possível capturar`}
            tom="verde"
          />
          <CartaoHero
            valor={pct(modelo.nivel_servico, 1)}
            unidade=""
            rotulo="Nível de serviço no dia crítico"
            detalhe={`contra ${pct(estatico.nivel_servico, 1)} se a escala fosse feita pela média histórica`}
            tom="azul"
          />
          <CartaoHero
            valor={`−${num((estatico.abandono - modelo.abandono) * 100, 1)}`}
            unidade="pontos"
            rotulo="Abandono no dia crítico"
            detalhe={`${pct(modelo.abandono, 1)} contra ${pct(estatico.abandono, 1)} — gente que desliga antes de ser atendida`}
            tom="laranja"
          />
          <CartaoHero
            valor={reais(economiaMes)}
            unidade={`em ${mes.resumo.dias_simulados} dias`}
            rotulo="Custo de escala poupado"
            detalhe={`${num(mes.resumo.estatico_atendentes_hora - mes.resumo.modelo_atendentes_hora)} atendentes-hora a menos, com nível de serviço equivalente (${pct(mes.resumo.modelo_sl, 1)} × ${pct(mes.resumo.estatico_sl, 1)})`}
            tom="roxo"
          />
        </div>

        <p className="mt-6 max-w-3xl text-xs leading-relaxed text-tenue">
          O dia reproduzido é <strong className="text-suave">{dataLonga(dia.data)}</strong>, escolhido
          por ser o pior do período: aquele em que dimensionar pela média histórica mais se afasta da
          realidade. Chegaram {num(dia.total_real)} ligações. O gêmeo rodou{" "}
          {parametros.replicacoes} replicações independentes e fechou o dia com{" "}
          {num(resultado_dia.espera_media_s, 1)}s de espera média (±{" "}
          {num(resultado_dia.espera_media_ic_s, 1)}s, IC 95%). Toda a base é sintética, com semente
          fixa — foi assim que o piso teórico de {num(campo.mae_piso, 1)} ligações/dia pôde ser
          calculado exatamente.
        </p>
      </div>
    </section>
  );
}

function CartaoHero({
  valor,
  unidade,
  rotulo,
  detalhe,
  tom,
}: {
  valor: string;
  unidade: string;
  rotulo: string;
  detalhe: string;
  tom: "verde" | "azul" | "laranja" | "roxo";
}) {
  const cores = {
    verde: "text-verde",
    azul: "text-azul",
    laranja: "text-laranja",
    roxo: "text-roxo",
  };
  return (
    <div className="rounded-2xl border border-borda bg-painel/70 p-5">
      <div className="text-[0.7rem] font-medium uppercase tracking-wider text-tenue">{rotulo}</div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className={`numero text-3xl font-semibold tracking-tight ${cores[tom]}`}>{valor}</span>
        {unidade ? <span className="text-xs text-tenue">{unidade}</span> : null}
      </div>
      <p className="mt-2 text-xs leading-relaxed text-suave">{detalhe}</p>
    </div>
  );
}
