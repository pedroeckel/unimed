import { GraficoLinhas } from "@/componentes/graficos";
import { Cartao, Kpi, Legenda, Leitura, Secao } from "@/componentes/ui";
import { dataCurta, num } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

export function PrevisaoOperacional({ dados }: { dados: Operacao }) {
  const { serie_diaria, previsao_14d, erro_horizonte, duas_etapas, campo, campeao } = dados;
  const d1 = erro_horizonte[0].mae;
  const d7 = erro_horizonte[6].mae;
  const d14 = erro_horizonte[13].mae;

  return (
    <Secao
      id="previsao"
      etapa="Da previsão para a escala"
      titulo="Um número por dia não escala turno nenhum"
      chamada={
        <>
          O modelo entrega um total diário. A escala é montada por hora. A ponte é uma tabela
          simples: <strong className="text-texto">previsão do dia × perfil intradiário</strong>,
          estimado só com dados de treino e separado por dia da semana. Duas etapas, um modelo só —
          e uma frase que qualquer gestor audita.
        </>
      }
    >
      <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Cartao
          titulo="Previsão contra realidade no período de teste"
          descricao={`${serie_diaria.datas.length} dias que o modelo nunca viu durante o ajuste`}
        >
          <GraficoLinhas
            series={[
              { nome: "real", valores: serie_diaria.real, cor: "#004e4c", largura: 1.6 },
              { nome: "previsto", valores: serie_diaria.previsto, cor: "#00995d", largura: 2 },
            ]}
            rotulosX={serie_diaria.datas.map(dataCurta)}
            altura={250}
          />
          <div className="mt-3">
            <Legenda
              itens={[
                { cor: "#004e4c", texto: "ligações que chegaram" },
                { cor: "#00995d", texto: `previsão do ${campeao.nome}` },
              ]}
            />
          </div>
          <Leitura>
            O modelo acompanha o nível e o ciclo semanal quase colado. O que ele{" "}
            <strong className="text-texto">não</strong> acompanha são os saltos súbitos — e é
            proposital: a base tem surtos que começam de repente e decaem por semanas. Nenhum modelo
            adivinha o início de um surto; o que um bom modelo faz é reagir rápido a ele. Os dias em
            que a linha verde fica abaixo da azul são exatamente os dias em que a operação sofre.
          </Leitura>
        </Cartao>

        <Cartao titulo="As duas últimas semanas, com faixa provável" descricao="quantis 10% e 90% dos resíduos observados">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-borda text-left text-[0.7rem] uppercase tracking-wider text-tenue">
                  <th className="pb-2 font-medium">Dia</th>
                  <th className="pb-2 text-right font-medium">Previsto</th>
                  <th className="pb-2 text-right font-medium">Faixa</th>
                  <th className="pb-2 text-right font-medium">Real</th>
                  <th className="pb-2 text-right font-medium">Erro</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borda/60">
                {previsao_14d.map((l) => (
                  <tr key={l.data}>
                    <td className="py-1.5 text-suave">
                      {dataCurta(l.data)}{" "}
                      <span className="text-[0.68rem] text-tenue">{l.dia_semana.slice(0, 3)}</span>
                    </td>
                    <td className="numero py-1.5 text-right text-texto">{num(l.previsto)}</td>
                    <td className="numero py-1.5 text-right text-[0.75rem] text-tenue">
                      {num(l.faixa_lo)}–{num(l.faixa_hi)}
                    </td>
                    <td className="numero py-1.5 text-right text-suave">{num(l.real)}</td>
                    <td
                      className={`numero py-1.5 text-right ${
                        Math.abs(l.erro) > campeao.mae * 1.5 ? "text-laranja" : "text-tenue"
                      }`}
                    >
                      {l.erro > 0 ? "+" : ""}
                      {num(l.erro)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-tenue">
            A faixa não vem de hipótese de normalidade: são os quantis dos resíduos já observados. É
            a forma honesta de declarar incerteza quando o modelo não produz intervalo por conta
            própria — o caso de todos os modelos de árvore.
          </p>
        </Cartao>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Cartao
          titulo="Até onde dá para prever"
          descricao="previsão recursiva: o modelo passa a se alimentar das próprias previsões"
        >
          <GraficoLinhas
            series={[
              {
                nome: "MAE",
                valores: erro_horizonte.map((e) => e.mae),
                cor: "#f47920",
                largura: 2.4,
              },
            ]}
            rotulosX={erro_horizonte.map((e) => `D+${e.horizonte}`)}
            altura={220}
            minimoY={0}
            marcoY={{
              valor: campo.mae_referencia,
              rotulo: "melhor referência simples",
              cor: "#ed1651",
            }}
          />
          <Leitura>
            Em <strong className="text-texto">D+1</strong> o erro é de {num(d1, 1)} ligações — a
            janela útil para remanejar equipe dentro da semana. Em{" "}
            <strong className="text-texto">D+7</strong> sobe para {num(d7, 1)}, e em{" "}
            <strong className="text-texto">D+14</strong> chega a {num(d14, 1)}, ainda{" "}
            {d14 < campo.mae_referencia ? "abaixo" : "acima"} da melhor referência simples. A curva{" "}
            <strong className="text-texto">satura em vez de explodir</strong> porque as colunas de
            calendário continuam corretas no futuro. Tradução operacional: feche a escala base com
            14 dias usando o calendário e ajuste o fino em D-1, quando o modelo já viu o volume de
            ontem.
          </Leitura>
        </Cartao>

        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Kpi
              valor={num(duas_etapas.mae_estatico, 2)}
              rotulo="MAE/hora — média histórica"
              tom="vermelho"
            />
            <Kpi
              valor={num(duas_etapas.mae_duas_etapas, 2)}
              rotulo="MAE/hora — duas etapas"
              tom="verde"
            />
            <Kpi valor={num(duas_etapas.mae_piso_horario, 2)} rotulo="MAE/hora — piso" tom="azul" />
          </div>
          <Cartao>
            <p className="text-[0.88rem] leading-relaxed text-suave">
              <strong className="text-texto">Por que duas etapas, e não um modelo horário.</strong>{" "}
              Treinar direto na série horária significa 17.520 linhas, mais um artefato para
              versionar e monitorar, e uma explicação mais difícil. A estratégia de duas etapas
              chega a {num(duas_etapas.mae_duas_etapas, 2)} ligações por hora — a{" "}
              {num(duas_etapas.mae_duas_etapas - duas_etapas.mae_piso_horario, 2)} do piso teórico e
              muito à frente das {num(duas_etapas.mae_estatico, 2)} do input estático. Para decisão
              de escala, a diferença para um modelo horário dedicado é irrelevante; a diferença de
              manutenção não é.
            </p>
            <p className="mt-3 text-[0.88rem] leading-relaxed text-suave">
              E a frase que sai daqui é auditável por qualquer gestor:{" "}
              <em className="text-texto">
                &ldquo;prevemos {num(dados.dia.total_previsto)} ligações para{" "}
                {dados.dia.dia_semana.toLowerCase()}, e historicamente{" "}
                {num((dados.dia.previsto[10] / dados.dia.total_previsto) * 100, 1)}% delas chegam
                entre 10h e 11h&rdquo;.
              </em>
            </p>
          </Cartao>
        </div>
      </div>
    </Secao>
  );
}
