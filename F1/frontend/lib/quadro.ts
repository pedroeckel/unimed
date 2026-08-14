/**
 * De atendentes-hora para gente contratada.
 *
 * O dimensionamento de Erlang responde uma pergunta ("quantos atendentes
 * precisam estar EM LINHA às 10h?") e o RH faz outra ("quantas pessoas eu
 * contrato?"). São números diferentes, e a distância entre eles é onde escala
 * de call center costuma quebrar. Duas perdas separam um do outro:
 *
 * 1. O BLOCO DE TURNO. Ninguém é contratado por hora solta: entra num turno
 *    fechado. Um turno é escalado pelo seu pico, então as horas de vale dentro
 *    do mesmo turno são pagas de qualquer jeito. É folga estrutural, não erro.
 *
 * 2. O SHRINKAGE. A escala pede gente em linha; pausa da NR-17, intervalo,
 *    férias, absenteísmo, treinamento e turnover não estão em linha. Dividir a
 *    necessidade pela jornada contratada — sem descontar isso — é o erro que
 *    entrega uma central com 20% menos gente do que ela precisa.
 *
 * Nada aqui inventa demanda: a entrada é a mesma escala prescrita que alimenta
 * a tabela dos próximos sete dias.
 */

import type { DiaFuturo } from "./tipos";

const APELIDOS: Record<string, string> = {
  "0-5": "Madrugada",
  "6-11": "Manhã",
  "12-17": "Tarde",
  "18-23": "Noite",
  "0-7": "Primeiro turno",
  "8-15": "Segundo turno",
  "16-23": "Terceiro turno",
};

export type BlocoTurno = { nome: string; de: number; ate: number };

/** Os turnos que cobrem as 24 horas, dado o tamanho do bloco. */
export function blocosDeTurno(turnoH: number): BlocoTurno[] {
  const blocos: BlocoTurno[] = [];
  for (let de = 0; de < 24; de += turnoH) {
    const ate = Math.min(23, de + turnoH - 1);
    blocos.push({ nome: APELIDOS[`${de}-${ate}`] ?? `${de}h–${ate + 1}h`, de, ate });
  }
  return blocos;
}

export type Politica = {
  /** Jornada contratual semanal, em horas. Teleatendimento: 36h (NR-17, anexo II). */
  jornadaSemanalH: number;
  /** Tamanho do turno, em horas. */
  turnoH: number;
  /** Fração do tempo contratado que não vira atendimento: pausas, férias,
   *  absenteísmo, treinamento, turnover. */
  shrinkage: number;
};

export type LinhaTurno = {
  nome: string;
  de: number;
  ate: number;
  /** Postos abertos em cada dia da semana — o pico da escala dentro do bloco. */
  porDia: number[];
  postos: number;
  pessoas: number;
};

export type Quadro = {
  /** A necessidade crua: soma da escala hora a hora. */
  atendentesHora: number;
  /** Posições ocupadas em média, se a operação fosse plana 24/7. */
  posicoesMedias: number;
  /** Turnos-pessoa a preencher na semana. */
  postosTurno: number;
  /** O que o bloco de turno obriga a pagar. */
  horasPagas: number;
  /** Quanto do turno fechado é folga estrutural. */
  folgaBloco: number;
  turnosPorPessoa: number;
  /** Quadro num mundo sem pausa, falta ou férias. */
  quadroBruto: number;
  /** Quadro depois do shrinkage. */
  quadro: number;
  /** O número que vai para o RH. */
  contratados: number;
  turnos: LinhaTurno[];
  dias: { data: string; diaSemana: string; postos: number }[];
};

export function dimensionarQuadro(dias: DiaFuturo[], p: Politica): Quadro {
  const blocos = blocosDeTurno(p.turnoH);
  const turnosPorPessoa = p.jornadaSemanalH / p.turnoH;
  const liquido = Math.max(0.05, 1 - p.shrinkage);

  const turnos: LinhaTurno[] = blocos.map((b) => {
    const porDia = dias.map((d) => Math.max(...d.escala.slice(b.de, b.ate + 1)));
    const postos = porDia.reduce((a, x) => a + x, 0);
    return { ...b, porDia, postos, pessoas: postos / turnosPorPessoa / liquido };
  });

  const atendentesHora = dias.reduce((a, d) => a + d.atendentes_hora, 0);
  const postosTurno = turnos.reduce((a, t) => a + t.postos, 0);
  const horasPagas = postosTurno * p.turnoH;
  const quadroBruto = postosTurno / turnosPorPessoa;
  const quadro = quadroBruto / liquido;

  return {
    atendentesHora,
    posicoesMedias: atendentesHora / (dias.length * 24),
    postosTurno,
    horasPagas,
    folgaBloco: horasPagas > 0 ? 1 - atendentesHora / horasPagas : 0,
    turnosPorPessoa,
    quadroBruto,
    quadro,
    contratados: Math.ceil(quadro),
    turnos,
    dias: dias.map((d, i) => ({
      data: d.data,
      diaSemana: d.dia_semana,
      postos: turnos.reduce((a, t) => a + t.porDia[i], 0),
    })),
  };
}

/** Só o headcount, para varrer cenários de jornada × shrinkage sem refazer tudo. */
export function quadroPara(dias: DiaFuturo[], p: Politica): number {
  return dimensionarQuadro(dias, p).quadro;
}
