import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date


@st.cache_resource
def get_engine():
    url = st.secrets["DATABASE_URL"]
    return create_engine(url)


@st.cache_data(ttl=300)
def get_dados_diarios(data_inicio: date, data_fim: date, unidade: str = None) -> pd.DataFrame:
    engine = get_engine()

    filtro = "AND unidade = :unidade" if unidade else ""

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
        params["unidade"] = unidade

    with engine.connect() as conn:
        result = conn.execute(query, params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    return df


@st.cache_data(ttl=3600)
def get_unidades() -> list:
    engine = get_engine()
    query = text("SELECT DISTINCT unidade FROM saidas ORDER BY unidade")
    with engine.connect() as conn:
        result = conn.execute(query)
        unidades = [row[0] for row in result]
    return ["Todas"] + unidades


@st.cache_data(ttl=300)
def get_resumo_mes(ano: int, mes: int, unidade: str = None) -> dict:
    engine = get_engine()
    filtro = "AND unidade = :unidade" if unidade else ""

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
        params["unidade"] = unidade

    with engine.connect() as conn:
        total_saidas = conn.execute(query_saidas, params).scalar()
        total_fat = conn.execute(query_fat, params).scalar()

    ticket = float(total_fat) / float(total_saidas) if total_saidas > 0 else 0
    return {
        "total_saidas": int(total_saidas),
        "total_faturamento": float(total_fat),
        "ticket_medio": ticket,
    }
