"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

type Alerta = { minuto: number; texto: string };

const NAVEGACAO = [
  {
    grupo: "Operação",
    itens: [
      { href: "/", rotulo: "Hoje", icone: "◉" },
      { href: "/semana", rotulo: "Escala da semana", icone: "▤" },
    ],
  },
  {
    grupo: "Planejamento",
    itens: [{ href: "/simulador", rotulo: "Simulador de cenários", icone: "⌾" }],
  },
  {
    grupo: "Análise",
    itens: [{ href: "/tecnico", rotulo: "Qualidade da previsão", icone: "◈" }],
  },
];

const relogioDe = (minuto: number) =>
  `${String(Math.floor(minuto / 60) % 24).padStart(2, "0")}:${String(minuto % 60).padStart(2, "0")}`;

/**
 * O invólucro do produto: barra lateral, barra superior e área de conteúdo.
 *
 * A marca entra por `public/marca.svg` — basta soltar o arquivo oficial lá que
 * ele aparece no topo da barra lateral. Sem o arquivo, fica o texto.
 */
export function Shell({
  alertas,
  temMarca,
  children,
}: {
  alertas: Alerta[];
  temMarca: boolean;
  children: ReactNode;
}) {
  const caminho = usePathname();
  const [menuAberto, setMenuAberto] = useState(false);
  const [avisosAbertos, setAvisosAbertos] = useState(false);
  const [segundos, setSegundos] = useState(3);
  const avisos = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = setInterval(() => setSegundos((s) => (s >= 30 ? 1 : s + 1)), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!avisosAbertos) return;
    const fora = (e: MouseEvent) => {
      if (avisos.current && !avisos.current.contains(e.target as Node)) setAvisosAbertos(false);
    };
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, [avisosAbertos]);

  return (
    <div className="flex min-h-screen">
      {/* ── Barra lateral ────────────────────────────────────────────────── */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-60 shrink-0 flex-col bg-barra transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          menuAberto ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="border-b border-white/10 px-4 py-3.5">
          {temMarca ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img src="/marca.svg" alt="Unimed" className="h-9 w-auto" />
          ) : (
            <div className="flex items-baseline gap-1.5">
              <span className="text-[1.35rem] font-bold leading-none tracking-tight text-white">
                Unimed
              </span>
              <span className="text-[0.7rem] font-medium text-citrico">FESP</span>
            </div>
          )}
          <div className="mt-1.5 text-[0.68rem] uppercase tracking-[0.14em] text-white/55">
            Gêmeo Digital
          </div>
        </div>

        <div className="border-b border-white/10 px-3 py-3">
          <button className="flex w-full items-center gap-2.5 rounded-lg border border-white/15 bg-white/5 px-2.5 py-2 text-left transition hover:bg-white/10">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-citrico/25 text-[0.65rem] font-semibold text-citrico">
              CS
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs font-medium text-white">
                Central de Atendimento
              </span>
              <span className="block text-[0.65rem] text-white/55">Operadora · SP</span>
            </span>
            <span className="text-[0.6rem] text-white/55">▾</span>
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {NAVEGACAO.map((grupo) => (
            <div key={grupo.grupo} className="mb-5">
              <div className="mb-1.5 px-2 text-[0.62rem] font-semibold uppercase tracking-wider text-white/45">
                {grupo.grupo}
              </div>
              <div className="space-y-0.5">
                {grupo.itens.map((item) => {
                  const ativo = caminho === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMenuAberto(false)}
                      className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[0.82rem] transition ${
                        ativo
                          ? "bg-white/15 font-medium text-white"
                          : "text-white/70 hover:bg-white/10 hover:text-white"
                      }`}
                    >
                      <span className={`text-xs ${ativo ? "text-citrico" : "text-white/45"}`}>
                        {item.icone}
                      </span>
                      {item.rotulo}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="border-t border-white/10 px-4 py-3">
          <div className="flex items-center justify-between text-[0.68rem]">
            <span className="flex items-center gap-1.5 text-white/60">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-citrico" />
              Todos os serviços no ar
            </span>
            <span className="text-white/45">v1.4.2</span>
          </div>
          <div className="mt-1.5 text-[0.62rem] text-white/40">
            Ambiente de demonstração · dados sintéticos
          </div>
        </div>
      </aside>

      {menuAberto ? (
        <button
          aria-label="Fechar menu"
          onClick={() => setMenuAberto(false)}
          className="fixed inset-0 z-40 bg-black/40 lg:hidden"
        />
      ) : null}

      {/* ── Conteúdo ─────────────────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-borda bg-painel px-4 sm:px-7">
          <button
            onClick={() => setMenuAberto(true)}
            className="rounded-md border border-borda px-2 py-1 text-sm text-suave lg:hidden"
            aria-label="Abrir menu"
          >
            ☰
          </button>

          <span className="hidden items-center gap-2 rounded-full border border-borda bg-painel2 px-2.5 py-1 text-[0.7rem] text-suave sm:flex">
            <span className="pulso inline-block h-1.5 w-1.5 rounded-full bg-verde" />
            Sincronizado há {segundos}s
          </span>

          <div className="ml-auto flex items-center gap-2">
            <span className="hidden rounded-md border border-borda bg-painel2 px-2 py-1 text-[0.68rem] text-tenue sm:inline">
              Produção
            </span>

            <div className="relative" ref={avisos}>
              <button
                onClick={() => setAvisosAbertos((v) => !v)}
                className="relative rounded-md border border-borda bg-painel px-2.5 py-1.5 text-sm text-suave transition hover:border-borda2 hover:text-texto"
                aria-label="Avisos"
              >
                <svg
                  viewBox="0 0 20 20"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.6}
                >
                  <path
                    d="M10 3a4.5 4.5 0 0 0-4.5 4.5v2.7L4 13h12l-1.5-2.8V7.5A4.5 4.5 0 0 0 10 3Z"
                    strokeLinejoin="round"
                  />
                  <path d="M8.2 15.4a1.9 1.9 0 0 0 3.6 0" strokeLinecap="round" />
                </svg>
                {alertas.length > 0 ? (
                  <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-vermelho px-1 text-[0.6rem] font-semibold text-white">
                    {alertas.length}
                  </span>
                ) : null}
              </button>

              {avisosAbertos ? (
                <div className="surgir cartao absolute right-0 top-11 z-50 w-80 rounded-xl border border-borda bg-painel">
                  <div className="border-b border-borda px-4 py-2.5 text-xs font-semibold text-texto">
                    Avisos do dia
                  </div>
                  <div className="max-h-72 overflow-y-auto">
                    {alertas.length === 0 ? (
                      <p className="px-4 py-3 text-xs text-tenue">Nada a reportar.</p>
                    ) : (
                      alertas.map((a) => (
                        <div
                          key={`${a.minuto}-${a.texto}`}
                          className="flex gap-3 border-b border-borda/60 px-4 py-2.5 text-xs last:border-0"
                        >
                          <span className="numero shrink-0 text-tenue">{relogioDe(a.minuto)}</span>
                          <span className="text-suave">{a.texto}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="flex items-center gap-2 rounded-md border border-borda bg-painel py-1 pl-1 pr-2.5">
              <span className="flex h-6 w-6 items-center justify-center rounded bg-verde/10 text-[0.65rem] font-semibold text-verde">
                CO
              </span>
              <span className="hidden text-[0.72rem] text-suave sm:inline">Coordenação</span>
            </div>
          </div>
        </header>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
