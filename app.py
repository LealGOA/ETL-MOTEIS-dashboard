import streamlit as st
import streamlit.components.v1 as components
from datetime import date
import calendar

from database import get_dados_diarios, get_unidades, get_resumo_mes, get_comparativo_mes
from calendar_view import render_calendar
from utils import formatar_moeda, formatar_numero

st.set_page_config(
    page_title="Dashboard Motéis",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
.metric-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    text-align: center;
    border: 1px solid #eee;
}
.metric-label { font-size: 13px; color: #888; margin-bottom: 4px; }
.metric-value { font-size: 26px; font-weight: 700; color: #333; }
.metric-value.money { color: #2e7d32; }
</style>
""", unsafe_allow_html=True)

# Impede teclado virtual ao abrir selectbox no mobile (marca inputs como readonly)
components.html("""
<script>
(function() {
    const makeReadonly = () => {
        document.querySelectorAll('[data-baseweb="popover"] input, [data-baseweb="select"] input')
            .forEach(el => el.setAttribute('readonly', 'true'));
    };
    const observer = new MutationObserver(makeReadonly);
    observer.observe(document.body, { childList: true, subtree: true });
    makeReadonly();
})();
</script>
""", height=0)

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

hoje = date.today()

MESES_PT = {
    1: "Janeiro",  2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",     6: "Junho",     7: "Julho",     8: "Agosto",
    9: "Setembro", 10: "Outubro",  11: "Novembro", 12: "Dezembro",
}

c1, c2 = st.sidebar.columns(2)
with c1:
    mes = st.selectbox(
        "Mês",
        options=list(range(1, 13)),
        format_func=lambda x: MESES_PT[x],
        index=hoje.month - 1,
    )
with c2:
    anos = list(range(2024, hoje.year + 2))
    ano = st.selectbox("Ano", options=anos, index=anos.index(hoje.year))

unidades = get_unidades()
unidade = st.sidebar.selectbox("Unidade", options=unidades, index=0)

st.sidebar.divider()

if st.sidebar.button("🔄 Atualizar dados"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("**Legenda**")
st.sidebar.markdown("""
<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
  <div style="width:14px;height:14px;background:#fff3e0;border-radius:3px;border:1px solid #ffcc80"></div>
  <span style="font-size:13px">Feriado</span>
</div>
<div style="display:flex;align-items:center;gap:8px">
  <div style="width:14px;height:14px;background:#e8f5e9;border-radius:3px;border:1px solid #c8e6c9"></div>
  <span style="font-size:13px">Fim de semana</span>
</div>
""", unsafe_allow_html=True)

# ── Dados ─────────────────────────────────────────────────────────────────────
data_inicio = date(ano, mes, 1)
data_fim    = date(ano, mes, calendar.monthrange(ano, mes)[1])
filtro_uni  = unidade if unidade != "Todas" else None

dados  = get_dados_diarios(data_inicio, data_fim, filtro_uni)
resumo = get_resumo_mes(ano, mes, filtro_uni)

# Se "Todas", agregar por data
if unidade == "Todas" and not dados.empty:
    import pandas as pd
    dados = (
        dados.groupby("data")
        .agg(total_saidas=("total_saidas", "sum"), total_faturamento=("total_faturamento", "sum"))
        .reset_index()
    )
    dados["ticket_medio"] = dados.apply(
        lambda r: r["total_faturamento"] / r["total_saidas"] if r["total_saidas"] > 0 else 0,
        axis=1,
    )

# ── Cabeçalho ─────────────────────────────────────────────────────────────────
titulo = f"{MESES_PT[mes]} {ano}"
if unidade != "Todas":
    titulo += f" · {unidade}"
st.markdown(f"## {titulo}")

# Cards de resumo
dias_com_dados = int((dados["total_saidas"] > 0).sum()) if not dados.empty else 0

# Calcular dia_limite para comparativo vs mês anterior
# Usa o último dia com dados reais (ETL captura D-1, não D)
if ano == hoje.year and mes == hoje.month:
    import pandas as pd
    dados_com_saidas = dados[dados["total_saidas"] > 0] if not dados.empty else pd.DataFrame()
    if not dados_com_saidas.empty:
        ultimo_dia_com_dados = pd.to_datetime(dados_com_saidas["data"]).max().day
    else:
        ultimo_dia_com_dados = max(hoje.day - 1, 1)
    _mes_ant = mes - 1 if mes > 1 else 12
    _ano_ant = ano if mes > 1 else ano - 1
    dia_limite = min(ultimo_dia_com_dados, calendar.monthrange(_ano_ant, _mes_ant)[1])
else:
    dia_limite = calendar.monthrange(ano, mes)[1]

comp = get_comparativo_mes(ano, mes, dia_limite, filtro_uni)

col1, col2, col3, col4 = st.columns(4)

with col1:
    delta_s = f"{comp['delta_pct']['saidas']:+.1f}%" if comp['delta_pct']['saidas'] is not None else None
    st.metric("Total de saídas", formatar_numero(resumo["total_saidas"]), delta=delta_s)

with col2:
    delta_f = f"{comp['delta_pct']['faturamento']:+.1f}%" if comp['delta_pct']['faturamento'] is not None else None
    st.metric("Faturamento total", formatar_moeda(resumo["total_faturamento"]), delta=delta_f)

with col3:
    delta_t = f"{comp['delta_pct']['ticket']:+.1f}%" if comp['delta_pct']['ticket'] is not None else None
    st.metric("Ticket médio", formatar_moeda(resumo["ticket_medio"]), delta=delta_t)

with col4:
    st.metric("Dias com movimento", str(dias_com_dados))

st.divider()

# ── Calendário ────────────────────────────────────────────────────────────────
render_calendar(ano, mes, dados)

st.divider()
st.markdown(
    "<p style='text-align:center;color:#bbb;font-size:12px'>"
    "Dashboard ETL Motéis · Atualizado diariamente às 08:00 BRT</p>",
    unsafe_allow_html=True,
)
