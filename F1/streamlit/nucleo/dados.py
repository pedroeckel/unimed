"""
Geradores sintéticos do módulo F1.

Toda base é construída em memória, com semente fixa. A decisão é didática: como somos
nos que plantamos cada efeito dentro dos dados, sabemos exatamente o que o modelo
DEVERIA descobrir, e podemos verificar se ele descobriu.

Contrato obrigatório: toda função devolve, junto com a série observada, a INTENSIDADE
verdadeira (o sinal antes do sorteio aleatório). Sem ela não existe oráculo, e sem
oráculo não existe piso do problema.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEMENTE = 42

# Perfil relativo por HORA DO DIA (formato call center: madrugada calma, pico da manhã,
# queda no almoço, segundo pico à tarde). Mesmo perfil dos notebooks F1_01/04/06.
PERFIL_HORARIO = np.array([
    -8, -9, -9, -9, -8, -6,   # 0h a 5h   madrugada
    -3,  1,  5,  8,  9,  8,   # 6h a 11h  pico da manhã
     3,  2,  7,  8,  6,  3,   # 12h a 17h almoço e pico da tarde
    -1, -3, -4, -5, -6, -7,   # 18h a 23h fim do expediente
], dtype=float)

# Perfil relativo por DIA DA SEMANA (0 = segunda ... 6 = domingo)
PERFIL_SEMANAL = np.array([3, 1, 0, 1, 2, -2, -3], dtype=float)

# Perfil de chegadas ao PRONTO ATENDIMENTO (vale de madrugada, pico no início da noite)
PERFIL_PA = np.array([0.55, 0.42, 0.34, 0.30, 0.30, 0.36, 0.52, 0.78, 1.05, 1.28, 1.40, 1.36,
                      1.22, 1.15, 1.20, 1.28, 1.34, 1.40, 1.45, 1.38, 1.20, 1.02, 0.86, 0.70])
PERFIL_SEMANAL_PA = np.array([1.14, 1.02, 0.98, 0.97, 1.00, 0.92, 1.05])

FERIADOS = pd.to_datetime([
    "2024-01-01", "2024-02-12", "2024-02-13", "2024-03-29", "2024-04-21", "2024-05-01",
    "2024-05-30", "2024-09-07", "2024-10-12", "2024-11-02", "2024-11-15", "2024-11-20",
    "2024-12-25",
    "2025-01-01", "2025-03-03", "2025-03-04", "2025-04-18", "2025-04-21", "2025-05-01",
    "2025-06-19", "2025-09-07", "2025-10-12", "2025-11-02", "2025-11-15", "2025-11-20",
    "2025-12-25",
])

# Campanhas de comunicação da operadora: (início, duração em dias). Conhecidas de antemão,
# porque é a própria operadora que dispara o SMS.
CAMPANHAS = [("2024-04-08", 5), ("2024-09-16", 5), ("2025-03-10", 5),
             ("2025-08-11", 5), ("2025-10-20", 5)]

ESPECIALIDADES = {
    # nome: (base/dia, mês de pico, amplitude sazonal, % alta complexidade, taxa de negativa)
    "Ortopedia":         (34, 1, 0.22, 0.22, 0.11),
    "Cardiologia":       (26, 7, 0.18, 0.30, 0.08),
    "Oncologia":         (12, 0, 0.05, 0.62, 0.05),
    "Pneumologia":       (18, 7, 0.38, 0.24, 0.09),
    "Ginecologia":       (30, 3, 0.12, 0.14, 0.07),
    "Oftalmologia":      (28, 10, 0.15, 0.10, 0.13),
    "Gastroenterologia": (22, 5, 0.10, 0.20, 0.10),
    "Neurologia":        (16, 6, 0.12, 0.34, 0.12),
}

# Defasagens VERDADEIRAS embutidas no gerador do PA. A página 2 tenta descobri-las sozinha.
LAG_TEMPERATURA, LAG_CHUVA, LAG_GRIPE, LAG_DENGUE = 3, 0, 4, 7

INICIO = "2024-01-01"


# ═══════════════════════════════════════════════════════════════════════════════
# Auxiliares de calendário
# ═══════════════════════════════════════════════════════════════════════════════

def eh_feriado(datas) -> np.ndarray:
    return np.isin(pd.DatetimeIndex(datas).normalize(), FERIADOS).astype(int)


def eh_vespera(datas) -> np.ndarray:
    return np.isin(pd.DatetimeIndex(datas).normalize(),
                   pd.DatetimeIndex(FERIADOS) - pd.Timedelta(days=1)).astype(int)


def eh_pos_feriado(datas) -> np.ndarray:
    return np.isin(pd.DatetimeIndex(datas).normalize(),
                   pd.DatetimeIndex(FERIADOS) + pd.Timedelta(days=1)).astype(int)


def ferias_escolares(datas) -> np.ndarray:
    d = pd.DatetimeIndex(datas)
    return (d.month.isin([1, 7]) | ((d.month == 12) & (d.day >= 20))).astype(int)


def em_campanha(datas) -> np.ndarray:
    d = pd.DatetimeIndex(datas)
    dentro = np.zeros(len(d), dtype=int)
    for inicio, duracao in CAMPANHAS:
        ini = pd.Timestamp(inicio)
        dentro |= ((d >= ini) & (d < ini + pd.Timedelta(days=duracao))).astype(int)
    return dentro


def janela_vencimento(datas) -> np.ndarray:
    """Vencimento da mensalidade: dias 5 a 9 concentram boleto e segunda via."""
    d = pd.DatetimeIndex(datas)
    return ((d.day >= 5) & (d.day <= 9)).astype(int)


def fim_trimestre(datas) -> np.ndarray:
    d = pd.DatetimeIndex(datas)
    return (d.month.isin([3, 6, 9, 12]) & (d.day >= 25)).astype(int)


def _ondas_epidemiologicas(n_dias: int, g: np.random.Generator,
                           prob=0.010, meia_vida=12.0) -> np.ndarray:
    """Estado latente: surtos que começam de repente e decaem por semanas.

    Este componente é o coração didático da base: NENHUMA coluna de calendário o captura.
    Nenhum modelo adivinha quando um surto começa; o que um bom modelo faz é perceber
    que ele já começou, e para isso precisa olhar o passado recente.
    """
    surto = np.zeros(n_dias)
    decaimento = 0.5 ** (1.0 / meia_vida)
    atual = 0.0
    for d in range(n_dias):
        if g.random() < prob:
            atual += g.uniform(0.18, 0.42)
        atual *= decaimento
        surto[d] = atual
    return surto


# ═══════════════════════════════════════════════════════════════════════════════
# Caso principal: central de atendimento da operadora
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_central_horaria(dias: int = 730, semente: int = SEMENTE) -> pd.DataFrame:
    """Dois anos de volume horário de ligações na central da operadora.

    Estrutura multiplicativa:
        lambda(t) = nivel_dia x fator_hora x fator_semana x fator_feriado
                    x (1 + onda_anual + surto) x fator_vencimento x fator_campanha

    O número observado é um sorteio de Poisson dessa intensidade, o que da ao problema
    um PISO exato: quem conhecesse lambda erraria, em média, sqrt(2*lambda/pi).

    Colunas devolvidas:
        n_ligacoes  contagem observada (o que o sistema registra)
        intensidade lambda verdadeiro (o ORACULO, indisponível na vida real)
        surto       estado latente epidemiológico, em fração do nível
        onda_anual  sazonalidade anual, em fração do nível
    """
    g = np.random.default_rng(semente)
    n = dias * 24
    idx = pd.date_range(INICIO, periods=n, freq="h")
    hora = idx.hour.to_numpy()
    dsem = idx.dayofweek.to_numpy()
    doy = idx.dayofyear.to_numpy()
    dia_corrido = (idx.normalize() - idx.normalize()[0]).days.to_numpy()

    base = 22.0
    fator_hora = (base + PERFIL_HORARIO)[hora] / base
    fator_semana = (base + PERFIL_SEMANAL)[dsem] / base

    # Tendência: a carteira de beneficiários cresce, e com ela o volume de contatos.
    tendencia = 1.0 + 0.00022 * dia_corrido

    onda_anual = 0.12 * np.cos(2 * np.pi * (doy - 196) / 365.25)

    surto_diario = _ondas_epidemiologicas(dias, g)
    surto = surto_diario[np.clip(dia_corrido, 0, dias - 1)]

    fator_feriado = np.where(eh_feriado(idx) == 1, 0.45, 1.0)

    # Interação vencimento x hora: o efeito do boleto só existe no horário comercial.
    dentro_venc = janela_vencimento(idx) == 1
    comercial = (hora >= 8) & (hora <= 18)
    fator_venc = np.where(dentro_venc & comercial, 1.18, 1.0)

    fator_camp = np.where(em_campanha(idx) == 1, 1.25, 1.0)

    intensidade = (base * tendencia * fator_hora * fator_semana * fator_feriado
                   * (1.0 + onda_anual + surto) * fator_venc * fator_camp)
    intensidade = np.clip(intensidade, 0.3, None)

    df = pd.DataFrame({
        "n_ligacoes": g.poisson(intensidade).astype(float),
        "intensidade": intensidade,
        "surto": surto,
        "onda_anual": onda_anual,
    }, index=idx)
    df.index.name = "datahora"
    return df


def agregar_diario(central: pd.DataFrame) -> pd.DataFrame:
    """Total do dia. É nesse nível que a escala é fechada e que os modelos competem."""
    diario = pd.DataFrame({
        "n_ligacoes": central["n_ligacoes"].resample("D").sum(),
        "intensidade": central["intensidade"].resample("D").sum(),
        "surto": central["surto"].resample("D").mean(),
    })
    diario.index.name = "data"
    return diario


def perfil_intradiario(central: pd.DataFrame, ate: pd.Timestamp) -> pd.DataFrame:
    """Fração do total do dia que acontece em cada hora, por dia da semana.

    Estimado APENAS com dados até `até` (fim do treino). Sem esse recorte, o perfil
    conteria informação do futuro e a avaliação ficaria otimista.
    """
    treino = central.loc[:ate, "n_ligacoes"]
    perfil = treino.groupby([treino.index.dayofweek, treino.index.hour]).mean()
    perfil = perfil / perfil.groupby(level=0).sum()
    perfil = perfil.rename_axis(["dia_semana", "hora"]).rename("fracao")
    return perfil.reset_index()


def perfil_intradiario_medio(central: pd.DataFrame, ate: pd.Timestamp) -> pd.DataFrame:
    """Perfil único, sem separar por dia da semana. É o 'input estático' da apostila:
    uma taxa média fixa aplicada a todos os dias, que sobra na madrugada e falta no pico."""
    treino = central.loc[:ate, "n_ligacoes"]
    por_hora = treino.groupby(treino.index.hour).mean()
    fracao = (por_hora / por_hora.sum()).to_numpy()
    linhas = [{"dia_semana": d, "hora": h, "fracao": fracao[h]}
              for d in range(7) for h in range(24)]
    return pd.DataFrame(linhas)


# ═══════════════════════════════════════════════════════════════════════════════
# Caso secundário: chegadas ao pronto atendimento (lags externos a descobrir)
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_pa_diario(dias: int = 730, semente: int = SEMENTE) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Chegadas diárias ao PA é a tabela de variáveis externas.

    O ponto do caso: clima e epidemia afetam o PA com DEFASAGEM (3, 0, 4 e 7 dias),
    e a correlação bruta erra todas elas por causa da sazonalidade compartilhada.
    """
    g = np.random.default_rng(semente + 1)
    datas = pd.date_range(INICIO, periods=dias, freq="D")
    doy = datas.dayofyear.to_numpy()
    dsem = datas.dayofweek.to_numpy()

    # Externas: temperatura com onda anual, chuva, alertas de gripe (inverno) e dengue (verão)
    temp = 23 - 6 * np.cos(2 * np.pi * (doy - 196) / 365.25) + g.normal(0, 2.2, dias)
    chuva = np.clip(g.gamma(1.1, 4.0, dias) * (1 + 0.6 * np.cos(2 * np.pi * (doy - 15) / 365.25)), 0, None)
    gripe = np.clip(30 + 45 * np.cos(2 * np.pi * (doy - 200) / 365.25)
                    + np.convolve(g.normal(0, 26, dias), np.ones(5) / 5, mode="same"), 0, None)
    dengue = np.clip(25 + 40 * np.cos(2 * np.pi * (doy - 40) / 365.25)
                     + np.convolve(g.normal(0, 24, dias), np.ones(5) / 5, mode="same"), 0, None)

    def defasar(v, k):
        return np.concatenate([np.full(k, v[0]), v[:-k]]) if k > 0 else v.copy()

    # Sazonalidade anual PROPRIA do PA (demanda eletiva, férias, ciclo assistencial),
    # com fase deslocada em relação ao inverno. É ela que confunde a correlação bruta:
    # todas as séries sobem e descem ao longo do ano, então todas correlacionam com todas.
    base = 190.0
    nivel = (base * (1 + 0.00015 * np.arange(dias))
             * (1 + 0.16 * np.cos(2 * np.pi * (doy - 300) / 365.25)))
    efeito_semana = PERFIL_SEMANAL_PA[dsem]
    graus_frio = np.maximum(0, 19 - defasar(temp, LAG_TEMPERATURA))
    efeito_clima = 1 + 0.018 * graus_frio - 0.0040 * defasar(chuva, LAG_CHUVA)
    efeito_epi = 1 + 0.0030 * defasar(gripe, LAG_GRIPE) + 0.0045 * defasar(dengue, LAG_DENGUE)

    fator_fer = np.where(eh_feriado(datas) == 1, 0.74, 1.0)
    fator_fer = np.where(eh_vespera(datas) == 1, 0.81, fator_fer)
    fator_fer = np.where(eh_pos_feriado(datas) == 1, 1.077, fator_fer)
    fator_ferias = np.where(ferias_escolares(datas) == 1, 1.09, 1.0)

    intensidade = np.clip(nivel * efeito_semana * efeito_clima * efeito_epi
                          * fator_fer * fator_ferias, 5, None)

    chegadas = pd.DataFrame({"chegadas": g.poisson(intensidade).astype(float),
                             "intensidade": intensidade}, index=datas)
    chegadas.index.name = "data"
    externas = pd.DataFrame({"temp_media": temp, "chuva_mm": chuva,
                             "alerta_gripe": gripe, "alerta_dengue": dengue}, index=datas)
    externas.index.name = "data"
    return chegadas, externas


