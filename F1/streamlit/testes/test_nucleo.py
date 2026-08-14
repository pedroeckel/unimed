"""
Testes do núcleo. Rodam sem subir o Streamlit:

    cd F1/streamlit && python -m pytest testes -q

Cada teste aqui é um invariante didático da aplicação, não uma recomendação. Se um deles
quebrar, a aplicação passou a ensinar algo errado.
"""

from __future__ import annotations

import ast
import os
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nucleo import avaliacao as A  # noqa: E402
from nucleo import dados as D  # noqa: E402
from nucleo import features as F  # noqa: E402
from nucleo import gemeo as GE  # noqa: E402
from nucleo import modelos as M  # noqa: E402


@pytest.fixture(scope="module")
def base():
    horaria = D.gerar_central_horaria()
    diaria = D.agregar_diario(horaria)
    X, y = F.construir_features_central(diaria)
    mascaras = D.separar(X.index)
    return {"horária": horaria, "diária": diaria, "X": X, "y": y, "mascaras": mascaras}


# ═══════════════════════════════════════════════════════════════════════════════
# Separação temporal
# ═══════════════════════════════════════════════════════════════════════════════

def test_split_e_cronologico(base):
    """Treino no passado, teste no futuro. Nunca o contrário."""
    idx = base["X"].index
    m = base["mascaras"]
    assert idx[m["treino"]].max() < idx[m["validação"]].min()
    assert idx[m["validação"]].max() < idx[m["teste"]].min()
    assert m["treino"].sum() > 0 and m["validação"].sum() > 0 and m["teste"].sum() > 0
    # As três mascaras são uma partição: nenhuma linha em dois conjuntos, nenhuma de fora.
    assert (m["treino"].astype(int) + m["validação"].astype(int)
            + m["teste"].astype(int) == 1).all()


# ═══════════════════════════════════════════════════════════════════════════════
# Vazamento
# ═══════════════════════════════════════════════════════════════════════════════

def test_features_nao_usam_o_futuro(base):
    """O teste funcional de vazamento, mais forte do que inspecionar o código.

    Constrói as features de duas rotas: com a série inteira e com a série cortada no dia
    alvo (tudo o que existiria em produção). Se alguma coluna olhasse para o futuro, as
    duas rotas divergiriam.
    """
    diaria = base["diária"]
    alvo = pd.Timestamp("2025-10-15")
    X_completo, _ = F.construir_features_central(diaria)
    X_producao, _ = F.construir_features_central(diaria.loc[:alvo])

    linha_c = X_completo.loc[alvo].to_numpy(dtype=float)
    linha_p = X_producao.loc[alvo].to_numpy(dtype=float)
    assert np.max(np.abs(linha_c - linha_p)) < 1e-9


def test_pipeline_treino_igual_producao():
    """O teste que a primeira versão do notebook F1_08 reprovou."""
    painel = D.gerar_autorizacoes()
    r = F.verificar_treino_producao(painel, pd.Timestamp("2025-10-15"), "Ortopedia")
    assert r["ok"], f"divergência de {r['diferenca_maxima']} em {r['coluna_pior']}"


def test_rolling_sempre_precedido_de_shift():
    """Varredura estática: nenhuma janela móvel pode ser calculada sobre o dia corrente."""
    caminho = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "nucleo", "features.py")
    with open(caminho, encoding="utf-8") as arquivo:
        linhas = arquivo.readlines()

    suspeitas = []
    for numero, linha in enumerate(linhas, start=1):
        if ".rolling(" not in linha or "=" not in linha:
            continue                      # prosa e docstring não são código
        if linha.strip().startswith("#") or "vazamento-proposital" in linha:
            continue                      # a demonstração do erro é intencional
        # Aceita o shift na própria expressão ou na variável `passado`, definida como shift(1).
        if ".shift(" in linha or "passado" in linha:
            continue
        suspeitas.append(f"{numero}: {linha.strip()}")
    assert not suspeitas, "rolling sem shift em features.py:\n" + "\n".join(suspeitas)


# ═══════════════════════════════════════════════════════════════════════════════
# O piso do problema
# ═══════════════════════════════════════════════════════════════════════════════

