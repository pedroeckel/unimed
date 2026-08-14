"""
Exporta, para o painel executivo em Next.js, os números REAIS do módulo F1.

Nada aqui é inventado para a tela: cada número sai do mesmo núcleo que a aplicação
Streamlit e os notebooks usam (`F1/streamlit/nucleo`). O painel é uma camada de
apresentação — o cálculo continua sendo o do projeto.

Rodar:

    .venv/bin/python "F1/frontend/scripts/exportar_operacao.py"

Saída: F1/frontend/dados/operacao.json
"""

from __future__ import annotations

import json
import os
import sys
import time
import unicodedata
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

AQUI = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.dirname(AQUI)
F1 = os.path.dirname(FRONTEND)
sys.path.insert(0, os.path.join(F1, "streamlit"))

from nucleo import avaliacao as A  # noqa: E402
from nucleo import dados as D  # noqa: E402
from nucleo import features as F  # noqa: E402
from nucleo import gemeo as GE  # noqa: E402
from nucleo import modelos as M  # noqa: E402

# ── Parâmetros da operação (os mesmos padrões das páginas 6 e 7) ───────────────
TMA = 5.0                 # tempo médio de atendimento, em minutos
PACIENCIA = 3.0           # paciência média antes do abandono, em minutos
META_SL = 0.80            # meta de nível de serviço (atender em até 20s)
CUSTO_HORA = 38.0         # custo do atendente-hora
JORNADA_SEMANAL = 36.0    # jornada de teleatendimento (NR-17, anexo II): 6h/dia
TURNO_H = 6.0             # tamanho do bloco de turno que a escala publica
SHRINKAGE = 0.30          # pausa, intervalo, férias, absenteísmo, treinamento, turnover
N_REP = 8                 # replicações do gêmeo
DIAS_MES = 21             # dias simulados na conta do "mês de operação"
NOMES_DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def cronometro(rotulo: str):
    print(f"  · {rotulo}...", end="", flush=True)
    return time.time()


def fim(inicio: float) -> None:
    print(f" {time.time() - inicio:.1f}s")


def lista(v) -> list:
    """Converte para lista de floats finitos e arredondados (JSON não aceita NaN/Inf)."""
    saida = []
    for x in np.asarray(v, dtype=float).ravel():
        saida.append(round(float(x), 4) if np.isfinite(x) else None)
    return saida


def sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")


def normalizar(obj):
    """Devolve o mesmo objeto com todas as CHAVES e COLUNAS sem acento.

    O nucleo do modulo usa nomes acentuados ("previsao", "média", "fracao"), e a
    grafia varia entre ambientes. Normalizar na fronteira deixa este exportador
    imune a isso: daqui para baixo, toda busca e feita em ASCII.
    """
    if isinstance(obj, dict):
        return {sem_acento(k): normalizar(v) for k, v in obj.items()}
    if isinstance(obj, pd.DataFrame):
        copia = obj.copy()
        copia.columns = [sem_acento(c) for c in copia.columns]
        return copia
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Base, features e o campo de jogo
# ═══════════════════════════════════════════════════════════════════════════════

print("\n▸ Base sintética e campo de jogo")
t = cronometro("gerando 2 anos de central horária")
horaria = D.gerar_central_horaria()
diaria = D.agregar_diario(horaria)
X, y = F.construir_features_central(diaria)
m = D.separar(X.index)
indice_teste = X.index[m["teste"]]
y_teste = y[m["teste"]].to_numpy()
oraculo = diaria.loc[X.index, "intensidade"][m["teste"]].to_numpy()
fim(t)

