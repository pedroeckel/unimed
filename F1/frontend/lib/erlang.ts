/**
 * Erlang C — a mesma conta de `F1/streamlit/nucleo/gemeo.py`, em TypeScript.
 *
 * Está aqui porque a recomendação do meio do dia precisa ser calculada com o que
 * já se sabe *naquele instante*: se a demanda está vindo 30% acima do previsto,
 * quantos atendentes as próximas horas pedem? Usar um número pré-calculado com o
 * dia inteiro conhecido seria trapaça — o painel estaria lendo o futuro.
 *
 * `prescreverEscala` reproduz `gemeo.prescrever_escala`: para cada hora, a menor
 * equipe que mantém o nível de serviço acima da meta.
 */

function erlangB(c: number, a: number): number {
  let b = 1;
  for (let i = 1; i <= c; i += 1) b = (a * b) / (i + a * b);
  return b;
}

export function erlangC(c: number, a: number): number {
  if (c <= a) return 1;
  const b = erlangB(c, a);
  return b / (1 - (a / c) * (1 - b));
}

/** Probabilidade de atender dentro do prazo, dado o tráfego e a equipe. */
export function nivelDeServico(
  chamadasHora: number,
  agentes: number,
  tmaMin: number,
  nivelServicoSeg: number,
): number {
  const a = (chamadasHora * tmaMin) / 60;
  if (agentes <= a) return 0;
  const pw = erlangC(agentes, a);
  return 1 - pw * Math.exp((-(agentes - a) * (nivelServicoSeg / 60)) / tmaMin);
}

export function prescreverEscala(
  chamadasPorHora: number[],
  tmaMin: number,
  metaSl: number,
  nivelServicoSeg: number,
  maximo = 40,
): number[] {
  return chamadasPorHora.map((lam) => {
    const a = (lam * tmaMin) / 60;
    let c = Math.max(Math.ceil(a), 1);
    while (c <= maximo) {
      if (nivelDeServico(lam, c, tmaMin, nivelServicoSeg) >= metaSl) break;
      c += 1;
    }
    return Math.min(c, maximo);
  });
}
