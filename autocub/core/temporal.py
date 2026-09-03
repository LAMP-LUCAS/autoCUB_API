from datetime import date, datetime
from typing import Tuple, Optional


def get_max_published_period(ref_date: Optional[date] = None) -> Tuple[int, int]:
    """
    Retorna o período mais recente (ano, mês) que pode conter cotações do CUB publicadas.
    Conforme o Art. 54 da Lei Federal 4.591/1964, o CUB de determinado mês é apurado
    e divulgado até o 5º dia útil do mês subsequente. Portanto, o mês corrente e
    meses futuros nunca possuem dados oficiais publicados.
    """
    current = ref_date or date.today()
    ano = current.year
    mes = current.month

    if mes == 1:
        # Em janeiro, o último CUB publicado é dezembro do ano anterior
        return ano - 1, 12
    else:
        return ano, mes - 1


def sanitize_etl_range(ano_inicio: int, ano_fim: int) -> Tuple[int, int, int]:
    """
    Valida e sanitiza os parâmetros de ano do pipeline ETL:
    1. Impede tentativas de coleta para anos futuros.
    2. Ajusta automaticamente o ano final para o ano corrente se informado acima dele.
    3. Retorna (ano_inicio_valido, ano_fim_valido, mes_limite_ano_fim).
    """
    max_ano, max_mes = get_max_published_period()

    if ano_inicio > max_ano:
        raise ValueError(
            f"O ano inicial informado ({ano_inicio}) está no futuro. "
            f"O período mais recente disponível para apuração do CUB é {max_mes:02d}/{max_ano}."
        )

    if ano_fim > max_ano:
        ano_fim = max_ano

    if ano_inicio > ano_fim:
        raise ValueError(f"O ano inicial ({ano_inicio}) não pode ser superior ao ano final ({ano_fim}).")

    return ano_inicio, ano_fim, max_mes
