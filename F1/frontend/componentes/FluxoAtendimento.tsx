"use client";

import type { ReactNode } from "react";

import type { Ligacao, Situacao } from "@/lib/fluxo";

/**
 * O fluxo do atendimento, ligação por ligação.
 *
 * Cada pastilha na tela e uma ligação de verdade do dia: ela aparece no instante
 * em que chegou, entra na fila se não houver atendente livre, ocupa um posto
 * pelo tempo exato da conversa e sai como atendida — ou desiste no meio da
 * espera. Este componente não calcula nada: recebe pronto o retrato do instante
 * (`lib/fluxo.ts`), o mesmo que alimenta os cartões de indicadores.
 */
export function FluxoAtendimento({
  situacao,
  minuto,
  capacidadeAgora,
  capacidadeMaxima,
}: {
  situacao: Situacao;
  minuto: number;
  capacidadeAgora: number;
  capacidadeMaxima: number;
}) {
  const { chegando, naFila, emAtendimento, atendidas, desistencias } = situacao;
  const porPosto = new Map<number, Ligacao>();
  emAtendimento.forEach((l) => porPosto.set(l.posto, l));

  return (
    <div className="rounded-xl border border-borda bg-painel">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-borda px-5 py-3">
        <div>
          <h3 className="text-[0.88rem] font-semibold text-texto">Fluxo de atendimento</h3>
          <p className="mt-0.5 text-xs text-tenue">
            cada pastilha é uma ligação real deste dia — da chegada até o desfecho
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5 text-tenue">
            <span className="inline-block h-2 w-2 rounded-full bg-azul" /> chegando
          </span>
          <span className="flex items-center gap-1.5 text-tenue">
            <span className="inline-block h-2 w-2 rounded-full bg-laranja" /> na fila
          </span>
          <span className="flex items-center gap-1.5 text-tenue">
            <span className="inline-block h-2 w-2 rounded-full bg-verde" /> em atendimento
          </span>
        </div>
      </div>

      <div className="grid gap-3 p-4 lg:grid-cols-[minmax(0,0.8fr)_auto_minmax(0,1fr)_auto_minmax(0,1.7fr)_auto_minmax(0,0.75fr)]">
        {/* ── Chegando ──────────────────────────────────────────────────── */}
        <Coluna titulo="Chegando" contagem={chegando.length} unidade="agora">
          <div className="flex min-h-[92px] flex-wrap content-start gap-1.5">
            {chegando.length === 0 ? (
              <span className="text-[0.7rem] text-tenue">sem chamadas neste instante</span>
            ) : (
              chegando.slice(-10).map((l) => (
                <span
                  key={l.id}
                  className="entrar numero rounded-md border border-azul/40 bg-azul/10 px-1.5 py-1 text-[0.65rem] text-azul"
                >
                  ☎ #{l.id + 1}
                </span>
              ))
            )}
          </div>
        </Coluna>

        <Seta />

        {/* ── Fila ──────────────────────────────────────────────────────── */}
        <Coluna titulo="Fila de espera" contagem={naFila.length} unidade="aguardando">
          <div className="flex min-h-[92px] flex-wrap content-start gap-1.5">
            {naFila.length === 0 ? (
              <span className="text-[0.7rem] text-tenue">ninguém esperando</span>
            ) : (
              naFila.slice(0, 16).map((l) => {
                const esperaSeg = Math.max(0, (minuto - l.chegada) * 60);
                const cor =
                  esperaSeg > 60
                    ? "border-vermelho/50 bg-vermelho/10 text-vermelho"
                    : esperaSeg > 20
                      ? "border-laranja/50 bg-laranja/10 text-laranja"
                      : "border-borda2 bg-painel2 text-suave";
                return (
                  <span
                    key={l.id}
                    className={`entrar numero rounded-md border px-1.5 py-1 text-[0.65rem] ${cor}`}
                  >
                    #{l.id + 1} · {Math.round(esperaSeg)}s
                  </span>
                );
              })
            )}
          </div>
        </Coluna>

        <Seta />

        {/* ── Postos ────────────────────────────────────────────────────── */}
        <Coluna
          titulo="Em atendimento"
          contagem={emAtendimento.length}
          unidade={`de ${capacidadeAgora} em turno`}
        >
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {Array.from({ length: capacidadeMaxima }).map((_, i) => {
              const ligacao = porPosto.get(i);
              const foraDeTurno = i >= capacidadeAgora;

              if (!ligacao) {
                return (
                  <div
                    key={i}
                    className={`rounded-lg px-2 py-1.5 text-[0.62rem] ${
                      foraDeTurno
                        ? "border border-dashed border-borda text-tenue/60"
                        : "border border-borda bg-painel2/60 text-tenue"
                    }`}
                  >
                    posto {i + 1}
                    <div className="mt-0.5">{foraDeTurno ? "fora de turno" : "livre"}</div>
                  </div>
                );
              }

              const inicio = ligacao.inicio as number;
              const fim = ligacao.fim as number;
              const progresso = Math.min(1, Math.max(0, (minuto - inicio) / Math.max(fim - inicio, 0.01)));
              const decorridos = Math.max(0, (minuto - inicio) * 60);
              return (
                <div
                  key={i}
                  className="rounded-lg border border-verde/50 bg-verde/10 px-2 py-1.5 text-[0.62rem] text-verde"
                >
                  <div className="flex items-center justify-between gap-1">
                    <span>posto {i + 1}</span>
                    <span className="numero text-verde/80">
                      {Math.floor(decorridos / 60)}:
                      {String(Math.floor(decorridos % 60)).padStart(2, "0")}
                    </span>
                  </div>
                  <div className="numero mt-0.5 truncate">☎ #{ligacao.id + 1}</div>
                  <div className="mt-1 h-1 overflow-hidden rounded-full bg-verde/20">
                    <div
                      className="h-full rounded-full bg-verde"
                      style={{ width: `${progresso * 100}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Coluna>

        <Seta />

        {/* ── Saídas ────────────────────────────────────────────────────── */}
        <Coluna titulo="Desfecho" contagem={atendidas + desistencias} unidade="no dia">
          <div className="space-y-2">
            <div className="flex items-center justify-between rounded-lg border border-borda bg-painel2/60 px-3 py-2">
              <span className="text-[0.68rem] text-tenue">✓ atendidas</span>
              <span key={atendidas} className="numero surgir text-lg font-semibold text-verde">
                {atendidas}
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-borda bg-painel2/60 px-3 py-2">
              <span className="text-[0.68rem] text-tenue">✕ desistiram</span>
              <span key={desistencias} className="numero surgir text-lg font-semibold text-vermelho">
                {desistencias}
              </span>
            </div>
          </div>
        </Coluna>
      </div>
    </div>
  );
}

function Coluna({
  titulo,
  contagem,
  unidade,
  children,
}: {
  titulo: string;
  contagem: number;
  unidade: string;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0">
      <div className="mb-2 flex items-baseline gap-2">
        <span className="text-[0.68rem] font-semibold uppercase tracking-wider text-tenue">
          {titulo}
        </span>
        <span className="numero text-xs text-suave">{contagem}</span>
        <span className="text-[0.62rem] text-tenue">{unidade}</span>
      </div>
      {children}
    </div>
  );
}

/** A seta entre as etapas, com o tracejado correndo: é o que dá a sensação de fluxo. */
function Seta() {
  return (
    <div className="hidden items-center justify-center lg:flex">
      <svg width="26" height="12" viewBox="0 0 26 12" aria-hidden>
        <line
          x1="0"
          y1="6"
          x2="19"
          y2="6"
          stroke="#2f3846"
          strokeWidth="1.5"
          strokeDasharray="4 4"
          className="fluxo"
        />
        <path d="M19 2.5 L25 6 L19 9.5 Z" fill="#2f3846" />
      </svg>
    </div>
  );
}
