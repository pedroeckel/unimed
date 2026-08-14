"use client";

import { useMemo, useState } from "react";

import { Fronteira, GraficoCenario } from "@/componentes/graficos";
import { Cartao, Legenda } from "@/componentes/ui";
import { prescreverEscala } from "@/lib/erlang";
import { num, pct, reais, segundos } from "@/lib/formato";
import { rodarReplicacoes } from "@/lib/gemeo";
import type { Operacao } from "@/lib/tipos";

const TURNOS = [
  { chave: "madrugada", nome: "Madrugada", de: 0, ate: 5 },
  { chave: "manha", nome: "Manhã", de: 6, ate: 11 },
  { chave: "tarde", nome: "Tarde", de: 12, ate: 17 },
  { chave: "noite", nome: "Noite", de: 18, ate: 23 },
] as const;

type Ajustes = Record<(typeof TURNOS)[number]["chave"], number>;

const SEM_AJUSTE: Ajustes = { madrugada: 0, manha: 0, tarde: 0, noite: 0 };

/**
 * O simulador de cenários: o gêmeo digital rodando ao vivo no navegador.
 *
 * O gestor mexe na demanda e na equipe; a cada mudança a central é simulada de
 * novo — chegadas de Poisson, fila com abandono, atendimento lognormal — e os
 * indicadores respondem. É o mesmo motor de `nucleo/gemeo.py`, conferido contra
 * ele em três níveis de escala.
 */
