import bruto from "@/dados/operacao.json";
import type { Operacao } from "./tipos";

/**
 * O JSON e gerado por `scripts/exportar_operacao.py` e entra no bundle direto,
 * sem servidor de dados: o painel e uma leitura de um resultado ja calculado,
 * exatamente como um relatorio executivo fechado no fim do dia.
 */
export const operacao = bruto as unknown as Operacao;

export const NOMES_TURNO = [
  { nome: "Madrugada", de: 0, ate: 5 },
  { nome: "Manhã", de: 6, ate: 11 },
  { nome: "Tarde", de: 12, ate: 17 },
  { nome: "Noite", de: 18, ate: 23 },
];

export function turnoDaHora(hora: number): string {
  return NOMES_TURNO.find((t) => hora >= t.de && hora <= t.ate)?.nome ?? "Madrugada";
}
