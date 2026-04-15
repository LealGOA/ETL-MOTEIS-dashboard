import streamlit as st
import pandas as pd
from datetime import date
from utils import get_dias_do_mes, get_semana_do_primeiro_dia

DIAS_SEMANA = ["S", "T", "Q", "Q", "S", "S", "D"]

_CSS = """
<style>
/* ── wrapper com scroll horizontal no mobile ── */
.cal-wrapper {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

/* ── grid único: header + dias na mesma grade ── */
.cal-table {
    display: grid;
    grid-template-columns: repeat(7, minmax(44px, 1fr));
    gap: 2px;
    min-width: 320px;
}

/* ── header ── */
.cal-header-cell {
    text-align: center;
    font-weight: 700;
    font-size: 0.65rem;
    color: #888;
    padding: 6px 2px;
    background: #f5f5f5;
    border-radius: 4px;
}
.cal-header-cell.fds-h {
    color: #388e3c;
    background: #e8f5e9;
}

/* ── células dos dias ── */
.cal-day {
    border: 1px solid #eee;
    border-radius: 6px;
    padding: 4px;
    min-height: 65px;
    background: #fff;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
}
.cal-day.empty { background: transparent; border: none; min-height: 0; }
.cal-day.fds   { background: #e8f5e9; border-color: #c8e6c9; }
.cal-day.fer   { background: #fff3e0; border-color: #ffe0b2; }

.cal-num {
    font-weight: 700;
    font-size: 0.85rem;
    line-height: 1;
    color: #333;
}

.cal-badge {
    font-size: 0.45rem;
    background: #ff9800;
    color: #fff;
    padding: 1px 3px;
    border-radius: 2px;
    margin-left: 2px;
    vertical-align: middle;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 40px;
    display: inline-block;
}

.cal-metrics {
    margin-top: auto;
    font-size: 0.6rem;
    line-height: 1.4;
}

.cal-metric-row {
    display: flex;
    justify-content: space-between;
    color: #888;
}

.cal-metric-val {
    font-weight: 600;
    color: #333;
}

.cal-metric-val.money { color: #2e7d32; }

.cal-no-data {
    margin-top: auto;
    text-align: center;
    color: #ccc;
    font-size: 0.65rem;
}

/* Tablet */
@media (min-width: 480px) {
    .cal-day { min-height: 75px; padding: 6px; }
    .cal-num { font-size: 0.9rem; }
    .cal-metrics { font-size: 0.65rem; }
    .cal-badge { font-size: 0.5rem; }
}

/* Desktop */
@media (min-width: 768px) {
    .cal-table { gap: 4px; }
    .cal-header-cell { font-size: 0.75rem; padding: 8px 2px; }
    .cal-day { min-height: 95px; padding: 8px; border-radius: 8px; }
    .cal-num { font-size: 1rem; }
    .cal-metrics { font-size: 0.75rem; }
    .cal-badge { font-size: 0.55rem; padding: 2px 5px; }
}

@media (min-width: 1024px) {
    .cal-day { min-height: 110px; padding: 10px; }
    .cal-metrics { font-size: 0.8rem; }
}
</style>
"""

FDS_COLS = {5, 6}  # sábado=5, domingo=6 (índices de DIAS_SEMANA)


def _fmt_curta(valor: float) -> str:
    """Formata valor de forma compacta para mobile."""
    if valor >= 1_000_000:
        return f"{valor / 1_000_000:.1f}M"
    elif valor >= 1_000:
        return f"{valor / 1_000:.1f}k"
    else:
        return f"{valor:.0f}"


def render_calendar(ano: int, mes: int, dados: pd.DataFrame):
    dados_por_data: dict[date, dict] = {}
    if not dados.empty:
        dados = dados.copy()
        dados["data"] = pd.to_datetime(dados["data"]).dt.date
        for _, row in dados.iterrows():
            dados_por_data[row["data"]] = {
                "saidas": int(row["total_saidas"]),
                "faturamento": float(row["total_faturamento"]),
                "ticket": float(row["ticket_medio"]),
            }

    dias = get_dias_do_mes(ano, mes)
    offset = get_semana_do_primeiro_dia(ano, mes)

    html = _CSS
    html += '<div class="cal-wrapper"><div class="cal-table">'

    # Header
    for i, d in enumerate(DIAS_SEMANA):
        cls = " fds-h" if i in FDS_COLS else ""
        html += f'<div class="cal-header-cell{cls}">{d}</div>'

    # Células vazias antes do primeiro dia
    for _ in range(offset):
        html += '<div class="cal-day empty"></div>'

    # Dias do mês
    for info in dias:
        d = info["data"]
        feriado = info["feriado"]
        fds = info["fim_de_semana"]

        cls = "cal-day fer" if feriado else ("cal-day fds" if fds else "cal-day")

        m = dados_por_data.get(d, {})
        saidas = m.get("saidas", 0)
        fat = m.get("faturamento", 0)
        ticket = m.get("ticket", 0)

        # Badge de feriado
        badge = ""
        if feriado:
            tag = feriado[:6]
            badge = f'<span class="cal-badge">{tag}</span>'

        # Métricas
        if saidas > 0 or fat > 0:
            metricas = f"""
            <div class="cal-metrics">
                <div class="cal-metric-row">
                    <span>Saí</span>
                    <span class="cal-metric-val">{saidas}</span>
                </div>
                <div class="cal-metric-row">
                    <span>R$</span>
                    <span class="cal-metric-val money">{_fmt_curta(fat)}</span>
                </div>
                <div class="cal-metric-row">
                    <span>TM</span>
                    <span class="cal-metric-val">{_fmt_curta(ticket)}</span>
                </div>
            </div>"""
        else:
            metricas = '<div class="cal-no-data">—</div>'

        html += f"""
        <div class="{cls}">
            <div class="cal-num">{info['dia']}{badge}</div>
            {metricas}
        </div>"""

    # Células vazias após o último dia
    ultimo_ds = dias[-1]["dia_semana"]
    for _ in range(6 - ultimo_ds):
        html += '<div class="cal-day empty"></div>'

    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)
