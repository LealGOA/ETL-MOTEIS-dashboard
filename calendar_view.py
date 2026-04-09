import streamlit as st
import pandas as pd
from datetime import date
from utils import get_dias_do_mes, get_semana_do_primeiro_dia, formatar_moeda, formatar_numero

DIAS_SEMANA_CURTO = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
DIAS_SEMANA_LETRA = ["S", "T", "Q", "Q", "S", "S", "D"]

_CSS = """
<style>
/* ── Calendário desktop: grid 7 colunas ── */
.cal-wrap { width: 100%; }

.cal-header {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
    margin-bottom: 4px;
}
.cal-header-cell {
    text-align: center;
    font-weight: 700;
    font-size: 11px;
    color: #999;
    padding: 4px 0;
    text-transform: uppercase;
    letter-spacing: .5px;
}

.cal-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 3px;
}

.cal-day {
    border: 1px solid #e8e8e8;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 90px;
    background: #fff;
    position: relative;
}
.cal-day.empty { background: transparent; border: none; min-height: 0; }
.cal-day.fds   { background: #f0faf1; }
.cal-day.fer   { background: #fff8ee; border-color: #ffc46b; }

.cal-num {
    font-weight: 800;
    font-size: 16px;
    line-height: 1;
    color: #222;
    margin-bottom: 6px;
}
.cal-num-today {
    background: #1a1a2e;
    color: #fff;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
}
.cal-badge {
    display: block;
    font-size: 8px;
    background: #ff9800;
    color: #fff;
    padding: 1px 4px;
    border-radius: 3px;
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
}
.cal-metric { font-size: 10px; color: #888; margin: 1px 0; line-height: 1.5; }
.cal-val    { font-weight: 700; color: #222; }
.cal-money  { font-weight: 700; color: #1b7a34; }
.cal-sem-dados { font-size: 10px; color: #ddd; margin-top: 4px; }

/* ── Mobile: lista vertical por semana ── */
@media (max-width: 640px) {
    .cal-header { display: none; }

    .cal-grid {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    /* Cada "linha" de semana vira um card horizontal */
    .cal-semana {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 2px;
        background: #f5f5f5;
        border-radius: 8px;
        padding: 4px;
    }

    .cal-day {
        min-height: 64px;
        padding: 4px 3px;
        border-radius: 4px;
        font-size: 10px;
    }

    .cal-num { font-size: 13px; margin-bottom: 3px; }
    .cal-num-today { width: 20px; height: 20px; font-size: 11px; }
    .cal-metric { font-size: 9px; }
    .cal-badge { font-size: 7px; }

    /* Label do dia da semana acima do número */
    .cal-dia-label {
        font-size: 8px;
        color: #bbb;
        font-weight: 600;
        margin-bottom: 2px;
        text-transform: uppercase;
    }
}

@media (min-width: 641px) {
    .cal-semana { display: contents; }
    .cal-dia-label { display: none; }
}
</style>
"""


def render_calendar(ano: int, mes: int, dados: pd.DataFrame):
    hoje = date.today()

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

    # Monta lista de células: None para células vazias, dict para dias reais
    celulas = [None] * offset + dias
    # Completa até múltiplo de 7
    while len(celulas) % 7 != 0:
        celulas.append(None)

    html = _CSS + '<div class="cal-wrap">'

    # Cabeçalho (só aparece em desktop)
    html += '<div class="cal-header">'
    for d in DIAS_SEMANA_CURTO:
        html += f'<div class="cal-header-cell">{d}</div>'
    html += "</div>"

    # Grid com semanas agrupadas
    html += '<div class="cal-grid">'

    semanas = [celulas[i:i+7] for i in range(0, len(celulas), 7)]
    for semana in semanas:
        html += '<div class="cal-semana">'
        for idx, info in enumerate(semana):
            if info is None:
                html += '<div class="cal-day empty"></div>'
                continue

            d = info["data"]
            feriado = info["feriado"]
            fds = info["fim_de_semana"]
            eh_hoje = (d == hoje)

            cls = "cal-day fer" if feriado else ("cal-day fds" if fds else "cal-day")

            m = dados_por_data.get(d, {})
            saidas = m.get("saidas", 0)
            fat = m.get("faturamento", 0)
            ticket = m.get("ticket", 0)

            # Número do dia
            if eh_hoje:
                num_html = f'<div class="cal-num"><span class="cal-num-today">{info["dia"]}</span></div>'
            else:
                num_html = f'<div class="cal-num">{info["dia"]}</div>'

            # Label do dia (só aparece no mobile)
            label_html = f'<div class="cal-dia-label">{DIAS_SEMANA_LETRA[idx]}</div>'

            # Badge feriado
            badge = ""
            if feriado:
                nome = feriado[:10] + "…" if len(feriado) > 10 else feriado
                badge = f'<span class="cal-badge">{nome}</span>'

            # Métricas
            if saidas > 0 or fat > 0:
                metricas = (
                    f'<div class="cal-metric">Saídas <span class="cal-val">{formatar_numero(saidas)}</span></div>'
                    f'<div class="cal-metric">Fat. <span class="cal-money">{formatar_moeda(fat)}</span></div>'
                    f'<div class="cal-metric">Tkt <span class="cal-val">{formatar_moeda(ticket)}</span></div>'
                )
            else:
                metricas = '<div class="cal-sem-dados">–</div>'

            html += f"""
            <div class="{cls}">
                {label_html}
                {num_html}
                {badge}
                {metricas}
            </div>"""

        html += '</div>'  # fecha cal-semana

    html += "</div></div>"  # fecha cal-grid e cal-wrap
    st.markdown(html, unsafe_allow_html=True)
