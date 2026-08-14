import type { NextConfig } from "next";

/**
 * O painel e 100% estatico: os dados vem de `dados/operacao.json`, gerado pelo
 * exportador Python. Com EXPORT_ESTATICO=1, o build emite a pasta `out/`, que
 * pode ser aberta em qualquer lugar (inclusive sem servidor Node).
 */
const nextConfig: NextConfig = {
  output: process.env.EXPORT_ESTATICO ? "export" : undefined,
  images: { unoptimized: true },
};

export default nextConfig;
