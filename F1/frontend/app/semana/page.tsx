import Link from "next/link";

import { BotaoExportar } from "@/componentes/BotaoExportar";
import { ProximaSemana } from "@/componentes/ProximaSemana";
import { QuadroDePessoal } from "@/componentes/QuadroDePessoal";
import { Bloco, CabecalhoPagina, Kpi } from "@/componentes/ui";
import { operacao } from "@/lib/dados";
import { num, pct, reais } from "@/lib/formato";
import { dimensionarQuadro } from "@/lib/quadro";

export const metadata = {
  title: "Escala da semana · Gêmeo Digital",
};

export default function PaginaSemana() {
  const dados = operacao;
  const dias = dados.proximos_dias;
  const totalChamadas = dias.reduce((a, d) => a + d.previsto, 0);
  const totalHoras = dias.reduce((a, d) => a + d.atendentes_hora, 0);
  const totalCusto = dias.reduce((a, d) => a + d.custo, 0);
  const maiorPico = Math.max(...dias.map((d) => d.pico_atendentes));
  const p = dados.parametros;
  const quadro = dimensionarQuadro(dias, {
    jornadaSemanalH: p.jornada_semanal_h,
    turnoH: p.turno_h,
    shrinkage: p.shrinkage,
  });

  return (
    <>
      <CabecalhoPagina
        trilha={["Central de Atendimento", "Operação", "Escala da semana"]}
        titulo="Escala da semana"
        descricao="Os sete dias seguintes já dimensionados pela previsão. É o que sustenta folga, férias e banco de horas — e o que o RH precisa saber com antecedência."
        acoes={
          <>
            <BotaoExportar dias={dias} />
            <Link
              href="/"
              className="rounded-lg border border-borda bg-painel px-3 py-2 text-xs text-suave transition hover:border-borda2 hover:text-texto"
            >
              ← Operação de hoje
            </Link>
          </>
        }
      />

      <div className="space-y-8 px-5 py-6 sm:px-7">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi valor={num(totalChamadas)} rotulo="Ligações previstas na semana" tom="azul" />
          <Kpi
            valor={`${num(quadro.contratados)} pessoas`}
            rotulo="Quadro necessário"
            nota={`${num(totalHoras)} atendentes-hora · jornada de ${num(p.jornada_semanal_h)}h · shrinkage de ${pct(p.shrinkage, 0)}`}
            tom="verde"
          />
          <Kpi valor={reais(totalCusto)} rotulo="Custo estimado de escala" tom="neutro" />
          <Kpi
            valor={`${maiorPico} pessoas`}
            rotulo="Maior pico simultâneo da semana"
            nota="o máximo em linha ao mesmo tempo, não o tamanho do time"
            tom="laranja"
          />
        </div>

        <Bloco titulo="Dia a dia" descricao="a escala é recalculada toda madrugada, com o volume do dia anterior">
          <ProximaSemana dados={dados} />
        </Bloco>

        <Bloco
          titulo="Quadro de pessoal"
          descricao="quantas pessoas contratar para sustentar essa escala — e sob quais regras de jornada"
        >
          <QuadroDePessoal dados={dados} />
        </Bloco>
      </div>
    </>
  );
}
