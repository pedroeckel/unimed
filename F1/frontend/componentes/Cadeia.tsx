import { Cartao, Secao } from "@/componentes/ui";
import { num, pct, reais } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

const ETAPAS = [
  ["Dados", "diagnóstico da série: tendência, sazonalidade, estacionariedade", "F1_01 · F1_02"],
  ["Variáveis", "calendário, defasagens, janelas móveis — e o que a LGPD deixa usar", "F1_07 · F1_08"],
  ["Modelos", "referências, clássicos, árvores e boosting no mesmo teste", "F1_02 a F1_05"],
  ["Avaliação", "MAE, RMSE, MAPE, walk-forward e custo assimétrico", "F1_09"],
  ["Previsão", "D+1 a D+14 e a descida para a hora", "F1_07"],
  ["Gêmeo digital", "SimPy + Erlang C: erro de previsão vira fila e SLA", "D9 · D10"],
  ["Decisão", "cenários, fronteira custo × serviço, escala do turno", "E4"],
];

const GARANTIAS = [
  [
    "Separação cronológica",
    "Treino no passado, teste no futuro, sem sobreposição. Divisão aleatória faria o modelo aprender com o dia 15 e ser avaliado no 16 — o vizinho.",
  ],
  [
    "Nenhuma variável do futuro",
    "Toda janela móvel começa com defasagem. A linha de hoje é idêntica com e sem os dados de amanhã, e isso é verificado por teste automatizado.",
  ],
  [
    "Treino idêntico à produção",
    "Uma única função constrói as variáveis nos dois momentos. É o teste que a primeira versão do notebook F1_08 reprovou.",
  ],
  [
    "Piso do problema calculado",
    "A base é sintética justamente para que a intensidade verdadeira de cada hora seja conhecida. Modelo abaixo do piso não é conquista: é vazamento.",
  ],
  [
    "Simulação com replicações",
    "Uma rodada é um sorteio. Todo KPI do gêmeo é média entre replicações independentes, com intervalo de confiança de 95%.",
  ],
  [
    "Simulação checada contra a teoria",
    "Erlang C roda em paralelo como teste de sanidade. Quando as duas divergem, a diferença precisa ter explicação — aqui, o abandono.",
  ],
];

export function Cadeia({ dados }: { dados: Operacao }) {
  const p = dados.parametros;

  return (
    <Secao
      id="cadeia"
      etapa="Procedência"
      titulo="De onde vem cada número desta tela"
      chamada={
        <>
          Nenhum número deste painel foi digitado à mão. Todos saem de um exportador que roda o
          mesmo núcleo dos notebooks do módulo — geração da base, engenharia de variáveis, modelos,
          avaliação e gêmeo digital. Trocar um parâmetro e reexecutar refaz a tela inteira.
        </>
      }
    >
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-7">
        {ETAPAS.map(([titulo, descricao, origem], i) => (
          <div key={titulo} className="relative rounded-xl border border-borda bg-painel/70 p-4">
            <div className="numero text-[0.7rem] text-tenue">{String(i + 1).padStart(2, "0")}</div>
            <h3 className="mt-1 text-sm font-semibold text-texto">{titulo}</h3>
            <p className="mt-1.5 text-[0.72rem] leading-relaxed text-tenue">{descricao}</p>
            <p className="mt-3 text-[0.68rem] font-medium text-verde">{origem}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Cartao titulo="O que sustenta os números" descricao="as garantias metodológicas que o módulo exige">
          <div className="grid gap-3 sm:grid-cols-2">
            {GARANTIAS.map(([titulo, texto]) => (
              <div key={titulo} className="rounded-lg border border-borda bg-painel2/50 p-3">
                <h4 className="text-xs font-semibold text-texto">{titulo}</h4>
                <p className="mt-1 text-[0.72rem] leading-relaxed text-tenue">{texto}</p>
              </div>
            ))}
          </div>
        </Cartao>

        <Cartao titulo="Ficha técnica" descricao={`dados gerados em ${dados.gerado_em.replace("T", " às ")}`}>
          <dl className="space-y-2 text-sm">
            <Item rotulo="Período da base" valor={`${p.inicio_base} a ${p.fim_base}`} />
            <Item rotulo="Observações" valor={`${num(p.n_dias_base)} dias · ${num(p.n_horas_base)} horas`} />
            <Item rotulo="Corte de validação" valor={p.corte_validacao} />
            <Item rotulo="Corte de teste" valor={`${p.corte_teste} (${num(p.n_dias_teste)} dias)`} />
            <Item rotulo="Tempo médio de atendimento" valor={`${num(p.tma_min, 1)} min`} />
            <Item rotulo="Paciência média" valor={`${num(p.paciencia_min, 1)} min`} />
            <Item rotulo="Meta de nível de serviço" valor={`${pct(p.meta_nivel_servico, 0)} em ${num(p.nivel_servico_seg)}s`} />
            <Item rotulo="Custo do atendente-hora" valor={reais(p.custo_atendente_hora)} />
            <Item rotulo="Replicações do gêmeo" valor={num(p.replicacoes)} />
            <Item rotulo="Semente aleatória" valor={num(p.semente)} />
          </dl>
        </Cartao>
      </div>

      <div className="mt-6 rounded-2xl border border-borda bg-painel/50 px-5 py-4 text-xs leading-relaxed text-tenue">
        <strong className="text-suave">Sobre os dados.</strong> Toda a base é{" "}
        <strong className="text-suave">sintética e gerada em memória</strong>, com semente fixa.
        Nenhum dado de beneficiário real é usado, e nenhum número desta tela descreve a operação
        real de qualquer operadora. A decisão é didática: como somos nós que plantamos cada efeito
        dentro dos dados — o ciclo diário, o feriado, a janela de vencimento do boleto, a onda
        epidemiológica —, sabemos exatamente o que o modelo deveria descobrir e podemos verificar se
        ele descobriu.
      </div>

      <footer className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-borda pt-6 text-xs text-tenue">
        <span>
          Módulo F1 · Previsão de Demanda na Gestão de Planos de Saúde — Prof. Pedro | UNIMED SP
        </span>
        <span>Arco do curso: prever (F1) → integrar (D9) → simular (D10)</span>
      </footer>
    </Secao>
  );
}

function Item({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-borda/50 pb-1.5">
      <dt className="text-xs text-tenue">{rotulo}</dt>
      <dd className="numero text-[0.82rem] text-texto">{valor}</dd>
    </div>
  );
}
