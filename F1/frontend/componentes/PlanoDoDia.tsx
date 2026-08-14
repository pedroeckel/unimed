import { Cartao } from "@/componentes/ui";
import { num, pct, reais } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

/**
 * O que o sistema já decidiu para hoje, em linguagem de escala: quanta gente em
 * cada turno, quanto custa e em que horas a operação fica no limite.
 */
export function PlanoDoDia({ dados }: { dados: Operacao }) {
  const { turnos, dia, parametros } = dados;
  const totalHoras = dia.escala.reduce((a, b) => a + b, 0);
  const custoTotal = totalHoras * parametros.custo_atendente_hora;
  const horasApertadas = dia.ocupacao
    .map((o, h) => ({ hora: h, ocupacao: o, atendentes: dia.escala[h], chamadas: dia.previsto[h] }))
    .filter((x) => x.ocupacao >= 0.82)
    .sort((a, b) => b.ocupacao - a.ocupacao);

  const maiorTurno = [...turnos].sort((a, b) => b.pico - a.pico)[0];

  return (
    <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
      <Cartao
        titulo="A escala publicada para hoje"
        descricao={`${num(totalHoras)} atendentes-hora · ${reais(custoTotal)} no dia`}
      >
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {turnos.map((t) => (
            <div key={t.turno} className="rounded-xl border border-borda bg-painel2/60 p-4">
              <div className="text-xs font-medium text-suave">{t.turno.split(" (")[0]}</div>
              <div className="text-[0.68rem] text-tenue">{t.horas}</div>
              <div className="numero mt-3 text-2xl font-semibold text-texto">{t.pico}</div>
              <div className="text-[0.68rem] uppercase tracking-wider text-tenue">
                atendentes no pico
              </div>
              <div className="mt-3 flex items-baseline justify-between border-t border-borda pt-2 text-[0.72rem]">
                <span className="text-tenue">média</span>
                <span className="numero text-suave">{num(t.media, 1)}</span>
              </div>
              <div className="flex items-baseline justify-between text-[0.72rem]">
                <span className="text-tenue">custo</span>
                <span className="numero text-suave">{reais(t.custo)}</span>
              </div>
            </div>
          ))}
        </div>

        <p className="mt-4 text-[0.85rem] leading-relaxed text-suave">
          A escala não é uma tabela fixa: ela acompanha a curva do dia. O turno mais pesado é o da{" "}
          <strong className="text-texto">{maiorTurno.turno.split(" (")[0].toLowerCase()}</strong>, com{" "}
          {maiorTurno.pico} pessoas no pico, e a madrugada opera com o mínimo. É essa diferença que
          separa dimensionar por hora de dimensionar &ldquo;pela média&rdquo; — a média sobra de
          madrugada e falta às 10h.
        </p>
      </Cartao>

      <Cartao
        titulo="Horas de atenção"
        descricao="onde a equipe fica perto do limite e qualquer imprevisto vira fila"
      >
        {horasApertadas.length === 0 ? (
          <p className="text-sm text-suave">
            Nenhuma hora do dia passa de 82% de ocupação. A escala tem folga para absorver
            imprevistos.
          </p>
        ) : (
          <div className="space-y-2">
            {horasApertadas.slice(0, 6).map((x) => (
              <div
                key={x.hora}
                className="flex items-center gap-3 rounded-lg border border-borda bg-painel2/50 px-3 py-2"
              >
                <span className="numero w-12 shrink-0 text-sm text-texto">
                  {String(x.hora).padStart(2, "0")}h
                </span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-borda">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(x.ocupacao, 1) * 100}%`,
                      background: x.ocupacao >= 0.85 ? "#ed1651" : "#f47920",
                    }}
                  />
                </div>
                <span className="numero w-12 shrink-0 text-right text-xs text-suave">
                  {pct(x.ocupacao, 0)}
                </span>
                <span className="w-24 shrink-0 text-right text-[0.7rem] text-tenue">
                  {num(x.chamadas)} lig. · {x.atendentes} pes.
                </span>
              </div>
            ))}
          </div>
        )}
        <p className="mt-4 text-[0.8rem] leading-relaxed text-tenue">
          Acima de 85% de ocupação a fila deixa de crescer devagar e passa a explodir. É o momento de
          acionar contingência — <strong className="text-suave">antes</strong> de a fila aparecer,
          porque depois já é tarde.
        </p>
      </Cartao>
    </div>
  );
}
