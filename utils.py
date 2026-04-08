from datetime import date
import calendar

FERIADOS_FIXOS = {
    (1, 1):   "Confraternização Universal",
    (4, 21):  "Tiradentes",
    (5, 1):   "Dia do Trabalho",
    (9, 7):   "Independência",
    (10, 12): "Nossa Senhora Aparecida",
    (11, 2):  "Finados",
    (11, 15): "Proclamação da República",
    (12, 25): "Natal",
}

FERIADOS_MOVEIS = {
    (2024, 2, 12): "Carnaval",
    (2024, 2, 13): "Carnaval",
    (2024, 3, 29): "Sexta-feira Santa",
    (2024, 5, 30): "Corpus Christi",
    (2025, 3, 3):  "Carnaval",
    (2025, 3, 4):  "Carnaval",
    (2025, 4, 18): "Sexta-feira Santa",
    (2025, 6, 19): "Corpus Christi",
    (2026, 2, 16): "Carnaval",
    (2026, 2, 17): "Carnaval",
    (2026, 4, 3):  "Sexta-feira Santa",
    (2026, 6, 4):  "Corpus Christi",
    (2027, 2, 8):  "Carnaval",
    (2027, 2, 9):  "Carnaval",
    (2027, 3, 26): "Sexta-feira Santa",
    (2027, 5, 27): "Corpus Christi",
    (2028, 2, 28): "Carnaval",
    (2028, 2, 29): "Carnaval",
    (2028, 4, 14): "Sexta-feira Santa",
    (2028, 6, 15): "Corpus Christi",
    (2029, 2, 12): "Carnaval",
    (2029, 2, 13): "Carnaval",
    (2029, 3, 30): "Sexta-feira Santa",
    (2029, 5, 31): "Corpus Christi",
    (2030, 3, 4):  "Carnaval",
    (2030, 3, 5):  "Carnaval",
    (2030, 4, 19): "Sexta-feira Santa",
    (2030, 6, 20): "Corpus Christi",
}


def get_feriado(data: date) -> str | None:
    chave_fixa = (data.month, data.day)
    if chave_fixa in FERIADOS_FIXOS:
        return FERIADOS_FIXOS[chave_fixa]
    chave_movel = (data.year, data.month, data.day)
    return FERIADOS_MOVEIS.get(chave_movel)


def is_fim_de_semana(data: date) -> bool:
    return data.weekday() >= 5


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def get_dias_do_mes(ano: int, mes: int) -> list[dict]:
    num_dias = calendar.monthrange(ano, mes)[1]
    dias = []
    for dia in range(1, num_dias + 1):
        data = date(ano, mes, dia)
        dias.append({
            "dia": dia,
            "data": data,
            "dia_semana": data.weekday(),
            "feriado": get_feriado(data),
            "fim_de_semana": is_fim_de_semana(data),
        })
    return dias


def get_semana_do_primeiro_dia(ano: int, mes: int) -> int:
    return date(ano, mes, 1).weekday()
