import { Cartao } from "@/componentes/ui";
import { dataCurta, num, reais } from "@/lib/formato";
import type { Operacao } from "@/lib/tipos";

/**
 * A semana que vem, já dimensionada. É a tela que fecha escala: volume esperado,
 * gente necessária, custo — e o motivo de cada dia fugir do normal.
 */
export function ProximaSemana({ dados }: { dados: Operacao }) {
  const dias = dados.proximos_dias;
  if (dias.length === 0) return null;

  const maiorVolume = Math.max(...dias.map((d) => d.previsto));
  const totalChamadas = dias.reduce((a, d) => a + d.previsto, 0);
  const totalHoras = dias.reduce((a, d) => a + d.atendentes_hora, 0);
  const totalCusto = dias.reduce((a, d) => a + d.custo, 0);
  const maisLeve = [...dias].sort((a, b) => a.previsto - b.previsto)[0];
  const maisPesado = [...dias].sort((a, b) => b.previsto - a.previsto)[0];

  return (
    <Cartao
      titulo="Os próximos sete dias, já dimensionados"
      descricao="volume esperado, equipe necessária e custo — atualizados todo dia à meia-noite"
    >
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b border-borda text-left text-[0.7rem] uppercase tracking-wider text-tenue">
              <th className="pb-2 font-medium">Dia</th>
              <th className="pb-2 font-medium">Ligações esperadas</th>
              <th className="pb-2 text-right font-medium">Faixa provável</th>
              <th className="pb-2 text-right font-medium">Hora de pico</th>
              <th className="pb-2 text-right font-medium">Equipe</th>
              <th className="pb-2 text-right font-medium">Custo</th>
              <th className="pb-2 pl-4 font-medium">Por quê</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-borda/60">
            {dias.map((d) => (
              <tr key={d.data}>
                <td className="py-2.5 whitespace-nowrap">
                  <span className="text-suave">{d.dia_semana}</span>{" "}
                  <span className="numero text-[0.72rem] text-tenue">{dataCurta(d.data)}</span>
                </td>
                <td className="py-2.5 pr-4">
                  <div className="flex items-center gap-2.5">
                    <div className="h-1.5 w-28 overflow-hidden rounded-full bg-borda">
                      <div
                        className="h-full rounded-full bg-azul"
                        style={{ width: `${(d.previsto / maiorVolume) * 100}%` }}
                      />
                    </div>
                    <span className="numero text-texto">{num(d.previsto)}</span>
                  </div>
                </td>
                <td className="numero py-2.5 text-right text-[0.78rem] text-tenue">
                  {num(d.faixa_lo)} – {num(d.faixa_hi)}
                </td>
                <td className="py-2.5 text-right">
                  <span className="numero text-suave">{num(d.pico_chamadas)}</span>
                  <span className="text-[0.7rem] text-tenue">
                    {" "}
                    lig. às {String(d.pico_hora).padStart(2, "0")}h
                  </span>
                </td>
                <td className="numero py-2.5 text-right text-texto">
                  {num(d.atendentes_hora)}
                  <span className="text-[0.7rem] text-tenue"> h</span>
                </td>
                <td className="numero py-2.5 text-right text-suave">{reais(d.custo)}</td>
                <td className="py-2.5 pl-4 text-[0.75rem] text-tenue">
                  {d.motivos.length > 0 ? d.motivos.join(" · ") : "dia típico"}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-borda2 text-sm">
              <td className="pt-3 font-medium text-suave">Semana</td>
              <td className="numero pt-3 text-texto">{num(totalChamadas)}</td>
              <td />
              <td />
              <td className="numero pt-3 text-right text-texto">
                {num(totalHoras)}
                <span className="text-[0.7rem] text-tenue"> h</span>
              </td>
              <td className="numero pt-3 text-right text-texto">{reais(totalCusto)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>

      <p className="mt-5 text-[0.88rem] leading-relaxed text-suave">
        A semana não é plana, e é isso que a tabela mostra:{" "}
        <strong className="text-texto">{maisPesado.dia_semana.toLowerCase()}</strong> pede{" "}
        {num(maisPesado.atendentes_hora)} atendentes-hora e{" "}
        <strong className="text-texto">{maisLeve.dia_semana.toLowerCase()}</strong>, apenas{" "}
        {num(maisLeve.atendentes_hora)} —{" "}
        {num(100 * (1 - maisLeve.atendentes_hora / maisPesado.atendentes_hora), 0)}% a menos
        {maisLeve.motivos.length > 0 ? ` (${maisLeve.motivos[0]})` : ""}. Escalar o mesmo time todos
        os dias significa pagar gente ociosa no dia fraco e deixar fila no dia forte.
      </p>
    </Cartao>
  );
}
