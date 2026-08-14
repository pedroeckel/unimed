import type { AoVivo } from "./tipos";

export type Ligacao = {
  id: number;
  chegada: number;
  inicio: number | null;
  fim: number | null;
  /** Instante em que desistiu, para quem abandonou a espera. */
  desiste: number | null;
  esperaSeg: number;
  atendido: boolean;
  posto: number;
};

export type Situacao = {
  chegando: Ligacao[];
  naFila: Ligacao[];
  emAtendimento: Ligacao[];
  recebidas: number;
  atendidas: number;
  desistencias: number;
  noPrazo: number;
};

/** Quanto tempo uma ligação recém-chegada fica visível na faixa "chegando". */
export const JANELA_CHEGADA = 0.5;

/**
 * Prepara a lista de ligações do dia e decide em qual posto cada uma foi
 * atendida.
 *
 * A simulação registra o TEMPO de cada ligação (quando chegou, quando começou a
 * ser atendida e quando terminou), não a cadeira. A distribuição pelos postos é
 * feita aqui, uma única vez para o dia inteiro, sempre pelo primeiro posto livre
 * — assim uma ligação nunca "pula" de cadeira no meio da conversa, e o número de
 * postos ocupados continua sendo exatamente o da simulação.
 */
export function prepararLigacoes(chamadas: AoVivo["chamadas"]): Ligacao[] {
  const lista: Ligacao[] = chamadas.map((c, i) => ({
    id: i,
    chegada: c.chegada,
    inicio: c.inicio,
    fim: c.fim,
    desiste: c.atendido ? null : c.chegada + c.espera_s / 60,
    esperaSeg: c.espera_s,
    atendido: c.atendido,
    posto: -1,
  }));

  const fimDoPosto: number[] = [];
  lista
    .filter((l) => l.atendido && l.inicio !== null)
    .sort((a, b) => (a.inicio as number) - (b.inicio as number))
    .forEach((l) => {
      const inicio = l.inicio as number;
      let posto = fimDoPosto.findIndex((f) => f <= inicio + 1e-9);
      if (posto === -1) {
        fimDoPosto.push(l.fim as number);
        posto = fimDoPosto.length - 1;
      } else {
        fimDoPosto[posto] = l.fim as number;
      }
      l.posto = posto;
    });

  return lista;
}

/**
 * O retrato da central em um instante qualquer do dia.
 *
 * Todos os indicadores da tela saem daqui, inclusive os cartões de KPI: assim o
 * número de pessoas na fila e o desenho da fila são, necessariamente, a mesma
 * coisa.
 */
export function situacaoEm(ligacoes: Ligacao[], t: number, nivelServicoSeg: number): Situacao {
  const chegando: Ligacao[] = [];
  const naFila: Ligacao[] = [];
  const emAtendimento: Ligacao[] = [];
  let recebidas = 0;
  let atendidas = 0;
  let desistencias = 0;
  let noPrazo = 0;

  for (const l of ligacoes) {
    if (l.chegada > t) break; // a lista está em ordem de chegada
    recebidas += 1;

    if (l.atendido) {
      if ((l.fim as number) <= t) {
        atendidas += 1;
        if (l.esperaSeg <= nivelServicoSeg) noPrazo += 1;
      } else if ((l.inicio as number) <= t) {
        emAtendimento.push(l);
      } else {
        naFila.push(l);
      }
    } else if ((l.desiste as number) <= t) {
      desistencias += 1;
    } else {
      naFila.push(l);
    }

    if (t - l.chegada <= JANELA_CHEGADA) chegando.push(l);
  }

  return { chegando, naFila, emAtendimento, recebidas, atendidas, desistencias, noPrazo };
}
