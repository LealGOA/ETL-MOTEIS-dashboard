import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date

MAPEAMENTO_UNIDADES = {
    "ABOSLUTO":          "ABSOLUTO",
    "CANCUN MOTEL":      "CANCUM",
    "INSTINTO MOTEL":    "INSTINTO",
    "MOTEL ANONIMATO":   "ANONIMATO",
    "MOTEL BLUE STAR":   "BLUE STAR",
    "MOTEL BRAS CUBAS":  "BRAZ CUBAS",
    "MOTEL DIAMOND":     "CALIFORNIA",
    "MOTEL CALIFORNIA":  "CALIFORNIA",
    "MOTEL DOLCE":       "DOLCE",
    "MOTEL INFINITUS":   "INFINITUS",
    "MOTEL JD SECRETO":  "JARDIM SECRETO",
    "MOTEL LAREIRA":     "LAREIRA",
    "MOTEL PARIS":       "PARIS",
    "MOTEL RIVIERA":     "RIVIERA",
    "XANADU SP":         "XANADU",
    "MOTEL QUEEN":       "QUEEN",
    "MOTEL HOBBY":       "HOBBY",
    "0":                 "ZERO",
}


@st.cache_resource
def get_engine():
    url = st.secrets["DATABASE_URL"]
    return create_engine(url, connect_args={"sslmode": "require"})


