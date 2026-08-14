"""
Gêmeo Digital da Operadora — Ponta a Ponta
Módulo F1 | Previsão de Demanda na Gestão de Planos de Saúde — Prof. Pedro, UNIMED SP

Rodar:  streamlit run F1/streamlit/app.py

Esta aplicação amarra as nove aulas do módulo em uma única narrativa:
dados -> diagnóstico -> engenharia de variáveis -> modelos -> avaliação ->
previsão -> gêmeo digital -> decisão de escala.
"""

from __future__ import annotations

import os
import sys
import warnings

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Gêmeo Digital da Operadora — F1",
                   page_icon="📞", layout="wide", initial_sidebar_state="expanded")

from paginas import comum  # noqa: E402
from paginas import (p0_visao_geral, p1_dados, p2_features, p3_modelos, p4_avaliacao,  # noqa: E402
                     p5_previsao, p6_gemeo, p7_cenarios, p8_sintese)

st.markdown(comum.CSS, unsafe_allow_html=True)
comum.iniciar_estado()

PAGINAS = {
    "🗺️  Visão geral": p0_visao_geral,
    "📈  1. Dados e diagnóstico": p1_dados,
    "🧱  2. Engenharia de variáveis": p2_features,
    "🤖  3. Modelos": p3_modelos,
    "📏  4. Avaliação honesta": p4_avaliacao,
    "🔮  5. Previsão operacional": p5_previsao,
    "🏥  6. Gêmeo digital": p6_gemeo,
    "🎯  7. Cenários e decisão": p7_cenarios,
    "📚  8. Síntese": p8_sintese,
}

with st.sidebar:
    st.markdown("## 📞 Gêmeo Digital")
    st.markdown("**Central de atendimento — operadora**")
    st.markdown("---")
    escolha = st.radio("Navegação", list(PAGINAS), label_visibility="collapsed")

    st.markdown("---")
    campeao = st.session_state.get("campeão")
    rodados = st.session_state.get("modelos_rodados", {})
    st.markdown("**Estado da sessão**")
    if campeao:
        st.markdown(f"- Campeão: **{campeao}**")
    else:
        st.markdown("- Campeão: _ainda não escolhido_")
    st.markdown(f"- Modelos rodados: **{len(rodados)}**")
    tem_previsao = st.session_state.get("previsao_horaria") is not None
    st.markdown(f"- Previsão horária: **{'pronta' if tem_previsao else 'pendente'}**")

    st.markdown("---")
    if st.button("♻️ Limpar cache e recomecar", width="stretch"):
        st.cache_data.clear()
        st.cache_resource.clear()
        for chave in list(comum.PADROES):
            st.session_state.pop(chave, None)
        st.rerun()

    st.markdown(
        "<small style='color:gray'>F1 — Previsão de Demanda<br>"
        "Prof. Pedro | UNIMED SP<br>"
        "Base sintética, semente fixa</small>", unsafe_allow_html=True)

PAGINAS[escolha].render()
