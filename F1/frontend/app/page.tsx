import Link from "next/link";

import { PainelOperacao } from "@/componentes/PainelOperacao";
import { PlanoDoDia } from "@/componentes/PlanoDoDia";
import { StatusSistema } from "@/componentes/StatusSistema";
import { Bloco, CabecalhoPagina } from "@/componentes/ui";
import { operacao } from "@/lib/dados";
import { dataLonga, num } from "@/lib/formato";

export default function Pagina() {
  const dados = operacao;
  const [, mes, dia] = dados.dia.data.split("-");

  return (
    <>
      <CabecalhoPagina
        trilha={["Central de Atendimento", "Operação", "Hoje"]}
        titulo="Operação de hoje"
        descricao="A demanda foi prevista ontem à noite, a escala saiu dessa previsão e o dia está em curso. Esta tela mostra as três coisas ao mesmo tempo."
        acoes={
          <>
            <span className="rounded-lg border border-borda bg-painel px-3 py-2 text-xs text-suave">
              <span className="text-tenue">Dia </span>
              <span className="numero">
                {dados.dia.dia_semana}, {dia}/{mes}
              </span>
            </span>
            <Link
              href="/semana"
              className="rounded-lg border border-borda bg-painel px-3 py-2 text-xs text-suave transition hover:border-borda2 hover:text-texto"
            >
              Escala da semana →
            </Link>
          </>
        }
      />

      <div className="space-y-8 px-5 py-6 sm:px-7">
        <StatusSistema dia={dados.dia} />

        <Bloco
          titulo="A central agora"
          descricao={`${dataLonga(dados.dia.data)} · ligações, fila e equipe minuto a minuto`}
        >
          <PainelOperacao dia={dados.dia} aoVivo={dados.ao_vivo} parametros={dados.parametros} />
        </Bloco>

        <Bloco
          titulo="Escala publicada"
          descricao={`dimensionada para as ${num(dados.dia.total_previsto)} ligações previstas para hoje`}
        >
          <PlanoDoDia dados={dados} />
        </Bloco>
      </div>
    </>
  );
}
