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
    Usa 2 queries com CASE WHEN (em vez de 4 separadas) e date ranges sargables.
    """
    import calendar as _cal
    engine = get_engine()

    if mes == 1:
        ano_ant, mes_ant = ano - 1, 12
    else:
        ano_ant, mes_ant = ano, mes - 1

    ini_atual = date(ano,     mes,     1)
    fim_atual = date(ano,     mes,     dia_limite)
    ini_ant   = date(ano_ant, mes_ant, 1)
    fim_ant   = date(ano_ant, mes_ant, min(dia_limite, _cal.monthrange(ano_ant, mes_ant)[1]))

    if unidade:
        nomes_sistema = [k for k, v in MAPEAMENTO_UNIDADES.items() if v == unidade]
        nomes_sistema.append(unidade)
        nomes_sistema = list(set(nomes_sistema))
        placeholders = ", ".join(f":u{i}" for i in range(len(nomes_sistema)))
        filtro_uni = f"AND unidade IN ({placeholders})"
    else:
        filtro_uni = ""
        nomes_sistema = []

    params = {
        "ini_atual": ini_atual, "fim_atual": fim_atual,
        "ini_ant":   ini_ant,   "fim_ant":   fim_ant,
    }
    for i, nome in enumerate(nomes_sistema):
        params[f"u{i}"] = nome

    q_saidas = text(f"""
        SELECT
            COALESCE(SUM(CASE WHEN data BETWEEN :ini_atual AND :fim_atual THEN quantidade END), 0) AS s_atual,
            COALESCE(SUM(CASE WHEN data BETWEEN :ini_ant   AND :fim_ant   THEN quantidade END), 0) AS s_ant
        FROM saidas
        WHERE tipo = '1-Realizado'
          AND data BETWEEN :ini_ant AND :fim_atual
          {filtro_uni}
    """)

    q_fat = text(f"""
        SELECT
            COALESCE(SUM(CASE WHEN data BETWEEN :ini_atual AND :fim_atual THEN valor END), 0) AS f_atual,
            COALESCE(SUM(CASE WHEN data BETWEEN :ini_ant   AND :fim_ant   THEN valor END), 0) AS f_ant
        FROM faturamento
        WHERE tipo = '1-Realizado'
          AND data BETWEEN :ini_ant AND :fim_atual
          {filtro_uni}
    """)

    with engine.connect() as conn:
        row_s = conn.execute(q_saidas, params).fetchone()
        row_f = conn.execute(q_fat,    params).fetchone()

    s_atual, s_ant = int(row_s[0]), int(row_s[1])
    f_atual, f_ant = float(row_f[0]), float(row_f[1])

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
def get_dados_por_unidade(ano: int, mes: int, dia_limite: int) -> pd.DataFrame:
    """
    Retorna métricas agregadas por unidade para o mês selecionado,
    incluindo comparação com o mês anterior até o mesmo dia limite.
    """
    import calendar as _cal
    engine = get_engine()

    if mes == 1:
        ano_ant, mes_ant = ano - 1, 12
    else:
        ano_ant, mes_ant = ano, mes - 1

    ini_atual = date(ano,     mes,     1)
    fim_atual = date(ano,     mes,     dia_limite)
    ini_ant   = date(ano_ant, mes_ant, 1)
    fim_ant   = date(ano_ant, mes_ant, min(dia_limite, _cal.monthrange(ano_ant, mes_ant)[1]))

    query = text("""
        WITH saidas_atual AS (
            SELECT unidade, SUM(quantidade) AS saidas
            FROM saidas
            WHERE data BETWEEN :ini_atual AND :fim_atual
              AND tipo = '1-Realizado'
            GROUP BY unidade
        ),
        saidas_anterior AS (
            SELECT unidade, SUM(quantidade) AS saidas
            FROM saidas
            WHERE data BETWEEN :ini_ant AND :fim_ant
              AND tipo = '1-Realizado'
            GROUP BY unidade
        ),
        fat_atual AS (
            SELECT unidade, SUM(valor) AS faturamento
            FROM faturamento
            WHERE data BETWEEN :ini_atual AND :fim_atual
            GROUP BY unidade
        ),
        fat_anterior AS (
            SELECT unidade, SUM(valor) AS faturamento
            FROM faturamento
            WHERE data BETWEEN :ini_ant AND :fim_ant
            GROUP BY unidade
        )
        SELECT
            COALESCE(sa.unidade, sp.unidade, fa.unidade, fp.unidade) AS unidade,
            COALESCE(sa.saidas, 0)       AS saidas,
            COALESCE(sp.saidas, 0)       AS saidas_anterior,
            COALESCE(fa.faturamento, 0)  AS faturamento,
            COALESCE(fp.faturamento, 0)  AS faturamento_anterior
        FROM saidas_atual sa
        FULL OUTER JOIN saidas_anterior sp ON sa.unidade = sp.unidade
        FULL OUTER JOIN fat_atual       fa ON COALESCE(sa.unidade, sp.unidade) = fa.unidade
        FULL OUTER JOIN fat_anterior    fp ON COALESCE(sa.unidade, sp.unidade, fa.unidade) = fp.unidade
        WHERE COALESCE(sa.saidas, 0) > 0 OR COALESCE(fa.faturamento, 0) > 0
        ORDER BY COALESCE(sa.saidas, 0) DESC
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {
            "ini_atual": ini_atual, "fim_atual": fim_atual,
            "ini_ant":   ini_ant,   "fim_ant":   fim_ant,
        })
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    if df.empty:
        return df

    # Normalizar nomes e reagrupar duplicatas pós-mapeamento
    df["unidade"] = df["unidade"].replace(MAPEAMENTO_UNIDADES)
    df = df.groupby("unidade", as_index=False).agg({
        "saidas":             "sum",
        "saidas_anterior":    "sum",
        "faturamento":        "sum",
        "faturamento_anterior": "sum",
    })

    df["delta_saidas"]      = df["saidas"]      - df["saidas_anterior"]
    df["delta_faturamento"] = df["faturamento"]  - df["faturamento_anterior"]
    df["ticket_medio"]      = df.apply(
        lambda r: r["faturamento"] / r["saidas"] if r["saidas"] > 0 else 0,
        axis=1,
    )

    return df.sort_values("saidas", ascending=False).reset_index(drop=True)


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


