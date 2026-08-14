/**
 * O contrato entre o exportador Python e o painel.
 *
 * Cada campo aqui e produzido por `scripts/exportar_operacao.py`, que roda o
 * mesmo nucleo usado pelos notebooks e pela aplicacao Streamlit do modulo F1.
 * Nenhum numero desta interface e digitado a mao.
 */

export type Parametros = {
  tma_min: number;
  paciencia_min: number;
  meta_nivel_servico: number;
  custo_atendente_hora: number;
  /** Politica de escala da casa. Nao sai do modelo: e o que o RH pratica, e e o
   *  que converte atendentes-hora em gente contratada. */
  jornada_semanal_h: number;
  turno_h: number;
  shrinkage: number;
  replicacoes: number;
  nivel_servico_seg: number;
  semente: number;
  inicio_base: string;
  fim_base: string;
  corte_validacao: string;
  corte_teste: string;
  n_dias_base: number;
  n_horas_base: number;
  n_dias_teste: number;
};

export type Campo = {
  referencias: { nome: string; mae: number }[];
  melhor_referencia: string;
  mae_referencia: number;
  mae_piso: number;
};

export type LinhaPlacar = {
  modelo: string;
  familia: string;
  mae: number;
  rmse: number;
  mape: number;
  wmape: number;
  rmse_mae: number;
  mase: number | null;
  aproveitado: number | null;
  tempo_s: number | null;
};

export type Campeao = {
  nome: string;
  mae: number;
  aproveitado: number;
  ganho_sobre_referencia: number;
  importancias: { variavel: string; peso: number }[];
};

export type DiaOperacao = {
  data: string;
  dia_semana: string;
  real: number[];
  intensidade: number[];
  previsto: number[];
  estatico: number[];
  escala: number[];
  escala_estatica: number[];
  /** Dimensionamento que o volume observado teria pedido — a régua da contingência. */
  escala_ideal: number[];
  ocupacao: number[];
  espera_erlang_s: number[];
  total_real: number;
  total_previsto: number;
  total_estatico: number;
  ocupacao_max: number;
  faixa_lo: number;
  faixa_hi: number;
  motivos: string[];
};

export type DiaFuturo = {
  data: string;
  dia_semana: string;
  previsto: number;
  faixa_lo: number;
  faixa_hi: number;
  pico_hora: number;
  pico_chamadas: number;
  atendentes_hora: number;
  pico_atendentes: number;
  custo: number;
  motivos: string[];
  escala: number[];
};

export type AoVivo = {
  fila: number[];
  ocupados: number[];
  capacidade: number[];
  chegadas_acum: number[];
  atendidos_acum: number[];
  abandonos_acum: number[];
  no_prazo_acum: number[];
  eventos: { minuto: number; tipo: "escala" | "alerta" | "demanda"; texto: string }[];
  /** Uma linha por ligação oferecida no dia: quando chegou, quando foi atendida
   *  e quando a chamada terminou (em minutos desde a meia-noite). */
  chamadas: {
    chegada: number;
    espera_s: number;
    atendido: boolean;
    inicio: number | null;
    fim: number | null;
  }[];
};

export type ResultadoDia = {
  chamadas: number;
  espera_media_s: number;
  espera_media_ic_s: number;
  espera_p90_s: number;
  nivel_servico: number;
  nivel_servico_ic: number;
  abandono: number;
  atendentes_hora: number;
  custo: number;
  erlang_espera_s: number;
  erlang_nivel_servico: number;
  por_replicacao: {
    replicacao: number;
    chamadas: number;
    espera_s: number;
    nivel_servico: number;
    abandono: number;
  }[];
};

export type Fonte = {
  fonte: string;
  atendentes_hora: number;
  custo: number;
  espera_s: number;
  espera_p90_s: number;
  nivel_servico: number;
  abandono: number;
};

export type DiaMes = {
  data: string;
  dia_semana: string;
  chamadas: number;
  modelo_sl: number;
  modelo_espera_s: number;
  modelo_abandono: number;
  modelo_custo: number;
  modelo_atendentes_hora: number;
  estatico_sl: number;
  estatico_espera_s: number;
  estatico_abandono: number;
  estatico_custo: number;
  estatico_atendentes_hora: number;
};

export type Cenario = {
  nome: string;
  fator: number;
  descricao: string;
  origem: string;
  demanda: number;
  atendentes_hora: number;
  pico_atendentes: number;
  custo: number;
  espera_s: number;
  nivel_servico: number;
  abandono: number;
  escala: number[];
};

export type PontoFronteira = {
  ajuste: string;
  delta: number;
  atendentes_hora: number;
  custo: number;
  nivel_servico: number;
  espera_s: number;
  abandono: number;
};

export type Operacao = {
  gerado_em: string;
  parametros: Parametros;
  campo: Campo;
  placar: LinhaPlacar[];
  campeao: Campeao;
  serie_diaria: { datas: string[]; real: number[]; previsto: number[]; referencia: number[] };
  previsao_14d: {
    data: string;
    dia_semana: string;
    previsto: number;
    faixa_lo: number;
    faixa_hi: number;
    real: number;
    erro: number;
  }[];
  erro_horizonte: { horizonte: number; mae: number }[];
  duas_etapas: { mae_duas_etapas: number; mae_estatico: number; mae_piso_horario: number };
  dia: DiaOperacao;
  proximos_dias: DiaFuturo[];
  ao_vivo: AoVivo;
  resultado_dia: ResultadoDia;
  distribuicao_espera: {
    bordas_s: number[];
    contagens: number[];
    p90_s: number;
    mediana_s: number;
  };
  comparacao_fontes: Fonte[];
  mes: {
    dias: DiaMes[];
    resumo: {
      modelo_sl: number;
      estatico_sl: number;
      modelo_espera_s: number;
      estatico_espera_s: number;
      modelo_abandono: number;
      estatico_abandono: number;
      modelo_custo: number;
      estatico_custo: number;
      modelo_atendentes_hora: number;
      estatico_atendentes_hora: number;
      chamadas: number;
      dias_simulados: number;
    };
  };
  cenarios: Cenario[];
  fronteira: PontoFronteira[];
  turnos: { turno: string; horas: string; media: number; pico: number; custo: number }[];
};
