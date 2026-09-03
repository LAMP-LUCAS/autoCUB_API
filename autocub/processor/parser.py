import re
import io
from datetime import date
from decimal import Decimal
from typing import Union, BinaryIO, Optional, List
import pdfplumber

from autocub.processor.schemas import CubRelatorioExtracted, CubItemExtracted
from autocub.core.logging import logger

MESES_MAP = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
    "abril": 4, "maio": 5, "junho": 6, "julho": 7,
    "agosto": 8, "setembro": 9, "outubro": 10,
    "novembro": 11, "dezembro": 12
}

TABLE_SPECS = {
    0: ("RESIDENCIAL", "BAIXO"),
    1: ("RESIDENCIAL", "NORMAL"),
    2: ("RESIDENCIAL", "ALTO"),
    3: ("COMERCIAL", "NORMAL"),
    4: ("COMERCIAL", "ALTO"),
    5: ("ESPECIAL", "UNICO")
}


def parse_cub_pdf(
    source: Union[str, BinaryIO, io.BytesIO],
    uf: Optional[str] = None,
    sinduscon_id: Optional[int] = None,
    desoneracao: str = "SEM_DESONERACAO",
    ano_fallback: Optional[int] = None,
    mes_fallback: Optional[int] = None
) -> CubRelatorioExtracted:
    """
    Extrai as tabelas de CUB/m² e metadados de um PDF gerado pelo cub.org.br.
    Identifica de forma determinística os 19 projetos da NBR 12.721:2006.
    """
    with pdfplumber.open(source) as pdf:
        if not pdf.pages:
            raise ValueError("O PDF fornecido não possui páginas.")

        page = pdf.pages[0]
        text = page.extract_text() or ""

        # 1. Extração de Metadados do Cabeçalho
        sinduscon_nome = None
        m_sind = re.search(r'(Sinduscon[A-Za-z0-9\s\-\_]+)', text, re.IGNORECASE)
        if m_sind:
            sinduscon_nome = m_sind.group(1).strip()

        # Extrai Mês e Ano
        ano = ano_fallback
        mes = mes_fallback
        mes_nome = None

        m_ref = re.search(
            r'(Janeiro|Fevereiro|Março|Marco|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro)/(\d{4})',
            text,
            re.IGNORECASE
        )
        if m_ref:
            mes_nome = m_ref.group(1).capitalize()
            mes = MESES_MAP.get(m_ref.group(1).lower(), mes_fallback or 1)
            ano = int(m_ref.group(2))

        if not ano or not mes:
            raise ValueError(f"Não foi possível identificar mês/ano de referência no PDF. Texto: {text[:200]}")

        data_ref = date(ano, mes, 1)

        # 2. Extração Determinística das Tabelas
        tables = page.extract_tables()
        if not tables or len(tables) < 6:
            logger.warning(
                f"Número inesperado de tabelas ({len(tables) if tables else 0}). "
                "Esperado pelo menos 6 blocos tabulares padrão CBIC."
            )

        extracted_items: List[CubItemExtracted] = []

        for idx, table in enumerate(tables):
            if idx not in TABLE_SPECS:
                continue

            categoria, padrao = TABLE_SPECS[idx]

            for row in table:
                if not row or not row[0]:
                    continue

                # Ignora cabeçalhos do tipo 'PADRÃO BAIXO', etc.
                cell_0 = str(row[0]).strip().upper()
                if "PADR" in cell_0 or "RESID" in cell_0 or "COMERC" in cell_0:
                    continue

                codigo_base = str(row[0]).strip()
                valor_raw = str(row[1]).strip() if len(row) > 1 and row[1] else "0"
                var_raw = str(row[2]).strip() if len(row) > 2 and row[2] else None

                # Conversão segura de valores monetários
                try:
                    valor_clean = valor_raw.replace(".", "").replace(",", ".")
                    valor_m2 = Decimal(valor_clean)
                except Exception:
                    logger.warning(f"Não foi possível converter valor '{valor_raw}' para Decimal.")
                    continue

                # Conversão de variação percentual
                variacao_pct = None
                if var_raw and var_raw != "-":
                    try:
                        var_clean = var_raw.replace("%", "").replace(".", "").replace(",", ".").strip()
                        variacao_pct = Decimal(var_clean)
                    except Exception:
                        variacao_pct = None

                # Formação do código canônico do projeto
                if padrao == "UNICO" or codigo_base in ["PIS", "RP1Q", "GI"]:
                    codigo_canonico = codigo_base
                else:
                    suf = padrao[0]  # 'B', 'N', 'A'
                    clean_base = codigo_base.replace("-", "") if codigo_base.startswith("R-") else codigo_base
                    codigo_canonico = f"{clean_base}-{suf}"

                extracted_items.append(
                    CubItemExtracted(
                        categoria=categoria,
                        padrao=padrao,
                        codigo_base=codigo_base,
                        codigo_canonico=codigo_canonico,
                        valor_m2=valor_m2,
                        variacao_pct=variacao_pct
                    )
                )

        return CubRelatorioExtracted(
            sinduscon_nome=sinduscon_nome,
            uf=uf,
            mes_nome=mes_nome,
            ano=ano,
            mes=mes,
            data_referencia=data_ref,
            desoneracao=desoneracao,
            itens=extracted_items
        )