refs = A.referencias_diarias(y, m["treino"], m["teste"])
maes_ref = {k: A.metricas(y_teste, v)[0] for k, v in refs.items()}
melhor_ref = min(maes_ref, key=maes_ref.get)
mae_piso = A.metricas(y_teste, oraculo)[0]
print(f"    melhor referência: {melhor_ref} (MAE {maes_ref[melhor_ref]:.2f}) · "
      f"piso {mae_piso:.2f}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Os modelos, todos no mesmo conjunto de teste
# ═══════════════════════════════════════════════════════════════════════════════

print("\n▸ Modelos")
previsoes: dict[str, np.ndarray] = dict(refs)
familias = {nome: "Referência simples" for nome in refs}
tempos: dict[str, float] = {}

t = cronometro("SARIMA (1,1,1)(1,1,1,7), um passo à frente")
r_sarima = normalizar(M.sarima_um_passo(y, m))
previsoes["SARIMA (1,1,1)(1,1,1,7)"] = r_sarima["previsao"]
familias["SARIMA (1,1,1)(1,1,1,7)"] = "Clássico"
tempos["SARIMA (1,1,1)(1,1,1,7)"] = r_sarima["tempo_s"]
fim(t)

t = cronometro("Prophet")
r_prophet = normalizar(M.prophet_previsao(y, m))
previsoes["Prophet"] = r_prophet["previsao"]
familias["Prophet"] = "Clássico"
tempos["Prophet"] = r_prophet["tempo_s"]
fim(t)

t = cronometro("Árvore de decisão")
r_arvore = normalizar(M.arvore(X, y, m))
previsoes["Árvore de decisão"] = r_arvore["previsao"]
familias["Árvore de decisão"] = "Árvores"
tempos["Árvore de decisão"] = r_arvore["tempo_s"]
fim(t)

t = cronometro("Random Forest")
r_rf = normalizar(M.random_forest(X, y, m))
previsoes["Random Forest"] = r_rf["previsao"]
familias["Random Forest"] = "Árvores"
tempos["Random Forest"] = r_rf["tempo_s"]
fim(t)

importancias = {"Random Forest": r_rf["importancias"]}

resultados_boost = {}
for biblioteca in ("LightGBM", "XGBoost", "CatBoost"):
    t = cronometro(biblioteca)
    r = normalizar(M.boosting(biblioteca, X, y, m))
    previsoes[biblioteca] = r["previsao"]
    familias[biblioteca] = "Boosting"
    tempos[biblioteca] = r["tempo_s"]
    resultados_boost[biblioteca] = r
    importancias[biblioteca] = r["importancias"]
    fim(t)

placar = normalizar(A.montar_placar(y_teste, previsoes, y_ingenuo=refs["Mesmo dia da semana passada (lag 7)"],
                         mae_referencia=maes_ref[melhor_ref], mae_piso=mae_piso))
placar["familia"] = placar["modelo"].map(familias)
placar["tempo_s"] = placar["modelo"].map(tempos)
campeao = str(placar.iloc[0]["modelo"])
previsao_campeao = np.asarray(previsoes[campeao], dtype=float)
mae_campeao = float(placar.iloc[0]["MAE"])
# Importâncias do próprio campeão (as referências simples não têm nenhuma).
imp_campeao = importancias.get(campeao, importancias["Random Forest"])
imp_campeao = (imp_campeao / imp_campeao.sum()).sort_values(ascending=False)
print(f"    campeão: {campeao} (MAE {mae_campeao:.2f})")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Da previsão diária para a hora (estratégia de duas etapas)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n▸ Previsão operacional")
t = cronometro("perfil intradiário (estimado só no treino)")
perfil = normalizar(D.perfil_intradiario(horaria, D.CORTE_VALIDACAO))
perfil_medio = normalizar(D.perfil_intradiario_medio(horaria, D.CORTE_VALIDACAO))
fim(t)

horaria_teste = horaria.loc[indice_teste[0]:indice_teste[-1] + pd.Timedelta(hours=23)]
mapa_perfil = {(int(d), int(h)): float(f)
               for d, h, f in perfil[["dia_semana", "hora", "fracao"]].to_numpy()}
mapa_medio = {(int(d), int(h)): float(f)
              for d, h, f in perfil_medio[["dia_semana", "hora", "fracao"]].to_numpy()}
fracoes = np.array([mapa_perfil[(d, h)]
                    for d, h in zip(horaria_teste.index.dayofweek, horaria_teste.index.hour)])
fracoes_medias = np.array([mapa_medio[(d, h)]
                           for d, h in zip(horaria_teste.index.dayofweek, horaria_teste.index.hour)])

mapa_dia = pd.Series(previsao_campeao, index=indice_teste)
total_dia = horaria_teste.index.normalize().map(mapa_dia).to_numpy(dtype=float)
media_treino = float(diaria.loc[X.index, "n_ligacoes"][m["treino"]].mean())

previsao_horaria = pd.DataFrame({
    "datahora": horaria_teste.index,
    "previsto": total_dia * fracoes,                 # duas etapas: modelo × perfil do dia
    "estatico": media_treino * fracoes_medias,       # o input estático da apostila
    "real": horaria_teste["n_ligacoes"].to_numpy(),
    "intensidade": horaria_teste["intensidade"].to_numpy(),
})
previsao_horaria["data"] = pd.DatetimeIndex(previsao_horaria["datahora"]).normalize()

mae_h_duas = A.metricas(previsao_horaria["real"], previsao_horaria["previsto"])[0]
mae_h_estatico = A.metricas(previsao_horaria["real"], previsao_horaria["estatico"])[0]
mae_h_piso = A.metricas(previsao_horaria["real"], previsao_horaria["intensidade"])[0]

# ── Erro por horizonte: até onde a previsão ainda serve para fechar escala ─────
t = cronometro("erro por horizonte (previsão recursiva, D+1 a D+14)")
HORIZONTE = 14
modelo_h = M.lgbm_simples(X, y, m, list(X.columns))
serie_diaria = diaria["n_ligacoes"].copy()
idx_teste_pos = np.flatnonzero(serie_diaria.index.isin(indice_teste))
inicios = idx_teste_pos[:-HORIZONTE][:28]
erros = np.zeros((len(inicios), HORIZONTE))
for a, ini in enumerate(inicios):
    historico = serie_diaria.iloc[:ini].copy()
    for passo in range(HORIZONTE):
        estendida = pd.concat([historico,
                               pd.Series([np.nan], index=[serie_diaria.index[ini + passo]])])
        Xf, _ = F.construir_features_central(estendida.to_frame("n_ligacoes").ffill())
        previsto = float(modelo_h.predict(Xf.iloc[[-1]])[0])
        erros[a, passo] = abs(previsto - float(serie_diaria.iloc[ini + passo]))
        historico = pd.concat([historico,
                               pd.Series([previsto], index=[serie_diaria.index[ini + passo]])])
erro_horizonte = erros.mean(axis=0)
fim(t)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. O dia de operação que vai para a tela
# ═══════════════════════════════════════════════════════════════════════════════

print("\n▸ O dia da operação")
por_dia = previsao_horaria.groupby("data")[["real", "estatico", "previsto"]].sum()
# O dia escolhido é aquele em que a média histórica mais erra: é nos dias atípicos
# que a operação quebra, e é neles que ter um modelo faz diferença.
dia = (por_dia["real"] - por_dia["estatico"]).abs().idxmax()
do_dia = previsao_horaria[previsao_horaria["data"] == dia].sort_values("datahora")
lam_real = do_dia["intensidade"].to_numpy()
lam_previsto = do_dia["previsto"].to_numpy()
lam_estatico = do_dia["estatico"].to_numpy()
real_observado = do_dia["real"].to_numpy()
print(f"    {dia.date()} ({NOMES_DIAS[dia.dayofweek]}) — "
      f"real {real_observado.sum():.0f} · previsto {lam_previsto.sum():.0f} · "
      f"estático {lam_estatico.sum():.0f} ligações")

escala = GE.prescrever_escala(lam_previsto, TMA, META_SL)
escala_estatica = GE.prescrever_escala(lam_estatico, TMA, META_SL)
# A escala que o dia teria pedido se o volume observado fosse conhecido de manhã.
# É a régua da recomendação de contingência: "para o ritmo de hoje, o certo seria".
escala_ideal = GE.prescrever_escala(lam_real, TMA, META_SL)
erlang = normalizar(GE.kpis_erlang(lam_real, escala, TMA))

# ── Os sete dias seguintes: o que o sistema já tem dimensionado ────────────────
# Nenhum dado real desses dias entra aqui: só a previsão e a escala que sai dela.
# É o que o gestor tem em mãos hoje para fechar a semana.
residuos_dia = y_teste[:-14] - previsao_campeao[:-14]
faixa_lo, faixa_hi = np.quantile(residuos_dia, [0.1, 0.9])


def motivos_do_dia(data: pd.Timestamp) -> list[str]:
    """Por que o volume deste dia foge do normal — em linguagem de operação."""
    encontrados = []
    if D.eh_feriado([data])[0]:
        encontrados.append("feriado")
    if D.eh_vespera([data])[0]:
        encontrados.append("véspera de feriado")
    if D.eh_pos_feriado([data])[0]:
        encontrados.append("dia seguinte ao feriado")
    if D.janela_vencimento([data])[0]:
        encontrados.append("janela de vencimento do boleto")
    if D.em_campanha([data])[0]:
        encontrados.append("campanha de comunicação em curso")
    if data.dayofweek == 0:
        encontrados.append("segunda-feira, o pico da semana")
    if data.dayofweek >= 5:
        encontrados.append("fim de semana")
    return encontrados


proximos_dias = []
for k in range(1, 8):
    data_futura = dia + pd.Timedelta(days=k)
    linha_futura = previsao_horaria[previsao_horaria["data"] == data_futura].sort_values("datahora")
    if linha_futura.empty:
        continue
    lam_futuro = linha_futura["previsto"].to_numpy()
    escala_futura = GE.prescrever_escala(lam_futuro, TMA, META_SL)
    proximos_dias.append({
        "data": str(data_futura.date()),
        "dia_semana": NOMES_DIAS[data_futura.dayofweek],
        "previsto": int(round(lam_futuro.sum())),
        "faixa_lo": int(round(lam_futuro.sum() + faixa_lo)),
        "faixa_hi": int(round(lam_futuro.sum() + faixa_hi)),
        "pico_hora": int(np.argmax(lam_futuro)),
        "pico_chamadas": int(round(lam_futuro.max())),
        "atendentes_hora": int(escala_futura.sum()),
        "pico_atendentes": int(escala_futura.max()),
        "custo": round(GE.custo_escala(escala_futura, CUSTO_HORA), 0),
        "motivos": motivos_do_dia(data_futura),
        "escala": [int(v) for v in escala_futura],
    })

t = cronometro(f"gêmeo digital ({N_REP} replicações)")
rep = normalizar(GE.rodar_replicacoes(lam_real, escala, TMA, PACIENCIA, N_REP))
fim(t)
resumo = rep["resumo"]
esperas_seg = rep["esperas"] * 60

t = cronometro("traço minuto a minuto (replicação instrumentada)")
detalhe = normalizar(GE.simular_dia_detalhado(lam_real, escala, TMA, PACIENCIA, semente=42))
fim(t)
traco = detalhe["por_minuto"]
chamadas = detalhe["chamadas"]

# ── Marcos narrativos do dia, calculados sobre o próprio traço ─────────────────
eventos = []
capacidade = traco["capacidade"].to_numpy()
fila = traco["fila"].to_numpy()
for minuto in range(1, len(capacidade)):
    if capacidade[minuto] != capacidade[minuto - 1]:
        delta = int(capacidade[minuto] - capacidade[minuto - 1])
        eventos.append({
            "minuto": minuto, "tipo": "escala",
            "texto": (f"Escala {'sobe' if delta > 0 else 'desce'} para "
                      f"{int(capacidade[minuto])} atendentes "
                      f"({delta:+d})")})
pico_fila = int(np.argmax(fila))
eventos.append({"minuto": pico_fila, "tipo": "alerta",
                "texto": f"Pico de fila: {int(fila[pico_fila])} beneficiários aguardando"})
hora_pico = int(np.argmax(lam_real))
eventos.append({"minuto": hora_pico * 60, "tipo": "demanda",
                "texto": (f"Hora de maior demanda: {lam_real[hora_pico]:.0f} ligações "
                          f"com {int(escala[hora_pico])} atendentes")})
ocupacao = erlang["por_hora"]["ocupacao"].to_numpy()
for h in range(24):
    if ocupacao[h] > 0.85:
        eventos.append({"minuto": h * 60, "tipo": "alerta",
                        "texto": (f"Ocupação em {ocupacao[h]:.2f} — acima de 0,85 a fila "
                                  "deixa de crescer devagar e passa a explodir")})
abandonos = traco["abandonos_acum"].to_numpy()
primeiro_abandono = int(np.argmax(abandonos > 0)) if abandonos.max() > 0 else None
if primeiro_abandono:
    eventos.append({"minuto": primeiro_abandono, "tipo": "alerta",
                    "texto": "Primeiro abandono do dia: alguém desligou antes de ser atendido"})
eventos.append({"minuto": 0, "tipo": "escala",
                "texto": f"Turno da madrugada abre com {int(capacidade[0])} atendentes"})
eventos = sorted(eventos, key=lambda e: e["minuto"])

# ── Distribuição da espera ────────────────────────────────────────────────────
limite_hist = float(np.quantile(esperas_seg, 0.995)) if len(esperas_seg) else 60.0
contagens, bordas = np.histogram(esperas_seg, bins=28, range=(0, max(limite_hist, 30.0)))

# ═══════════════════════════════════════════════════════════════════════════════
# 5. O experimento que justifica o módulo: erro de previsão → KPI
# ═══════════════════════════════════════════════════════════════════════════════

print("\n▸ O valor da previsão")
t = cronometro("gêmeo com três fontes de dimensionamento")
fontes = {
    "Média histórica (input estático)": lam_estatico,
    f"Previsão do modelo ({campeao})": lam_previsto,
    "Demanda real (previsão perfeita)": lam_real,
}
comparacao = normalizar(GE.comparar_fontes(lam_real, fontes, TMA, PACIENCIA, META_SL,
                                           n_rep=max(N_REP // 2, 3), custo_hora=CUSTO_HORA))
fim(t)

# ── O mesmo experimento repetido ao longo de um mês de operação ────────────────
t = cronometro(f"mês de operação ({DIAS_MES} dias × 2 fontes)")
dias_mes = list(por_dia.index[-DIAS_MES:])
mes = []
for d in dias_mes:
    linha = previsao_horaria[previsao_horaria["data"] == d].sort_values("datahora")
    real_d = linha["intensidade"].to_numpy()
    registro = {"data": str(d.date()), "dia_semana": NOMES_DIAS[d.dayofweek],
                "chamadas": float(linha["real"].sum())}
    for chave, lam_fonte in (("modelo", linha["previsto"].to_numpy()),
                             ("estatico", linha["estatico"].to_numpy())):
        esc = GE.prescrever_escala(lam_fonte, TMA, META_SL)
        r = normalizar(GE.rodar_replicacoes(real_d, esc, TMA, PACIENCIA, n_rep=3))
        registro[f"{chave}_sl"] = float(r["resumo"]["nivel_servico"]["media"])
        registro[f"{chave}_espera_s"] = float(r["resumo"]["espera_media_min"]["media"] * 60)
        registro[f"{chave}_abandono"] = float(r["resumo"]["taxa_abandono"]["media"])
        registro[f"{chave}_custo"] = float(GE.custo_escala(esc, CUSTO_HORA))
        registro[f"{chave}_atendentes_hora"] = int(esc.sum())
    mes.append(registro)
mes_df = pd.DataFrame(mes)
fim(t)
print(f"    SL do mês — modelo {100 * mes_df['modelo_sl'].mean():.1f}% × "
      f"estático {100 * mes_df['estatico_sl'].mean():.1f}%")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. Cenários e fronteira custo × serviço
# ═══════════════════════════════════════════════════════════════════════════════

print("\n▸ Cenários e decisão")
CENARIOS = [
    ("Operação normal", 1.00, "A previsão do modelo, sem nenhum ajuste.", "linha de base"),
    ("Onda epidemiológica", 1.40, "Surto respiratório em curso eleva o contato com a central.",
     "estado latente medido na própria base (F1_06)"),
    ("Campanha de comunicação", 1.25, "Disparo de SMS em massa: pico de poucos dias, conhecido de antemão.",
     "efeito de +45,6% medido em autorização prévia (F1_08)"),
    ("Crescimento da carteira", 1.08, "Entrada de um contrato coletivo grande, com 8% mais vidas.",
     "modelo de variação de carteira (F1_05)"),
    ("Feriado", 0.45, "Operação praticamente parada, com repique no dia seguinte.",
     "efeito medido na base (-55%) e pós-feriado (+7,7%) do F1_07"),
]
t = cronometro("gêmeo em cada cenário")
cenarios = []
for nome, fator, descricao, origem in CENARIOS:
    lam = lam_previsto * fator
    esc = GE.prescrever_escala(lam, TMA, META_SL)
    r = normalizar(GE.rodar_replicacoes(lam, esc, TMA, PACIENCIA, n_rep=5))
    cenarios.append({
        "nome": nome, "fator": fator, "descricao": descricao, "origem": origem,
        "demanda": int(round(lam.sum())), "atendentes_hora": int(esc.sum()),
        "pico_atendentes": int(esc.max()), "custo": round(GE.custo_escala(esc, CUSTO_HORA), 0),
        "espera_s": round(r["resumo"]["espera_media_min"]["media"] * 60, 1),
        "nivel_servico": round(r["resumo"]["nivel_servico"]["media"], 3),
        "abandono": round(r["resumo"]["taxa_abandono"]["media"], 3),
        "escala": [int(v) for v in esc],
    })
fim(t)

t = cronometro("fronteira custo × serviço")
fronteira = []
for delta in range(-3, 4):
    esc = np.maximum(escala + delta, 1)
    r = normalizar(GE.rodar_replicacoes(lam_real, esc, TMA, PACIENCIA, n_rep=4))
    fronteira.append({
        "ajuste": f"{delta:+d}" if delta else "meta",
        "delta": delta,
        "atendentes_hora": int(esc.sum()),
        "custo": round(GE.custo_escala(esc, CUSTO_HORA), 0),
        "nivel_servico": round(r["resumo"]["nivel_servico"]["media"], 3),
        "espera_s": round(r["resumo"]["espera_media_min"]["media"] * 60, 1),
        "abandono": round(r["resumo"]["taxa_abandono"]["media"], 3),
    })
fim(t)

turnos = normalizar(GE.escala_por_turno(escala))
turnos["custo"] = [round(sum(float(escala[h]) for h in horas) * CUSTO_HORA, 0)
                   for horas in GE.TURNOS.values()]

# ═══════════════════════════════════════════════════════════════════════════════
# 7. Empacotar
# ═══════════════════════════════════════════════════════════════════════════════

janela = slice(-14, None)
residuos = y_teste[:-14] - previsao_campeao[:-14]
q_lo, q_hi = np.quantile(residuos, [0.1, 0.9])

saida = {
    "gerado_em": datetime.now().isoformat(timespec="seconds"),
    "parametros": {
        "tma_min": TMA, "paciencia_min": PACIENCIA, "meta_nivel_servico": META_SL,
        "custo_atendente_hora": CUSTO_HORA, "jornada_semanal_h": JORNADA_SEMANAL,
        "turno_h": TURNO_H, "shrinkage": SHRINKAGE, "replicacoes": N_REP,
        "nivel_servico_seg": GE.NIVEL_SERVICO_SEG, "semente": D.SEMENTE,
        "inicio_base": str(diaria.index[0].date()), "fim_base": str(diaria.index[-1].date()),
        "corte_validacao": str(D.CORTE_VALIDACAO.date()),
        "corte_teste": str(D.CORTE_TESTE.date()),
        "n_dias_base": int(len(diaria)), "n_horas_base": int(len(horaria)),
        "n_dias_teste": int(len(indice_teste)),
    },
    "campo": {
        "referencias": [{"nome": k, "mae": round(v, 3)} for k, v in
                        sorted(maes_ref.items(), key=lambda kv: -kv[1])],
        "melhor_referencia": melhor_ref,
        "mae_referencia": round(maes_ref[melhor_ref], 3),
        "mae_piso": round(mae_piso, 3),
    },
    "placar": [
        {"modelo": r["modelo"], "familia": r["familia"], "mae": r["MAE"], "rmse": r["RMSE"],
         "mape": r["MAPE (%)"], "wmape": r["WMAPE (%)"], "rmse_mae": r["RMSE/MAE"],
         "mase": r.get("MASE"), "aproveitado": r.get("% do aproveitavel"),
         "tempo_s": round(float(r["tempo_s"]), 2) if pd.notna(r["tempo_s"]) else None}
        for _, r in placar.iterrows()],
    "campeao": {
        "nome": campeao, "mae": mae_campeao,
        "aproveitado": float(placar.iloc[0].get("% do aproveitavel", 0.0)),
        "ganho_sobre_referencia": round(100 * (maes_ref[melhor_ref] - mae_campeao)
                                        / maes_ref[melhor_ref], 1),
        "importancias": [{"variavel": k, "peso": round(float(v), 4)}
                         for k, v in imp_campeao.head(12).items()],
    },
    "serie_diaria": {
        "datas": [str(d.date()) for d in indice_teste],
        "real": lista(y_teste),
        "previsto": lista(previsao_campeao),
        "referencia": lista(refs[melhor_ref]),
    },
    "previsao_14d": [
        {"data": str(d.date()), "dia_semana": NOMES_DIAS[d.dayofweek],
         "previsto": round(float(p), 0), "faixa_lo": round(float(p + q_lo), 0),
         "faixa_hi": round(float(p + q_hi), 0), "real": round(float(v), 0),
         "erro": round(float(v - p), 0)}
        for d, p, v in zip(indice_teste[janela], previsao_campeao[janela], y_teste[janela])],
    "erro_horizonte": [{"horizonte": h + 1, "mae": round(float(erro_horizonte[h]), 2)}
                       for h in range(HORIZONTE)],
    "duas_etapas": {
        "mae_duas_etapas": round(mae_h_duas, 3),
        "mae_estatico": round(mae_h_estatico, 3),
        "mae_piso_horario": round(mae_h_piso, 3),
    },
    "dia": {
        "data": str(dia.date()),
        "dia_semana": NOMES_DIAS[dia.dayofweek],
        "real": lista(real_observado),
        "intensidade": lista(lam_real),
        "previsto": lista(lam_previsto),
        "estatico": lista(lam_estatico),
        "escala": [int(v) for v in escala],
        "escala_estatica": [int(v) for v in escala_estatica],
        "escala_ideal": [int(v) for v in escala_ideal],
        "ocupacao": lista(erlang["por_hora"]["ocupacao"]),
        "espera_erlang_s": lista(erlang["por_hora"]["espera_min"] * 60),
        "total_real": int(real_observado.sum()),
        "total_previsto": int(round(lam_previsto.sum())),
        "total_estatico": int(round(lam_estatico.sum())),
        "ocupacao_max": round(float(erlang["ocupacao_max"]), 3),
        "faixa_lo": int(round(lam_previsto.sum() + faixa_lo)),
        "faixa_hi": int(round(lam_previsto.sum() + faixa_hi)),
        "motivos": motivos_do_dia(dia),
    },
    "proximos_dias": proximos_dias,
    "ao_vivo": {
        "fila": [int(v) for v in traco["fila"]],
        "ocupados": [int(v) for v in traco["ocupados"]],
        "capacidade": [int(v) for v in traco["capacidade"]],
        "chegadas_acum": [int(v) for v in traco["chegadas_acum"]],
        "atendidos_acum": [int(v) for v in traco["atendidos_acum"]],
        "abandonos_acum": [int(v) for v in traco["abandonos_acum"]],
        "no_prazo_acum": [int(v) for v in traco["no_prazo_acum"]],
        "eventos": eventos,
        # Uma linha por ligação oferecida no dia, com o instante em que ela chegou,
        # em que foi atendida e em que a chamada terminou. É o que permite reproduzir
        # o fluxo do atendimento fora da simulação, ligação por ligação.
        "chamadas": [
            {"chegada": round(float(r["chegada"]), 2),
             "espera_s": round(float(r["espera"]) * 60, 1),
             "atendido": bool(r["atendido"]),
             "inicio": None if not np.isfinite(r["inicio"]) else round(float(r["inicio"]), 2),
             "fim": None if not np.isfinite(r["fim"]) else round(float(r["fim"]), 2)}
            for _, r in chamadas.iterrows()],
    },
    "resultado_dia": {
        "chamadas": round(float(resumo["chamadas"]["media"]), 1),
        "espera_media_s": round(float(resumo["espera_media_min"]["media"]) * 60, 1),
        "espera_media_ic_s": round(float(resumo["espera_media_min"]["ic"]) * 60, 1),
        "espera_p90_s": round(float(resumo["espera_p90_min"]["media"]) * 60, 1),
        "nivel_servico": round(float(resumo["nivel_servico"]["media"]), 4),
        "nivel_servico_ic": round(float(resumo["nivel_servico"]["ic"]), 4),
        "abandono": round(float(resumo["taxa_abandono"]["media"]), 4),
        "atendentes_hora": int(escala.sum()),
        "custo": round(GE.custo_escala(escala, CUSTO_HORA), 0),
        "erlang_espera_s": round(float(erlang["espera_media_min"]) * 60, 1),
        "erlang_nivel_servico": round(float(erlang["nivel_servico"]), 4),
        "por_replicacao": [
            {"replicacao": int(r["replicacao"]), "chamadas": int(r["chamadas"]),
             "espera_s": round(float(r["espera_media_min"]) * 60, 1),
             "nivel_servico": round(float(r["nivel_servico"]), 4),
             "abandono": round(float(r["taxa_abandono"]), 4)}
            for _, r in rep["por_replicacao"].iterrows()],
    },
    "distribuicao_espera": {
        "bordas_s": lista(bordas),
        "contagens": [int(v) for v in contagens],
        "p90_s": round(float(np.quantile(esperas_seg, 0.9)), 1) if len(esperas_seg) else 0.0,
        "mediana_s": round(float(np.median(esperas_seg)), 1) if len(esperas_seg) else 0.0,
    },
    "comparacao_fontes": [
        {"fonte": r["fonte usada para dimensionar"],
         "atendentes_hora": int(r["atendentes-hora"]),
         "custo": float(r["custo do dia (R$)"]),
         "espera_s": round(float(r["espera media (min)"]) * 60, 1),
         "espera_p90_s": round(float(r["espera P90 (min)"]) * 60, 1),
         "nivel_servico": float(r["nivel de servico"]),
         "abandono": float(r["abandono"])}
        for _, r in comparacao.iterrows()],
    "mes": {
        "dias": mes,
        "resumo": {
            "modelo_sl": round(float(mes_df["modelo_sl"].mean()), 4),
            "estatico_sl": round(float(mes_df["estatico_sl"].mean()), 4),
            "modelo_espera_s": round(float(mes_df["modelo_espera_s"].mean()), 1),
            "estatico_espera_s": round(float(mes_df["estatico_espera_s"].mean()), 1),
            "modelo_abandono": round(float(mes_df["modelo_abandono"].mean()), 4),
            "estatico_abandono": round(float(mes_df["estatico_abandono"].mean()), 4),
            "modelo_custo": round(float(mes_df["modelo_custo"].sum()), 0),
            "estatico_custo": round(float(mes_df["estatico_custo"].sum()), 0),
            "modelo_atendentes_hora": int(mes_df["modelo_atendentes_hora"].sum()),
            "estatico_atendentes_hora": int(mes_df["estatico_atendentes_hora"].sum()),
            "chamadas": int(mes_df["chamadas"].sum()),
            "dias_simulados": len(mes_df),
        },
    },
    "cenarios": cenarios,
    "fronteira": fronteira,
    "turnos": [
        {"turno": r["turno"], "horas": r["horas"], "media": float(r["agentes (media)"]),
         "pico": int(r["agentes (pico)"]), "custo": float(r["custo"])}
        for _, r in turnos.iterrows()],
}

destino = os.path.join(FRONTEND, "dados", "operacao.json")
os.makedirs(os.path.dirname(destino), exist_ok=True)
with open(destino, "w", encoding="utf-8") as arquivo:
    json.dump(saida, arquivo, ensure_ascii=False, separators=(",", ":"))

tamanho = os.path.getsize(destino) / 1024
print(f"\n✓ {destino}  ({tamanho:.0f} KB)\n")
