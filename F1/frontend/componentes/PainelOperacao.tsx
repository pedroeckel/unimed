"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { FluxoAtendimento } from "@/componentes/FluxoAtendimento";
import { RecomendacaoAgora } from "@/componentes/RecomendacaoAgora";
import { GraficoFila, GraficoOperacaoDia } from "@/componentes/graficos";
import { Cartao, Legenda } from "@/componentes/ui";
import { turnoDaHora } from "@/lib/dados";
import { prepararLigacoes, situacaoEm } from "@/lib/fluxo";
import { num, pct, relogio, segundos } from "@/lib/formato";
import type { AoVivo, DiaOperacao, Parametros } from "@/lib/tipos";

/** Velocidades em minutos simulados por segundo de relógio real. */
const VELOCIDADES = [
  { rotulo: "1 min/s", valor: 1, dica: "acompanha ligação por ligação (dia em 24 min)" },
  { rotulo: "4 min/s", valor: 4, dica: "dia inteiro em 6 minutos" },
  { rotulo: "15 min/s", valor: 15, dica: "dia inteiro em 1min36" },
  { rotulo: "1 h/s", valor: 60, dica: "dia inteiro em 24 segundos" },
];

const MINUTOS_DIA = 1440;
const FIM = MINUTOS_DIA - 0.001;

/**
 * O painel da operação.
 *
 * Nada e simulado no navegador: a tela caminha sobre o registro do dia gravado
 * pelo sistema — o traço minuto a minuto da central e a lista de todas as
 * ligações, com a hora em que cada uma chegou, foi atendida e terminou.
 */
