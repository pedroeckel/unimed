/** Formatacao no padrao brasileiro. Numero mal formatado em painel executivo
 *  custa credibilidade antes de qualquer discussao sobre o metodo. */

const nf = (casas: number) =>
  new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export function num(valor: number | null | undefined, casas = 0): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "—";
  return nf(casas).format(valor);
}

export function pct(fracao: number | null | undefined, casas = 1): string {
  if (fracao === null || fracao === undefined || !Number.isFinite(fracao)) return "—";
  return `${nf(casas).format(fracao * 100)}%`;
}

export function reais(valor: number | null | undefined, casas = 0): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "—";
  return `R$ ${nf(casas).format(valor)}`;
}

export function segundos(valor: number | null | undefined, casas = 0): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "—";
  if (valor < 60) return `${nf(casas).format(valor)}s`;
  const min = Math.floor(valor / 60);
  const seg = Math.round(valor % 60);
  return `${min}min ${String(seg).padStart(2, "0")}s`;
}

export function relogio(minuto: number): string {
  const h = Math.floor(minuto / 60) % 24;
  const m = Math.floor(minuto % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

const DIAS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];
const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

/** Datas chegam como "2025-10-06"; construir com `new Date(iso)` puxaria fuso. */
export function dataLonga(iso: string): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  const d = new Date(ano, mes - 1, dia);
  return `${DIAS[d.getDay()]}, ${dia} de ${MESES[mes - 1]} de ${ano}`;
}

export function dataCurta(iso: string): string {
  const [, mes, dia] = iso.split("-").map(Number);
  return `${String(dia).padStart(2, "0")}/${String(mes).padStart(2, "0")}`;
}