# ═══════════════════════════════════════════════════════════════════════════════
# Caso secundário: autorizações prévia por especialidade (painel + LGPD)
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_autorizacoes(dias: int = 730, semente: int = SEMENTE) -> pd.DataFrame:
    """Painel dia x especialidade de solicitações de autorizações prévia.

    Traz as colunas de perfil do beneficiário (idade média, % 60+, % crônico) que
    são o objeto da discussão de LGPD: elas descrevem QUEM solicitou naquele dia,
    então só podem entrar no modelo defasadas.
    """
    g = np.random.default_rng(semente + 2)
    datas = pd.date_range(INICIO, periods=dias, freq="D")
    dsem = datas.dayofweek.to_numpy()
    doy = datas.dayofyear.to_numpy()

    fator_dsem = np.array([1.28, 1.18, 1.12, 1.10, 1.02, 0.34, 0.12])[dsem]
    fator_fer = np.where(eh_feriado(datas) == 1, 0.119, 1.0)
    fator_venc = np.where(janela_vencimento(datas) == 1, 1.11, 1.0)
    fator_tri = np.where(fim_trimestre(datas) == 1, 1.26, 1.0)
    fator_camp = np.where(em_campanha(datas) == 1, 1.456, 1.0)
    onda = 1 + _ondas_epidemiologicas(dias, g, prob=0.012, meia_vida=10.0)

    linhas = []
    for nome, (base, mes_pico, amp, pct_alta, taxa_neg) in ESPECIALIDADES.items():
        sazonal = 1 + amp * np.cos(2 * np.pi * (doy - mes_pico * 30.4) / 365.25)
        intensidade = np.clip(base * fator_dsem * fator_fer * fator_venc * fator_tri
                              * fator_camp * sazonal * onda, 0.2, None)
        solicitacoes = g.poisson(intensidade).astype(float)
        idade_base = 42 + 22 * pct_alta
        linhas.append(pd.DataFrame({
            "data": datas,
            "especialidade": nome,
            "solicitacoes": solicitacoes,
            "intensidade": intensidade,
            # Perfil do beneficiário: descreve o próprio dia, só entra defasado.
            "idade_media": idade_base + 3.5 * (onda - 1) * 10 + g.normal(0, 1.6, dias),
            "pct_60mais": np.clip(0.18 + 0.55 * pct_alta + 0.05 * (onda - 1) * 10
                                  + g.normal(0, 0.02, dias), 0, 1),
            "pct_cronico": np.clip(0.22 + 0.40 * pct_alta + 0.09 * (onda - 1) * 10
                                   + g.normal(0, 0.025, dias), 0, 1),
            "pct_alta_complexidade": np.clip(pct_alta + g.normal(0, 0.02, dias), 0, 1),
            "taxa_negativa": np.clip(taxa_neg + g.normal(0, 0.015, dias), 0, 1),
        }))
    painel = pd.concat(linhas, ignore_index=True)
    return painel.sort_values(["especialidade", "data"]).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Caso secundário: carteira de vidas por contrato (painel, para o boosting)
