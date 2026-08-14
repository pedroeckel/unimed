"use client";

import { useMemo, useState } from "react";

import { Cartao, Leitura } from "@/componentes/ui";
import { num, pct } from "@/lib/formato";
import { dimensionarQuadro, quadroPara } from "@/lib/quadro";
import type { Operacao } from "@/lib/tipos";

const JORNADAS = [36, 40, 44];
const SHRINKAGES = [0.2, 0.25, 0.3, 0.35];
const TURNOS = [6, 8];

/**
 * A tradução do dimensionamento para a única pergunta que o RH faz: quantas
 * pessoas eu contrato? Os controles existem porque jornada e shrinkage são
 * política da casa, não saída de modelo — o gêmeo entrega a necessidade, o
 * gestor informa sob quais regras ela vai ser coberta.
 */
export function QuadroDePessoal({ dados }: { dados: Operacao }) {
  const dias = dados.proximos_dias;
  const padrao = dados.parametros;

  const [jornada, setJornada] = useState(padrao.jornada_semanal_h);
  const [turno, setTurno] = useState(padrao.turno_h);
  const [shrinkage, setShrinkage] = useState(padrao.shrinkage);

  const q = useMemo(
    () => dimensionarQuadro(dias, { jornadaSemanalH: jornada, turnoH: turno, shrinkage }),
    [dias, jornada, turno, shrinkage],
  );

  const grade = useMemo(
    () =>
      SHRINKAGES.map((s) => ({
        s,
        valores: JORNADAS.map((j) =>
          quadroPara(dias, { jornadaSemanalH: j, turnoH: turno, shrinkage: s }),
        ),
      })),
    [dias, turno],
  );

  const maisPesado = [...q.turnos].sort((a, b) => b.postos - a.postos)[0];
  const maisLeve = [...q.turnos].sort((a, b) => a.postos - b.postos)[0];

  const passos = [
    {
      valor: `${num(q.atendentesHora)} h`,
      rotulo: "atendentes-hora",
      nota: `a necessidade hora a hora · ${num(q.posicoesMedias, 1)} posições em média, 24/7`,
    },
    {
      valor: num(q.postosTurno),
      rotulo: "postos-turno",
      nota: `turno fechado de ${turno}h escalado pelo pico → ${num(q.horasPagas)} h pagas (${pct(q.folgaBloco, 0)} de folga do bloco)`,
    },
    {
      valor: num(q.quadroBruto, 1),
      rotulo: "pessoas, no papel",
      nota: `÷ ${num(q.turnosPorPessoa, 1)} turnos por pessoa (jornada de ${jornada}h) — mundo sem pausa nem falta`,
    },
    {
      valor: num(q.contratados),
      rotulo: "contratados",
      nota: `÷ ${num(1 - shrinkage, 2)} de tempo produtivo = ${num(q.quadro, 1)}, arredondado para cima`,
      destaque: true,
    },
  ];

  return (
    <Cartao
      titulo="De atendentes-hora para gente contratada"
      descricao="a escala pede gente em linha; o RH contrata jornada — a diferença entre os dois é turno fechado mais shrinkage"
    >
      {/* ── Política da casa ──────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end gap-x-8 gap-y-4 rounded-xl border border-borda bg-painel2/60 px-4 py-3">
        <Escolha
          rotulo="Jornada semanal"
          opcoes={JORNADAS.map((j) => ({ valor: j, texto: `${j}h` }))}
          atual={jornada}
          aoEscolher={setJornada}
        />
        <Escolha
          rotulo="Turno"
          opcoes={TURNOS.map((t) => ({ valor: t, texto: `${t}h` }))}
          atual={turno}
          aoEscolher={setTurno}
        />
        <div className="min-w-[200px] flex-1">
          <div className="flex items-baseline justify-between text-[0.72rem]">
            <span className="font-medium uppercase tracking-wider text-tenue">Shrinkage</span>
            <span className="numero text-texto">{pct(shrinkage, 0)}</span>
          </div>
          <input
            type="range"
            min={0.1}
            max={0.45}
            step={0.01}
            value={shrinkage}
            onChange={(e) => setShrinkage(Number(e.target.value))}
            className="mt-2 h-1 w-full cursor-pointer appearance-none rounded-full bg-borda accent-verde"
          />
          <div className="mt-1 flex justify-between text-[0.62rem] text-tenue">
            <span>10%</span>
            <span>pausa, férias, falta, treinamento</span>
            <span>45%</span>
          </div>
        </div>
      </div>

      {/* ── A conta, passo a passo ────────────────────────────────────────── */}
      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {passos.map((p, i) => (
          <div
            key={p.rotulo}
            className={`relative rounded-xl border px-4 py-3 ${
              p.destaque ? "border-verde/50 bg-verde/[0.07]" : "border-borda bg-painel2/50"
            }`}
          >
            {i > 0 ? (
              <span className="absolute -left-[9px] top-1/2 hidden -translate-y-1/2 text-borda2 xl:block">
                ›
              </span>
            ) : null}
            <div
              className={`numero text-xl font-semibold tracking-tight ${
                p.destaque ? "text-verde" : "text-texto"
              }`}
            >
              {p.valor}
            </div>
            <div className="mt-0.5 text-[0.72rem] font-medium uppercase tracking-wider text-tenue">
              {p.rotulo}
            </div>
            <p className="mt-1.5 text-[0.72rem] leading-snug text-suave">{p.nota}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_240px]">
        {/* ── Postos abertos por turno e por dia ─────────────────────────── */}
        <div>
          <h4 className="text-[0.78rem] font-semibold text-texto">Postos abertos, turno a turno</h4>
          <p className="mt-0.5 text-[0.72rem] text-tenue">
            cada turno é escalado pelo seu pico — é assim que a necessidade vira vaga
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="border-b border-borda text-[0.7rem] uppercase tracking-wider text-tenue">
                  <th className="pb-2 text-left font-medium">Turno</th>
                  {dias.map((d) => (
                    <th key={d.data} className="pb-2 text-right font-medium">
                      {d.dia_semana.slice(0, 3)}
                    </th>
                  ))}
                  <th className="pb-2 text-right font-medium">Semana</th>
                  <th className="pb-2 text-right font-medium">Pessoas</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borda/60">
                {q.turnos.map((t) => (
                  <tr key={t.nome}>
                    <td className="py-2 whitespace-nowrap text-suave">
                      {t.nome}{" "}
                      <span className="numero text-[0.7rem] text-tenue">
                        {String(t.de).padStart(2, "0")}–{String(t.ate + 1).padStart(2, "0")}h
                      </span>
                    </td>
                    {t.porDia.map((v, i) => (
                      <td key={dias[i].data} className="numero py-2 text-right text-texto">
                        {v}
                      </td>
                    ))}
                    <td className="numero py-2 text-right text-suave">{t.postos}</td>
                    <td className="numero py-2 text-right font-medium text-texto">
                      {num(t.pessoas, 1)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-borda2">
                  <td className="pt-2.5 font-medium text-suave">Total</td>
                  {q.dias.map((d) => (
                    <td key={d.data} className="numero pt-2.5 text-right text-texto">
                      {d.postos}
                    </td>
                  ))}
                  <td className="numero pt-2.5 text-right text-texto">{q.postosTurno}</td>
                  <td className="numero pt-2.5 text-right font-semibold text-verde">
                    {num(q.quadro, 1)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* ── Sensibilidade ───────────────────────────────────────────────── */}
        <div>
          <h4 className="text-[0.78rem] font-semibold text-texto">Se a política mudar</h4>
          <p className="mt-0.5 text-[0.72rem] text-tenue">quadro necessário, turno de {turno}h</p>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b border-borda text-[0.7rem] uppercase tracking-wider text-tenue">
                <th className="pb-2 text-left font-medium">Shrink.</th>
                {JORNADAS.map((j) => (
                  <th key={j} className="pb-2 text-right font-medium">
                    {j}h
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-borda/60">
              {grade.map((linha) => (
                <tr key={linha.s}>
                  <td className="numero py-2 text-tenue">{pct(linha.s, 0)}</td>
                  {linha.valores.map((v, i) => {
                    const atual =
                      JORNADAS[i] === jornada && Math.abs(linha.s - shrinkage) < 0.005;
                    return (
                      <td
                        key={JORNADAS[i]}
                        className={`numero py-2 text-right ${
                          atual ? "font-semibold text-verde" : "text-texto"
                        }`}
                      >
                        {Math.ceil(v)}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-[0.72rem] leading-relaxed text-tenue">
            36h é a jornada de teleatendimento (NR-17, anexo II). 44h aparece em retaguarda, onde
            não há atendimento telefônico contínuo.
          </p>
        </div>
      </div>

      <div className="mt-6">
        <Leitura>
          <strong className="text-texto">{num(q.contratados)} pessoas</strong> cobrem os{" "}
          {num(q.atendentesHora)} atendentes-hora da semana — não {num(q.atendentesHora / jornada, 1)},
          que é o que sai de dividir a necessidade pela jornada e é o erro clássico dessa conta. O
          que separa os dois números: turno fechado de {turno}h obriga a pagar {num(q.horasPagas)} h
          para entregar {num(q.atendentesHora)}, e só {pct(1 - shrinkage, 0)} do tempo contratado
          chega a ser atendimento. Dentro do quadro, {maisPesado.nome.toLowerCase()} pesa{" "}
          {num(maisPesado.pessoas, 1)} pessoas contra {num(maisLeve.pessoas, 1)} da{" "}
          {maisLeve.nome.toLowerCase()} — contratar em bloco único ignora essa diferença.
        </Leitura>
      </div>
    </Cartao>
  );
}

function Escolha<T extends number>({
  rotulo,
  opcoes,
  atual,
  aoEscolher,
}: {
  rotulo: string;
  opcoes: { valor: T; texto: string }[];
  atual: T;
  aoEscolher: (v: T) => void;
}) {
  return (
    <div>
      <div className="text-[0.72rem] font-medium uppercase tracking-wider text-tenue">{rotulo}</div>
      <div className="mt-2 flex gap-1.5">
        {opcoes.map((o) => (
          <button
            key={o.valor}
            onClick={() => aoEscolher(o.valor)}
            className={`numero rounded-lg border px-2.5 py-1 text-xs transition ${
              o.valor === atual
                ? "border-verde bg-verde/10 text-verde"
                : "border-borda bg-painel2 text-suave hover:border-borda2"
            }`}
          >
            {o.texto}
          </button>
        ))}
      </div>
    </div>
  );
}
