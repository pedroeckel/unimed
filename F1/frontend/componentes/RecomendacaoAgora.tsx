import { prescreverEscala } from "@/lib/erlang";
import { num, pct, reais } from "@/lib/formato";
import type { DiaOperacao, Parametros } from "@/lib/tipos";

const TURNOS = [
  { nome: "Madrugada", de: 0, ate: 5 },
  { nome: "Manhã", de: 6, ate: 11 },
  { nome: "Tarde", de: 12, ate: 17 },
  { nome: "Noite", de: 18, ate: 23 },
];

/**
 * A pergunta que o supervisor faz no meio do dia: "está vindo mais gente do que
 * o previsto — e daí, o que eu faço nas próximas horas?".
 *
 * Tudo aqui é calculado com o que já se sabe NESTE instante: o desvio das horas
 * já fechadas é projetado sobre a previsão que resta, e a equipe necessária sai
 * do mesmo Erlang C que fecha a escala na véspera. Nada olha o resto do dia.
 */
export function RecomendacaoAgora({
  dia,
  parametros,
  hora,
  recebidas,
  desvioRecente,
}: {
  dia: DiaOperacao;
  parametros: Parametros;
  hora: number;
  recebidas: number;
  desvioRecente: number;
}) {
  const restantes = [];
  for (let h = hora + 1; h <= 23; h += 1) restantes.push(h);

  const previstoRestante = restantes.reduce((a, h) => a + dia.previsto[h], 0);
  const projecao = Math.round(recebidas + previstoRestante * (1 + desvioRecente));
  const desvioProjetado = projecao / dia.total_previsto - 1;

  /** Se o ritmo das últimas horas continuar, é esta a demanda que vem — e esta a
   *  equipe que ela pede, hora a hora. */
  const demandaProjetada = restantes.map((h) => dia.previsto[h] * (1 + desvioRecente));
  const escalaRecomendada = prescreverEscala(
    demandaProjetada,
    parametros.tma_min,
    parametros.meta_nivel_servico,
    parametros.nivel_servico_seg,
  );
  const faltas = restantes
    .map((h, i) => ({ hora: h, falta: Math.max(0, escalaRecomendada[i] - dia.escala[h]) }))
    .filter((x) => x.falta > 0);
  const atendentesHoraExtra = faltas.reduce((a, x) => a + x.falta, 0);
  const custoExtra = atendentesHoraExtra * parametros.custo_atendente_hora;
  const maiorFalta = faltas.reduce(
    (melhor, x) => (x.falta > melhor.falta ? x : melhor),
    { hora: -1, falta: 0 },
  );

  const porTurno = TURNOS.map((t) => ({
    ...t,
    falta: faltas.filter((f) => f.hora >= t.de && f.hora <= t.ate).reduce((a, f) => a + f.falta, 0),
    pico: Math.max(0, ...faltas.filter((f) => f.hora >= t.de && f.hora <= t.ate).map((f) => f.falta)),
  })).filter((t) => t.falta > 0);

  const fimDoDia = restantes.length === 0;

  return (
    <div className="cartao grid gap-0 overflow-hidden rounded-xl border border-borda bg-painel lg:grid-cols-[1fr_1.25fr]">
      {/* ── Projeção de fechamento ────────────────────────────────────────── */}
      <div className="border-b border-borda p-5 lg:border-b-0 lg:border-r">
        <h3 className="text-[0.88rem] font-semibold text-texto">Como o dia deve fechar</h3>
        <p className="mt-0.5 text-xs text-tenue">
          {fimDoDia
            ? "o dia terminou"
            : "no ritmo das últimas horas, projetado sobre a previsão que falta"}
        </p>

        <div className="mt-4 flex items-end gap-5">
          <div>
            <div className="numero text-3xl font-semibold tracking-tight text-texto">
              {num(projecao)}
            </div>
            <div className="text-[0.68rem] uppercase tracking-wider text-tenue">
              ligações projetadas
            </div>
          </div>
          <div
            className={`mb-1 rounded-md px-2 py-1 text-xs font-medium ${
              desvioProjetado > 0.05
                ? "bg-vermelho/10 text-vermelho"
                : desvioProjetado < -0.05
                  ? "bg-azul/10 text-azul"
                  : "bg-verde/10 text-verde"
            }`}
          >
            {desvioProjetado > 0 ? "+" : ""}
            {pct(desvioProjetado, 0)} sobre o previsto
          </div>
        </div>

        <dl className="mt-4 space-y-1.5 border-t border-borda pt-3 text-xs">
          <div className="flex justify-between">
            <dt className="text-tenue">Previsto na véspera</dt>
            <dd className="numero text-suave">{num(dia.total_previsto)} ligações</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-tenue">Faixa provável do dia</dt>
            <dd className="numero text-suave">
              {num(dia.faixa_lo)} – {num(dia.faixa_hi)}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-tenue">Recebidas até agora</dt>
            <dd className="numero text-suave">{num(recebidas)}</dd>
          </div>
        </dl>
      </div>

      {/* ── O que fazer ───────────────────────────────────────────────────── */}
      <div className="p-5">
        <h3 className="text-[0.88rem] font-semibold text-texto">O que fazer nas próximas horas</h3>
        <p className="mt-0.5 text-xs text-tenue">
          escala publicada × equipe que o ritmo atual pede
        </p>

        {fimDoDia || atendentesHoraExtra === 0 ? (
          <p className="mt-4 rounded-lg border-l-2 border-verde bg-verde/[0.06] px-3.5 py-3 text-[0.85rem] leading-relaxed text-suave">
            {fimDoDia
              ? "O dia acabou. O fechamento entra na base de amanhã e a próxima previsão já sai com ele."
              : "A escala publicada cobre o resto do dia no ritmo atual. Nenhuma ação necessária."}
          </p>
        ) : (
          <>
            <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-3">
              <div>
                <div className="numero text-2xl font-semibold text-laranja">
                  +{num(atendentesHoraExtra)}
                </div>
                <div className="text-[0.68rem] uppercase tracking-wider text-tenue">
                  atendentes-hora a mais
                </div>
              </div>
              <div>
                <div className="numero text-2xl font-semibold text-texto">
                  +{maiorFalta.falta}
                </div>
                <div className="text-[0.68rem] uppercase tracking-wider text-tenue">
                  no pico, às {String(maiorFalta.hora).padStart(2, "0")}h
                </div>
              </div>
              <div>
                <div className="numero text-2xl font-semibold text-texto">{reais(custoExtra)}</div>
                <div className="text-[0.68rem] uppercase tracking-wider text-tenue">
                  custo do reforço
                </div>
              </div>
            </div>

            <div className="mt-4 space-y-1.5">
              {porTurno.map((t) => (
                <div
                  key={t.nome}
                  className="flex items-center justify-between rounded-lg border border-borda bg-painel2 px-3 py-2 text-xs"
                >
                  <span className="text-suave">
                    Turno da {t.nome.toLowerCase()}{" "}
                    <span className="text-tenue">
                      ({String(t.de).padStart(2, "0")}h–{String(t.ate).padStart(2, "0")}h)
                    </span>
                  </span>
                  <span className="numero text-laranja">
                    +{t.pico} pessoa{t.pico > 1 ? "s" : ""} no pico · +{t.falta} atendentes-hora
                  </span>
                </div>
              ))}
            </div>

            <p className="mt-3 text-[0.78rem] leading-relaxed text-tenue">
              Mobilizar leva tempo: hora extra, remanejamento do time de retenção ou acionamento do
              parceiro. Por isso a decisão é agora, e não quando a fila aparecer.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