# ═══════════════════════════════════════════════════════════════════════════════

SETORES = {
    # setor: (taxa base de adesão, taxa base de cancelamento, sensibilidade macro, meses de pico)
    "Construção Civil": (0.030, 0.026, 1.8, [3, 4]),
    "Comércio":         (0.024, 0.022, 1.4, [11, 12]),
    "Indústria":        (0.018, 0.015, 1.1, [2, 3]),
    "Serviços":         (0.022, 0.020, 1.0, [1, 2]),
    "Saúde":            (0.020, 0.013, 0.4, [1, 8]),
    "Educação":         (0.026, 0.021, 0.5, [2, 3]),
    "Tecnologia":       (0.034, 0.024, 0.9, [1, 7]),
    "Transporte":       (0.020, 0.019, 1.3, [4, 10]),
}
PORTES = {"Micro": (25, 79), "Pequena": (80, 249), "Média": (250, 899), "Grande": (900, 4200)}
REGIOES = ["Grande SP", "Campinas", "Baixada Santista", "Vale do Paraíba", "Ribeirão Preto"]
MODALIDADES = ["Ambulatorial", "Hospitalar", "Hospitalar + Obstetrícia", "Referência"]
COPARTICIPACAO = ["Sem coparticipação", "Coparticipação 20%", "Coparticipação 30%"]
CANAIS = ["Corretora Alfa", "Corretora Beta", "Corretora Gama", "Corretora Delta",
          "Corretora Epsilon", "Venda direta", "Parceria contábil", "Marketplace"]

