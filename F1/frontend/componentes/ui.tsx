import type { ReactNode } from "react";

/** O cabeçalho padrão de uma tela do produto: trilha, título, ações. */
export function CabecalhoPagina({
  trilha,
  titulo,
  descricao,
  acoes,
}: {
  trilha: string[];
  titulo: string;
  descricao?: ReactNode;
  acoes?: ReactNode;
}) {
  return (
    <div className="border-b border-borda bg-barra/40">
      <div className="px-5 py-5 sm:px-7">
        <nav className="flex items-center gap-1.5 text-[0.72rem] text-tenue">
          {trilha.map((t, i) => (
            <span key={t} className="flex items-center gap-1.5">
              {i > 0 ? <span className="text-borda2">/</span> : null}
              <span className={i === trilha.length - 1 ? "text-suave" : undefined}>{t}</span>
            </span>
          ))}
        </nav>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-texto sm:text-2xl">
              {titulo}
            </h1>
            {descricao ? (
              <p className="mt-1.5 max-w-2xl text-[0.85rem] leading-relaxed text-suave">
                {descricao}
              </p>
            ) : null}
          </div>
          {acoes ? <div className="flex flex-wrap items-center gap-2">{acoes}</div> : null}
        </div>
      </div>
    </div>
  );
}

/** Um bloco de conteúdo dentro de uma tela. Discreto de propósito: em produto,
 *  o título da seção não disputa atenção com o dado. */
export function Bloco({
  titulo,
  descricao,
  acoes,
  children,
  className = "",
}: {
  titulo: string;
  descricao?: ReactNode;
  acoes?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`space-y-3 ${className}`}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-[0.92rem] font-semibold tracking-tight text-texto">{titulo}</h2>
          {descricao ? <p className="mt-0.5 text-xs text-tenue">{descricao}</p> : null}
        </div>
        {acoes}
      </div>
      {children}
    </section>
  );
}

export function Secao({
  id,
  etapa,
  titulo,
  chamada,
  children,
}: {
  id: string;
  etapa: string;
  titulo: string;
  chamada?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-borda/70 py-10">
      <div className="px-5 sm:px-7">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.22em] text-verde">
          {etapa}
        </p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-texto sm:text-3xl">
          {titulo}
        </h2>
        {chamada ? (
          <p className="mt-3 max-w-3xl text-[0.95rem] leading-relaxed text-suave">{chamada}</p>
        ) : null}
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}

export function Cartao({
  children,
  className = "",
  titulo,
  descricao,
}: {
  children: ReactNode;
  className?: string;
  titulo?: string;
  descricao?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-borda bg-painel/80 p-5 shadow-[0_1px_0_0_rgba(255,255,255,0.03)_inset] ${className}`}
    >
      {titulo ? (
        <div className="mb-4">
          <h3 className="text-sm font-semibold tracking-tight text-texto">{titulo}</h3>
          {descricao ? <p className="mt-1 text-xs text-tenue">{descricao}</p> : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}

const TONS = {
  verde: "text-verde",
  azul: "text-azul",
  laranja: "text-laranja",
  vermelho: "text-vermelho",
  roxo: "text-roxo",
  neutro: "text-texto",
} as const;

export type Tom = keyof typeof TONS;

export function Kpi({
  valor,
  rotulo,
  nota,
  tom = "neutro",
  grande = false,
}: {
  valor: ReactNode;
  rotulo: string;
  nota?: ReactNode;
  tom?: Tom;
  grande?: boolean;
}) {
  return (
    <div className="rounded-xl border border-borda bg-painel2/70 px-4 py-3">
      <div
        className={`numero font-semibold tracking-tight ${TONS[tom]} ${
          grande ? "text-3xl" : "text-2xl"
        }`}
      >
        {valor}
      </div>
      <div className="mt-1 text-[0.72rem] font-medium uppercase tracking-wider text-tenue">
        {rotulo}
      </div>
      {nota ? <div className="mt-1.5 text-xs text-suave">{nota}</div> : null}
    </div>
  );
}

export function Selo({
  children,
  tom = "verde",
}: {
  children: ReactNode;
  tom?: "verde" | "azul" | "laranja" | "vermelho" | "neutro";
}) {
  const cores = {
    verde: "border-verde/40 bg-verde/10 text-verde",
    azul: "border-azul/40 bg-azul/10 text-azul",
    laranja: "border-laranja/40 bg-laranja/10 text-laranja",
    vermelho: "border-vermelho/40 bg-vermelho/10 text-vermelho",
    neutro: "border-borda2 bg-painel2 text-suave",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[0.7rem] font-medium ${cores[tom]}`}
    >
      {children}
    </span>
  );
}

/** A caixa de leitura guiada: um numero sem interpretacao e decoracao. */
export function Leitura({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border-l-2 border-verde bg-verde/[0.06] px-4 py-3.5 text-[0.88rem] leading-relaxed text-suave">
      {children}
    </div>
  );
}

export function Alerta({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border-l-2 border-laranja bg-laranja/[0.07] px-4 py-3.5 text-[0.88rem] leading-relaxed text-suave">
      {children}
    </div>
  );
}

export function Legenda({ itens }: { itens: { cor: string; texto: string; tracejada?: boolean }[] }) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-suave">
      {itens.map((i) => (
        <span key={i.texto} className="inline-flex items-center gap-2">
          <span
            className="inline-block h-0.5 w-4 rounded"
            style={{
              background: i.tracejada
                ? `repeating-linear-gradient(90deg, ${i.cor} 0 4px, transparent 4px 7px)`
                : i.cor,
            }}
          />
          {i.texto}
        </span>
      ))}
    </div>
  );
}
