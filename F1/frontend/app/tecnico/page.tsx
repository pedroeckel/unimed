import { Cadeia } from "@/componentes/Cadeia";
import { CenariosDecisao } from "@/componentes/CenariosDecisao";
import { Hero } from "@/componentes/Hero";
import { Modelos } from "@/componentes/Modelos";
import { PrevisaoOperacional } from "@/componentes/PrevisaoOperacional";
import { ResultadoDoDia } from "@/componentes/ResultadoDoDia";
import { ValorDaPrevisao } from "@/componentes/ValorDaPrevisao";
import { CabecalhoPagina } from "@/componentes/ui";
import { operacao } from "@/lib/dados";

export const metadata = {
  title: "Qualidade da previsão · Gêmeo Digital",
};

/**
 * A tela do time técnico: modelos, métricas, gêmeo digital e procedência.
 * As telas de operação não falam nada disso de propósito — o gestor decide
 * escala, não hiperparâmetro.
 */
export default function PaginaTecnica() {
  const dados = operacao;

  return (
    <>
      <CabecalhoPagina
        trilha={["Central de Atendimento", "Análise", "Qualidade da previsão"]}
        titulo="Qualidade da previsão"
        descricao="Como o sistema chega aos números da operação: o modelo em produção, o erro medido, a simulação de capacidade e a procedência de cada indicador."
        acoes={
          <span className="rounded-lg border border-borda bg-painel px-3 py-2 text-xs text-tenue">
            Atualizado em {dados.gerado_em.slice(0, 10).split("-").reverse().join("/")}
          </span>
        }
      />
      <Hero dados={dados} />
      <ResultadoDoDia dados={dados} />
      <ValorDaPrevisao dados={dados} />
      <Modelos dados={dados} />
      <PrevisaoOperacional dados={dados} />
      <CenariosDecisao dados={dados} />
      <Cadeia dados={dados} />
    </>
  );
}
