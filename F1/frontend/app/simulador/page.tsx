import { Simulador } from "@/componentes/Simulador";
import { CabecalhoPagina } from "@/componentes/ui";
import { operacao } from "@/lib/dados";

export const metadata = {
  title: "Simulador de cenários · Gêmeo Digital",
};

/**
 * A tela do "e se". O gêmeo roda no navegador a cada ajuste, então a pergunta
 * "quanto custa segurar o SLA se vier um surto?" tem resposta em tempo real —
 * antes de a decisão precisar ser tomada.
 */
export default function PaginaSimulador() {
  const dados = operacao;

  return (
    <>
      <CabecalhoPagina
        trilha={["Central de Atendimento", "Planejamento", "Simulador"]}
        titulo="Simulador de cenários"
        descricao="Mexa na demanda e no tamanho da equipe e veja o dia inteiro ser simulado de novo: fila, nível de serviço, abandono e custo. É o mesmo motor que valida a escala publicada todas as noites."
        acoes={
          <span className="rounded-lg border border-borda bg-painel px-3 py-2 text-xs text-tenue">
            Base: previsão de {dados.dia.dia_semana.toLowerCase()}, {dados.dia.data.slice(8, 10)}/
            {dados.dia.data.slice(5, 7)}
          </span>
        }
      />

      <div className="px-5 py-6 sm:px-7">
        <Simulador dados={dados} />
      </div>
    </>
  );
}