def test_oraculo_bate_a_formula_de_poisson(base):
    """Para contagens de Poisson, o erro de quem conhece lambda é ~ sqrt(2*lambda/pi)."""
    diaria = base["diária"]
    mae_oraculo = A.metricas(diaria["n_ligacoes"], diaria["intensidade"])[0]
    teorico = np.sqrt(2 * diaria["intensidade"].mean() / np.pi)
    assert abs(mae_oraculo - teorico) / teorico < 0.10


def test_ninguem_bate_o_oraculo(base):
    """Se um modelo fica abaixo do piso, há vazamento. Não há terceira explicação."""
    X, y, m = base["X"], base["y"], base["mascaras"]
    y_te = y[m["teste"]].to_numpy()
    piso = A.metricas(y_te, base["diária"].loc[X.index, "intensidade"][m["teste"]])[0]

    previsoes = {
        "LightGBM": M.boosting("LightGBM", X, y, m)["previsão"],
        "Random Forest": M.random_forest(X, y, m, n_estimators=100)["previsão"],
        "Árvore": M.arvore(X, y, m, max_depth=8)["previsão"],
    }
    for nome, prev in previsoes.items():
        mae = A.metricas(y_te, prev)[0]
        assert mae >= piso, f"{nome} ficou abaixo do piso ({mae:.2f} < {piso:.2f})"


def test_modelo_supera_a_melhor_referencia(base):
    """Se o modelo não bate a referência simples, o projeto não se justifica."""
    X, y, m = base["X"], base["y"], base["mascaras"]
    y_te = y[m["teste"]].to_numpy()
    refs = A.referencias_diarias(y, m["treino"], m["teste"])
    melhor_ref = min(A.metricas(y_te, v)[0] for v in refs.values())
    mae = A.metricas(y_te, M.boosting("LightGBM", X, y, m)["previsão"])[0]
    assert mae < melhor_ref


# ═══════════════════════════════════════════════════════════════════════════════
# Métricas
# ═══════════════════════════════════════════════════════════════════════════════

def test_rmse_maior_ou_igual_ao_mae():
    g = np.random.default_rng(0)
    for _ in range(20):
        y = g.uniform(50, 200, 60)
        p = y + g.normal(0, 12, 60)
        mae, rmse, _ = A.metricas(y, p)
        assert rmse >= mae - 1e-12


def test_mase_menor_que_um_significa_melhor_que_ingenuo():
    y = np.array([100.0, 120, 110, 130, 125])
    ingenuo = np.array([90.0, 100, 120, 110, 130])
    bom = y + np.array([1.0, -1, 1, -1, 1])
    assert A.mase(y, bom, ingenuo) < 1
    assert A.mase(y, ingenuo, ingenuo) == pytest.approx(1.0)


def test_wmape_sobrevive_a_zeros():
    y = np.array([3.0, 1, 0, 2, 0, 4])
    p = np.array([2.0, 2, 1, 2, 1, 3])
    assert np.isfinite(A.wmape(y, p))


# ═══════════════════════════════════════════════════════════════════════════════
# Defasagens externas
# ═══════════════════════════════════════════════════════════════════════════════

def test_residuo_encontra_a_defasagem_verdadeira():
    """A correlação dos resíduos acha as defasagens; a bruta não."""
    chegadas, externas = D.gerar_pa_diario()
    tabela = F.descobrir_defasagens(chegadas, externas)
    assert tabela["acertou_residual"].sum() >= 3
    assert tabela["acertou_bruto"].sum() <= tabela["acertou_residual"].sum()


# ═══════════════════════════════════════════════════════════════════════════════
# O gêmeo
# ═══════════════════════════════════════════════════════════════════════════════

def test_gemeo_concorda_com_erlang_em_regime_estavel():
    """Teste de sanidade: sob as hipóteses da fórmula, os dois motores têm que concordar.

    A simulação usa atendimento lognormal (menos variável que o exponencial da fórmula),
    então ela deve ficar IGUAL OU MELHOR que o Erlang C, nunca muito pior.
    """
    lam = np.full(24, 20.0)
    escala = np.full(24, 3, dtype=int)
    tma = 5.0

    erlang = GE.kpis_erlang(lam, escala, tma)
    sim = GE.rodar_replicacoes(lam, escala, tma, paciencia_min=float("inf"), n_rep=6)

    assert erlang["ocupacao_max"] < 1.0
    espera_sim = sim["resumo"]["espera_media_min"]["media"]
    assert espera_sim <= erlang["espera_media_min"] * 1.6
    assert espera_sim > 0