@st.cache_data(ttl=300)
def get_dados_diarios(data_inicio: date, data_fim: date, unidade: str = None) -> pd.DataFrame:
    engine = get_engine()

    # Descobre todos os nomes do sistema que mapeiam para o nome interno selecionado
    if unidade:
        nomes_sistema = [k for k, v in MAPEAMENTO_UNIDADES.items() if v == unidade]
        nomes_sistema.append(unidade)  # inclui o próprio nome caso já esteja no banco
        nomes_sistema = list(set(nomes_sistema))
        placeholders = ", ".join(f":u{i}" for i in range(len(nomes_sistema)))
        filtro = f"AND unidade IN ({placeholders})"
    else:
        filtro = ""
        nomes_sistema = []

    query = text(f"""
        WITH saidas_dia AS (
            SELECT data, unidade, SUM(quantidade) AS total_saidas
            FROM saidas
            WHERE data BETWEEN :data_inicio AND :data_fim
            {filtro}
            GROUP BY data, unidade
        ),
        faturamento_dia AS (
            SELECT data, unidade, SUM(valor) AS total_faturamento
            FROM faturamento
            WHERE data BETWEEN :data_inicio AND :data_fim
            {filtro}
            GROUP BY data, unidade
        )
        SELECT
            COALESCE(s.data, f.data)         AS data,
            COALESCE(s.unidade, f.unidade)   AS unidade,
            COALESCE(s.total_saidas, 0)      AS total_saidas,
            COALESCE(f.total_faturamento, 0) AS total_faturamento,
            CASE
                WHEN COALESCE(s.total_saidas, 0) > 0
                THEN ROUND(COALESCE(f.total_faturamento, 0) / s.total_saidas, 2)
                ELSE 0
            END AS ticket_medio
        FROM saidas_dia s
        FULL OUTER JOIN faturamento_dia f ON s.data = f.data AND s.unidade = f.unidade
        ORDER BY data
    """)

    params = {"data_inicio": data_inicio, "data_fim": data_fim}
    if unidade:
        for i, nome in enumerate(nomes_sistema):
            params[f"u{i}"] = nome

    with engine.connect() as conn:
        result = conn.execute(query, params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    df["unidade"] = df["unidade"].replace(MAPEAMENTO_UNIDADES)
    return df


@st.cache_data(ttl=3600)
def get_unidades() -> list:
    engine = get_engine()
    query = text("SELECT DISTINCT unidade FROM saidas ORDER BY unidade")
    with engine.connect() as conn:
        result = conn.execute(query)
        unidades = [row[0] for row in result]
    unidades = sorted(set(MAPEAMENTO_UNIDADES.get(u, u) for u in unidades))
    return ["Todas"] + unidades


@st.cache_data(ttl=300)
def get_comparativo_mes(ano: int, mes: int, dia_limite: int, unidade: str = None) -> dict:
    """
    Retorna acumulados do mês selecionado (até dia_limite) e do mês anterior
    (até o mesmo dia), além dos deltas percentuais.
    Filtra tipo = '1-Realizado' para ignorar valores orçados.
    """
    engine = get_engine()

    if mes == 1:
        ano_ant, mes_ant = ano - 1, 12
    else:
        ano_ant, mes_ant = ano, mes - 1

    if unidade:
        nomes_sistema = [k for k, v in MAPEAMENTO_UNIDADES.items() if v == unidade]
        nomes_sistema.append(unidade)
        nomes_sistema = list(set(nomes_sistema))
        placeholders = ", ".join(f":u{i}" for i in range(len(nomes_sistema)))
        filtro_uni = f"AND unidade IN ({placeholders})"
    else:
        filtro_uni = ""
        nomes_sistema = []

    def build_params(a, m):
        p = {"ano": a, "mes": m, "dia": dia_limite}
        for i, nome in enumerate(nomes_sistema):
            p[f"u{i}"] = nome
        return p

    q_saidas = text(f"""
        SELECT COALESCE(SUM(quantidade), 0)
        FROM saidas
        WHERE EXTRACT(YEAR FROM data) = :ano
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(DAY FROM data) <= :dia
          AND tipo = '1-Realizado'
          {filtro_uni}
    """)

    q_fat = text(f"""
        SELECT COALESCE(SUM(valor), 0)
        FROM faturamento
        WHERE EXTRACT(YEAR FROM data) = :ano
          AND EXTRACT(MONTH FROM data) = :mes
          AND EXTRACT(DAY FROM data) <= :dia
          AND tipo = '1-Realizado'
          {filtro_uni}
    """)

    with engine.connect() as conn:
        s_atual = int(conn.execute(q_saidas, build_params(ano, mes)).scalar())
        f_atual = float(conn.execute(q_fat,    build_params(ano, mes)).scalar())
        s_ant   = int(conn.execute(q_saidas, build_params(ano_ant, mes_ant)).scalar())
        f_ant   = float(conn.execute(q_fat,    build_params(ano_ant, mes_ant)).scalar())

    t_atual = f_atual / s_atual if s_atual > 0 else 0.0
    t_ant   = f_ant   / s_ant   if s_ant   > 0 else 0.0

    def pct(a, b):
        return ((a - b) / b * 100) if b != 0 else None

    return {
        "atual":    {"saidas": s_atual, "faturamento": f_atual, "ticket": t_atual},
        "anterior": {"saidas": s_ant,   "faturamento": f_ant,   "ticket": t_ant},
        "delta_pct": {
            "saidas":      pct(s_atual, s_ant),
            "faturamento": pct(f_atual, f_ant),
            "ticket":      pct(t_atual, t_ant),
        },
    }


@st.cache_data(ttl=300)
def get_resumo_mes(ano: int, mes: int, unidade: str = None) -> dict:
    engine = get_engine()
    if unidade:
        nomes_sistema = [k for k, v in MAPEAMENTO_UNIDADES.items() if v == unidade]
        nomes_sistema.append(unidade)
        nomes_sistema = list(set(nomes_sistema))
        placeholders = ", ".join(f":u{i}" for i in range(len(nomes_sistema)))
        filtro = f"AND unidade IN ({placeholders})"
    else:
        filtro = ""
        nomes_sistema = []

    query_saidas = text(f"""
        SELECT COALESCE(SUM(quantidade), 0)
        FROM saidas
        WHERE EXTRACT(YEAR FROM data) = :ano
          AND EXTRACT(MONTH FROM data) = :mes
        {filtro}
    """)
    query_fat = text(f"""
        SELECT COALESCE(SUM(valor), 0)
        FROM faturamento
        WHERE EXTRACT(YEAR FROM data) = :ano
          AND EXTRACT(MONTH FROM data) = :mes
        {filtro}
    """)

    params = {"ano": ano, "mes": mes}
    if unidade:
        for i, nome in enumerate(nomes_sistema):
            params[f"u{i}"] = nome

    with engine.connect() as conn:
        total_saidas = conn.execute(query_saidas, params).scalar()
        total_fat = conn.execute(query_fat, params).scalar()

    ticket = float(total_fat) / float(total_saidas) if total_saidas > 0 else 0
    return {
        "total_saidas": int(total_saidas),
        "total_faturamento": float(total_fat),
        "ticket_medio": ticket,
    }
