/**
 * Os graficos do painel, em SVG puro.
 *
 * Sem biblioteca de charts de proposito: sao poucas formas, todas com escala
 * explicita, e assim o painel nao carrega nada alem do proprio HTML. Cada
 * componente recebe numeros ja calculados — nenhum deles faz estatistica.
 */

/** Os mesmos tokens de `globals.css`: gráfico e legenda precisam ser a mesma cor. */
export const COR = {
  verde: "#00995d",
  citrico: "#b1d34b",
  azul: "#004e4c",
  laranja: "#f47920",
  vermelho: "#ed1651",
  roxo: "#a3238e",
  amarelo: "#e8a33d",
  grade: "#e6ece8",
  eixo: "#7d8b84",
  texto: "#4f6058",
};

const escala2 = (dominio: [number, number], faixa: [number, number]) => {
  const [d0, d1] = dominio;
  const [r0, r1] = faixa;
  const amplitude = d1 - d0 || 1;
  return (v: number) => r0 + ((v - d0) / amplitude) * (r1 - r0);
};

const caminho = (pontos: [number, number][]) =>
  pontos.map((p, i) => `${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(" ");

const caminhoDegrau = (pontos: [number, number][], largura: number) => {
  const partes: string[] = [];
  pontos.forEach((p, i) => {
    partes.push(`${i === 0 ? "M" : "L"}${p[0].toFixed(2)},${p[1].toFixed(2)}`);
    partes.push(`L${(p[0] + largura).toFixed(2)},${p[1].toFixed(2)}`);
  });
  return partes.join(" ");
};

/* ═══════════════════════════════════════════════════════════════════════════
   A operacao do dia: demanda por hora contra a escala dimensionada
   ═══════════════════════════════════════════════════════════════════════ */

/**
 * O dia da operação como o gestor o vê enquanto ele acontece: barras para as
 * ligações que JA chegaram, linha cheia para a previsão do que já passou e
 * linha pontilhada para o que o sistema espera do resto do dia.
 */
export function GraficoOperacaoDia({
  real,
  previsto,
  escalaModelo,
  minutoAtual,
  altura = 300,
}: {
  real: number[];
  previsto: number[];
  escalaModelo: number[];
  minutoAtual: number;
  altura?: number;
}) {
  const L = 46, R = 46, T = 18, B = 28;
  const W = 900, H = altura;
  const horaAtual = Math.min(23, Math.floor(minutoAtual / 60));
  const maxChamadas = Math.max(...real, ...previsto) * 1.12;
  const maxAgentes = Math.max(...escalaModelo) * 1.35;
  const x = escala2([0, 24], [L, W - R]);
  const y = escala2([0, maxChamadas], [H - B, T]);
  const yA = escala2([0, maxAgentes], [H - B, T]);
  const larguraHora = (W - R - L) / 24;
  const centro = (h: number) => x(h) + larguraHora / 2;
  const xAgora = L + (minutoAtual / 1440) * (W - R - L);

  const trecho = (de: number, ate: number) =>
    caminho(
      previsto
        .map((v, h) => [centro(h), y(v)] as [number, number])
        .filter((_, h) => h >= de && h <= ate),
    );

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <g key={f}>
          <line x1={L} x2={W - R} y1={y(maxChamadas * f)} y2={y(maxChamadas * f)} stroke={COR.grade} />
          <text x={L - 8} y={y(maxChamadas * f) + 4} textAnchor="end" fontSize={11} fill={COR.eixo}>
            {Math.round(maxChamadas * f)}
          </text>
        </g>
      ))}

      {/* O futuro fica visivelmente "por acontecer". */}
      <rect x={xAgora} y={T} width={Math.max(0, W - R - xAgora)} height={H - B - T} fill="#eef2ef" fillOpacity={0.75} />

      {real.map((v, h) =>
        h <= horaAtual ? (
          <rect
            key={h}
            x={x(h) + 3}
            y={y(v)}
            width={larguraHora - 6}
            height={H - B - y(v)}
            rx={2.5}
            fill={COR.azul}
            fillOpacity={h === horaAtual ? 0.32 : 0.62}
          />
        ) : null,
      )}

      <path d={trecho(0, horaAtual)} fill="none" stroke={COR.verde} strokeWidth={2.4} />
      <path
        d={trecho(horaAtual, 23)}
        fill="none"
        stroke={COR.verde}
        strokeWidth={2}
        strokeDasharray="6 4"
        strokeOpacity={0.75}
      />
      <path
        d={caminhoDegrau(
          escalaModelo.map((v, h) => [x(h), yA(v)] as [number, number]),
          larguraHora,
        )}
        fill="none"
        stroke={COR.laranja}
        strokeWidth={2}
      />

      <line x1={xAgora} x2={xAgora} y1={T} y2={H - B} stroke={COR.texto} strokeWidth={1.2} />
      <circle cx={xAgora} cy={T} r={3.5} fill={COR.texto} />
      <text x={xAgora + 6} y={T + 4} fontSize={11} fill={COR.texto}>
        agora
      </text>

      {[0, 6, 12, 18, 24].map((h) => (
        <text key={h} x={h === 24 ? W - R : x(h)} y={H - 9} fontSize={11} fill={COR.eixo} textAnchor="middle">
          {String(h).padStart(2, "0")}h
        </text>
      ))}
      {[0, 0.5, 1].map((f) => (
        <text key={f} x={W - R + 8} y={yA(maxAgentes * f) + 4} fontSize={11} fill={COR.laranja} textAnchor="start">
          {Math.round(maxAgentes * f)}
        </text>
      ))}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={COR.eixo} />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   O traco ao vivo: fila e atendentes ocupados minuto a minuto
   ═══════════════════════════════════════════════════════════════════════ */

export function GraficoFila({
  fila,
  ocupados,
  capacidade,
  ate,
  altura = 170,
}: {
  fila: number[];
  ocupados: number[];
  capacidade: number[];
  ate: number;
  altura?: number;
}) {
  const L = 30, R = 40, T = 14, B = 20;
  const W = 900, H = altura;
  const maxFila = Math.max(2, ...fila);
  const x = escala2([0, 1440], [L, W - R]);
  const yF = escala2([0, maxFila * 1.25], [H - B, T]);
  const yO = escala2([0, 1.05], [H - B, T]);

  const passo = 3;
  const indices: number[] = [];
  for (let i = 0; i <= ate; i += passo) indices.push(i);
  if (indices.length && indices[indices.length - 1] !== ate) indices.push(ate);

  /** A ocupação instantânea oscila a cada atendimento que começa ou termina.
   *  O que interessa ao supervisor é a tendência: média móvel de 30 minutos. */
  const janela = 30;
  const ocupacaoSuave = indices.map((i) => {
    const de = Math.max(0, i - janela);
    let soma = 0;
    let n = 0;
    for (let k = de; k <= i; k += 1) {
      const cap = capacidade[k] ?? 0;
      if (cap > 0) {
        soma += (ocupados[k] ?? 0) / cap;
        n += 1;
      }
    }
    return n > 0 ? soma / n : 0;
  });

  const pontosFila = indices.map((i) => [x(i), yF(fila[i] ?? 0)] as [number, number]);
  const pontosOcup = ocupacaoSuave.map((v, k) => [x(indices[k]), yO(v)] as [number, number]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {[0, 0.5, 1].map((f) => (
        <line key={f} x1={L} x2={W - R} y1={yF(maxFila * 1.25 * f)} y2={yF(maxFila * 1.25 * f)} stroke={COR.grade} />
      ))}
      <text x={L - 6} y={yF(0) + 4} textAnchor="end" fontSize={10} fill={COR.verde}>0</text>
      <text x={L - 6} y={yF(maxFila) + 4} textAnchor="end" fontSize={10} fill={COR.verde}>
        {maxFila}
      </text>

      <line x1={L} x2={W - R} y1={yO(0.85)} y2={yO(0.85)} stroke={COR.vermelho} strokeWidth={1} strokeDasharray="3 4" />
      <text x={W - R + 6} y={yO(0.85) + 4} fontSize={10} fill={COR.vermelho}>
        85%
      </text>
      <text x={W - R + 6} y={yO(0) + 4} fontSize={10} fill={COR.azul}>
        0%
      </text>

      {pontosOcup.length > 1 ? (
        <path d={caminho(pontosOcup)} fill="none" stroke={COR.azul} strokeWidth={1.8} strokeLinejoin="round" />
      ) : null}
      {pontosFila.length > 1 ? (
        <>
          <path
            d={`${caminho(pontosFila)} L${pontosFila[pontosFila.length - 1][0]},${H - B} L${L},${H - B} Z`}
            fill={COR.verde}
            fillOpacity={0.18}
          />
          <path d={caminho(pontosFila)} fill="none" stroke={COR.verde} strokeWidth={1.6} strokeLinejoin="round" />
        </>
      ) : null}

      {[0, 6, 12, 18, 24].map((h) => (
        <text key={h} x={x(h * 60)} y={H - 6} fontSize={10} fill={COR.eixo} textAnchor="middle">
          {String(h).padStart(2, "0")}h
        </text>
      ))}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={COR.grade} />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Barras horizontais com marcos (usado no placar dos modelos)
   ═══════════════════════════════════════════════════════════════════════ */

export function BarrasHorizontais({
  itens,
  maximo,
  marcos = [],
  formatar,
}: {
  itens: { rotulo: string; valor: number; cor: string; nota?: string }[];
  maximo: number;
  marcos?: { valor: number; rotulo: string; cor: string }[];
  formatar: (v: number) => string;
}) {
  const alturaLinha = 30;
  const L = 262, R = 66, T = 22;
  const W = 900;
  const H = T + itens.length * alturaLinha + 12;
  const x = escala2([0, maximo], [L, W - R]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {marcos.map((m) => (
        <g key={m.rotulo}>
          <line x1={x(m.valor)} x2={x(m.valor)} y1={T - 12} y2={H - 6} stroke={m.cor} strokeWidth={1.2} strokeDasharray="4 3" />
          <text x={x(m.valor)} y={T - 16} fontSize={11} fill={m.cor} textAnchor="middle">
            {m.rotulo}
          </text>
        </g>
      ))}
      {itens.map((it, i) => {
        const y = T + i * alturaLinha;
        return (
          <g key={it.rotulo}>
            <text x={L - 10} y={y + 15} fontSize={12} fill={COR.texto} textAnchor="end">
              {it.rotulo}
            </text>
            <rect x={L} y={y + 4} width={Math.max(2, x(it.valor) - L)} height={16} rx={3} fill={it.cor} fillOpacity={0.85} />
            <text x={x(it.valor) + 8} y={y + 16} fontSize={12} fill={COR.texto} className="numero">
              {formatar(it.valor)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Linhas genericas (serie no teste, erro por horizonte)
   ═══════════════════════════════════════════════════════════════════════ */

export function GraficoLinhas({
  series,
  rotulosX,
  altura = 260,
  minimoY,
  formatarY = (v: number) => String(Math.round(v)),
  faixa,
  marcoY,
}: {
  series: { nome: string; valores: number[]; cor: string; tracejada?: boolean; largura?: number }[];
  rotulosX: string[];
  altura?: number;
  minimoY?: number;
  formatarY?: (v: number) => string;
  faixa?: { baixo: number[]; alto: number[]; cor: string };
  marcoY?: { valor: number; rotulo: string; cor: string };
}) {
  const L = 46, R = 16, T = 14, B = 26;
  const W = 900, H = altura;
  const todos = series.flatMap((s) => s.valores).concat(faixa ? [...faixa.baixo, ...faixa.alto] : []);
  const maxY = Math.max(...todos) * 1.08;
  const minY = minimoY ?? Math.min(0, ...todos);
  const n = series[0]?.valores.length ?? 0;
  const x = escala2([0, Math.max(n - 1, 1)], [L, W - R]);
  const y = escala2([minY, maxY], [H - B, T]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {[0, 0.25, 0.5, 0.75, 1].map((f) => {
        const v = minY + (maxY - minY) * f;
        return (
          <g key={f}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke={COR.grade} />
            <text x={L - 8} y={y(v) + 4} fontSize={11} fill={COR.eixo} textAnchor="end">
              {formatarY(v)}
            </text>
          </g>
        );
      })}

      {faixa ? (
        <path
          d={`${caminho(faixa.alto.map((v, i) => [x(i), y(v)]))} ${faixa.baixo
            .map((v, i) => [x(faixa.baixo.length - 1 - i), y(faixa.baixo[faixa.baixo.length - 1 - i])])
            .map((p) => `L${p[0].toFixed(2)},${p[1].toFixed(2)}`)
            .join(" ")} Z`}
          fill={faixa.cor}
          fillOpacity={0.14}
        />
      ) : null}

      {marcoY ? (
        <g>
          <line x1={L} x2={W - R} y1={y(marcoY.valor)} y2={y(marcoY.valor)} stroke={marcoY.cor} strokeDasharray="5 4" strokeWidth={1.2} />
          <text x={W - R} y={y(marcoY.valor) - 6} fontSize={11} fill={marcoY.cor} textAnchor="end">
            {marcoY.rotulo}
          </text>
        </g>
      ) : null}

      {series.map((s) => (
        <path
          key={s.nome}
          d={caminho(s.valores.map((v, i) => [x(i), y(v)]))}
          fill="none"
          stroke={s.cor}
          strokeWidth={s.largura ?? 2}
          strokeDasharray={s.tracejada ? "5 4" : undefined}
          strokeLinejoin="round"
        />
      ))}

      {rotulosX.map((r, i) => {
        const passo = Math.max(1, Math.ceil(n / 8));
        if (i % passo !== 0 && i !== n - 1) return null;
        return (
          <text key={i} x={x(i)} y={H - 8} fontSize={11} fill={COR.eixo} textAnchor="middle">
            {r}
          </text>
        );
      })}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={COR.eixo} />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Histograma (distribuicao da espera)
   ═══════════════════════════════════════════════════════════════════════ */

/**
 * A curva de espera: que fração das ligações atendidas ja tinha sido atendida
 * ate cada instante. E a leitura natural de um nivel de servico — a meta de
 * "atender em 20 segundos" e simplesmente um ponto sobre esta curva.
 */
export function CurvaEspera({
  bordas,
  contagens,
  p90,
  metaSeg,
  altura = 230,
}: {
  bordas: number[];
  contagens: number[];
  p90: number;
  metaSeg: number;
  altura?: number;
}) {
  const L = 44, R = 18, T = 16, B = 30;
  const W = 900, H = altura;
  const total = contagens.reduce((a, b) => a + b, 0) || 1;
  const maxX = bordas[bordas.length - 1];
  const x = escala2([0, maxX], [L, W - R]);
  const y = escala2([0, 1], [H - B, T]);

  let acumulado = 0;
  const pontos: [number, number][] = [[x(0), y(0)]];
  contagens.forEach((c, i) => {
    acumulado += c;
    pontos.push([x(bordas[i + 1]), y(acumulado / total)]);
  });

  /** Interpolação linear dentro da faixa que contém a meta. */
  const fracaoAte = (segundos: number) => {
    let soma = 0;
    for (let i = 0; i < contagens.length; i += 1) {
      const de = bordas[i];
      const ate = bordas[i + 1];
      if (segundos >= ate) {
        soma += contagens[i];
      } else if (segundos > de) {
        soma += (contagens[i] * (segundos - de)) / (ate - de);
        break;
      } else break;
    }
    return soma / total;
  };
  const naMeta = fracaoAte(metaSeg);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <g key={f}>
          <line x1={L} x2={W - R} y1={y(f)} y2={y(f)} stroke={COR.grade} />
          <text x={L - 8} y={y(f) + 4} fontSize={11} fill={COR.eixo} textAnchor="end">
            {Math.round(f * 100)}%
          </text>
        </g>
      ))}

      <path
        d={`${caminho(pontos)} L${x(maxX)},${y(0)} L${x(0)},${y(0)} Z`}
        fill={COR.azul}
        fillOpacity={0.12}
      />
      <path d={caminho(pontos)} fill="none" stroke={COR.azul} strokeWidth={2.2} strokeLinejoin="round" />

      <line x1={x(metaSeg)} x2={x(metaSeg)} y1={T} y2={H - B} stroke={COR.verde} strokeWidth={1.4} strokeDasharray="4 3" />
      <circle cx={x(metaSeg)} cy={y(naMeta)} r={5} fill={COR.verde} stroke="#ffffff" strokeWidth={2} />
      <text x={x(metaSeg) + 10} y={y(naMeta) - 8} fontSize={12} fill={COR.verde}>
        {Math.round(metaSeg)}s → {(naMeta * 100).toFixed(1).replace(".", ",")}% das atendidas
      </text>

      <line x1={x(p90)} x2={x(p90)} y1={y(0.9)} y2={H - B} stroke={COR.laranja} strokeWidth={1.2} strokeDasharray="3 4" />
      <text x={x(p90) + 8} y={y(0.9) + 14} fontSize={11} fill={COR.laranja}>
        P90 = {Math.round(p90)}s
      </text>

      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <text key={f} x={x(maxX * f)} y={H - 10} fontSize={11} fill={COR.eixo} textAnchor="middle">
          {Math.round(maxX * f)}s
        </text>
      ))}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={COR.eixo} />
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Fronteira custo x servico
   ═══════════════════════════════════════════════════════════════════════ */

export function Fronteira({
  pontos,
  meta,
  altura = 300,
}: {
  pontos: { ajuste: string; custo: number; nivel_servico: number; delta: number }[];
  meta: number;
  altura?: number;
}) {
  const L = 52, R = 22, T = 18, B = 40;
  const W = 900, H = altura;
  const custos = pontos.map((p) => p.custo);
  const x = escala2([Math.min(...custos) * 0.92, Math.max(...custos) * 1.04], [L, W - R]);
  const y = escala2([0, 1], [H - B, T]);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <g key={f}>
          <line x1={L} x2={W - R} y1={y(f)} y2={y(f)} stroke={COR.grade} />
          <text x={L - 8} y={y(f) + 4} fontSize={11} fill={COR.eixo} textAnchor="end">
            {Math.round(f * 100)}%
          </text>
        </g>
      ))}
      <line x1={L} x2={W - R} y1={y(meta)} y2={y(meta)} stroke={COR.verde} strokeDasharray="5 4" strokeWidth={1.4} />
      <text x={L + 6} y={y(meta) - 7} fontSize={11} fill={COR.verde}>
        meta contratada ({Math.round(meta * 100)}%)
      </text>

      <path
        d={caminho(pontos.map((p) => [x(p.custo), y(p.nivel_servico)]))}
        fill="none"
        stroke={COR.azul}
        strokeWidth={2}
      />
      {pontos.map((p) => (
        <g key={p.ajuste}>
          <circle
            cx={x(p.custo)}
            cy={y(p.nivel_servico)}
            r={p.delta === 0 ? 7 : 5}
            fill={p.delta === 0 ? COR.verde : COR.azul}
            stroke="#ffffff"
            strokeWidth={2}
          />
          <text
            x={x(p.custo)}
            y={y(p.nivel_servico) - 14}
            fontSize={11}
            fill={p.delta === 0 ? COR.verde : COR.texto}
            textAnchor="middle"
          >
            {p.ajuste}
          </text>
        </g>
      ))}
      {pontos.map((p, i) =>
        i % 2 === 0 ? (
          <text key={p.ajuste} x={x(p.custo)} y={H - 14} fontSize={10.5} fill={COR.eixo} textAnchor="middle">
            {`R$ ${(p.custo / 1000).toFixed(1)}k`}
          </text>
        ) : null,
      )}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={COR.eixo} />
      <text x={(W - R + L) / 2} y={H - 2} fontSize={11} fill={COR.eixo} textAnchor="middle">
        custo do dia
      </text>
    </svg>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   Simulador: demanda do cenário contra a escala escolhida
   ═══════════════════════════════════════════════════════════════════════ */

export function GraficoCenario({
  demanda,
  escala,
  escalaPublicada,
  altura = 260,
}: {
  demanda: number[];
  escala: number[];
  escalaPublicada: number[];
  altura?: number;
}) {
  const L = 44, R = 44, T = 16, B = 26;
  const W = 900, H = altura;
  const maxChamadas = Math.max(...demanda) * 1.15;
  const maxAgentes = Math.max(...escala, ...escalaPublicada) * 1.35;
  const x = escala2([0, 24], [L, W - R]);
  const y = escala2([0, maxChamadas], [H - B, T]);
  const yA = escala2([0, maxAgentes], [H - B, T]);
  const largura = (W - R - L) / 24;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={L} x2={W - R} y1={y(maxChamadas * f)} y2={y(maxChamadas * f)} stroke={COR.grade} />
          <text x={L - 8} y={y(maxChamadas * f) + 4} textAnchor="end" fontSize={11} fill={COR.eixo}>
            {Math.round(maxChamadas * f)}
          </text>
        </g>
      ))}

      {demanda.map((v, h) => (
        <rect
          key={h}
          x={x(h) + 3}
          y={y(v)}
          width={largura - 6}
          height={H - B - y(v)}
          rx={2.5}
          fill={COR.azul}
          fillOpacity={0.5}
        />
      ))}

      <path
        d={caminhoDegrau(escalaPublicada.map((v, h) => [x(h), yA(v)] as [number, number]), largura)}
        fill="none"
        stroke={COR.eixo}
        strokeWidth={1.6}
        strokeDasharray="5 4"
      />
      <path
        d={caminhoDegrau(escala.map((v, h) => [x(h), yA(v)] as [number, number]), largura)}
        fill="none"
        stroke={COR.laranja}
        strokeWidth={2.4}
      />

      {[0, 6, 12, 18, 24].map((h) => (
        <text key={h} x={h === 24 ? W - R : x(h)} y={H - 8} fontSize={11} fill={COR.eixo} textAnchor="middle">
          {String(h).padStart(2, "0")}h
        </text>
      ))}
      {[0, 0.5, 1].map((f) => (
        <text key={f} x={W - R + 8} y={yA(maxAgentes * f) + 4} fontSize={11} fill={COR.laranja}>
          {Math.round(maxAgentes * f)}
        </text>
      ))}
      <line x1={L} x2={W - R} y1={H - B} y2={H - B} stroke={COR.eixo} />
    </svg>
  );
}
