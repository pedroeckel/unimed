"use client";

import type { DiaFuturo } from "@/lib/tipos";

const CABECALHO = [
  "data",
  "dia_semana",
  "ligacoes_previstas",
  "faixa_minima",
  "faixa_maxima",
  "hora_de_pico",
  "atendentes_hora",
  "pico_de_atendentes",
  "custo_estimado",
  "observacao",
];

/** Exporta a escala da semana em CSV — separador ";" e BOM, que é o que o
 *  Excel em português abre sem perguntar nada. */
export function BotaoExportar({ dias }: { dias: DiaFuturo[] }) {
  const baixar = () => {
    const linhas = [
      CABECALHO,
      ...dias.map((d) => [
        d.data,
        d.dia_semana,
        String(d.previsto),
        String(d.faixa_lo),
        String(d.faixa_hi),
        `${String(d.pico_hora).padStart(2, "0")}:00`,
        String(d.atendentes_hora),
        String(d.pico_atendentes),
        String(d.custo).replace(".", ","),
        d.motivos.join(" / ") || "dia tipico",
      ]),
    ];
    const csv = linhas.map((l) => l.join(";")).join("\r\n");
    const blob = new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `escala-semana-${dias[0]?.data ?? "export"}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <button
      onClick={baixar}
      className="rounded-lg border border-borda bg-painel px-3 py-2 text-xs text-suave transition hover:border-borda2 hover:text-texto"
    >
      ↓ Exportar CSV
    </button>
  );
}
