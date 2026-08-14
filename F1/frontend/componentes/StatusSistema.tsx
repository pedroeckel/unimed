import { num } from "@/lib/formato";
import type { DiaOperacao } from "@/lib/tipos";

const PASSOS = [
  { rotulo: "Coleta dos dados de ontem", detalhe: "23h45", pronto: true },
  { rotulo: "Previsão do dia", detalhe: "23h50", pronto: true },
  { rotulo: "Dimensionamento da escala", detalhe: "23h55", pronto: true },
  { rotulo: "Operação em curso", detalhe: "agora", pronto: false },
];

/**
 * O estado do ciclo diário: o que já rodou de madrugada e o que está rodando
 * agora. É a primeira coisa que um gestor procura — "o sistema fez a parte
 * dele?".
 */
export function StatusSistema({ dia }: { dia: DiaOperacao }) {
  return (
    <div className="rounded-xl border border-borda bg-painel">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-borda px-5 py-3.5">
        <div className="flex items-center gap-2.5">
          <span className="pulso inline-block h-2 w-2 rounded-full bg-verde" />
          <span className="text-[0.85rem] font-semibold text-texto">Rotina diária</span>
          <span className="text-xs text-tenue">3 de 3 etapas concluídas · nenhuma falha</span>
        </div>

        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-2">
          {PASSOS.map((p, i) => (
            <span key={p.rotulo} className="flex items-center gap-1.5">
              <span
                className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[0.68rem] ${
                  p.pronto
                    ? "border-borda2 bg-painel2 text-suave"
                    : "border-verde/40 bg-verde/10 text-verde"
                }`}
              >
                <span>{p.pronto ? "✓" : <span className="pulso inline-block">●</span>}</span>
                {p.rotulo}
                <span className="text-tenue">{p.detalhe}</span>
              </span>
              {i < PASSOS.length - 1 ? <span className="text-borda2">→</span> : null}
            </span>
          ))}
        </div>
      </div>

      <p className="px-5 py-3.5 text-sm text-suave">
        Para hoje o sistema espera{" "}
        <strong className="numero text-texto">{num(dia.total_previsto)} ligações</strong>{" "}
        <span className="text-tenue">
          (entre {num(dia.faixa_lo)} e {num(dia.faixa_hi)}, em 8 de cada 10 dias parecidos)
        </span>
        {dia.motivos.length > 0 ? <> — {dia.motivos.join(" e ")}.</> : "."}
      </p>
    </div>
  );
}