def test_escala_maior_reduz_espera():
    lam = np.full(24, 30.0)
    tma = 5.0
    curta = GE.rodar_replicacoes(lam, np.full(24, 4), tma, 3.0, n_rep=4)
    larga = GE.rodar_replicacoes(lam, np.full(24, 7), tma, 3.0, n_rep=4)
    assert (larga["resumo"]["espera_media_min"]["media"]
            < curta["resumo"]["espera_media_min"]["media"])
    assert (larga["resumo"]["nivel_servico"]["media"]
            > curta["resumo"]["nivel_servico"]["media"])


def test_prescricao_atinge_a_meta():
    """A escala prescrita tem que entregar o nível de serviço pedido."""
    perfil = D.perfil_intradiario(D.gerar_central_horaria(), D.CORTE_VALIDACAO)
    lam = GE.lambda_por_hora(600.0, perfil, dia_semana=2)
    escala = GE.prescrever_escala(lam, tma_min=5.0, meta_sl=0.80)
    r = GE.rodar_replicacoes(lam, escala, 5.0, 3.0, n_rep=6)
    assert r["resumo"]["nivel_servico"]["media"] >= 0.80


# ═══════════════════════════════════════════════════════════════════════════════
# Reprodutibilidade
# ═══════════════════════════════════════════════════════════════════════════════

def test_geradores_sao_reprodutiveis():
    a = D.gerar_central_horaria()
    b = D.gerar_central_horaria()
    assert np.array_equal(a["n_ligacoes"].to_numpy(), b["n_ligacoes"].to_numpy())


def test_modelo_e_reprodutivel(base):
    X, y, m = base["X"], base["y"], base["mascaras"]
    p1 = M.boosting("LightGBM", X, y, m)["previsão"]
    p2 = M.boosting("LightGBM", X, y, m)["previsão"]
    assert np.allclose(p1, p2)


def test_perfil_intradiario_soma_um_por_dia():
    perfil = D.perfil_intradiario(D.gerar_central_horaria(), D.CORTE_VALIDACAO)
    somas = perfil.groupby("dia_semana")["fracao"].sum()
    assert np.allclose(somas.to_numpy(), 1.0)
    assert len(perfil) == 7 * 24


# ═══════════════════════════════════════════════════════════════════════════════
# Painel de carteiras (caso do F1_05)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def painel():
    bruto = D.gerar_carteiras()
    dados = F.construir_features_carteira(bruto)
    mascaras = D.separar(pd.DatetimeIndex(dados["data"]),
                         pd.Timestamp("2025-01-01"), pd.Timestamp("2025-07-01"))
    return {"bruto": bruto, "dados": dados, "mascaras": mascaras}


def test_painel_features_nao_usam_o_futuro(painel):
    """Mesmo teste da série diária, agora em painel: o shift tem que ser dentro do grupo."""
    bruto = painel["bruto"]
    alvo = pd.Timestamp("2025-03-01")
    completo = F.construir_features_carteira(bruto)
    producao = F.construir_features_carteira(bruto[bruto["data"] <= alvo])

    colunas = [c for b in F.BLOCOS_CARTEIRA.values() for c in b]
    filtro = lambda df: (df[(df["data"] == alvo) & (df["carteira_id"] == "C0007")][colunas]
                         .to_numpy(dtype=float))
    assert np.max(np.abs(filtro(completo)[0] - filtro(producao)[0])) < 1e-9


