"""
Painel do Gêmeo Digital — PA UNIMED SP
Baseado no notebook D10_GemeDigital_PontaAPonta.ipynb
"""

import streamlit as st
import pandas as pd
import numpy as np
import simpy
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats
from scipy.stats import lognorm
import os, random, copy, warnings, json
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")

# ── Configuração da página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Gêmeo Digital — PA UNIMED SP",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paleta de cores ────────────────────────────────────────────────────────
VERDE  = "#1A5E3A"
VERDE2 = "#2E7D52"
AZUL   = "#1F4E79"
AZUL2  = "#2E86C1"
LARANJA = "#E65100"
CINZA   = "#F5F5F5"

COR_MANCHESTER = {
    "Vermelho": "#C0392B",
    "Laranja":  "#E67E22",
    "Amarelo":  "#F1C40F",
    "Verde":    "#27AE60",
    "Azul":     "#2980B9",
}
NIVEIS = ["Vermelho", "Laranja", "Amarelo", "Verde", "Azul"]
MANCHESTER_PRIORIDADE = {"Vermelho": 1, "Laranja": 2, "Amarelo": 3, "Verde": 4, "Azul": 5}

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.kpi-card {
    background: linear-gradient(135deg,#1A5E3A 0%,#2E7D52 100%);
    padding:1.2rem 1rem; border-radius:12px; color:white;
    text-align:center; margin-bottom:.5rem;
}
.kpi-card.warning { background:linear-gradient(135deg,#E65100 0%,#F57C00 100%); }
.kpi-card.info    { background:linear-gradient(135deg,#1F4E79 0%,#2E86C1 100%); }
.kpi-card.neutral { background:linear-gradient(135deg,#424242 0%,#616161 100%); }
.kpi-value { font-size:2rem; font-weight:700; line-height:1.1; }
.kpi-label { font-size:.78rem; opacity:.88; margin-top:.2rem; }
.kpi-delta { font-size:.75rem; margin-top:.3rem; }
.etapa-header {
    border-left:4px solid #2E7D52; padding-left:.8rem; margin-bottom:1rem;
}
.aviso-metodologico {
    background:#FFF3E0; border-left:4px solid #E65100;
    padding:.8rem 1rem; border-radius:0 8px 8px 0; margin:.5rem 0 1rem 0;
    font-size:.88rem; color:#333;
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# HELPER — caixa informativa com ícone e matemática
# ═══════════════════════════════════════════════════════════════════════════

def info(titulo: str, conteudo_md: str):
    """Exibe um expander compacto com ícone ℹ️ e conteúdo em Markdown/LaTeX."""
    with st.expander(f"ℹ️ {titulo}"):
        st.markdown(conteudo_md, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# DADOS
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_data
def carregar_dados():
    LAMBDA_HORA = {
        0:1.5,1:1.2,2:1.0,3:0.8,4:0.9,5:1.3,
        6:2.5,7:4.0,8:6.2,9:7.5,10:8.1,11:7.8,
        12:6.8,13:6.3,14:6.5,15:7.0,16:8.2,17:9.1,
        18:8.8,19:7.5,20:6.5,21:5.5,22:4.5,23:3.0,
    }
    MANCHESTER = {
        "Vermelho": {"mu":2.10,"sigma":0.35,"prop":0.05},
        "Laranja":  {"mu":2.60,"sigma":0.40,"prop":0.15},
        "Amarelo":  {"mu":2.95,"sigma":0.50,"prop":0.30},
        "Verde":    {"mu":3.30,"sigma":0.60,"prop":0.40},
        "Azul":     {"mu":2.75,"sigma":0.45,"prop":0.10},
    }
    DIAS_PT = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
    proporcoes = [MANCHESTER[r]["prop"] for r in NIVEIS]
    random.seed(42); np.random.seed(42)

    D9_ALT = os.path.join(os.path.dirname(__file__), "..", "D9")
    PATH_HIST = os.path.join(D9_ALT, "historico_pa_clean.csv")

    if os.path.exists(PATH_HIST):
        df = pd.read_csv(PATH_HIST, parse_dates=["dt_chegada"])
        if "hora" not in df.columns and "hora_chegada" in df.columns:
            df = df.rename(columns={"hora_chegada": "hora"})
        fonte = "D9 — dados reais"
    else:
        registros = []
        dt_inicio = datetime(2024, 11, 1)
        for dia in range(30):
            for hora in range(24):
                n = np.random.poisson(LAMBDA_HORA[hora])
                for _ in range(n):
                    dt = dt_inicio + timedelta(days=dia, hours=hora,
                                               minutes=random.randint(0,59),
                                               seconds=random.randint(0,59))
                    risco = np.random.choice(NIVEIS, p=proporcoes)
                    p = MANCHESTER[risco]
                    t_triagem = np.random.lognormal(2.20, 0.45)
                    t_espera   = np.random.lognormal(p["mu"]-0.8, p["sigma"])
                    t_consulta = np.random.lognormal(p["mu"], p["sigma"])
                    if random.random() < .05: t_triagem = np.nan
                    if random.random() < .05: t_espera  = np.nan
                    registros.append({
                        "id": f"PA{len(registros)+1:05d}",
                        "dt_chegada": dt, "risco_manchester": risco,
                        "hora": hora, "dia_semana": DIAS_PT[dt.weekday()],
                        "t_triagem_min": round(t_triagem,1),
                        "t_espera_medico_min": round(t_espera,1),
                        "t_consulta_min": round(t_consulta,1),
                    })
        df = pd.DataFrame(registros)
        df["dt_chegada"] = pd.to_datetime(df["dt_chegada"])
        fonte = "Sintético (fallback — D9 não encontrado)"

    df["t_consulta_min"] = df["t_consulta_min"].clip(lower=1, upper=240)
    df["t_triagem_min"]  = df["t_triagem_min"].fillna(df["t_triagem_min"].median())
    df["t_espera_medico_min"] = df["t_espera_medico_min"].fillna(df["t_espera_medico_min"].median())
    return df, fonte


@st.cache_data
def construir_params(df: pd.DataFrame):
    lambda_por_hora   = (df.groupby("hora").size() / 30).to_dict()
    proporcao_risco   = df.risco_manchester.value_counts(normalize=True).to_dict()
    params_servico    = {}
    for nivel in NIVEIS:
        dados = df[df.risco_manchester == nivel]["t_consulta_min"].dropna()
        dados = dados[dados > 0]
        if len(dados) > 5:
            sig, _, scale = lognorm.fit(dados, floc=0)
            params_servico[nivel] = {"mu": float(np.log(scale)), "sigma": float(sig)}
        else:
            params_servico[nivel] = {"mu": 3.0, "sigma": 0.5}
    sig_t, _, scale_t = lognorm.fit(df["t_triagem_min"].dropna().clip(lower=0.5), floc=0)
    recursos_turno = {
        "noturno1":  {"medicos":2,"triadores":1,"inicio":0, "fim":7},
        "matutino":  {"medicos":5,"triadores":2,"inicio":7, "fim":13},
        "vespertino":{"medicos":4,"triadores":2,"inicio":13,"fim":19},
        "noturno2":  {"medicos":3,"triadores":1,"inicio":19,"fim":24},
    }
    return {
        "lambda_hora": lambda_por_hora,
        "servico": params_servico,
        "proporcao_risco": proporcao_risco,
        "recursos_turno": recursos_turno,
        "triagem_mu": float(np.log(scale_t)),
        "triagem_sigma": float(sig_t),
        "t_overhead_doc_min": 15.0,
        "prioridade_manchester": MANCHESTER_PRIORIDADE,
        "seed_base": 42,
        "data_geracao": df.dt_chegada.max().strftime("%Y-%m-%d"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# SIMULADOR SimPy
# ═══════════════════════════════════════════════════════════════════════════

def gemeo_digital_pa(params, semente=42, duracao_min=30*60, warmup_min=4*60, coleta_fim_min=24*60):
    np.random.seed(semente)
    env = simpy.Environment()
    resultados = []
    n_med_max = max(v["medicos"]   for v in params["recursos_turno"].values())
    n_tri_max = max(v["triadores"] for v in params["recursos_turno"].values())
    triadores = simpy.Resource(env, capacity=n_tri_max)
    medicos   = simpy.PriorityResource(env, capacity=n_med_max)
    overhead_doc = params.get("t_overhead_doc_min", 0.0)

    def shift_manager(env):
        turnos = sorted(params["recursos_turno"].values(), key=lambda t: t["inicio"])
        while True:
            hora_atual = int(env.now // 60) % 24
            turno_ativo = turnos[0]
            for t in turnos:
                if t["inicio"] <= hora_atual < t["fim"]:
                    turno_ativo = t; break
            medicos._capacity   = turno_ativo["medicos"]
            triadores._capacity = turno_ativo["triadores"]
            min_atuais = env.now % (24 * 60)
            proximos = [t["inicio"]*60 for t in turnos if t["inicio"]*60 > min_atuais]
            espera = min(proximos) - min_atuais if proximos else (24+turnos[0]["inicio"])*60 - min_atuais
            yield env.timeout(max(1.0, espera))

    env.process(shift_manager(env))

    def paciente(env, id_pac, risco, t_chegada):
        prioridade = params["prioridade_manchester"][risco]
        with triadores.request() as req:
            yield req
            t_ini_triagem   = env.now
            t_serv_triagem  = max(1., np.random.lognormal(params["triagem_mu"], params["triagem_sigma"]))
            yield env.timeout(t_serv_triagem)
        espera_triagem = t_ini_triagem - t_chegada
        s = params["servico"][risco]
        with medicos.request(priority=prioridade) as req:
            yield req
            t_ini_medico = env.now
            t_consulta   = max(1., np.random.lognormal(s["mu"], s["sigma"]))
            yield env.timeout(t_consulta + overhead_doc)
        espera_medico = t_ini_medico - t_chegada - espera_triagem - t_serv_triagem
        tempo_total   = t_ini_medico + t_consulta - t_chegada
        if warmup_min <= t_chegada <= coleta_fim_min:
            resultados.append({
                "id": id_pac, "risco": risco, "prioridade": prioridade,
                "t_chegada_min": round(t_chegada, 1),
                "espera_triagem": round(max(0, espera_triagem), 1),
                "t_consulta":    round(t_consulta, 1),
                "espera_medico": round(max(0, espera_medico), 1),
                "tempo_total":   round(tempo_total, 1),
            })

    def chegadas(env):
        id_pac = 0
        while True:
            hora_atual = int(env.now // 60) % 24
            lam = params["lambda_hora"].get(hora_atual, 5.0)
            intervalo = max(0.1, np.random.exponential(60.0 / lam))
            yield env.timeout(intervalo)
            id_pac += 1
            risco = np.random.choice(
                list(params["proporcao_risco"].keys()),
                p=list(params["proporcao_risco"].values()),
            )
            env.process(paciente(env, id_pac, risco, env.now))

    env.process(chegadas(env))
    env.run(until=duracao_min)

    df_res = pd.DataFrame(resultados) if resultados else pd.DataFrame()
    if df_res.empty:
        return df_res, {}
    estat = {
        "n_pacientes":          len(df_res),
        "espera_triagem_media": df_res.espera_triagem.mean().round(1),
        "espera_medico_media":  df_res.espera_medico.mean().round(1),
        "tempo_total_medio":    df_res.tempo_total.mean().round(1),
        "p90_espera_medico":    df_res.espera_medico.quantile(.90).round(1),
        "p90_tempo_total":      df_res.tempo_total.quantile(.90).round(1),
        "pct_espera_acima_60":  (df_res.espera_medico > 60).mean().round(4),
    }
    return df_res, estat


@st.cache_data
def rodar_replicacoes(params_json: str, n_rep: int = 10):
    params = json.loads(params_json)
    estats, dfs = [], []
    for rep in range(n_rep):
        df_rep, estat = gemeo_digital_pa(params, semente=42+rep)
        estats.append(estat)
        if not df_rep.empty:
            dfs.append(df_rep.assign(replicacao=rep+1))
    return pd.DataFrame(estats), pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════
# GRÁFICOS
# ═══════════════════════════════════════════════════════════════════════════

def fig_lambda_hora(df, params):
    horas    = list(range(24))
    lam_real = [df.groupby("hora").size().get(h,0)/30  for h in horas]
    lam_gem  = [params["lambda_hora"].get(h,0)          for h in horas]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=horas,y=lam_real,mode="lines+markers",name="Sistema real (HIS)",
        line=dict(color=VERDE2,width=2.5),marker=dict(size=6),
        fill="tozeroy",fillcolor="rgba(46,125,82,0.12)"))
    fig.add_trace(go.Scatter(x=horas,y=lam_gem,mode="lines+markers",name="Gêmeo Digital",
        line=dict(color=AZUL2,width=2.5,dash="dash"),marker=dict(size=6),
        fill="tozeroy",fillcolor="rgba(46,134,193,0.08)"))
    fig.update_layout(title="Taxa de chegada por hora — Real vs Gêmeo Digital",
        xaxis_title="Hora do dia",yaxis_title="λ (pacientes/hora)",
        legend=dict(orientation="h",y=-0.25),height=320,margin=dict(t=40,b=10))
    return fig


def fig_manchester_dist(df):
    counts = df.risco_manchester.value_counts().reindex(NIVEIS).fillna(0)
    fig = go.Figure(go.Bar(
        x=NIVEIS,y=counts.values,
        marker_color=[COR_MANCHESTER[n] for n in NIVEIS],
        text=[f"{v:.0f}<br>({v/len(df)*100:.1f}%)" for v in counts.values],
        textposition="outside"))
    fig.update_layout(title="Distribuição por Nível Manchester",
        xaxis_title="Nível",yaxis_title="Atendimentos",
        height=300,margin=dict(t=40,b=10),showlegend=False)
    return fig


def fig_box_espera(df):
    fig = go.Figure()
    for nivel in NIVEIS:
        sub = df[df.risco_manchester==nivel]["t_espera_medico_min"]
        fig.add_trace(go.Box(y=sub,name=nivel,
            marker_color=COR_MANCHESTER[nivel],boxpoints="outliers",jitter=0.3))
    fig.add_hline(y=60,line_dash="dash",line_color="red",annotation_text="Meta 60 min")
    fig.update_layout(title="Espera p/ médico por Nível Manchester",
        yaxis_title="Minutos",height=350,margin=dict(t=40,b=10))
    return fig


def fig_sazonalidade(df):
    pivot = df.groupby(["dia_semana","hora"]).size().unstack(fill_value=0)
    ordem = [d for d in ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"] if d in pivot.index]
    pivot = pivot.reindex(ordem)
    fig = px.imshow(pivot,color_continuous_scale=[[0,"#EEF7F1"],[0.5,VERDE2],[1,VERDE]],
        labels=dict(x="Hora",y="Dia",color="Atendimentos"),
        title="Mapa de Calor — Sazonalidade Intradiária",aspect="auto")
    fig.update_layout(height=300,margin=dict(t=40,b=10))
    return fig


def fig_kpi_replicacoes(df_estats):
    kpis = [
        ("espera_medico_media","Espera média médico (min)",60),
        ("tempo_total_medio","Tempo total médio (min)",90),
        ("pct_espera_acima_60","% espera > 60 min",0.15),
    ]
    fig = make_subplots(rows=1,cols=3,subplot_titles=[k[1] for k in kpis])
    for j,(col,titulo,meta) in enumerate(kpis,1):
        vals = df_estats[col]
        fig.add_trace(go.Violin(y=vals,name=titulo,box_visible=True,meanline_visible=True,
            fillcolor=AZUL2,line_color=AZUL,opacity=0.7,points="all",
            marker=dict(size=5)),row=1,col=j)
        fig.add_hline(y=meta,line_dash="dot",line_color="red",row=1,col=j)
    fig.update_layout(title="Distribuição dos KPIs — Replicações Monte Carlo",
        showlegend=False,height=380,margin=dict(t=55,b=10))
    return fig


def fig_validacao(kpis_reais, kpis_sim, erros):
    nomes = list(kpis_reais.keys())
    labels = {
        "espera_medico_media": "Espera média (min)",
        "tempo_total_medio":   "Tempo total (min)",
        "p90_espera_medico":   "P90 espera (min)",
        "pct_espera_acima_60": "% espera > 60 min",
    }
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Sistema Real",
        x=[labels.get(n,n) for n in nomes],y=[kpis_reais[n] for n in nomes],
        marker_color=VERDE2,opacity=0.85))
    fig.add_trace(go.Bar(name="Gêmeo Digital",
        x=[labels.get(n,n) for n in nomes],y=[kpis_sim[n]   for n in nomes],
        marker_color=AZUL2,opacity=0.85))
    for nome in nomes:
        erro = erros.get(nome,0)
        fig.add_annotation(x=labels.get(nome,nome),
            y=max(kpis_reais[nome],kpis_sim[nome])*1.05,
            text=f"Δ {erro:.1f}%",showarrow=False,
            font=dict(color="green" if erro<=15 else "red",size=11))
    fig.update_layout(title="Validação: Real vs Gêmeo Digital (Δ% ≤ 15% = aprovado)",
        barmode="group",height=380,margin=dict(t=45,b=10),
        legend=dict(orientation="h",y=-0.2))
    return fig


def fig_gap_horario(df_clean, df_sim_all):
    """Etapa 5B — espera real vs simulada por hora."""
    hora_inicio = 4
    df_real = df_clean[df_clean["hora"] >= hora_inicio].copy()
    df_sim  = df_sim_all.copy()
    df_sim["hora"] = (df_sim["t_chegada_min"] // 60).astype(int) % 24

    dias = df_clean.dt_chegada.dt.date.nunique()
    n_rep = df_sim["replicacao"].nunique() if "replicacao" in df_sim.columns else 1

    real_h = df_real.groupby("hora").agg(
        espera_real=("t_espera_medico_min","mean"),
        p90_real=("t_espera_medico_min",lambda s:s.quantile(.9))).reset_index()
    sim_h = df_sim.groupby("hora").agg(
        espera_sim=("espera_medico","mean"),
        p90_sim=("espera_medico",lambda s:s.quantile(.9))).reset_index()

    d = real_h.merge(sim_h,on="hora",how="outer").fillna(0).sort_values("hora")
    d["gap"] = d["espera_real"] - d["espera_sim"]

    fig = make_subplots(rows=1,cols=2,
        subplot_titles=["Espera média por hora — Real vs Simulado",
                        "Cauda da fila (P90) — Real vs Simulado"])
    for (col_r,col_s,nome,row,col) in [
        ("espera_real","espera_sim","Espera média",1,1),
        ("p90_real","p90_sim","P90",1,2),
    ]:
        fig.add_trace(go.Scatter(x=d.hora,y=d[col_r],mode="lines+markers",name="Real",
            line=dict(color=LARANJA,width=2),marker=dict(size=6),
            legendgroup="real",showlegend=(col==1)),row=row,col=col)
        fig.add_trace(go.Scatter(x=d.hora,y=d[col_s],mode="lines+markers",name="Simulado",
            line=dict(color=AZUL2,width=2,dash="dash"),marker=dict(size=6),
            legendgroup="sim",showlegend=(col==1)),row=row,col=col)
    fig.update_layout(height=380,margin=dict(t=55,b=10),
        legend=dict(orientation="h",y=-0.18))
    return fig, d


def fig_cenarios(resultados_cenarios):
    kpis = [
        ("espera_medico_media","Espera média médico (min)",60),
        ("tempo_total_medio","Tempo total médio (min)",90),
        ("p90_espera_medico","P90 espera médico (min)",90),
        ("pct_espera_acima_60","% espera > 60 min",0.15),
    ]
    nomes = list(resultados_cenarios.keys())
    cores = [VERDE2,AZUL2,LARANJA]
    fig = make_subplots(rows=2,cols=2,subplot_titles=[k[1] for k in kpis])
    posicoes = [(1,1),(1,2),(2,1),(2,2)]
    for (row,col),(kpi,titulo,meta) in zip(posicoes,kpis):
        for nome,cor in zip(nomes,cores):
            vals = resultados_cenarios[nome][kpi]
            fig.add_trace(go.Bar(
                name=nome,x=[nome],y=[vals.mean()],marker_color=cor,
                error_y=dict(type="data",array=[vals.std()*1.96],visible=True),
                showlegend=(row==1 and col==1),legendgroup=nome),row=row,col=col)
        fig.add_hline(y=meta,line_dash="dot",line_color="red",row=row,col=col)
    fig.update_layout(title="Comparação de Cenários — Média ± IC 95%",
        height=480,margin=dict(t=55,b=10),
        legend=dict(orientation="h",y=-0.12),barmode="group")
    return fig


def fig_predicao(df):
    try:
        from prophet import Prophet
        df_p = (df.groupby(df.dt_chegada.dt.date).size()
                .reset_index(name="y").rename(columns={"dt_chegada":"ds"}))
        df_p["ds"] = pd.to_datetime(df_p["ds"])
        m = Prophet(yearly_seasonality=False,weekly_seasonality=True,
                    daily_seasonality=False,changepoint_prior_scale=0.05)
        m.fit(df_p)
        futuro = m.make_future_dataframe(periods=14)
        prev   = m.predict(futuro)
        prev_f = prev[prev.ds > df_p.ds.max()].copy()

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_p.ds,y=df_p.y,mode="lines+markers",
            name="Histórico",line=dict(color=VERDE2,width=2),marker=dict(size=5)))
        fig.add_trace(go.Scatter(x=prev_f.ds,y=prev_f.yhat,mode="lines+markers",
            name="Previsão (Prophet)",line=dict(color=AZUL2,width=2.5,dash="dash")))
        fig.add_trace(go.Scatter(
            x=pd.concat([prev_f.ds,prev_f.ds[::-1]]),
            y=pd.concat([prev_f.yhat_upper,prev_f.yhat_lower[::-1]]),
            fill="toself",fillcolor="rgba(46,134,193,0.15)",
            line=dict(color="rgba(255,255,255,0)"),name="IC 95%"))
        fig.add_vrect(x0=df_p.ds.max(),x1=prev_f.ds.max(),
            fillcolor="rgba(46,134,193,0.06)",line_width=0,
            annotation_text="Previsão 14 dias",annotation_position="top left")
        fig.update_layout(title="Predição de Demanda — Próximos 14 dias (Prophet)",
            xaxis_title="Data",yaxis_title="Pacientes/dia",
            height=350,margin=dict(t=45,b=10),
            legend=dict(orientation="h",y=-0.25))
        return fig, prev_f, df_p
    except ImportError:
        return None, None, None


# ═══════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🏥 Gêmeo Digital")
    st.markdown("**PA UNIMED SP**")
    st.markdown("---")

    pagina = st.radio("Navegação", label_visibility="collapsed", options=[
        "📊 Visão Geral",
        "🔍 Dados & Diagnóstico",
        "🤖 Simulação — Etapas 3–4",
        "✅ Validação — Etapa 5",
        "🔬 Diagnóstico — Etapa 5B",
        "🔮 Cenários — Etapa 7A",
        "📈 Predição & Prescrição — Etapas 7B–8",
    ])

    st.markdown("---")
    st.markdown("**Parâmetros da Simulação**")
    n_rep = st.slider("Replicações", 5, 20, 10, 5)
    n_medicos_extra = st.number_input("Médicos extras (Cenário +1)", 0, 3, 1)
    fator_epidemia  = st.slider("Fator epidemia (×λ)", 1.0, 2.0, 1.4, 0.05)

    st.markdown("---")
    st.markdown(
        "<small style='color:gray'>D10 — Gêmeo Digital Ponta a Ponta<br>"
        "Prof. Pedro | UNIMED SP</small>",
        unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# CARREGAMENTO
# ═══════════════════════════════════════════════════════════════════════════

df, fonte = carregar_dados()
params    = construir_params(df)
params_json = json.dumps(params)

kpis_reais = {
    "espera_medico_media":  float(df["t_espera_medico_min"].mean()),
    "tempo_total_medio":    float((df["t_triagem_min"]+df["t_espera_medico_min"]+df["t_consulta_min"]).mean()),
    "p90_espera_medico":    float(df["t_espera_medico_min"].quantile(.90)),
    "pct_espera_acima_60":  float((df["t_espera_medico_min"]>60).mean()),
}


# ═══════════════════════════════════════════════════════════════════════════
# AVISO metodológico (reutilizado em várias páginas)
# ═══════════════════════════════════════════════════════════════════════════

AVISO_METODOLOGICO = """
<div class="aviso-metodologico">
⚠️ <b>Status desta execução:</b> como o twin não validou nesta execução (erro relativo > 15%
em pelo menos um KPI), as etapas de cenários, predição e prescrição devem ser lidas como
<b>demonstrações ilustrativas do fluxo completo</b> — não como recomendação operacional homologada.
</div>
"""


# ═══════════════════════════════════════════════════════════════════════════
# PÁGINAS
# ═══════════════════════════════════════════════════════════════════════════

# ─── Visão Geral ──────────────────────────────────────────────────────────
if pagina == "📊 Visão Geral":
    st.title("📊 Painel do Gêmeo Digital — PA UNIMED SP")
    st.caption(f"Fonte: {fonte} | Período: {df.dt_chegada.min().date()} → {df.dt_chegada.max().date()}")

    info("O que é um Gêmeo Digital?",
        """
Um **Gêmeo Digital** é uma réplica computacional de um sistema real que:
1. **Aprende** com dados históricos do sistema (HIS/ERP)
2. **Simula** o comportamento usando modelos estocásticos (SimPy)
3. **Valida** a aderência ao mundo real (checkpoint de erro ≤ 15%)
4. **Projeta** cenários futuros e recomenda ações (prescrição)

Neste painel, o sistema real é o **Pronto Atendimento (PA)** e o motor de simulação é
baseado em **Simulação de Eventos Discretos (SED)** com protocolo de triagem **Manchester**.

**Framework completo (8 etapas):**
```
Dados reais → Parâmetros → Modelo SimPy → Replicações → Validação
→ Atualização → Cenários + Predição → Prescrição
```
""")

    # KPI Cards
    col1,col2,col3,col4,col5 = st.columns(5)
    total_pac   = len(df)
    media_diaria = total_pac / 30
    espera_media = df["t_espera_medico_min"].mean()
    tempo_total  = (df["t_triagem_min"]+df["t_espera_medico_min"]+df["t_consulta_min"]).mean()
    pct_criticos = (df["risco_manchester"].isin(["Vermelho","Laranja"])).mean()*100

    with col1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_pac:,}</div>'
                    f'<div class="kpi-label">Total de atendimentos</div>'
                    f'<div class="kpi-delta">30 dias</div></div>',unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card info"><div class="kpi-value">{media_diaria:.0f}</div>'
                    f'<div class="kpi-label">Pacientes/dia (média)</div>'
                    f'<div class="kpi-delta">λ médio diário</div></div>',unsafe_allow_html=True)
    with col3:
        cor = "warning" if espera_media > 60 else ""
        st.markdown(f'<div class="kpi-card {cor}"><div class="kpi-value">{espera_media:.1f}′</div>'
                    f'<div class="kpi-label">Espera média médico</div>'
                    f'<div class="kpi-delta">meta: ≤ 60 min</div></div>',unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-card info"><div class="kpi-value">{tempo_total:.0f}′</div>'
                    f'<div class="kpi-label">Tempo total médio no PA</div>'
                    f'<div class="kpi-delta">triagem + espera + consulta</div></div>',unsafe_allow_html=True)
    with col5:
        cor = "warning" if pct_criticos > 25 else ""
        st.markdown(f'<div class="kpi-card {cor}"><div class="kpi-value">{pct_criticos:.1f}%</div>'
                    f'<div class="kpi-label">Casos críticos</div>'
                    f'<div class="kpi-delta">Vermelho + Laranja</div></div>',unsafe_allow_html=True)

    info("Como interpretar os KPI cards",
        """
| KPI | Fórmula | Meta |
|-----|---------|------|
| Total de atendimentos | Σ registros no período | — |
| Pacientes/dia | Total ÷ 30 dias | — |
| Espera média médico | E[W] = média amostral de *t_espera_medico_min* | ≤ 60 min |
| Tempo total médio | E[T] = E[t_triagem] + E[W] + E[t_consulta] | ≤ 90 min |
| Casos críticos | (Vermelho + Laranja) ÷ total × 100% | depende do contexto |

O **tempo total médio** é o indicador mais próximo da experiência do paciente:
ele soma todas as etapas que o paciente precisa completar até sair do PA.
""")

    st.markdown("---")
    col_a, col_b = st.columns([3,2])
    with col_a:
        st.plotly_chart(fig_lambda_hora(df,params), use_container_width=True)
        info("O que é λ (taxa de chegada) e como ele é estimado?",
            r"""
**λ(h)** é a taxa média de chegada de pacientes na hora *h* do dia (pacientes/hora).

O gêmeo usa um **Processo de Poisson Não-Homogêneo (NHPP)**: em cada hora, o intervalo
entre chegadas segue uma Exponencial com média 60/λ(h) minutos.

**Estimação a partir do histórico:**
$$\hat{\lambda}(h) = \frac{\text{total de chegadas na hora } h}{\text{número de dias observados}}$$

A curva real mostra o **perfil intradiário real** do PA; a curva do gêmeo mostra o perfil
que o simulador usa. Quanto mais próximas, melhor a calibração de demanda.

**Por que NHPP e não Poisson homogêneo?**
Porque a demanda num PA não é constante ao longo do dia — há picos no início da manhã
(≈8h), no fim da tarde (≈17h) e menor volume na madrugada.
""")
    with col_b:
        st.plotly_chart(fig_manchester_dist(df), use_container_width=True)
        info("Protocolo de Triagem Manchester",
            """
O **Protocolo Manchester** classifica pacientes em 5 níveis de urgência:

| Nível | Cor | Tempo máximo de espera |
|-------|-----|----------------------|
| 1 | Vermelho | Imediato |
| 2 | Laranja | ≤ 10 min |
| 3 | Amarelo | ≤ 60 min |
| 4 | Verde | ≤ 120 min |
| 5 | Azul | ≤ 240 min |

No simulador, o recurso `medicos` é um **PriorityResource** do SimPy: pacientes
com número de prioridade menor (mais urgentes) entram na frente da fila,
independentemente da ordem de chegada.
""")

    st.plotly_chart(fig_sazonalidade(df), use_container_width=True)
    info("Como ler o mapa de calor de sazonalidade",
        """
Cada célula mostra o número médio de atendimentos naquele **dia × hora** ao longo
do período observado. Cores mais escuras = maior volume.

**Utilidade para o gêmeo:**
- Revela se há dias da semana com comportamento estruturalmente diferente (ex: segunda-feira mais pesada)
- Indica janelas de pico onde a fila tende a explodir
- Apoia decisões de alocação de escala por turno

**Leitura rápida:** se o pico de cor ocorre num turno onde a capacidade de médicos é menor,
há sinal de gargalo estrutural.
""")

    with st.expander("🧬 Framework completo do Gêmeo Digital"):
        col1,col2 = st.columns(2)
        with col1:
            st.markdown("""
| Etapa | Pergunta gerencial |
|-------|--------------------|
| 1 | O que o sistema real está dizendo? |
| 2 | Como o dado vira input do twin? |
| 3 | Como representar o PA no simulador? |
| 4 | Como gerar evidência confiável? |
| 5 | O twin é confiável para gestão? |
| **5B** | **Onde e por que o twin divergiu?** |
| 6 | Como o twin permanece vivo? |
| 7A | Como o sistema reage a cenários? |
| 7B | O que tende a acontecer à frente? |
| 8 | O que fazer diante disso? |
""")
        with col2:
            st.markdown("""
**Tecnologias**
- **SimPy** — simulação de eventos discretos
- **PriorityResource** — fila Manchester
- **MLE Lognormal** — ajuste de tempo de serviço
- **Prophet** — previsão de séries temporais
- **Pyomo** — otimização prescritiva

**Parâmetros do modelo**
- λ(h): taxa horária de chegada
- μ/σ por nível Manchester (Lognormal)
- 4 turnos ERP com capacidade variável
- Overhead de documentação: 15 min/atend
- Warm-up: 4h | Coleta: 4h–24h
""")


# ─── Dados & Diagnóstico ──────────────────────────────────────────────────
elif pagina == "🔍 Dados & Diagnóstico":
    st.title("🔍 Dados & Diagnóstico — Etapas 1 e 2")
    st.markdown('<div class="etapa-header"><b>Etapa 1</b> — Compreender o sistema real &nbsp;|&nbsp; '
                '<b>Etapa 2</b> — Transformar dados em parâmetros</div>',unsafe_allow_html=True)

    info("Pergunta gerencial desta etapa",
        """
**Etapa 1:** o que os dados do D9 revelam sobre o sistema real que o twin precisa reproduzir?

**Etapa 2:** como transformar o histórico observado em parâmetros defensáveis para o twin?

O fluxo é: dados brutos do HIS → limpeza → EDA → ajuste de distribuições por MLE →
dicionário `PARAMS_GEMEO` que alimenta o simulador.
""")

    col1,col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_box_espera(df), use_container_width=True)
        info("Como ler este boxplot",
            r"""
Cada caixa mostra a distribuição de **espera para atendimento médico** por nível Manchester.

- **Mediana** (linha central): valor típico de espera
- **IQR** (caixa): intervalo entre P25 e P75 — onde estão 50% dos pacientes
- **Bigodes**: P5 a P95 aproximadamente
- **Pontos**: outliers

**Implicação metodológica:** se os níveis mais urgentes (Vermelho, Laranja) têm
mediana alta, o protocolo Manchester não está sendo respeitado na operação real.

A linha vermelha tracejada marca a **meta operacional de 60 min**
(padrão Amarelo no protocolo Manchester).
""")
    with col2:
        st.plotly_chart(fig_manchester_dist(df), use_container_width=True)
        info("Distribuição de risco e estabilidade do ajuste",
            r"""
A proporção por nível determina a **composição do mix de pacientes** no simulador.

Para cada chegada no modelo, o nível de risco é sorteado usando:
$$P(\text{Vermelho}) = 0.05,\; P(\text{Laranja}) = 0.15,\; \ldots$$

Níveis com maior *n* amostral (Amarelo e Verde) têm ajustes Lognormal mais estáveis
estatisticamente. Níveis menores (Vermelho, Azul) requerem mais atenção ao intervalo
de confiança dos parâmetros estimados.
""")

    st.plotly_chart(fig_sazonalidade(df), use_container_width=True)

    # ── Tabela de parâmetros Lognormal ────────────────────────────────
    st.subheader("Parâmetros ajustados — Distribuição Lognormal por Nível Manchester")
    info("Por que Lognormal? E o que são μ e σ?",
        r"""
**Hipótese de modelagem:**
$$X \sim \text{Lognormal}(\mu, \sigma^2) \iff \ln(X) \sim \mathcal{N}(\mu, \sigma^2)$$

Esta hipótese é adequada para tempos de serviço em saúde porque:
- A variável é **estritamente positiva**
- Apresenta **assimetria à direita** (cauda longa — alguns casos muito demorados)
- É compatível com a estrutura multiplicativa de variação clínica

**Estimação por Máxima Verossimilhança (MLE):**
$$\hat{\theta} = \arg\max_\theta \prod_{i=1}^{n} f(x_i \mid \theta)$$

A biblioteca SciPy retorna `shape` = σ̂ e `scale` = e^μ̂, então:
$$\hat{\mu}_{\log} = \ln(\widehat{scale}), \quad \hat{\sigma}_{\log} = \widehat{shape}$$

**Média esperada:**
$$\mathbb{E}[X] = \exp\!\left(\mu + \frac{\sigma^2}{2}\right)$$

**Testes de aderência:**
- **KS** (*Kolmogorov-Smirnov*): $D_n = \sup_x |F_n(x) - F_{\hat\theta}(x)|$ — p > 0.05 aceita H₀
- **AD** (*Anderson-Darling*): enfatiza as caudas — estatística < crítico aceita H₀
""")

    rows = []
    for nivel in NIVEIS:
        dados = df[df.risco_manchester==nivel]["t_consulta_min"].dropna()
        dados = dados[dados > 0]
        mu    = params["servico"][nivel]["mu"]
        sigma = params["servico"][nivel]["sigma"]
        media_teorica = np.exp(mu + sigma**2/2)

        # KS test
        from scipy.stats import kstest, anderson, lognorm as lognorm_dist
        if len(dados) > 5:
            ks_stat, ks_p = kstest(dados, "lognorm", args=(sigma, 0, np.exp(mu)))
            ad_result = anderson(np.log(dados[dados>0]), dist="norm")
            ad_stat   = ad_result.statistic
            ad_crit   = ad_result.critical_values[2]  # 5%
            ks_ok  = "✅" if ks_p > 0.05 else "❌"
            ad_ok  = "✅" if ad_stat < ad_crit else "❌"
        else:
            ks_p, ad_stat, ks_ok, ad_ok = float("nan"),float("nan"),"—","—"

        rows.append({"Nível":nivel,"n":len(dados),
            "μ_log":round(mu,3),"σ_log":round(sigma,3),
            "Média teórica (min)":round(media_teorica,1),
            "Mediana (min)":round(dados.median(),1),
            "p-KS":f"{ks_p:.4f}" if not np.isnan(ks_p) else "—",
            "AD":f"{ad_stat:.3f}" if not np.isnan(ad_stat) else "—",
            "KS":ks_ok,"AD":ad_ok})

    df_params_raw = pd.DataFrame(rows)
    niveis_col    = df_params_raw["Nível"].tolist()
    styled = df_params_raw.style.apply(
        lambda col: [f"background-color:{COR_MANCHESTER[v]}22" for v in niveis_col]
        if col.name == "Nível" else [""]*len(col), axis=0)
    st.dataframe(styled, use_container_width=True)

    info("Como interpretar a tabela de ajuste",
        """
**Leitura coluna a coluna:**
- **μ_log, σ_log**: parâmetros da Lognormal que entram diretamente no simulador
- **Média teórica**: tempo médio de consulta esperado para o nível (em minutos)
- **p-KS ✅**: p > 0.05 — não há evidência de desalinhamento entre dados e Lognormal
- **AD ✅**: estatística Anderson-Darling abaixo do valor crítico a 5%

**Decisão prática:** aceite a Lognormal como distribuição operacional quando *ambos* os
testes passam. Se um falhar, o twin ainda pode operar, mas a calibração merece revisão.

**O valor real desta etapa:** o twin não usa um único tempo médio para todos os pacientes
— a heterogeneidade clínica por nível de gravidade está explicitamente incorporada.
""")

    # ── Escala por turno ──────────────────────────────────────────────
    st.subheader("Escala de recursos por turno (ERP)")
    info("O que é ρ (utilização) e por que importa?",
        r"""
**Utilização do servidor (fator de tráfego):**
$$\rho = \frac{\lambda \cdot \mathbb{E}[S]}{c}$$

Onde:
- λ = taxa média de chegada no turno (pacientes/min)
- 𝔼[S] = tempo médio de serviço por paciente (consulta + overhead de documentação)
- c = número de médicos no turno

**Interpretação:**
- ρ < 0.80: sistema estável com folga operacional
- 0.80 ≤ ρ < 0.90: operação pressionada — fila cresce nos picos
- ρ ≥ 0.90: risco alto de colapso da fila; qualquer variação cria espera longa

**Overhead de documentação (15 min):** o tempo que o médico permanece ocupado *além*
da consulta face a face (prontuário, prescrições, análise de exames). Ignorar este tempo
subestima ρ e faz o twin parecer mais ocioso do que a operação real.
""")
    mu_eff = 60.0 / (df["t_consulta_min"].mean() + params["t_overhead_doc_min"])
    turnos_rows = []
    for t, v in params["recursos_turno"].items():
        lam_t = np.mean([params["lambda_hora"].get(h,0) for h in range(v["inicio"],v["fim"])])
        rho   = lam_t / (v["medicos"] * mu_eff) if v["medicos"] > 0 else 0
        turnos_rows.append({"Turno":t,"Início":v["inicio"],"Fim":v["fim"],
            "Médicos":v["medicos"],"Triadores":v["triadores"],
            "λ médio (pac/h)":round(lam_t,2),"ρ estimado":round(rho,2),
            "Status":("✅ Estável" if rho<0.85 else ("⚠️ Pressionado" if rho<0.95 else "🔴 Crítico"))})
    st.dataframe(pd.DataFrame(turnos_rows), use_container_width=True, hide_index=True)

    with st.expander("📋 Amostra dos dados (50 primeiros registros)"):
        st.dataframe(df.head(50), use_container_width=True)


# ─── Simulação ─────────────────────────────────────────────────────────────
elif pagina == "🤖 Simulação — Etapas 3–4":
    st.title("🤖 Simulação — Etapas 3 e 4")
    st.markdown('<div class="etapa-header"><b>Etapa 3</b> — Construir o modelo (SimPy) &nbsp;|&nbsp; '
                '<b>Etapa 4</b> — Executar com rigor estatístico</div>',unsafe_allow_html=True)

    info("Pergunta gerencial — Etapa 4",
        """
**Que evidência precisamos produzir antes de comparar o twin com a realidade?**

Uma única replicação pode ser um sorteio atípico. O objetivo é estimar o **comportamento
esperado** com incerteza explícita, usando múltiplas replicações com sementes diferentes.
""")

    info("Como funciona o modelo SimPy — Etapa 3",
        r"""
O gêmeo é um **sistema de filas com prioridade** (M[t]/G/c/∞/FCFS-Priority):

**Fluxo de cada paciente:**
1. **Chegada** — NHPP com λ(h) por hora; intervalo ~ Exp(60/λ(h))
2. **Triagem** — fila FIFO; tempo ~ Lognormal(μ_triagem, σ_triagem)
3. **Consulta médica** — fila de prioridade Manchester (Vermelho=1 atende antes de Verde=4)
   - Tempo de serviço ~ Lognormal(μ_nível, σ_nível)
   - Overhead de documentação: +15 min no slot do médico

**Gerenciamento de turnos:**
O `shift_manager` altera a capacidade do `PriorityResource` a cada virada de turno,
simulando a escala real do ERP (4 turnos: noturno1, matutino, vespertino, noturno2).

**Warm-up e coleta:**
- Warm-up: 4h — descarta o transiente inicial (estado vazio ≠ estado estacionário)
- Coleta: 4h–24h — apenas chegadas nesta janela entram nos KPIs
- Duração total: 30h — permite que pacientes com espera longa completem o atendimento
""")

    col1,col2 = st.columns([2,1])
    with col1:
        st.info(f"O gêmeo roda **{n_rep} replicações** independentes. "
                "Cada replicação usa uma semente diferente (+42, +43, …) para garantir "
                "independência estatística entre as corridas.")
    with col2:
        btn_sim = st.button("▶️ Executar Simulação", use_container_width=True, type="primary")

    if btn_sim or ("df_estats" in st.session_state and "df_sim_all" in st.session_state):
        if btn_sim:
            with st.spinner(f"Rodando {n_rep} replicações..."):
                df_estats_new, df_sim_all_new = rodar_replicacoes(params_json, n_rep)
                st.session_state["df_estats"]   = df_estats_new
                st.session_state["df_sim_all"]  = df_sim_all_new

        df_estats  = st.session_state["df_estats"]
        df_sim_all = st.session_state["df_sim_all"]

        st.plotly_chart(fig_kpi_replicacoes(df_estats), use_container_width=True)
        info("Como interpretar os violin plots de KPI",
            r"""
Cada violin mostra a **distribuição empírica** do KPI entre as replicações.

- **Ponto interno** = valor de cada replicação
- **Caixa interna** = IQR (P25–P75)
- **Linha tracejada** = meta operacional
- **Largura do violin** = densidade de probabilidade

**Intervalo de Confiança 95% (IC 95%):**
$$\bar{X} \pm t_{n-1,0.975} \cdot \frac{S}{\sqrt{n}}$$

Com n=10 replicações e t₉,₀.₉₇₅ ≈ 2,26, o IC fica:
$$\bar{X} \pm 2.26 \cdot \frac{S}{\sqrt{10}}$$

**Interpretação:** quanto menor a largura do violin, maior a **precisão estatística**
das estimativas do twin. Se o violin é muito largo, considere aumentar o número de replicações.

**O que observar:** se a linha da meta (vermelha) cai dentro do violin, o sistema está
na margem da meta — qualquer perturbação pode violá-la.
""")

        st.subheader("Tabela resumo — IC 95%")
        labels_kpi = {
            "espera_medico_media": "Espera média médico (min)",
            "tempo_total_medio":   "Tempo total médio (min)",
            "p90_espera_medico":   "P90 espera médico (min)",
            "pct_espera_acima_60": "% espera > 60 min",
        }
        resumo = []
        for col_k in ["espera_medico_media","tempo_total_medio","p90_espera_medico","pct_espera_acima_60"]:
            vals = df_estats[col_k]
            t_crit = stats.t.ppf(0.975, df=len(vals)-1)
            ic_hw  = t_crit * vals.std() / np.sqrt(len(vals))
            resumo.append({"KPI": labels_kpi.get(col_k,col_k),
                "Média":round(vals.mean(),2), "Std":round(vals.std(),2),
                "IC 95% ±":round(ic_hw,2),
                "IC inferior":round(vals.mean()-ic_hw,2),
                "IC superior":round(vals.mean()+ic_hw,2)})
        st.dataframe(pd.DataFrame(resumo), use_container_width=True, hide_index=True)
    else:
        st.info("Clique em **Executar Simulação** para rodar as replicações.")


# ─── Validação ─────────────────────────────────────────────────────────────
elif pagina == "✅ Validação — Etapa 5":
    st.title("✅ Validação — Etapa 5")
    st.markdown('<div class="etapa-header"><b>Etapa 5</b> — Validar o twin contra a realidade</div>',
                unsafe_allow_html=True)

    info("Pergunta gerencial desta etapa",
        """
**O twin já reproduz o sistema real com qualidade suficiente para apoiar decisão?**

Este é o **checkpoint metodológico central**: sem validação aprovada, cenários, previsão
e prescrição não devem ser usados gerencialmente — apenas como demonstrações ilustrativas.

**Dois critérios simultâneos:**
1. O erro relativo de cada KPI deve ser ≤ 15%
2. O valor real deve cair dentro do IC 95% simulado (idealmente)
""")

    with st.spinner("Calculando KPIs simulados para validação..."):
        estats_val = []
        for rep in range(5):
            _, e = gemeo_digital_pa(params, semente=42+rep)
            estats_val.append(e)
        df_val = pd.DataFrame(estats_val)

    kpis_sim = {k: float(df_val[k].mean()) for k in kpis_reais}
    erros = {
        k: abs(kpis_sim[k]-kpis_reais[k]) / kpis_reais[k] * 100
        if kpis_reais[k] != 0 else 0.0
        for k in kpis_reais
    }
    aprovado = all(e <= 15.0 for e in erros.values())

    if aprovado:
        st.success("✅ Validação aprovada — todos os KPIs com erro relativo ≤ 15%")
    else:
        st.error("❌ Validação não aprovada — ao menos um KPI ultrapassou o limiar de 15%")
        st.markdown(AVISO_METODOLOGICO, unsafe_allow_html=True)

    st.plotly_chart(fig_validacao(kpis_reais, kpis_sim, erros), use_container_width=True)

    info("Fórmula do erro relativo e critério de aprovação",
        r"""
**Erro relativo percentual (ERP):**
$$\text{ERP}_k = \frac{|\hat{y}_k^{sim} - y_k^{real}|}{y_k^{real}} \times 100\%$$

**Critério de aprovação:** ERP ≤ 15% em *todos* os KPIs monitorados.

**Por que 15%?**
Em modelos de simulação de serviços de saúde, a convenção da literatura
(Law, 2015; Sargent, 2013) aceita ±15% como margem de validação, dado que:
- Os dados do HIS têm ruído inerente de registro
- Os parâmetros são estimados com MLE a partir de amostra finita
- O comportamento humano tem variabilidade irredutível

**O que fazer quando falha?**
1. Revisar capacidade efetiva por turno (ρ pode estar subestimado)
2. Recalibrar λ(h) com dados mais recentes
3. Incorporar mecanismos de fila adicional (reinternação, pacientes complexos)
4. Investigar na Etapa 5B *onde* e *por que* o twin diverge
""")

    st.subheader("Detalhamento por KPI")
    labels_map = {
        "espera_medico_media": "Espera média médico (min)",
        "tempo_total_medio":   "Tempo total médio (min)",
        "p90_espera_medico":   "P90 espera médico (min)",
        "pct_espera_acima_60": "% espera > 60 min",
    }
    val_rows = [{"KPI":labels_map.get(k,k),
        "Real":round(kpis_reais[k],3),
        "Simulado":round(kpis_sim[k],3),
        "Erro (%)":round(erros[k],1),
        "Limiar":"15%",
        "Status":"✅" if erros[k]<=15 else "❌"} for k in kpis_reais]
    st.dataframe(pd.DataFrame(val_rows), use_container_width=True, hide_index=True)


# ─── Diagnóstico 5B ────────────────────────────────────────────────────────
elif pagina == "🔬 Diagnóstico — Etapa 5B":
    st.title("🔬 Diagnóstico da Divergência — Etapa 5B")
    st.markdown('<div class="etapa-header"><b>Etapa 5B</b> — Diagnosticar onde e por que a '
                'validação falhou</div>',unsafe_allow_html=True)
    st.markdown(AVISO_METODOLOGICO, unsafe_allow_html=True)

    info("Pergunta gerencial desta etapa",
        """
**Onde o twin está ficando otimista demais ao comparar com o sistema real?**

Esta etapa decompõe a divergência em três lentes operacionais:
1. **Gap horário** — em que horas o twin subestima a espera real?
2. **Utilização efetiva** (ρ) — quão carregado está cada turno na prática?
3. **Sensibilidade à capacidade** — o erro melhora quando reduzimos a folga de médicos?

**O que isso habilita:** transformar a falha de validação em hipótese concreta de recalibração.
""")

    # ── Precisa de df_sim_all ─────────────────────────────────────────
    if "df_sim_all" not in st.session_state or st.session_state["df_sim_all"].empty:
        st.warning("Execute a **Simulação** (Etapas 3–4) primeiro para gerar os dados de diagnóstico.")
        if st.button("▶️ Rodar simulação agora"):
            with st.spinner("Rodando simulação..."):
                df_estats_new, df_sim_all_new = rodar_replicacoes(params_json, 10)
                st.session_state["df_estats"]  = df_estats_new
                st.session_state["df_sim_all"] = df_sim_all_new
                st.rerun()
    else:
        df_sim_all = st.session_state["df_sim_all"]

        # ── Gap horário ──────────────────────────────────────────────
        st.subheader("1. Espera por hora — Real vs Simulado")
        fig_gap, d_gap = fig_gap_horario(df, df_sim_all)
        st.plotly_chart(fig_gap, use_container_width=True)

        info("Como interpretar o gap horário",
            r"""
O **gap de espera** numa hora h é:
$$\text{gap}(h) = \bar{W}^{real}(h) - \bar{W}^{sim}(h)$$

- **gap positivo**: o twin está **subestimando** a espera real (otimista demais)
- **gap próximo de zero**: boa calibração nesta hora
- **gap negativo**: o twin superestima a espera (raramente problemático)

**Horas com maior gap são candidatas a recalibração:**
- Checar se λ(h) do gêmeo está abaixo do observado
- Checar se a capacidade nominal de médicos é maior do que a efetiva na operação

**P90 (gráfico da direita):** cauda da distribuição — afeta principalmente os pacientes
que mais esperam; é sensível a gargalos de curta duração nos picos.
""")

        d_gap_top = d_gap.sort_values("gap",ascending=False).head(6).round(2)
        if not d_gap_top.empty:
            st.markdown("**Horas com maior subestimação de espera:**")
            st.dataframe(d_gap_top[["hora","espera_real","espera_sim","gap","p90_real","p90_sim"]],
                         use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── ρ por turno ──────────────────────────────────────────────
        st.subheader("2. Utilização efetiva (ρ) por turno")
        info("Por que ρ efetivo pode diferir de ρ calculado?",
            r"""
O **ρ calculado** usa a média global de tempo de consulta:
$$\rho_{calc} = \frac{\lambda_{turno} \cdot (\bar{t}_{consulta} + t_{overhead})}{c \cdot \mu_{eff}}$$

O **ρ efetivo** inclui variabilidade e picos: em sistemas com alta variância no tempo
de serviço (σ_lognormal grande), a fila cresce muito acima do que ρ calculado sugere.

**Lei de Little aplicada ao turno:**
$$L = \lambda \cdot W$$

Onde L = número médio na fila, λ = taxa de chegada, W = espera média.
Se W real >> W simulado, há evidência de que ρ efetivo > ρ nominal.

**Hipótese de recalibração:** se `pac_medico_turno` do ERP implicar ρ_erp > ρ_hist_media,
o modelo está usando mais médicos do que a operação real disponibiliza.
""")
        mu_eff = 60.0 / (df["t_consulta_min"].mean() + params["t_overhead_doc_min"])
        rho_rows = []
        for nome_t, cfg in params["recursos_turno"].items():
            horas_t = list(range(cfg["inicio"],cfg["fim"]))
            df_t    = df[df["hora"].isin(horas_t)]
            chegadas_dia = len(df_t) / df.dt_chegada.dt.date.nunique()
            cons_media_t = df_t["t_consulta_min"].mean()
            dur_min      = (cfg["fim"]-cfg["inicio"])*60
            carga        = chegadas_dia * (cons_media_t + params["t_overhead_doc_min"])
            rho_hist     = carga / (cfg["medicos"] * dur_min)
            rho_rows.append({"Turno":nome_t,"Médicos nominais":cfg["medicos"],
                "Chegadas/dia":round(chegadas_dia,1),
                "Consulta média (min)":round(cons_media_t,1),
                "ρ estimado":round(rho_hist,3),
                "Status":("✅" if rho_hist<0.85 else ("⚠️" if rho_hist<0.95 else "🔴"))})
        st.dataframe(pd.DataFrame(rho_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Sensibilidade à capacidade ────────────────────────────────
        st.subheader("3. Sensibilidade à capacidade — Stress test de recalibração")
        info("O que este teste mostra?",
            """
Reduzindo artificialmente a capacidade de médicos em turnos específicos, verificamos se
o twin se aproxima dos KPIs reais. Se **sim**, há evidência de que a capacidade nominal
está superestimada em relação à operação real.

**Cenários testados:**
- Base nominal (configuração atual)
- −1 médico no vespertino
- −1 médico no vespertino + −1 no noturno2

**Interpretação:** o cenário com menor erro relativo sugere qual configuração de capacidade
é mais aderente ao comportamento real observado no HIS.
""")
        if st.button("▶️ Rodar stress test de capacidade"):
            estats_cap_reais = {k: float(df_val[k].mean()) if "df_val" in dir() else kpis_reais[k]
                                for k in kpis_reais}
            cap_rows = []
            cenarios_cap = {
                "Base nominal": {},
                "−1 médico vespertino": {"vespertino":-1},
                "−1 méd. vesp. + noturno2": {"vespertino":-1,"noturno2":-1},
            }
            with st.spinner("Testando configurações..."):
                for nome,ajustes in cenarios_cap.items():
                    p_t = copy.deepcopy(params)
                    for turno,delta in ajustes.items():
                        p_t["recursos_turno"][turno]["medicos"] = max(1,p_t["recursos_turno"][turno]["medicos"]+delta)
                    estats_t = [gemeo_digital_pa(p_t,semente=500+r)[1] for r in range(5)]
                    df_t2 = pd.DataFrame(estats_t)
                    cap_rows.append({"Cenário":nome,
                        "Espera sim (min)":round(df_t2.espera_medico_media.mean(),1),
                        "Erro espera (%)":round(abs(df_t2.espera_medico_media.mean()-kpis_reais["espera_medico_media"])/kpis_reais["espera_medico_media"]*100 if kpis_reais["espera_medico_media"]!=0 else 0,1),
                        "P90 sim (min)":round(df_t2.p90_espera_medico.mean(),1),
                        "Erro P90 (%)":round(abs(df_t2.p90_espera_medico.mean()-kpis_reais["p90_espera_medico"])/kpis_reais["p90_espera_medico"]*100 if kpis_reais["p90_espera_medico"]!=0 else 0,1)})
            st.dataframe(pd.DataFrame(cap_rows),use_container_width=True,hide_index=True)


# ─── Cenários 7A ───────────────────────────────────────────────────────────
elif pagina == "🔮 Cenários — Etapa 7A":
    st.title("🔮 Análise de Cenários — Etapa 7A")
    st.markdown('<div class="etapa-header"><b>Etapa 7A</b> — Explorar futuros possíveis '
                'com cenários</div>',unsafe_allow_html=True)
    st.markdown(AVISO_METODOLOGICO, unsafe_allow_html=True)

    info("Pergunta gerencial desta etapa",
        """
**Como o sistema reage quando mudamos capacidade ou sofremos um choque de demanda?**

Cenários transformam o twin em **laboratório gerencial de baixo risco**: testamos políticas
operacionais *antes* de implementá-las na operação real.

| Cenário | Descrição | Pergunta de gestão |
|---------|-----------|-------------------|
| **Baseline** | Configuração atual | Como o sistema reage hoje? |
| **+1 Médico** | +N médicos no vespertino (13h–19h) | Vale o custo extra de reforço? |
| **Epidemia** | ×fator na demanda horária | O PA absorve um pico epidêmico? |

> ⚠️ **Leitura metodológica:** priorize a **direção dos efeitos** entre cenários,
> não a homologação de valores absolutos (o twin ainda precisa recalibração).
""")

    info("Como funciona a análise de cenários — matemática",
        r"""
**Cenário 1 — Adição de capacidade:**
$$c_{vesp}^{novo} = c_{vesp}^{base} + \Delta c$$

O efeito esperado na fila segue a teoria de filas M/M/c:
$$W_q \propto \frac{\rho^c}{c! \cdot (1-\rho)^2}$$

Adicionar um servidor reduz ρ, que cai exponencialmente no numerador e aumenta $(1-\rho)^2$
no denominador — efeito não-linear: os ganhos são maiores quando ρ está próximo de 1.

**Cenário 2 — Choque de demanda:**
$$\lambda_{novo}(h) = \lambda_{base}(h) \times f_{epidemia}$$

Com mais chegadas e mesma capacidade, ρ aumenta, e a fila cresce de forma superlinear.

**IC 95% das barras:**
$$\bar{X} \pm 1.96 \cdot S$$
(usando σ amostral das 6 replicações por cenário — aproximação de grande amostra)
""")

    col1,col2,col3 = st.columns(3)
    with col1: st.info(f"**Baseline** — configuração atual.")
    with col2: st.success(f"**+{n_medicos_extra} médico(s)** no vespertino (13h–19h).")
    with col3: st.warning(f"**Epidemia** — demanda ×{fator_epidemia:.1f}.")

    btn_cen = st.button("▶️ Comparar Cenários", use_container_width=True, type="primary")

    if btn_cen or "resultados_cenarios" in st.session_state:
        if btn_cen:
            p_base = copy.deepcopy(params)
            p_c1   = copy.deepcopy(params)
            p_c1["recursos_turno"]["vespertino"]["medicos"] += n_medicos_extra
            p_c2   = copy.deepcopy(params)
            p_c2["lambda_hora"] = {h:lam*fator_epidemia for h,lam in params["lambda_hora"].items()}
            cenarios_dict = {"Baseline":p_base,
                f"+{n_medicos_extra} Médico(s)":p_c1,
                f"Epidemia (×{fator_epidemia:.1f})":p_c2}
            with st.spinner("Simulando cenários × 6 replicações..."):
                resultados = {}
                for nome,p in cenarios_dict.items():
                    estats = [gemeo_digital_pa(p,semente=42+r)[1] for r in range(6)]
                    resultados[nome] = pd.DataFrame(estats)
                st.session_state["resultados_cenarios"] = resultados

        resultados_cenarios = st.session_state["resultados_cenarios"]
        st.plotly_chart(fig_cenarios(resultados_cenarios), use_container_width=True)

        info("Como interpretar o comparativo de cenários",
            """
**Cenário +1 médico:**
- Compare a redução de espera com o custo de reforço
- Observe se a melhora aparece só na média ou também na cauda (P90 e % > 60 min)
- Efeito concentrado no turno vespertino (13h–19h) — verifique o gap horário

**Cenário epidemia:**
- Observe o quanto a fila cresce quando a demanda pressiona a mesma capacidade
- Verifique se o aumento afeta só a média ou também os extremos
- Este cenário é um ensaio de **resiliência operacional**

**Barras de erro:** representam IC 95% entre as 6 replicações.
Barras grandes indicam alta variabilidade — considere mais replicações.
""")

        st.subheader("Resumo comparativo")
        rows = [{"Cenário":nome,
            "Espera média (min)": round(d.espera_medico_media.mean(),1),
            "Tempo total (min)":  round(d.tempo_total_medio.mean(),1),
            "P90 espera (min)":   round(d.p90_espera_medico.mean(),1),
            "% > 60 min":         f"{d.pct_espera_acima_60.mean()*100:.1f}%"}
            for nome,d in resultados_cenarios.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Clique em **Comparar Cenários** para executar a análise.")


# ─── Predição & Prescrição ─────────────────────────────────────────────────
elif pagina == "📈 Predição & Prescrição — Etapas 7B–8":
    st.title("📈 Predição & Prescrição — Etapas 7B e 8")
    st.markdown('<div class="etapa-header">'
                '<b>Etapa 7B</b> — Antecipar demanda com predição &nbsp;|&nbsp; '
                '<b>Etapa 8</b> — Apoiar decisão com prescrição</div>',unsafe_allow_html=True)
    st.markdown(AVISO_METODOLOGICO, unsafe_allow_html=True)

    # ── Etapa 7B — Predição ───────────────────────────────────────────
    st.subheader("Etapa 7B — Predição de demanda — próximos 14 dias")
    info("Pergunta gerencial — Etapa 7B",
        """
**O que tende a acontecer com o PA nos próximos 14 dias se o padrão de demanda se mantiver?**

O twin não apenas replica o presente — ele antecipa gargalos antes que aconteçam.

**Fluxo desta etapa:**
1. Ajustar modelo Prophet na série histórica diária
2. Projetar volume para os próximos 14 dias
3. Converter projeção em fator λ = yhat / demanda_base
4. Escalar λ(h) e simular KPIs esperados para cada dia
""")
    info("Como funciona o Prophet — matemática",
        r"""
O Prophet decompõe a série temporal em componentes aditivos:
$$y(t) = g(t) + s(t) + h(t) + \varepsilon_t$$

- **g(t)**: tendência (linear ou logística com changepoints)
- **s(t)**: sazonalidade (semanal, anual — via séries de Fourier)
- **h(t)**: efeitos de feriados
- **εₜ**: ruído idiossincrático ~ N(0, σ²)

**Sazonalidade semanal** (ativo aqui com 30 dias de histórico):
$$s(t) = \sum_{n=1}^{N}\left[a_n \cos\!\left(\frac{2\pi n t}{P}\right) + b_n \sin\!\left(\frac{2\pi n t}{P}\right)\right]$$

Com P = 7 dias e N = 3 (padrão Prophet).

**Fator de escalonamento λ:**
$$f(d) = \frac{\hat{y}(d)}{\bar{y}_{histórico}}, \quad \lambda_{previsto}(h,d) = \lambda_{base}(h) \cdot f(d)$$

> ⚠️ Com apenas 30 dias históricos, o ajuste é deliberadamente enxuto.
> Em produção, usar janela maior de dados.
""")

    with st.spinner("Ajustando Prophet..."):
        fig_pred, prev_f, df_prophet = fig_predicao(df)

    if fig_pred is not None:
        st.plotly_chart(fig_pred, use_container_width=True)

        st.subheader("KPIs antecipados por dia")
        info("Como o volume previsto vira KPI simulado",
            r"""
Para cada dia d previsto:
1. Calcular fator: $f(d) = \hat{y}(d) / \bar{y}_{hist}$
2. Escalar: $\lambda_{prev}(h) = \lambda_{base}(h) \times f(d)$
3. Rodar 1 replicação do gêmeo com λ previsto → KPIs esperados

**Semáforo de alerta:**
- 🟢 Espera estimada ≤ 55 min — operação confortável
- 🟡 Espera 55–70 min — zona de atenção
- 🔴 Espera > 70 min — risco de violação da meta

Este semáforo opera *dentro do gêmeo*, não no sistema real — é um sinal antecipado,
não uma previsão homologada.
""")
        demanda_base = df_prophet.y.mean()
        resultados_pred = []
        with st.spinner("Simulando KPIs por dia..."):
            for _, row in prev_f.head(7).iterrows():
                fator = float(max(0.5, min(row["yhat"]/demanda_base, 2.0)))
                p_prev = copy.deepcopy(params)
                p_prev["lambda_hora"] = {h:lam*fator for h,lam in params["lambda_hora"].items()}
                _, e = gemeo_digital_pa(p_prev, semente=42)
                esp  = e.get("espera_medico_media",0)
                alerta = "🔴" if esp>70 else ("🟡" if esp>55 else "🟢")
                resultados_pred.append({
                    "Data": row["ds"].date(),
                    "Dia":  row["ds"].strftime("%a"),
                    "Previsão (pac)": round(float(row["yhat"])),
                    "IC 95% (min)":   round(float(row["yhat_lower"])),
                    "IC 95% (máx)":   round(float(row["yhat_upper"])),
                    "Fator λ":        round(fator,2),
                    "Espera est. (min)": round(esp,1),
                    "Alerta": alerta,
                })
        df_pred = pd.DataFrame(resultados_pred)
        st.dataframe(df_pred, use_container_width=True, hide_index=True)

        fig_bar = px.bar(df_pred, x="Data", y="Espera est. (min)",
            color="Fator λ",color_continuous_scale=[[0,VERDE2],[0.7,AZUL2],[1,LARANJA]],
            text="Espera est. (min)",title="Espera estimada por dia — próxima semana")
        fig_bar.add_hline(y=60,line_dash="dash",line_color="red",annotation_text="Meta 60 min")
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(height=350,margin=dict(t=45,b=10))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("Prophet não encontrado. Instale com `pip install prophet`.")
        df_pred = None

    # ── Etapa 8 — Prescrição ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("Etapa 8 — Recomendação Prescritiva de Escala")
    info("Pergunta gerencial — Etapa 8",
        """
**Qual reforço mínimo vale o custo para proteger o nível de serviço nos dias críticos?**

A camada prescritiva transforma a leitura preditiva em **recomendação operacional de escala**.

**Formulação do stress test:**
- Entrada: previsão de demanda × fator de estresse (pressão extra nos dias críticos)
- Políticas candidatas: combinações discretas de médicos extras por turno
- Objetivo: menor reforço capaz de manter espera ≤ 60 min
- Restrição: custo de reforço (noturno2 custa 20% mais)
""")
    info("Formulação matemática do problema prescritivo",
        r"""
**Problema de otimização combinatória:**
$$\min_{(\delta_m, \delta_v, \delta_{n2}) \in \{0,1\} \times \{0,1,2\} \times \{0,1\}} \;
c_m \delta_m + c_v \delta_v + c_{n2} \delta_{n2}$$

Sujeito a:
$$\bar{W}^{sim}(\delta_m, \delta_v, \delta_{n2}) \leq 60 \text{ min}$$
$$P(W > 60 \text{ min}) \leq 15\%$$

Onde:
- $\delta_t$ = médicos extras adicionados ao turno t
- $c_t$ = custo relativo do turno (matutino=1.0, vespertino=1.0, noturno2=1.2)
- $\bar{W}^{sim}$ = espera média estimada pelo gêmeo sob demanda estressada

**Busca por grade (grid search):** como o espaço é pequeno (≤ 12 combinações),
enumeramos todas e escolhemos a de menor custo que satisfaz as restrições.
""")

    turnos_otim = ["matutino","vespertino","noturno2"]
    col1,col2,col3 = st.columns(3)
    if st.button("▶️ Rodar Prescrição (stress test ×1.15)", use_container_width=True, type="primary"):
        resultados_presc = {}
        with st.spinner("Otimizando escala..."):
            for turno in turnos_otim:
                for extra in range(3):
                    p_t = copy.deepcopy(params)
                    p_t["lambda_hora"] = {h:lam*1.15 for h,lam in params["lambda_hora"].items()}
                    p_t["recursos_turno"][turno]["medicos"] += extra
                    estats_t = [gemeo_digital_pa(p_t,semente=42+r)[1] for r in range(4)]
                    df_t2 = pd.DataFrame(estats_t)
                    esp = df_t2.espera_medico_media.mean()
                    if turno not in resultados_presc:
                        resultados_presc[turno] = {"espera_base":esp,"reforco_otimo":extra,"espera_pos":esp}
                    if esp <= 60 and resultados_presc[turno]["reforco_otimo"] == extra:
                        resultados_presc[turno]["espera_pos"] = esp
                        break
                    resultados_presc[turno]["espera_pos"] = esp

        for turno,(col,) in zip(turnos_otim,[col1,col2,col3]):
            r  = resultados_presc[turno]
            delta = r["espera_base"] - r["espera_pos"]
            cor = "" if r["reforco_otimo"]==0 else "warning" if r["reforco_otimo"]>=2 else "info"
            col.markdown(f'<div class="kpi-card {cor}">'
                f'<div class="kpi-value">+{r["reforco_otimo"]} méd.</div>'
                f'<div class="kpi-label">{turno.title()}</div>'
                f'<div class="kpi-delta">Redução: {delta:.1f} min</div></div>',
                unsafe_allow_html=True)

        presc_rows = [{"Turno":t,
            "Reforço recomendado":f"+{r['reforco_otimo']} médico(s)",
            "Espera sem reforço":f"{r['espera_base']:.1f} min",
            "Espera com reforço":f"{r['espera_pos']:.1f} min",
            "Redução":f"{r['espera_base']-r['espera_pos']:.1f} min"}
            for t,r in resultados_presc.items()]
        st.dataframe(pd.DataFrame(presc_rows), use_container_width=True, hide_index=True)

        info("Como ler a recomendação prescritiva",
            """
- **Reforço 0**: o turno já está operando dentro da meta com a demanda estressada
- **Reforço +1 ou +2**: são os médicos extras mínimos para proteger a meta de 60 min
- **Redução de espera**: impacto esperado do reforço na espera média do turno

**Custo relativo do reforço:**
- Matutino e Vespertino: custo unitário 1.0
- Noturno2: custo unitário 1.2 (adicional noturno)

**Quando a recomendação mudaria:**
- Se a demanda crítica fosse mais severa (fator > 1.15)
- Se a meta fosse endurecida (ex: ≤ 45 min)
- Se a capacidade base fosse recalibrada para baixo
""")
    else:
        st.info("Clique em **Rodar Prescrição** para gerar as recomendações.")

    # ── Fechamento ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📚 Framework completo — Resumo gerencial")
    info("Fechamento: o que esta aula consolida",
        """
| Etapa | Pergunta respondida | Entrega principal |
|-------|--------------------|--------------------|
| 1 | O que o sistema real está dizendo? | Base histórica do D9 como fotografia operacional |
| 2 | Como o dado vira input do twin? | λ(h), Lognormal por Manchester, escala ERP |
| 3 | Como representar o PA? | Fluxo SimPy com PriorityResource |
| 4 | Como gerar evidência confiável? | Replicações, warm-up e IC 95% |
| 5 | O twin é confiável para gestão? | Checkpoint de validação (ERP ≤ 15%) |
| **5B** | **Onde e por que o twin divergiu?** | **Gap horário, ρ efetivo, stress test** |
| 6 | Como o twin permanece vivo? | Pipeline de atualização e drift detection |
| 7A | Como o sistema reage a cenários? | Comparativo baseline × capacidade × epidemia |
| 7B | O que tende a acontecer à frente? | Previsão Prophet + KPIs antecipados |
| 8 | O que fazer diante disso? | Stress test prescritivo com grade search |

**Referências:**
- Law, A. M. *Simulation Modeling and Analysis*, 5ª ed. McGraw-Hill, 2015.
- Sargent, R. G. Verification and validation of simulation models. *Journal of Simulation*, 7(1), 2013.
- Taylor & Letham. Forecasting at scale. *The American Statistician*, 72(1), 2018.
- SimPy Docs: https://simpy.readthedocs.io
""")