# Sensibilidade ao reajuste por porte: quanto menor a empresa, mais sensível ao preço.
SENSIBILIDADE_REAJUSTE = {"Micro": 4.0, "Pequena": 2.4, "Média": 0.8, "Grande": 1.4}


def gerar_carteiras(n_carteiras: int = 260, meses: int = 48,
                    semente: int = SEMENTE) -> pd.DataFrame:
    """Painel de contratos coletivos empresariais, mês a mês.

    O alvo é a **variação líquida de vidas** de cada carteira no próximo mês:

        variação = adesões - cancelamentos

    É um alvo difícil de propósito, e a dificuldade é estrutural: saldo de vidas é a
    diferença entre dois fluxos grandes e parecidos, então o sinal é pequeno diante da
    dispersão. Nenhum modelo conserta isso; o que um bom modelo faz é capturar a parte
    que existe.

    Três efeitos ficam escondidos na base, e cada um só aparece com um bloco de features:

    - **momento comercial latente** (AR(1) por carteira): não está em nenhum cadastro,
      só as defasagens da própria carteira o enxergam;
    - **interação reajuste x porte**: micro perde muito mais vida por ponto de reajuste;
    - **crise macro** com sensibilidade por setor.
    """
    g = np.random.default_rng(semente + 3)
    datas = pd.date_range("2022-01-01", periods=meses, freq="MS")

    # Macro: desemprego sobe na crise de 2023 e recua depois. É o U da carteira total.
    t = np.arange(meses)
    desemprego = 8.0 + 3.2 * np.exp(-((t - 20) ** 2) / (2 * 6.5 ** 2)) + g.normal(0, 0.10, meses)
    desvio_macro = desemprego - desemprego[:6].mean()

    nomes_setor = list(SETORES)
    linhas = []
    for c in range(n_carteiras):
        setor = nomes_setor[c % len(nomes_setor)]
        adesao_base, cancel_base, sens_macro, meses_pico = SETORES[setor]
        # Mais micro e pequena do que média e grande, como na carteira real de coletivo.
        porte = str(g.choice(list(PORTES), p=[0.35, 0.30, 0.22, 0.13]))
        minimo, maximo = PORTES[porte]

        vidas = float(g.integers(minimo, maximo))
        mes_reajuste = int(g.integers(1, 13))
        reajuste = float(np.clip(g.normal(0.115, 0.045), 0.03, 0.28))
        cadastro = {
            "carteira_id": f"C{c:04d}", "setor": setor, "porte": porte,
            "regiao": REGIOES[g.integers(0, len(REGIOES))],
            "modalidade": MODALIDADES[g.integers(0, len(MODALIDADES))],
            "coparticipacao": COPARTICIPACAO[g.integers(0, len(COPARTICIPACAO))],
            "canal_venda": CANAIS[g.integers(0, len(CANAIS))],
        }
        sinistralidade = float(np.clip(g.normal(0.78, 0.09), 0.45, 1.15))

        momento = 0.0                      # estado latente: o momento comercial da empresa
        for k, data in enumerate(datas):
            momento = 0.86 * momento + g.normal(0, 0.16)     # AR(1): persiste por meses
            mes = data.month

            # O reajuste é RENEGOCIADO todo ano, no mês de aniversário do contrato. Sem
            # essa variação dentro da carteira, o percentual ficaria confundido com a
            # identidade do contrato e nenhum modelo conseguiria isolar o seu efeito.
            if mes == mes_reajuste:
                reajuste = float(np.clip(g.normal(0.115, 0.045), 0.03, 0.28))

            pico = 1.35 if mes in meses_pico else 1.0
            macro = sens_macro * desvio_macro[k]
            meses_desde_reajuste = (mes - mes_reajuste) % 12
            pos_reajuste = meses_desde_reajuste <= 2

            taxa_adesao = adesao_base * pico * (1 + 0.55 * momento) * (1 - 0.065 * macro)
            taxa_cancel = cancel_base * (1 + 0.105 * macro) * (1 - 0.35 * momento)
            if pos_reajuste:
                taxa_cancel *= 1 + SENSIBILIDADE_REAJUSTE[porte] * reajuste
            if mes == 12:
                taxa_cancel *= 1.30                          # dezembro é sempre o pior mês

            esperado_adesao = max(vidas * taxa_adesao, 0.05)
            esperado_cancel = max(vidas * taxa_cancel, 0.05)
            adesoes = float(g.poisson(esperado_adesao))
            cancelamentos = float(g.poisson(esperado_cancel))

            linhas.append({
                "data": data, **cadastro, "vidas_inicio_mes": vidas,
                "adesoes": adesoes, "cancelamentos": cancelamentos,
                "variacao_vidas": adesoes - cancelamentos,
                # O ORACULO: a variação esperada, conhecida só por quem gerou os dados.
                "variacao_esperada": esperado_adesao - esperado_cancel,
                "reajuste_vigente": reajuste, "mes_reajuste": mes_reajuste,
                "meses_desde_reajuste": meses_desde_reajuste,
                "taxa_desemprego": desemprego[k],
                "sinistralidade_12m": float(np.clip(sinistralidade + 0.05 * momento
                                                    + g.normal(0, 0.02), 0.3, 1.4)),
            })
            vidas = max(vidas + adesoes - cancelamentos, 12.0)

    painel = pd.DataFrame(linhas)
    painel["vidas_fim_mes"] = painel["vidas_inicio_mes"] + painel["variacao_vidas"]
    return painel.sort_values(["carteira_id", "data"]).reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Caso secundário: teleconsultas (3 anos, para o Prophet)