@st.cache_data(ttl=3600)
def get_recordes_dia_semana(unidade: str = None) -> pd.DataFrame:
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

    query = text(f"""
        WITH daily AS (
            SELECT
                data,
                EXTRACT(YEAR  FROM data)::INT AS ano,
                EXTRACT(MONTH FROM data)::INT AS mes,
                EXTRACT(DOW   FROM data)::INT AS dia_semana,
                SUM(quantidade) AS total_saidas
            FROM saidas
            WHERE tipo = '1-Realizado'
              {filtro}
            GROUP BY data
        ),
        ranked AS (
            SELECT *,
                RANK() OVER (
                    PARTITION BY ano, mes, dia_semana
                    ORDER BY total_saidas DESC, data DESC
                ) AS rnk
            FROM daily
        )
        SELECT data, ano, mes, dia_semana, total_saidas
        FROM ranked
        WHERE rnk = 1
        ORDER BY ano DESC, mes DESC, dia_semana
    """)

    params = {}
    if unidade:
        for i, nome in enumerate(nomes_sistema):
            params[f"u{i}"] = nome

    with engine.connect() as conn:
        result = conn.execute(query, params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    if not df.empty:
        df["data"] = pd.to_datetime(df["data"]).dt.date
        df["ano"] = df["ano"].astype(int)
        df["mes"] = df["mes"].astype(int)
        df["dia_semana"] = df["dia_semana"].astype(int)
        df["total_saidas"] = df["total_saidas"].astype(int)

    return df


@st.cache_data(ttl=3600)
def get_totais_anuais(unidade: str = None) -> pd.DataFrame:
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

    query = text(f"""
        SELECT
            EXTRACT(YEAR  FROM data)::INT AS ano,
            EXTRACT(MONTH FROM data)::INT AS mes,
            SUM(quantidade) AS total_saidas
        FROM saidas
        WHERE tipo = '1-Realizado'
          {filtro}
        GROUP BY ano, mes
        ORDER BY ano, mes
    """)

    params = {}
    if unidade:
        for i, nome in enumerate(nomes_sistema):
            params[f"u{i}"] = nome

    with engine.connect() as conn:
        result = conn.execute(query, params)
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    if not df.empty:
        df["ano"] = df["ano"].astype(int)
        df["mes"] = df["mes"].astype(int)
        df["total_saidas"] = df["total_saidas"].astype(int)

    return df
