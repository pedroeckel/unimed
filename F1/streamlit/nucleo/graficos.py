"""Figuras Plotly reutilizáveis, com a identidade visual do curso."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

VERDE = "#1A5E3A"
VERDE2 = "#2E7D52"
AZUL = "#1F4E79"
AZUL2 = "#2E86C1"
LARANJA = "#E65100"
VERMELHO = "#C0392B"
CINZA = "#9E9E9E"
ROXO = "#7B4397"
PRETO = "#111111"

SEQUENCIA = [AZUL2, VERDE2, LARANJA, ROXO, VERMELHO, CINZA]
NOMES_DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def _base(fig: go.Figure, titulo: str = "", y: str = "", x: str = "",
          altura: int = 380) -> go.Figure:
    fig.update_layout(
        title=titulo, xaxis_title=x, yaxis_title=y, height=altura,
        margin=dict(l=10, r=10, t=45 if titulo else 15, b=10),
        hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.0,
                                           xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,.18)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,.18)")
    return fig


def serie(indice, valores, nome="Série", cor=AZUL2, titulo="", y="", x="Data",
          media_movel: int | None = None, altura: int = 340) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=indice, y=valores, name=nome, line=dict(color=cor, width=1.2)))
    if media_movel:
        suave = pd.Series(np.asarray(valores, dtype=float)).rolling(media_movel).mean()
        fig.add_trace(go.Scatter(x=indice, y=suave, name=f"Média móvel ({media_movel})",
                                 line=dict(color=VERDE, width=2.4)))
    return _base(fig, titulo, y, x, altura)


def marcar_feriados(fig: go.Figure, feriados, indice) -> go.Figure:
    inicio, fim = pd.Timestamp(min(indice)), pd.Timestamp(max(indice))
    for f in pd.DatetimeIndex(feriados):
        if inicio <= f <= fim:
            fig.add_vline(x=f, line=dict(color=VERMELHO, width=1, dash="dot"), opacity=0.45)
    return fig


def comparar_previsoes(indice, real, previsoes: dict, titulo="", y="", banda=None,
                       altura: int = 400) -> go.Figure:
    """Real em preto grosso; cada previsão em uma cor. A banda opcional é o IC 95%."""
    fig = go.Figure()
    if banda is not None:
        li, ls = banda
        fig.add_trace(go.Scatter(x=list(indice) + list(indice)[::-1],
                                 y=list(ls) + list(li)[::-1], fill="toself",
                                 fillcolor="rgba(46,125,82,.16)", line=dict(width=0),
                                 name="IC 95%", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=indice, y=real, name="Real",
                             line=dict(color=PRETO, width=2.4)))
    for i, (nome, v) in enumerate(previsoes.items()):
        fig.add_trace(go.Scatter(x=indice, y=v, name=nome,
                                 line=dict(color=SEQUENCIA[i % len(SEQUENCIA)],
                                           width=1.6, dash="dash")))
    return _base(fig, titulo, y, "Data", altura)


def barras_horizontais(rotulos, valores, titulo="", x="", cores=None,
                       altura: int = 380) -> go.Figure:
    cores = cores or [AZUL2] * len(rotulos)
    fig = go.Figure(go.Bar(x=list(valores), y=list(rotulos), orientation="h",
                           marker_color=cores,
                           text=[f"{v:,.2f}".replace(",", ".") for v in valores],
                           textposition="auto"))
    return _base(fig, titulo, "", x, altura)


def barras(x, y, titulo="", rotulo_y="", rotulo_x="", cores=None, texto=None,
           altura: int = 340) -> go.Figure:
    fig = go.Figure(go.Bar(x=list(x), y=list(y), marker_color=cores or AZUL2,
                           text=texto, textposition="auto"))
    return _base(fig, titulo, rotulo_y, rotulo_x, altura)


def curva_dupla(x, y1, y2, nome1, nome2, titulo="", y="", rotulo_x="",
                marcar_minimo=True, altura: int = 380) -> go.Figure:
    """Duas curvas na mesma escala: o padrão de treino x teste / treino x validação."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y1, name=nome1, line=dict(color=AZUL2, width=2)))
    fig.add_trace(go.Scatter(x=x, y=y2, name=nome2, line=dict(color=VERMELHO, width=2)))
    if marcar_minimo and len(y2):
        k = int(np.argmin(y2))
        fig.add_vline(x=list(x)[k], line=dict(color=VERDE, width=1.6, dash="dot"))
        fig.add_annotation(x=list(x)[k], y=float(np.min(y2)), text="melhor ponto",
                           showarrow=True, arrowhead=2, ax=40, ay=-30,
                           font=dict(color=VERDE, size=11))
    return _base(fig, titulo, y, rotulo_x, altura)