export function Simulador({ dados }: { dados: Operacao }) {
  const { dia, parametros, cenarios } = dados;

  const [fator, setFator] = useState(1);
  const [ajustes, setAjustes] = useState<Ajustes>(SEM_AJUSTE);
  const [tma, setTma] = useState(parametros.tma_min);
  const [paciencia, setPaciencia] = useState(parametros.paciencia_min);
  const [meta, setMeta] = useState(parametros.meta_nivel_servico);

  const ajusteDaHora = (h: number) =>
    ajustes[(TURNOS.find((t) => h >= t.de && h <= t.ate) ?? TURNOS[0]).chave];

  /** O que depende só do cenário (demanda e parâmetros): dimensionamento
   *  sugerido, a curva custo × serviço e o resultado de não mexer em nada.
   *  Fica separado para que arrastar os controles de equipe não refaça as 28
   *  simulações da curva. */
  const base = useMemo(() => {
    const demanda = dia.previsto.map((v) => v * fator);
    const sugerida = prescreverEscala(demanda, tma, meta, parametros.nivel_servico_seg);
    const semMexer = rodarReplicacoes(demanda, dia.escala, tma, paciencia, 6);
    const fronteira = [-3, -2, -1, 0, 1, 2, 3].map((delta) => {
      const variante = sugerida.map((v) => Math.max(1, v + delta));
      const r = rodarReplicacoes(demanda, variante, tma, paciencia, 4);
      const horas = variante.reduce((a, b) => a + b, 0);
      return {
        ajuste: delta === 0 ? "sugerida" : `${delta > 0 ? "+" : ""}${delta}`,
        delta,
        atendentes_hora: horas,
        custo: horas * parametros.custo_atendente_hora,
        nivel_servico: r.nivelServico,
        espera_s: r.esperaMediaSeg,
        abandono: r.abandono,
      };
    });
    return {
      demanda,
      sugerida,
      semMexer,
      fronteira,
      totalChamadas: Math.round(demanda.reduce((a, b) => a + b, 0)),
    };
  }, [dia, parametros, fator, tma, paciencia, meta]);

  /** O que muda a cada toque nos controles de equipe. */
  const simulacao = useMemo(() => {
    const escala = base.sugerida.map((v, h) => Math.max(1, v + ajusteDaHora(h)));
    const cenario = rodarReplicacoes(base.demanda, escala, tma, paciencia, 6);
    const horas = escala.reduce((a, b) => a + b, 0);
    const horasPublicadas = dia.escala.reduce((a, b) => a + b, 0);
    return {
      ...base,
      escala,
      cenario,
      horas,
      custo: horas * parametros.custo_atendente_hora,
      horasPublicadas,
      custoPublicado: horasPublicadas * parametros.custo_atendente_hora,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base, ajustes, tma, paciencia, dia, parametros]);

  const { cenario, semMexer } = simulacao;
  const bateuMeta = cenario.nivelServico >= meta;
  const deltaCusto = simulacao.custo - simulacao.custoPublicado;
  const deltaSl = (cenario.nivelServico - semMexer.nivelServico) * 100;

  return (
    <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
      {/* ── Controles ────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <Cartao titulo="Demanda" descricao="quanto volume chega no dia simulado">
          <div className="grid grid-cols-2 gap-1.5">
            {cenarios.map((c) => (
              <button
                key={c.nome}
                onClick={() => setFator(c.fator)}
                className={`rounded-lg border px-2 py-1.5 text-left text-[0.7rem] leading-tight transition ${
                  Math.abs(fator - c.fator) < 0.001
                    ? "border-verde bg-verde/10 text-verde"
                    : "border-borda bg-painel2 text-suave hover:border-borda2"
                }`}
              >
                {c.nome}
                <span className="mt-0.5 block text-[0.62rem] text-tenue">×{num(c.fator, 2)}</span>
              </button>
            ))}
          </div>

          <div className="mt-4">
            <div className="flex items-baseline justify-between text-xs">
              <span className="text-tenue">Volume do dia</span>
              <span className="numero text-texto">
                {num(simulacao.totalChamadas)} ligações · ×{num(fator, 2)}
              </span>
            </div>
            <input
              type="range"
              min={0.4}
              max={2}
              step={0.05}
              value={fator}
              onChange={(e) => setFator(Number(e.target.value))}
              className="mt-2 h-1 w-full cursor-pointer appearance-none rounded-full bg-borda accent-verde"
            />
            <div className="mt-1 flex justify-between text-[0.62rem] text-tenue">
              <span>metade</span>
              <span>previsto ({num(dia.total_previsto)})</span>
              <span>dobro</span>
            </div>
          </div>
        </Cartao>

        <Cartao
          titulo="Equipe por turno"
          descricao="quantas pessoas a mais (ou a menos) que o dimensionamento sugerido"
        >
          <div className="space-y-3">
            {TURNOS.map((t) => {
              const valor = ajustes[t.chave];
              const base = simulacao.sugerida
                .slice(t.de, t.ate + 1)
                .reduce((a, b) => Math.max(a, b), 0);
              return (
                <div key={t.chave}>
                  <div className="flex items-baseline justify-between text-xs">
                    <span className="text-suave">{t.nome}</span>
                    <span className="numero text-tenue">
                      pico {Math.max(1, base + valor)}
                      {valor !== 0 ? (
                        <span className={valor > 0 ? "text-laranja" : "text-azul"}>
                          {" "}
                          ({valor > 0 ? "+" : ""}
                          {valor})
                        </span>
                      ) : null}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={-3}
                    max={5}
                    step={1}
                    value={valor}
                    onChange={(e) =>
                      setAjustes((a) => ({ ...a, [t.chave]: Number(e.target.value) }))
                    }
                    className="mt-1.5 h-1 w-full cursor-pointer appearance-none rounded-full bg-borda accent-laranja"
                  />
                </div>
              );
            })}
          </div>
          <button
            onClick={() => setAjustes(SEM_AJUSTE)}
            className="mt-4 w-full rounded-lg border border-borda bg-painel2 px-3 py-1.5 text-xs text-suave transition hover:text-texto"
          >
            Voltar ao dimensionamento sugerido
          </button>
        </Cartao>

        <Cartao titulo="Parâmetros da operação">
          <Controle
            rotulo="Tempo médio de atendimento"
            valor={`${num(tma, 1)} min`}
            min={2}
            max={10}
            step={0.5}
            atual={tma}
            aoMudar={setTma}
          />
          <Controle
            rotulo="Paciência do beneficiário"
            valor={`${num(paciencia, 1)} min`}
            min={0.5}
            max={10}
            step={0.5}
            atual={paciencia}
            aoMudar={setPaciencia}
          />
          <Controle
            rotulo="Meta de nível de serviço"
            valor={pct(meta, 0)}
            min={0.5}
            max={0.95}
            step={0.05}
            atual={meta}
            aoMudar={setMeta}
          />
        </Cartao>
      </div>

      {/* ── Resultado ────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
          <Resultado
            rotulo="Nível de serviço"
            valor={pct(cenario.nivelServico, 1)}
            tom={bateuMeta ? "verde" : "vermelho"}
            nota={`meta ${pct(meta, 0)}`}
          />
          <Resultado
            rotulo="Espera média"
            valor={segundos(cenario.esperaMediaSeg, 1)}
            tom="neutro"
            nota={`P90 ${segundos(cenario.esperaP90Seg, 0)}`}
          />
          <Resultado
            rotulo="Abandono"
            valor={pct(cenario.abandono, 1)}
            tom={cenario.abandono > 0.05 ? "vermelho" : "verde"}
            nota={`${num(cenario.abandonos)} ligações perdidas`}
          />
          <Resultado
            rotulo="Atendentes-hora"
            valor={num(simulacao.horas)}
            tom="neutro"
            nota={`publicado hoje: ${num(simulacao.horasPublicadas)}`}
          />
          <Resultado
            rotulo="Custo do dia"
            valor={reais(simulacao.custo)}
            tom="neutro"
            nota={`${deltaCusto >= 0 ? "+" : ""}${reais(deltaCusto)} vs. publicado`}
          />
          <Resultado
            rotulo="Chamadas simuladas"
            valor={num(cenario.chamadas)}
            tom="neutro"
            nota="média de 6 replicações"
          />
        </div>

        <div className="rounded-xl border-l-2 border-verde bg-verde/[0.06] px-4 py-3.5 text-[0.88rem] leading-relaxed text-suave">
          Com <strong className="text-texto">{num(simulacao.totalChamadas)} ligações</strong> no dia
          e a equipe deste cenário, a central fecha com{" "}
          <strong className="text-texto">{pct(cenario.nivelServico, 1)}</strong> de nível de serviço
          e {pct(cenario.abandono, 1)} de abandono, a {reais(simulacao.custo)}.{" "}
          {Math.abs(deltaSl) < 0.5 ? (
            <>Mantendo a escala publicada de hoje o resultado seria praticamente o mesmo.</>
          ) : (
            <>
              Mantendo a escala publicada de hoje, o nível de serviço seria{" "}
              <strong className="text-texto">{pct(semMexer.nivelServico, 1)}</strong> —{" "}
              {deltaSl > 0 ? "uma perda de " : "uma folga de "}
              {num(Math.abs(deltaSl), 1)} pontos.
            </>
          )}
        </div>

        <Cartao
          titulo="Demanda e equipe, hora a hora"
          descricao="a escala sugerida já acompanha a curva do cenário; os controles mexem em cima dela"
        >
          <GraficoCenario
            demanda={simulacao.demanda}
            escala={simulacao.escala}
            escalaPublicada={dia.escala}
          />
          <div className="mt-3">
            <Legenda
              itens={[
                { cor: "#004e4c", texto: "ligações do cenário" },
                { cor: "#f47920", texto: "equipe simulada" },
                { cor: "#7d8b84", texto: "escala publicada hoje", tracejada: true },
              ]}
            />
          </div>
        </Cartao>

        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <Cartao
            titulo="Quanto serviço cada real compra"
            descricao="a mesma demanda, variando a equipe de −3 a +3 pessoas por hora"
          >
            <Fronteira pontos={simulacao.fronteira} meta={meta} altura={260} />
          </Cartao>

          <Cartao titulo="Leitura da curva">
            <div className="space-y-2">
              {simulacao.fronteira.map((p) => (
                <div
                  key={p.ajuste}
                  className={`flex items-center justify-between rounded-lg border px-3 py-2 text-xs ${
                    p.delta === 0 ? "border-verde/40 bg-verde/[0.06]" : "border-borda bg-painel2"
                  }`}
                >
                  <span className="numero w-16 text-suave">{p.ajuste}</span>
                  <span className="numero w-16 text-right text-texto">
                    {pct(p.nivel_servico, 0)}
                  </span>
                  <span className="numero w-24 text-right text-suave">{reais(p.custo)}</span>
                  <span className="numero w-20 text-right text-tenue">
                    {segundos(p.espera_s, 0)}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[0.78rem] leading-relaxed text-tenue">
              A curva é côncava: os primeiros atendentes compram muitos pontos de serviço; depois de
              um ponto, cada real adicional compra quase nada. A decisão não é técnica — é escolher
              a posição na curva.
            </p>
          </Cartao>
        </div>
      </div>
    </div>
  );
}

function Controle({
  rotulo,
  valor,
  min,
  max,
  step,
  atual,
  aoMudar,
}: {
  rotulo: string;
  valor: string;
  min: number;
  max: number;
  step: number;
  atual: number;
  aoMudar: (v: number) => void;
}) {
  return (
    <div className="mb-3 last:mb-0">
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-suave">{rotulo}</span>
        <span className="numero text-texto">{valor}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={atual}
        onChange={(e) => aoMudar(Number(e.target.value))}
        className="mt-1.5 h-1 w-full cursor-pointer appearance-none rounded-full bg-borda accent-verde"
      />
    </div>
  );
}

function Resultado({
  rotulo,
  valor,
  nota,
  tom,
}: {
  rotulo: string;
  valor: string;
  nota?: string;
  tom: "verde" | "vermelho" | "neutro";
}) {
  const cores = { verde: "text-verde", vermelho: "text-vermelho", neutro: "text-texto" };
  return (
    <div className="cartao rounded-xl border border-borda bg-painel px-4 py-3">
      <div className="text-[0.68rem] font-medium uppercase tracking-wider text-tenue">{rotulo}</div>
      <div className={`numero mt-1 text-2xl font-semibold tracking-tight ${cores[tom]}`}>
        {valor}
      </div>
      {nota ? <div className="mt-0.5 text-[0.7rem] text-tenue">{nota}</div> : null}
    </div>
  );
}