def test_painel_ninguem_bate_o_piso(painel):
    dados, m = painel["dados"], painel["mascaras"]
    y = dados["variacao_vidas"]
    y_te = y[m["teste"]].to_numpy()
    piso = A.metricas(y_te, dados.loc[m["teste"], "variacao_esperada"])[0]

    colunas = [c for b in F.BLOCOS_CARTEIRA.values() for c in b]
    modelo = M.lgbm_simples(dados, y, m, colunas)
    mae = A.metricas(y_te, modelo.predict(dados.loc[m["teste"], colunas]))[0]
    assert mae >= piso
    # ... e o modelo tem que bater a melhor referência simples, senão não se justifica.
    assert mae < A.metricas(y_te, dados.loc[m["teste"], "media_variacao_3m"])[0]


def test_target_encoding_ingenuo_vaza(painel):
    """A assinatura do vazamento: a feature ingênua correlaciona mais com o alvo NO TREINO."""
    dados, m = painel["dados"], painel["mascaras"]
    y = dados["variacao_vidas"]
    treino = m["treino"]
    ingenuo = F.target_encoding(dados, m, "ingênuo")
    out_of_fold = F.target_encoding(dados, m, "out_of_fold")
    corr_ingenuo = abs(np.corrcoef(ingenuo[treino], y[treino])[0, 1])
    corr_oof = abs(np.corrcoef(out_of_fold[treino], y[treino])[0, 1])
    assert corr_ingenuo > corr_oof


def test_historico_e_o_bloco_mais_valioso(painel):
    """O momento comercial latente não está em nenhum cadastro: só as defasagens o veem."""
    dados, m = painel["dados"], painel["mascaras"]
    y = dados["variacao_vidas"]
    y_te = y[m["teste"]].to_numpy()

    def mae_com(blocos):
        colunas = [c for b in blocos for c in F.BLOCOS_CARTEIRA[b]]
        modelo = M.lgbm_simples(dados, y, m, colunas)
        return A.metricas(y_te, modelo.predict(dados.loc[m["teste"], colunas]))[0]

    sem_historico = mae_com(["cadastro", "categórico"])
    com_historico = mae_com(["cadastro", "categórico", "histórico"])
    assert com_historico < sem_historico


# ═══════════════════════════════════════════════════════════════════════════════
# Portugues da interface
# ═══════════════════════════════════════════════════════════════════════════════

# Palavras que so aparecem sem acento por descuido. Chaves internas (nome de coluna,
# chave de dicionario) ficam de fora porque sao codigo, e por isso a varredura olha
# apenas blocos de PROSA — strings longas, que sao o texto didatico e as docstrings.
SEM_ACENTO = [
    "nao", "sao", "entao", "estao", "tambem", "alem", "atras", "voce", "tres", "apos",
    "previsao", "previsoes", "avaliacao", "variavel", "variaveis", "referencia",
    "referencias", "metrica", "metricas", "historico", "grafico", "graficos",
    "periodo", "numero", "numeros", "serie", "series", "modulo", "pagina", "paginas",
    "codigo", "medico", "medicos", "analise", "decisao", "gestao", "operacao",
    "simulacao", "conclusao", "funcao", "razao", "padrao", "possivel", "impossivel",
    "util", "unico", "unica", "proprio", "propria", "ultimo", "ultima", "minimo",
    "maximo", "otimo", "estavel", "nivel", "niveis", "diario", "diaria", "horario",
    "sintese", "cenario", "cenarios", "calendario", "categorico", "ciclicas",
]


def test_prosa_esta_acentuada():
    """A interface é em português: prosa sem acento é erro de revisão, não de estilo."""
    import re

    raiz = pathlib.Path(__file__).resolve().parent.parent
    padrao = re.compile(r"\b(" + "|".join(SEM_ACENTO) + r")\b")
    faltas = []
    for arquivo in sorted(raiz.glob("**/*.py")):
        if "__pycache__" in str(arquivo) or arquivo.name == "test_nucleo.py":
            continue
        arvore = ast.parse(arquivo.read_text())
        for no in ast.walk(arvore):
            if not (isinstance(no, ast.Constant) and isinstance(no.value, str)):
                continue
            texto = no.value
            if len(texto) < 60 or " " not in texto:      # prosa, nao chave interna
                continue
            for m in padrao.finditer(texto):
                faltas.append(f"{arquivo.name}:{no.lineno}: {m.group(0)}")
    assert not faltas, "prosa sem acento:\n" + "\n".join(faltas[:40])
