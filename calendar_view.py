import streamlit as st
import pandas as pd
from datetime import date
from utils import get_dias_do_mes, get_semana_do_primeiro_dia, formatar_moeda, formatar_numero

DIAS_SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]

_CSS = """
<style>
.cal-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
    margin-bottom: 6px;
}
.cal-header-cell {
    text-align: center;
    font-weight: 600;
    font-size: 12px;
    color: #888;
    padding: 6px 0;
}
.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 4px;
}
.cal-day {
    border: 1px solid #e8e8e8;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 105px;
    background: #fff;
}
.cal-day.empty  { background: transparent; border: none; }
.cal-day.fds    { background: #e8f5e9; }
.cal-day.fer    { background: #fff3e0; border-color: #ffcc80; }
.cal-num {
    font-weight: 700;
    font-size: 15px;
    line-height: 1;
    margin-bottom: 5px;
    display: flex;
    align-items: center;
    gap: 5px;
}
.cal-badge {
    font-size: 9px;
    background: #ff9800;
    color: #fff;
    padding: 2px 5px;
    border-radius: 4px;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 80px;
}
.cal-metric { font-size: 11px; color: #777; margin: 2px 0; line-height: 1.4; }
.cal-val    { font-weight: 600; color: #333; }
.cal-money  { font-weight: 600; color: #2e7d32; }
.cal-empty-label { font-size: 11px; color: #ccc; margin-top: 6px; }
</style>
"""


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

    # Cabeçalho
    html += '<div class="cal-header">'
    for d in DIAS_SEMANA:
        html += f'<div class="cal-header-cell">{d}</div>'
    html += "</div>"

    # Grid
    html += '<div class="cal-grid">'

    for _ in range(offset):
        html += '<div class="cal-day empty"></div>'

    for info in dias:
        d = info["data"]
        feriado = info["feriado"]
        fds = info["fim_de_semana"]
        cls = "cal-day fer" if feriado else ("cal-day fds" if fds else "cal-day")

        m = dados_por_data.get(d, {})
        saidas = m.get("saidas", 0)
        fat = m.get("faturamento", 0)
        ticket = m.get("ticket", 0)

        badge = ""
        if feriado:
            nome = feriado[:12] + "…" if len(feriado) > 12 else feriado
            badge = f'<span class="cal-badge">{nome}</span>'

        if saidas > 0 or fat > 0:
            metricas = (
                f'<div class="cal-metric">Saídas <span class="cal-val">{formatar_numero(saidas)}</span></div>'
                f'<div class="cal-metric">Fat. <span class="cal-money">{formatar_moeda(fat)}</span></div>'
                f'<div class="cal-metric">Ticket <span class="cal-val">{formatar_moeda(ticket)}</span></div>'
            )
        else:
            metricas = '<div class="cal-empty-label">Sem dados</div>'

        html += f"""
        <div class="{cls}">
            <div class="cal-num">{info['dia']}{badge}</div>
            {metricas}
        </div>"""

    # Preenche última linha
    ultimo_fds = dias[-1]["dia_semana"]
    for _ in range(6 - ultimo_fds):
        html += '<div class="cal-day empty"></div>'

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)
