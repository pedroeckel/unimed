import { CurvaEspera } from "@/componentes/graficos";
import { Alerta, Cartao, Kpi, Leitura, Secao } from "@/componentes/ui";
import { num, pct, reais, segundos } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

export function ResultadoDoDia({ dados }: { dados: Operacao }) {
  const { resultado_dia: r, distribuicao_espera: d, parametros, turnos, dia } = dados;
  const bateuMeta = r.nivel_servico >= parametros.meta_nivel_servico;

  return (
    <Secao
      id="resultado"
      etapa="Fechamento"
      titulo="O dia fechou assim"
      chamada={
        <>
          Uma rodada de simulação é um sorteio. O que se reporta é a média de{" "}
          {parametros.replicacoes} replicações independentes, com intervalo de confiança de 95% —
          e nunca o tempo de espera sozinho, porque espera baixa com abandono alto é uma operação
          que perde beneficiário no caminho.
        </>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Kpi
          valor={segundos(r.espera_media_s, 1)}
          rotulo="Espera média"
          tom="azul"
          nota={`± ${num(r.espera_media_ic_s, 1)}s (IC 95%)`}
        />
        <Kpi
          valor={segundos(r.espera_p90_s, 0)}
          rotulo="Espera no P90"
          tom="laranja"
          nota="1 em cada 10 esperou mais do que isso"
        />
        <Kpi
          valor={pct(r.nivel_servico, 1)}
          rotulo={`Atendidas em até ${num(parametros.nivel_servico_seg)}s`}
          tom={bateuMeta ? "verde" : "vermelho"}
          nota={`meta de ${pct(parametros.meta_nivel_servico, 0)}`}
        />
        <Kpi
          valor={pct(r.abandono, 1)}
          rotulo="Taxa de abandono"
          tom={r.abandono > 0.05 ? "vermelho" : "verde"}
          nota={`${num(r.chamadas * r.abandono)} ligações perdidas`}
        />
        <Kpi
          valor={reais(r.custo)}
          rotulo="Custo da escala do dia"
          tom="neutro"
          nota={`${num(r.atendentes_hora)} atendentes-hora × ${reais(parametros.custo_atendente_hora)}`}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Cartao
          titulo="Curva de espera"
          descricao="fração das ligações atendidas que já havia falado com um atendente até cada instante"
        >
          <CurvaEspera
            bordas={d.bordas_s}
            contagens={d.contagens}
            p90={d.p90_s}
            metaSeg={parametros.nivel_servico_seg}
          />
          <Leitura>
            A curva sobe quase a pique e depois se arrasta: a distribuição da espera é{" "}
            <strong className="text-texto">fortemente assimétrica</strong>. A mediana é de{" "}
            {segundos(d.mediana_s, 0)} — metade das pessoas fala com um atendente praticamente na
            hora —, mas o P90 é de {segundos(d.p90_s, 0)}, contra uma média de{" "}
            {segundos(r.espera_media_s, 1)}.{" "}
            <strong className="text-texto">Reportar só a média esconde a cauda</strong>, e é a cauda
            que gera reclamação na ouvidoria.
            <br />
            <br />
            <strong className="text-texto">Cuidado com o ponto verde.</strong> Ele mede as ligações{" "}
            <em>atendidas</em>, e por isso fica acima do nível de serviço oficial de{" "}
            {pct(r.nivel_servico, 1)}: o indicador contratual conta sobre as ligações{" "}
            <strong className="text-texto">oferecidas</strong>, e quem abandonou entra nele como não
            atendido.
          </Leitura>
        </Cartao>

        <div className="space-y-4">
          <Cartao titulo="A escala que foi ao ar" descricao="dimensionada por Erlang C, validada por simulação">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-borda text-left text-[0.7rem] uppercase tracking-wider text-tenue">
                  <th className="pb-2 font-medium">Turno</th>
                  <th className="pb-2 text-right font-medium">Média</th>
                  <th className="pb-2 text-right font-medium">Pico</th>
                  <th className="pb-2 text-right font-medium">Custo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borda/60">
                {turnos.map((t) => (
                  <tr key={t.turno}>
                    <td className="py-2 text-suave">{t.turno}</td>
                    <td className="numero py-2 text-right text-texto">{num(t.media, 1)}</td>
                    <td className="numero py-2 text-right text-texto">{t.pico}</td>
                    <td className="numero py-2 text-right text-suave">{reais(t.custo)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-3 text-xs text-tenue">
              Ocupação máxima prevista para o dia: {num(dia.ocupacao_max, 2)}. Acima de 0,85 a
              relação entre ocupação e fila deixa de ser suave — sair de 0,85 para 0,92 multiplica a
              espera.
            </p>
          </Cartao>

          <Cartao titulo="Checagem contra a teoria" descricao="Erlang C, o padrão de call center desde 1917">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg border border-borda bg-painel2/60 px-3 py-2.5">
                <div className="text-[0.68rem] uppercase tracking-wider text-tenue">Fórmula</div>
                <div className="numero mt-1 text-lg text-texto">{segundos(r.erlang_espera_s, 0)}</div>
                <div className="text-[0.7rem] text-tenue">{pct(r.erlang_nivel_servico, 0)} em {num(parametros.nivel_servico_seg)}s</div>
              </div>
              <div className="rounded-lg border border-borda bg-painel2/60 px-3 py-2.5">
                <div className="text-[0.68rem] uppercase tracking-wider text-tenue">Gêmeo (SimPy)</div>
                <div className="numero mt-1 text-lg text-texto">{segundos(r.espera_media_s, 1)}</div>
                <div className="text-[0.7rem] text-tenue">{pct(r.nivel_servico, 0)} em {num(parametros.nivel_servico_seg)}s</div>
              </div>
            </div>
            <Alerta>
              As duas contas <strong className="text-texto">divergem de propósito</strong>, e a
              diferença é a lição. Erlang C assume{" "}
              <strong className="text-texto">paciência infinita</strong>: na fórmula, ninguém
              desiste, então a fila de um dia sobrecarregado cresce sem limite. No gêmeo,{" "}
              {pct(r.abandono, 1)} das pessoas desligaram antes de serem atendidas — e{" "}
              <strong className="text-texto">quem abandona não entra na conta da espera</strong>.
              Foi o abandono que &ldquo;melhorou&rdquo; o tempo, não a operação.
            </Alerta>
          </Cartao>
        </div>
      </div>

      <div className="mt-4">
        <Cartao titulo="As replicações, uma a uma" descricao="a variabilidade entre rodadas é parte do resultado">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b border-borda text-left text-[0.7rem] uppercase tracking-wider text-tenue">
                  <th className="pb-2 font-medium">Replicação</th>
                  <th className="pb-2 text-right font-medium">Ligações</th>
                  <th className="pb-2 text-right font-medium">Espera média</th>
                  <th className="pb-2 text-right font-medium">Nível de serviço</th>
                  <th className="pb-2 text-right font-medium">Abandono</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borda/60">
                {r.por_replicacao.map((linha) => (
                  <tr key={linha.replicacao}>
                    <td className="py-1.5 text-suave">#{linha.replicacao}</td>
                    <td className="numero py-1.5 text-right text-texto">{num(linha.chamadas)}</td>
                    <td className="numero py-1.5 text-right text-texto">{segundos(linha.espera_s, 1)}</td>
                    <td className="numero py-1.5 text-right text-texto">{pct(linha.nivel_servico, 1)}</td>
                    <td className="numero py-1.5 text-right text-texto">{pct(linha.abandono, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Cartao>
      </div>
    </Secao>
  );
}
