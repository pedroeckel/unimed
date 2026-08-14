import fs from "node:fs";
import path from "node:path";

import type { Metadata } from "next";

import { Shell } from "@/componentes/Shell";
import { operacao } from "@/lib/dados";

import "./globals.css";

export const metadata: Metadata = {
  title: "Gêmeo Digital · Central de Atendimento",
  description:
    "Plataforma de previsão de demanda e dimensionamento de equipe para centrais de atendimento.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  /** Marca oficial: basta soltar o arquivo em `public/marca.svg`. */
  const temMarca = fs.existsSync(path.join(process.cwd(), "public", "marca.svg"));

  const alertas = operacao.ao_vivo.eventos
    .filter((e) => e.tipo === "alerta")
    .map((e) => ({ minuto: e.minuto, texto: e.texto }));

  return (
    <html lang="pt-BR" className="h-full">
      <body className="min-h-full">
        <Shell alertas={alertas} temMarca={temMarca}>
          {children}
        </Shell>
      </body>
    </html>
  );
}
