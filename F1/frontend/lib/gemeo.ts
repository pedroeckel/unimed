/**
 * O gêmeo digital da central, rodando no navegador.
 *
 * É a mesma máquina de `F1/streamlit/nucleo/gemeo.py`, escrita de novo em
 * TypeScript para que o simulador responda enquanto o gestor mexe nos controles:
 *
 * - chegadas em processo de Poisson não homogêneo (a taxa muda a cada hora);
 * - fila FIFO com ABANDONO por impaciência (paciência exponencial);
 * - tempo de atendimento lognormal em torno do TMA (σ = 0,5);
 * - capacidade que muda por turno — quando a escala diminui, quem já está em
 *   ligação termina a conversa, como na vida real.
 *
 * O nível de serviço é medido sobre as chamadas OFERECIDAS: quem desistiu conta
 * como não atendido. Medir só entre as atendidas premia a operação que perde
 * beneficiário no meio do caminho.
 */

export const NIVEL_SERVICO_SEG = 20;
const SIGMA_LOG = 0.5;

/** Gerador com semente: mesma semente, mesmo dia — o resultado é reproduzível. */
function criarRng(semente: number) {
  let estado = semente >>> 0;
  return () => {
    estado |= 0;
    estado = (estado + 0x6d2b79f5) | 0;
    let t = Math.imul(estado ^ (estado >>> 15), 1 | estado);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function poisson(rng: () => number, media: number): number {
  if (media <= 0) return 0;
  if (media > 60) {
    // Aproximação normal: para taxas altas o método de Knuth fica lento.
    const u1 = Math.max(rng(), 1e-12);
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * rng());
    return Math.max(0, Math.round(media + Math.sqrt(media) * z));
  }
  const limite = Math.exp(-media);
  let n = 0;
  let p = 1;
  do {
    n += 1;
    p *= rng();
  } while (p > limite);
  return n - 1;
}

function exponencial(rng: () => number, media: number): number {
  return -media * Math.log(Math.max(rng(), 1e-12));
}

function lognormal(rng: () => number, mediana: number, sigma: number): number {
  const u1 = Math.max(rng(), 1e-12);
  const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * rng());
  const mu = Math.log(mediana) - (sigma * sigma) / 2;
  return Math.exp(mu + sigma * z);
}

export type ResultadoSimulacao = {
  chamadas: number;
  atendidas: number;
  abandonos: number;
  nivelServico: number;
  abandono: number;
  esperaMediaSeg: number;
  esperaP90Seg: number;
};

type Espera = { chegada: number; prazo: number };

/** Uma replicação de 24 horas de operação. */
export function simularDia(
  lambdaHora: number[],
  escalaHora: number[],
  tmaMin: number,
  pacienciaMin: number,
  semente: number,
): ResultadoSimulacao {
  const rng = criarRng(semente);

  const chegadas: number[] = [];
  for (let h = 0; h < 24; h += 1) {
    const n = poisson(rng, lambdaHora[h] ?? 0);
    for (let k = 0; k < n; k += 1) chegadas.push(h * 60 + rng() * 60);
  }
  chegadas.sort((a, b) => a - b);

  const fila: Espera[] = [];
  const emServico: number[] = []; // instantes de término, sempre ordenados
  const esperas: number[] = [];
  let atendidas = 0;
  let abandonos = 0;
  let noPrazo = 0;
  let proxima = 0;

  const capacidadeEm = (t: number) => escalaHora[Math.min(23, Math.max(0, Math.floor(t / 60)))] ?? 0;

  const iniciarAtendimento = (t: number, chegada: number) => {
    const espera = t - chegada;
    esperas.push(espera);
    atendidas += 1;
    if (espera <= NIVEL_SERVICO_SEG / 60) noPrazo += 1;
    const duracao = lognormal(rng, tmaMin, SIGMA_LOG);
    const fim = t + duracao;
    const posicao = emServico.findIndex((f) => f > fim);
    if (posicao === -1) emServico.push(fim);
    else emServico.splice(posicao, 0, fim);
  };

  const puxarDaFila = (t: number) => {
    while (fila.length > 0 && emServico.length < capacidadeEm(t)) {
      const proximoDaFila = fila.shift() as Espera;
      iniciarAtendimento(t, proximoDaFila.chegada);
    }
  };

  let t = 0;
  let guarda = 0;
  while (proxima < chegadas.length || fila.length > 0 || emServico.length > 0) {
    guarda += 1;
    if (guarda > 500_000) break; // rede de segurança: nunca deve ser atingida

    const tChegada = proxima < chegadas.length ? chegadas[proxima] : Infinity;
    const tFim = emServico.length > 0 ? emServico[0] : Infinity;
    let tAbandono = Infinity;
    let indiceAbandono = -1;
    for (let i = 0; i < fila.length; i += 1) {
      if (fila[i].prazo < tAbandono) {
        tAbandono = fila[i].prazo;
        indiceAbandono = i;
      }
    }
    // A troca de turno também é evento: escala que sobe puxa gente da fila.
    const tTurno = fila.length > 0 ? (Math.floor(t / 60) + 1) * 60 : Infinity;

    const proximoEvento = Math.min(tChegada, tFim, tAbandono, tTurno);
    if (!Number.isFinite(proximoEvento)) break;
    t = proximoEvento;

    if (t === tFim) {
      emServico.shift();
      puxarDaFila(t);
      continue;
    }
    if (t === tAbandono) {
      fila.splice(indiceAbandono, 1);
      abandonos += 1;
      continue;
    }
    if (t === tChegada) {
      proxima += 1;
      if (emServico.length < capacidadeEm(t)) {
        iniciarAtendimento(t, t);
      } else {
        fila.push({ chegada: t, prazo: t + exponencial(rng, pacienciaMin) });
      }
      continue;
    }
    // troca de turno
    puxarDaFila(t);
  }

  const total = atendidas + abandonos;
  const ordenadas = [...esperas].sort((a, b) => a - b);
  const p90 = ordenadas.length > 0 ? ordenadas[Math.floor(0.9 * (ordenadas.length - 1))] : 0;
  const media = esperas.length > 0 ? esperas.reduce((a, b) => a + b, 0) / esperas.length : 0;

  return {
    chamadas: total,
    atendidas,
    abandonos,
    nivelServico: total > 0 ? noPrazo / total : 1,
    abandono: total > 0 ? abandonos / total : 0,
    esperaMediaSeg: media * 60,
    esperaP90Seg: p90 * 60,
  };
}

/**
 * Várias replicações independentes. Uma rodada sozinha é um sorteio; o que se
 * reporta é a média entre replicações.
 */
export function rodarReplicacoes(
  lambdaHora: number[],
  escalaHora: number[],
  tmaMin: number,
  pacienciaMin: number,
  nRep = 6,
  semente = 42,
): ResultadoSimulacao {
  const rodadas: ResultadoSimulacao[] = [];
  for (let r = 0; r < nRep; r += 1) {
    rodadas.push(simularDia(lambdaHora, escalaHora, tmaMin, pacienciaMin, semente + r * 7919));
  }
  const media = (pegar: (x: ResultadoSimulacao) => number) =>
    rodadas.reduce((a, x) => a + pegar(x), 0) / rodadas.length;

  return {
    chamadas: media((x) => x.chamadas),
    atendidas: media((x) => x.atendidas),
    abandonos: media((x) => x.abandonos),
    nivelServico: media((x) => x.nivelServico),
    abandono: media((x) => x.abandono),
    esperaMediaSeg: media((x) => x.esperaMediaSeg),
    esperaP90Seg: media((x) => x.esperaP90Seg),
  };
}