export function PainelOperacao({
  dia,
  aoVivo,
  parametros,
}: {
  dia: DiaOperacao;
  aoVivo: AoVivo;
  parametros: Parametros;
}) {
  /** `agora` é o instante da operação; `vendo` é o instante que a tela mostra.
   *  Os dois só se separam quando o gestor volta no dia para rever — e nunca é
   *  possível passar de `agora`: o painel é histórico + projeção, não bola de
   *  cristal. */
  const [agora, setAgora] = useState(0);
  const [vendo, setVendo] = useState(0);
  const [seguindo, setSeguindo] = useState(true);
  const [rodando, setRodando] = useState(false);
  const [velocidade, setVelocidade] = useState(15);
  const [iniciou, setIniciou] = useState(false);
  const agoraRef = useRef(0);
  const seguindoRef = useRef(true);
  const raiz = useRef<HTMLDivElement>(null);

  const acompanharAgora = () => {
    seguindoRef.current = true;
    setSeguindo(true);
    setVendo(agoraRef.current);
  };

  const reverEm = (valor: number) => {
    seguindoRef.current = false;
    setSeguindo(false);
    setVendo(Math.min(valor, agoraRef.current));
  };

  const reiniciarDia = () => {
    agoraRef.current = 0;
    seguindoRef.current = true;
    setAgora(0);
    setVendo(0);
    setSeguindo(true);
  };

  useEffect(() => {
    const elemento = raiz.current;
    if (!elemento || iniciou) return;
    const comecar = () => {
      setIniciou(true);
      setRodando(true);
    };
    const observador = new IntersectionObserver(
      (entradas) => {
        if (entradas.some((e) => e.isIntersecting)) {
          comecar();
          observador.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    observador.observe(elemento);
    const reserva = setTimeout(comecar, 6000);
    return () => {
      observador.disconnect();
      clearTimeout(reserva);
    };
  }, [iniciou]);

  /** O relógio anda em tempo CONTÍNUO: a cada quadro soma o tempo real
   *  decorrido, em vez de um passo fixo. É isso que deixa a barra de cada
   *  atendimento correndo suave — e que mantém a hora simulada correta mesmo
   *  quando o navegador segura os quadros (aba em segundo plano). */
  useEffect(() => {
    if (!rodando) return;
    let anterior = performance.now();
    const id = setInterval(() => {
      const marca = performance.now();
      const dt = Math.min((marca - anterior) / 1000, 1);
      anterior = marca;
      const proximo = Math.min(agoraRef.current + dt * velocidade, FIM);
      agoraRef.current = proximo;
      setAgora(proximo);
      if (seguindoRef.current) setVendo(proximo);
      if (proximo >= FIM) setRodando(false);
    }, 33);
    return () => clearInterval(id);
  }, [rodando, velocidade]);

  /** Espera das ligações atendidas nos últimos 30 minutos: e assim que um
   *  supervisor le a fila — pelo que esta acontecendo agora. */
  const esperaRecente = useMemo(() => {
    const janela = 30;
    const soma = new Float64Array(MINUTOS_DIA);
    const contagem = new Int32Array(MINUTOS_DIA);
    for (const c of aoVivo.chamadas) {
      if (!c.atendido) continue;
      const indice = Math.min(MINUTOS_DIA - 1, Math.max(0, Math.round(c.chegada)));
      soma[indice] += c.espera_s;
      contagem[indice] += 1;
    }
    const saida = new Float64Array(MINUTOS_DIA);
    let acSoma = 0;
    let acContagem = 0;
    for (let i = 0; i < MINUTOS_DIA; i += 1) {
      acSoma += soma[i];
      acContagem += contagem[i];
      if (i >= janela) {
        acSoma -= soma[i - janela];
        acContagem -= contagem[i - janela];
      }
      saida[i] = acContagem > 0 ? Math.max(0, acSoma / acContagem) : 0;
    }
    return saida;
  }, [aoVivo.chamadas]);

  const minuto = vendo;
  const atrasoMin = Math.round(agora - vendo);
  const atrasoTexto =
    atrasoMin >= 60
      ? `${Math.floor(atrasoMin / 60)}h${String(atrasoMin % 60).padStart(2, "0")} atrás`
      : `${atrasoMin} min atrás`;

  /** O retrato exato do instante: fila, postos e acumulados saem todos daqui,
   *  então o cartão "na fila agora" e a fila desenhada são a mesma contagem. */
  const ligacoes = useMemo(() => prepararLigacoes(aoVivo.chamadas), [aoVivo.chamadas]);
  const situacao = useMemo(
    () => situacaoEm(ligacoes, minuto, parametros.nivel_servico_seg),
    [ligacoes, minuto, parametros.nivel_servico_seg],
  );

  const m = Math.min(Math.floor(minuto), MINUTOS_DIA - 1);
  const hora = Math.floor(m / 60);
  const capacidade = aoVivo.capacidade[m] ?? 0;
  const capacidadeMaxima = useMemo(() => Math.max(...aoVivo.capacidade), [aoVivo.capacidade]);
  const fila = situacao.naFila.length;
  const ocupados = situacao.emAtendimento.length;
  const recebidas = situacao.recebidas;
  const atendidas = situacao.atendidas;
  const abandonos = situacao.desistencias;
  const noPrazo = situacao.noPrazo;
  const resolvidas = atendidas + abandonos;
  const nivelServico = resolvidas > 0 ? noPrazo / resolvidas : 1;
  const taxaAbandono = resolvidas > 0 ? abandonos / resolvidas : 0;
  const ocupacao = capacidade > 0 ? ocupados / capacidade : 0;

  /** Previsto acumulado até este instante (a hora corrente entra proporcional). */
  const previstoAteAgora = useMemo(() => {
    let soma = 0;
    for (let h = 0; h < 24; h += 1) {
      if (h < hora) soma += dia.previsto[h];
      else if (h === hora) soma += (dia.previsto[h] * (m % 60)) / 60;
    }
    return soma;
  }, [dia.previsto, hora, m]);

  const desvio = previstoAteAgora > 20 ? recebidas / previstoAteAgora - 1 : 0;

  /** Desvio das três últimas horas fechadas: e o sinal que antecede a fila. */
  const desvioRecente = useMemo(() => {
    const de = Math.max(0, hora - 3);
    if (hora <= de) return 0;
    let real = 0;
    let prev = 0;
    for (let h = de; h < hora; h += 1) {
      real += dia.real[h];
      prev += dia.previsto[h];
    }
    return prev > 0 ? real / prev - 1 : 0;
  }, [dia.real, dia.previsto, hora]);

  const eventos = useMemo(() => {
    const abertura = [
      {
        minuto: 0,
        tipo: "sistema" as const,
        texto: `Previsão do dia carregada: ${num(dia.total_previsto)} ligações esperadas (faixa de ${num(dia.faixa_lo)} a ${num(dia.faixa_hi)})`,
      },
      {
        minuto: 0,
        tipo: "sistema" as const,
        texto: `Escala publicada: ${num(dia.escala.reduce((a, b) => a + b, 0))} atendentes-hora, pico de ${Math.max(...dia.escala)} pessoas`,
      },
    ];
    return [...abertura, ...aoVivo.eventos]
      .filter((e) => e.minuto <= m)
      .slice(-40)
      .reverse();
  }, [aoVivo.eventos, m, dia]);

  const concluido = agora >= FIM;
  const estado =
    fila >= 3 || (ocupacao >= 1 && fila > 0)
      ? { texto: "Fila formada", cor: "#ed1651" }
      : ocupacao >= 0.85
        ? { texto: "Operação carregada", cor: "#f47920" }
        : { texto: "Operação fluindo", cor: "#00995d" };

  return (
    <div className="space-y-4" ref={raiz}>
      {/* ── Relógio, estado e comandos ───────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-borda bg-painel px-5 py-4">
        <div>
          <div className="flex items-baseline gap-2.5">
            <span className="numero text-4xl font-semibold tracking-tight text-texto">
              {relogio(minuto)}
            </span>
            <span className="text-xs uppercase tracking-widest text-tenue">
              turno {turnoDaHora(hora).toLowerCase()}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="flex items-center gap-2">
              <span
                className={`inline-block h-2 w-2 rounded-full ${rodando && seguindo ? "pulso" : ""}`}
                style={{ background: estado.cor }}
              />
              <span className="text-xs text-suave">{estado.texto}</span>
            </span>
            {seguindo ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-vermelho/10 px-2 py-0.5 text-[0.65rem] font-semibold uppercase tracking-wider text-vermelho">
                <span className="pulso inline-block h-1.5 w-1.5 rounded-full bg-vermelho" />
                ao vivo
              </span>
            ) : (
              <span className="inline-flex items-center gap-2 text-[0.7rem] text-tenue">
                <span className="rounded-full bg-painel2 px-2 py-0.5 font-medium text-suave">
                  revendo o dia
                </span>
                {atrasoMin > 0 ? `${atrasoTexto} · agora são ${relogio(agora)}` : null}
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {!seguindo ? (
            <button
              onClick={acompanharAgora}
              className="rounded-lg border border-borda2 bg-painel2 px-3 py-2 text-xs font-medium text-suave transition hover:text-texto"
            >
              ↦ Voltar para agora
            </button>
          ) : null}
          <button
            onClick={() => {
              if (concluido) {
                reiniciarDia();
                setRodando(true);
                return;
              }
              setRodando((r) => !r);
            }}
            className="rounded-lg border border-verde/50 bg-verde/10 px-4 py-2 text-sm font-medium text-verde transition hover:bg-verde/20"
          >
            {rodando ? "❚❚  Pausar o dia" : concluido ? "↻  Rodar o dia de novo" : "▶  Retomar o dia"}
          </button>
          <div className="flex overflow-hidden rounded-lg border border-borda2">
            {VELOCIDADES.map((v) => (
              <button
                key={v.rotulo}
                onClick={() => setVelocidade(v.valor)}
                title={v.dica}
                className={`px-2.5 py-2 text-xs font-medium transition ${
                  velocidade === v.valor ? "bg-azul/15 text-azul" : "text-tenue hover:bg-painel2"
                }`}
              >
                {v.rotulo}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <input
          type="range"
          min={0}
          max={Math.max(agora, 1)}
          step={0.5}
          value={Math.min(vendo, Math.max(agora, 1))}
          onChange={(e) => reverEm(Number(e.target.value))}
          className="h-1 w-full cursor-pointer appearance-none rounded-full bg-borda accent-verde"
          aria-label="Voltar no dia"
        />
        <div className="mt-1 flex justify-between text-[0.65rem] text-tenue">
          <span>00:00</span>
          <span>arraste para rever o que já aconteceu</span>
          <span className="numero">{relogio(agora)}</span>
        </div>
      </div>

      {/* ── Os números que o gestor olha ─────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Caixa
          rotulo="Ligações recebidas"
          valor={num(recebidas)}
          tom="azul"
          nota={`previstas até agora: ${num(previstoAteAgora)}`}
        />
        <Caixa
          rotulo="Na fila agora"
          valor={num(fila)}
          tom={fila >= 3 ? "vermelho" : fila > 0 ? "laranja" : "verde"}
          nota={`espera de ${segundos(esperaRecente[m] ?? 0)} nos últimos 30 min`}
        />
        <Caixa
          rotulo="Atendentes em linha"
          valor={`${ocupados}/${capacidade}`}
          tom={ocupacao >= 0.85 ? "laranja" : "verde"}
          nota={`ocupação de ${pct(ocupacao, 0)}`}
        />
        <Caixa
          rotulo={`Atendidas em até ${num(parametros.nivel_servico_seg)}s`}
          valor={resolvidas > 0 ? pct(nivelServico, 1) : "—"}
          tom={
            resolvidas === 0
              ? "neutro"
              : nivelServico >= parametros.meta_nivel_servico
                ? "verde"
                : "vermelho"
          }
          nota={`meta do contrato: ${pct(parametros.meta_nivel_servico, 0)}`}
        />
        <Caixa
          rotulo="Desistiram na espera"
          valor={num(abandonos)}
          tom={taxaAbandono > 0.05 ? "vermelho" : "verde"}
          nota={`${pct(taxaAbandono, 1)} de quem ligou`}
          animar
        />
        <Caixa
          rotulo="Atendimentos concluídos"
          valor={num(atendidas)}
          tom="neutro"
          nota="acumulado do dia"
        />
      </div>

      {/* ── O aviso que antecede o problema ──────────────────────────────── */}
      {Math.abs(desvioRecente) > 0.12 && hora >= 3 && !concluido ? (
        <div
          className={`flex flex-wrap items-center gap-3 rounded-xl border-l-2 px-4 py-3 text-sm ${
            desvioRecente > 0
              ? "border-vermelho bg-vermelho/[0.08] text-suave"
              : "border-azul bg-azul/[0.07] text-suave"
          }`}
        >
          <span className={desvioRecente > 0 ? "text-vermelho" : "text-azul"}>
            {desvioRecente > 0 ? "▲" : "▼"}
          </span>
          <span>
            {desvioRecente > 0 ? (
              <>
                Nas últimas 3 horas chegaram{" "}
                <strong className="text-texto">{pct(Math.abs(desvioRecente), 0)} mais ligações</strong>{" "}
                do que o esperado. Se o ritmo se mantiver, vale acionar reforço para o próximo turno —
                depois que a fila aparece, já é tarde.
              </>
            ) : (
              <>
                Nas últimas 3 horas chegaram{" "}
                <strong className="text-texto">{pct(Math.abs(desvioRecente), 0)} menos ligações</strong>{" "}
                do que o esperado. Há folga na escala: dá para liberar gente para treinamento ou
                atendimento ativo.
              </>
            )}
          </span>
        </div>
      ) : null}

      <RecomendacaoAgora
        dia={dia}
        parametros={parametros}
        hora={hora}
        recebidas={recebidas}
        desvioRecente={desvioRecente}
      />

      <FluxoAtendimento
        situacao={situacao}
        minuto={minuto}
        capacidadeAgora={capacidade}
        capacidadeMaxima={capacidadeMaxima}
      />

      <div className="grid gap-4 lg:grid-cols-[1.55fr_1fr]">
        <Cartao className="space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-texto">
              Ligações por hora — realizado e previsto
            </h3>
            <p className="mt-1 text-xs text-tenue">
              As barras são as ligações que já chegaram. A linha verde é a previsão: cheia no que já
              passou, pontilhada no que o sistema espera do resto do dia. A linha laranja em degraus é
              a escala publicada.
            </p>
          </div>

          <GraficoOperacaoDia
            real={dia.real}
            previsto={dia.previsto}
            escalaModelo={dia.escala}
            minutoAtual={minuto}
          />
          <Legenda
            itens={[
              { cor: "#004e4c", texto: "ligações recebidas" },
              { cor: "#00995d", texto: "previsão do sistema" },
              { cor: "#f47920", texto: "atendentes escalados" },
            ]}
          />

          <div className="border-t border-borda pt-4">
            <h3 className="text-sm font-semibold text-texto">Fila e ocupação da equipe</h3>
            <p className="mb-2 mt-1 text-xs text-tenue">
              Quando a ocupação passa de 85%, a fila deixa de crescer devagar e passa a explodir.
            </p>
            <GraficoFila
              fila={aoVivo.fila}
              ocupados={aoVivo.ocupados}
              capacidade={aoVivo.capacidade}
              ate={m}
            />
            <Legenda
              itens={[
                { cor: "#00995d", texto: "pessoas na fila" },
                { cor: "#004e4c", texto: "ocupação da equipe (média de 30 min)" },
                { cor: "#ed1651", texto: "limite de 85%", tracejada: true },
              ]}
            />
          </div>
        </Cartao>

        <Cartao titulo="Registro do dia" descricao="o que o sistema anotou até agora">
          <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
            {eventos.length === 0 ? (
              <p className="text-xs text-tenue">O dia acabou de começar.</p>
            ) : (
              eventos.map((e, i) => (
                <div
                  key={`${e.minuto}-${e.texto}`}
                  className={`flex gap-3 rounded-lg border-l-2 bg-painel2/60 px-3 py-2 text-xs ${
                    e.tipo === "alerta"
                      ? "border-vermelho"
                      : e.tipo === "demanda"
                        ? "border-azul"
                        : e.tipo === "sistema"
                          ? "border-roxo"
                          : "border-verde"
                  } ${i === 0 ? "surgir" : ""}`}
                >
                  <span className="numero shrink-0 text-tenue">{relogio(e.minuto)}</span>
                  <span className="text-suave">{e.texto}</span>
                </div>
              ))
            )}
          </div>
        </Cartao>
      </div>

      {concluido ? (
        <div className="rounded-xl border border-verde/30 bg-verde/[0.06] px-5 py-4 text-sm leading-relaxed text-suave">
          <strong className="text-texto">Dia encerrado.</strong> Ligaram {num(recebidas)} pessoas — o
          sistema esperava {num(dia.total_previsto)}, {pct(Math.abs(desvio), 0)}{" "}
          {desvio > 0 ? "a mais" : "a menos"}. {num(atendidas)} foram atendidas e {num(abandonos)}{" "}
          desistiram na espera. O nível de serviço fechou em {pct(nivelServico, 1)}, contra a meta de{" "}
          {pct(parametros.meta_nivel_servico, 0)}.
        </div>
      ) : null}
    </div>
  );
}

function Caixa({
  rotulo,
  valor,
  nota,
  tom,
  animar = false,
}: {
  rotulo: string;
  valor: string;
  nota?: string;
  tom: "verde" | "azul" | "laranja" | "vermelho" | "neutro";
  animar?: boolean;
}) {
  const cores = {
    verde: "text-verde",
    azul: "text-azul",
    laranja: "text-laranja",
    vermelho: "text-vermelho",
    neutro: "text-texto",
  };
  return (
    <div className="rounded-xl border border-borda bg-painel px-4 py-3">
      <div className="text-[0.68rem] font-medium uppercase tracking-wider text-tenue">{rotulo}</div>
      <div
        key={animar ? valor : undefined}
        className={`numero mt-1 text-2xl font-semibold tracking-tight ${cores[tom]} ${animar ? "surgir" : ""}`}
      >
        {valor}
      </div>
      {nota ? <div className="mt-0.5 text-[0.7rem] text-tenue">{nota}</div> : null}
    </div>
  );
}