def perfil_duplo(perfil_hora: pd.Series, perfil_dia: pd.Series, altura: int = 320):
    """Os dois retratos que formam o mapa de escala do gestor."""
    f1 = go.Figure(go.Scatter(x=perfil_hora.index, y=perfil_hora.to_numpy(), mode="lines+markers",
                              line=dict(color=AZUL2, width=2.4), name="Média"))
    _base(f1, "Perfil por hora do dia", "Média por hora", "Hora", altura)
    f2 = go.Figure(go.Bar(x=NOMES_DIAS, y=perfil_dia.to_numpy(), marker_color=LARANJA))
    _base(f2, "Perfil por dia da semana", "Média por hora", "", altura)
    return f1, f2


def correlograma(valores, limites, titulo="", altura: int = 300, destaque=None) -> go.Figure:
    """ACF/PACF em barras, com a faixa de confiança aproximada."""
    cores = [VERMELHO if (destaque and lag in destaque) else AZUL2
             for lag in range(len(valores))]
    fig = go.Figure(go.Bar(x=list(range(len(valores))), y=list(valores), marker_color=cores))
    fig.add_hline(y=limites, line=dict(color=CINZA, dash="dot"))
    fig.add_hline(y=-limites, line=dict(color=CINZA, dash="dot"))
    return _base(fig, titulo, "Autocorrelação", "Defasagem", altura)


def dispersao_lags(curva_bruta, curva_residual, lag_verdadeiro, titulo="",
                   altura: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(len(curva_bruta))), y=curva_bruta,
                             name="Correlação bruta", mode="lines+markers",
                             line=dict(color=CINZA, width=2)))
    fig.add_trace(go.Scatter(x=list(range(len(curva_residual))), y=curva_residual,
                             name="Correlação dos resíduos", mode="lines+markers",
                             line=dict(color=VERDE, width=2.4)))
    fig.add_vline(x=lag_verdadeiro, line=dict(color=VERMELHO, width=1.6, dash="dash"))
    fig.add_annotation(x=lag_verdadeiro, y=0, text="lag verdadeiro", showarrow=False,
                       yshift=-28, font=dict(color=VERMELHO, size=10))
    fig.add_hline(y=0, line=dict(color=CINZA, width=1))
    return _base(fig, titulo, "Correlação", "Defasagem (dias)", altura)


def escala_versus_demanda(lambda_hora, agentes_hora, ocupacao=None,
                          altura: int = 400) -> go.Figure:
    """Demanda prevista contra capacidade escalada, hora a hora.

    Onde a ocupação passa de 0,85, a fila deixa de crescer devagar e passa a explodir.
    """
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(range(24)), y=list(lambda_hora), name="Chamadas previstas",
                         marker_color="rgba(46,134,193,.55)"))
    fig.add_trace(go.Scatter(x=list(range(24)), y=list(agentes_hora), name="Atendentes",
                             yaxis="y2", mode="lines+markers",
                             line=dict(color=LARANJA, width=2.6, shape="hv")))
    if ocupacao is not None:
        fig.add_trace(go.Scatter(x=list(range(24)), y=list(np.asarray(ocupacao) * 100),
                                 name="Ocupação (%)", yaxis="y2", mode="lines",
                                 line=dict(color=VERMELHO, width=1.4, dash="dot")))
    fig.update_layout(yaxis2=dict(title="Atendentes / ocupação", overlaying="y", side="right"))
    return _base(fig, "", "Chamadas por hora", "Hora do dia", altura)


def histograma(valores, titulo="", x="", p90=None, altura: int = 320) -> go.Figure:
    fig = go.Figure(go.Histogram(x=list(valores), nbinsx=40, marker_color=AZUL2))
    if p90 is not None:
        fig.add_vline(x=p90, line=dict(color=VERMELHO, width=2, dash="dash"))
        fig.add_annotation(x=p90, y=1, yref="paper", text=f"P90 = {p90:.2f}",
                           showarrow=False, yshift=-10, font=dict(color=VERMELHO, size=11))
    return _base(fig, titulo, "Frequência", x, altura)


def fronteira(custos, servicos, rotulos, altura: int = 380) -> go.Figure:
    """Custo contra nível de serviço: a tela que vai para a diretoria."""
    fig = go.Figure(go.Scatter(x=custos, y=np.asarray(servicos) * 100, mode="lines+markers+text",
                               text=rotulos, textposition="top center",
                               line=dict(color=VERDE2, width=2.4),
                               marker=dict(size=9, color=AZUL)))
    return _base(fig, "", "Nível de serviço (%)", "Custo do dia (R$)", altura)


def decomposicao(indice, observado, tendencia, sazonal, residuo, altura: int = 620) -> go.Figure:
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=("Observado", "Tendência", "Sazonalidade", "Resíduo"))
    for i, (v, cor) in enumerate([(observado, PRETO), (tendencia, VERDE),
                                  (sazonal, AZUL2), (residuo, CINZA)], start=1):
        fig.add_trace(go.Scatter(x=indice, y=v, line=dict(color=cor, width=1.2),
                                 showlegend=False), row=i, col=1)
    fig.update_layout(height=altura, margin=dict(l=10, r=10, t=40, b=10),
                      plot_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,.18)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(128,128,128,.18)")
    return fig