# ═══════════════════════════════════════════════════════════════════════════════

def gerar_teleconsultas(semente: int = 7) -> pd.DataFrame:
    """Três anos de demanda diária por teleconsulta, com changepoint de tendência.

    E a série desenhada para o Prophet: tendência que MUDA de inclinação, duas
    sazonalidades simultâneas e efeito de feriado.
    """
    g = np.random.default_rng(semente)
    datas = pd.date_range("2022-01-01", "2024-12-31", freq="D")
    n = len(datas)
    t = np.arange(n)

    apos_cp = np.asarray(datas >= pd.Timestamp("2022-09-01"), dtype=float)
    nivel = 80 + 0.03 * t + 0.10 * np.cumsum(apos_cp)
    peso_semana = np.array([12, 10, 9, 10, 8, -22, -30], dtype=float)[datas.dayofweek.to_numpy()]
    peso_ano = 14 * np.cos(2 * np.pi * (datas.dayofyear.to_numpy() - 196) / 365.25)

    feriados_3a = pd.to_datetime([
        f"{a}-01-01" for a in (2022, 2023, 2024)] + [
        f"{a}-04-21" for a in (2022, 2023, 2024)] + [
        f"{a}-05-01" for a in (2022, 2023, 2024)] + [
        f"{a}-09-07" for a in (2022, 2023, 2024)] + [
        f"{a}-10-12" for a in (2022, 2023, 2024)] + [
        f"{a}-11-02" for a in (2022, 2023, 2024)] + [
        f"{a}-11-15" for a in (2022, 2023, 2024)] + [
        f"{a}-12-25" for a in (2022, 2023, 2024)])
    efeito_feriado = np.where(np.isin(datas, feriados_3a), -35.0, 0.0)

    y = np.clip(nivel + peso_semana + peso_ano + efeito_feriado + g.normal(0, 6, n), 0, None)
    return pd.DataFrame({"ds": datas, "y": np.round(y)})


# ═══════════════════════════════════════════════════════════════════════════════
# Separação temporal
# ═══════════════════════════════════════════════════════════════════════════════

CORTE_VALIDACAO = pd.Timestamp("2025-06-01")
CORTE_TESTE = pd.Timestamp("2025-09-01")


def separar(indice: pd.DatetimeIndex,
            corte_val: pd.Timestamp = CORTE_VALIDACAO,
            corte_teste: pd.Timestamp = CORTE_TESTE) -> dict[str, np.ndarray]:
    """Separação SEMPRE cronológica: treino no passado, teste no futuro.

    Nunca aleatória. Sortear linhas faz o modelo treinar com dezembro e ser avaliado
    em novembro, ou seja, usar o futuro para prever o passado.
    """
    idx = pd.DatetimeIndex(indice)
    return {
        "treino": idx < corte_val,
        "validação": (idx >= corte_val) & (idx < corte_teste),
        "teste": idx >= corte_teste,
    }
