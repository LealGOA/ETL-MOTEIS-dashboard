import streamlit as st
import pandas as pd
from datetime import date
import calendar

from database import get_dados_diarios, get_unidades, get_resumo_mes, get_dados_por_unidade, get_comparativo_mes
from calendar_view import render_calendar
from utils import formatar_moeda, formatar_numero

# Configuração da página
st.set_page_config(
    page_title="Dashboard Motéis",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="collapsed"  # Sidebar fechada por padrão em mobile
)

# ── Autenticação ──────────────────────────────────────────────────────────────
if not st.session_state.get("autenticado"):
    st.markdown("## 🔐 Dashboard Motéis")
    senha = st.text_input("Senha de acesso", type="password")
    if st.button("Entrar"):
        if senha == st.secrets["DASHBOARD_PASSWORD"]:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# CSS Global — Mobile First
st.markdown("""
<style>
    /* Reset e base mobile */
    .block-container {
        padding: 1rem 0.75rem !important;
        max-width: 100% !important;
    }

    /* Header compacto */
    .dashboard-header {
        text-align: center;
        margin-bottom: 1rem;
    }

    .dashboard-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #333;
        margin: 0 0 0.5rem 0;
    }

    /* Badge do motel selecionado — DESTAQUE PRINCIPAL */
    .motel-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 1rem;
        font-weight: 700;
        padding: 0.6rem 1.25rem;
        border-radius: 50px;
        margin: 0.5rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .motel-badge.todas {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.4);
    }

    /* Cards de métricas — Grid responsivo */
    .metrics-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .metric-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 12px;
        padding: 0.75rem;
        text-align: center;
    }

    .metric-card-label {
        font-size: 0.7rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.25rem;
    }

    .metric-card-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: #333;
    }

    .metric-card-value.money { color: #2e7d32; }
    .metric-card-value.highlight { color: #667eea; }

    /* Legenda compacta */
    .legenda {
        display: flex;
        justify-content: center;
        gap: 1rem;
        font-size: 0.7rem;
        color: #666;
        margin-bottom: 0.75rem;
    }

    .legenda-item {
        display: flex;
        align-items: center;
        gap: 4px;
    }

    .legenda-dot {
        width: 12px;
        height: 12px;
        border-radius: 3px;
        border: 1px solid #ddd;
    }

    .legenda-dot.feriado { background: #fff3e0; }
    .legenda-dot.fds { background: #e8f5e9; }

    /* Esconder elementos do Streamlit */
    .stDeployButton,
    footer,
    #MainMenu {
        display: none !important;
    }

    /* Ajuste do selectbox */
    .stSelectbox > div > div {
        font-size: 0.9rem !important;
    }

    /* Divider mais sutil */
    hr {
        margin: 0.75rem 0 !important;
        border-color: #eee !important;
    }

    /* Desktop */
    @media (min-width: 768px) {
        .block-container {
            padding: 2rem 3rem !important;
            max-width: 1200px !important;
        }

        .dashboard-title { font-size: 1.5rem; }

        .motel-badge {
            font-size: 1.1rem;
            padding: 0.75rem 1.5rem;
        }

        .metrics-grid {
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
        }

        .metric-card { padding: 1rem; }
        .metric-card-label { font-size: 0.75rem; }
        .metric-card-value { font-size: 1.4rem; }
    }

    .metric-card-delta {
        font-size: 0.7rem;
        font-weight: 600;
        margin-top: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estado
if "mes" not in st.session_state:
    st.session_state.mes = date.today().month
if "ano" not in st.session_state:
    st.session_state.ano = date.today().year


def mes_anterior():
    if st.session_state.mes == 1:
        st.session_state.mes = 12
        st.session_state.ano -= 1
    else:
        st.session_state.mes -= 1


def mes_proximo():
    if st.session_state.mes == 12:
        st.session_state.mes = 1
        st.session_state.ano += 1
    else:
        st.session_state.mes += 1


# Header
st.markdown("""
<div class="dashboard-header">
    <p class="dashboard-title">🏨 Dashboard Operacional</p>
</div>
""", unsafe_allow_html=True)

# Filtro de unidade (inline, não na sidebar)
unidades = get_unidades()

col_filtro1, col_filtro2 = st.columns([2, 1])

with col_filtro1:
    unidade_selecionada = st.selectbox(
        "Unidade",
        options=unidades,
        index=0,
        label_visibility="collapsed"
    )

with col_filtro2:
    if st.button("🔄", help="Atualizar dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Badge do motel selecionado — DESTAQUE PRINCIPAL
badge_class = "motel-badge todas" if unidade_selecionada == "Todas" else "motel-badge"
badge_text = "🏨 Todas as Unidades" if unidade_selecionada == "Todas" else f"📍 {unidade_selecionada}"

st.markdown(f"""
<div style="text-align: center; margin-bottom: 0.75rem;">
    <span class="{badge_class}">{badge_text}</span>
</div>
""", unsafe_allow_html=True)

# Navegação de mês
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    st.button("◀", on_click=mes_anterior, use_container_width=True)

with col2:
    st.markdown(f"""
    <div style="text-align:center; font-size:1.1rem; font-weight:600; padding:0.5rem 0;">
        {MESES_PT[st.session_state.mes]} {st.session_state.ano}
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.button("▶", on_click=mes_proximo, use_container_width=True)

# Dados
ano_selecionado = st.session_state.ano
mes_selecionado = st.session_state.mes

data_inicio = date(ano_selecionado, mes_selecionado, 1)
ultimo_dia = calendar.monthrange(ano_selecionado, mes_selecionado)[1]
data_fim = date(ano_selecionado, mes_selecionado, ultimo_dia)

filtro_unidade = unidade_selecionada if unidade_selecionada != "Todas" else None

dados = get_dados_diarios(data_inicio, data_fim, filtro_unidade)

# Se filtro "Todas", agregar por data
if unidade_selecionada == "Todas" and not dados.empty:
    dados = (
        dados.groupby("data")
        .agg(total_saidas=("total_saidas", "sum"), total_faturamento=("total_faturamento", "sum"))
        .reset_index()
    )
    dados["ticket_medio"] = dados.apply(
        lambda r: r["total_faturamento"] / r["total_saidas"] if r["total_saidas"] > 0 else 0,
        axis=1,
    )

resumo = get_resumo_mes(ano_selecionado, mes_selecionado, filtro_unidade)

dias_com_dados = int((dados["total_saidas"] > 0).sum()) if not dados.empty else 0

hoje = date.today()
if (ano_selecionado, mes_selecionado) == (hoje.year, hoje.month):
    if not dados.empty:
        dias_validos = dados[dados["total_saidas"] > 0]["data"]
        dia_limite = int(dias_validos.max().day) if not dias_validos.empty else hoje.day
    else:
        dia_limite = hoje.day
else:
    dia_limite = ultimo_dia

comparativo = get_comparativo_mes(ano_selecionado, mes_selecionado, dia_limite, filtro_unidade)

def fmt_mom_badge(pct_val):
    if pct_val is None:
        return ""
    if abs(pct_val) < 2.0:
        symbol, color = "■", "#f9a825"
    elif pct_val > 0:
        symbol, color = "▲", "#2e7d32"
    else:
        symbol, color = "▼", "#c62828"
    sinal = "+" if pct_val > 0 else ""
    return f'<div class="metric-card-delta" style="color:{color};">{symbol} {sinal}{pct_val:.1f}% vs mês ant.</div>'

# Cards de métricas (grid 2x2 em mobile, 4x1 em desktop)
st.markdown(f"""
<div class="metrics-grid">
    <div class="metric-card">
        <div class="metric-card-label">Saídas</div>
        <div class="metric-card-value highlight">{formatar_numero(resumo['total_saidas'])}</div>
        {fmt_mom_badge(comparativo['delta_pct']['saidas'])}
    </div>
    <div class="metric-card">
        <div class="metric-card-label">Faturamento</div>
        <div class="metric-card-value money">{formatar_moeda(resumo['total_faturamento'])}</div>
        {fmt_mom_badge(comparativo['delta_pct']['faturamento'])}
    </div>
    <div class="metric-card">
        <div class="metric-card-label">Ticket Médio</div>
        <div class="metric-card-value">{formatar_moeda(resumo['ticket_medio'])}</div>
        {fmt_mom_badge(comparativo['delta_pct']['ticket'])}
    </div>
    <div class="metric-card">
        <div class="metric-card-label">Dias c/ Mov.</div>
        <div class="metric-card-value">{dias_com_dados}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_diaria, tab_mensal = st.tabs(["📅 Visão Diária", "📊 Visão Mensal"])

with tab_diaria:
    st.markdown("""
<div class="legenda">
    <div class="legenda-item">
        <div class="legenda-dot feriado"></div>
        <span>Feriado</span>
    </div>
    <div class="legenda-item">
        <div class="legenda-dot fds"></div>
        <span>Fim de semana</span>
    </div>
</div>
""", unsafe_allow_html=True)
    render_calendar(ano_selecionado, mes_selecionado, dados)

with tab_mensal:
    st.markdown("### Comparativo por Unidade")

    df_unidades = get_dados_por_unidade(ano_selecionado, mes_selecionado, dia_limite)

    if not df_unidades.empty:
        DELTA_THRESHOLD = 0.02

        def _arrow_color(delta, anterior):
            if anterior != 0 and abs(delta / anterior) < DELTA_THRESHOLD:
                return "■", "#f9a825"
            if delta > 0:
                return "▲", "#2e7d32"
            if delta < 0:
                return "▼", "#c62828"
            return "–", "#888888"

        def fmt_numero(x):
            return f"{int(x):,}".replace(",", ".")

        def fmt_moeda_br(x):
            return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        def fmt_delta(delta, arrow):
            sinal = "+" if delta > 0 else ""
            return f"{arrow} {sinal}{int(delta):,}".replace(",", ".")

        def fmt_delta_moeda(delta, arrow):
            sinal = "+" if delta > 0 else ""
            return f"{arrow} {sinal}{delta:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        arrows_s, colors_s = zip(*df_unidades.apply(
            lambda r: _arrow_color(r["delta_saidas"], r["saidas_anterior"]), axis=1
        ))
        arrows_f, colors_f = zip(*df_unidades.apply(
            lambda r: _arrow_color(r["delta_faturamento"], r["faturamento_anterior"]), axis=1
        ))

        df_display = pd.DataFrame({
            "Unidade":        df_unidades["unidade"],
            "Saídas":         df_unidades["saidas"].apply(fmt_numero),
            "Δ Saídas":       [fmt_delta(d, a) for d, a in zip(df_unidades["delta_saidas"], arrows_s)],
            "TM (R$)":        df_unidades["ticket_medio"].apply(fmt_moeda_br),
            "Fat. Acum (R$)": df_unidades["faturamento"].apply(fmt_moeda_br),
            "Δ Fat. (R$)":    [fmt_delta_moeda(d, a) for d, a in zip(df_unidades["delta_faturamento"], arrows_f)],
        })

        def highlight_unidade(row):
            if unidade_selecionada != "Todas" and row["Unidade"] == unidade_selecionada:
                return ["background-color: #FFF9C4"] * len(row)
            return [""] * len(row)

        def color_delta_col(_, color_vals):
            return [f"color: {c}; font-weight: bold" for c in color_vals]

        styled_df = (
            df_display.style
            .apply(highlight_unidade, axis=1)
            .apply(color_delta_col, color_vals=list(colors_s), subset=["Δ Saídas"])
            .apply(color_delta_col, color_vals=list(colors_f), subset=["Δ Fat. (R$)"])
        )

        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            height=min(len(df_display) * 35 + 38, 500),
        )

        # Totais
        total_saidas     = int(df_unidades["saidas"].sum())
        total_saidas_ant = int(df_unidades["saidas_anterior"].sum())
        total_delta_s    = int(df_unidades["delta_saidas"].sum())
        total_fat        = float(df_unidades["faturamento"].sum())
        total_fat_ant    = float(df_unidades["faturamento_anterior"].sum())
        total_delta_f    = float(df_unidades["delta_faturamento"].sum())
        total_tm         = total_fat / total_saidas if total_saidas > 0 else 0

        icon_s, color_s = _arrow_color(total_delta_s, total_saidas_ant)
        icon_f, color_f = _arrow_color(total_delta_f, total_fat_ant)

        st.markdown(
            f"---\n**Totais:** {fmt_numero(total_saidas)} saídas "
            f"(<span style='color:{color_s};font-weight:bold'>{fmt_delta(total_delta_s, icon_s)}</span>) · "
            f"TM R$ {fmt_moeda_br(total_tm)} · "
            f"Fat. R$ {fmt_moeda_br(total_fat)} "
            f"(<span style='color:{color_f};font-weight:bold'>{fmt_delta_moeda(total_delta_f, icon_f)}</span>)",
            unsafe_allow_html=True,
        )
    else:
        st.info("Nenhum dado encontrado para o período selecionado.")

# Footer compacto
st.markdown("""
<p style="text-align: center; color: #aaa; font-size: 0.65rem; margin-top: 1rem;">
    Atualizado diariamente às 08:00
</p>
""", unsafe_allow_html=True)
