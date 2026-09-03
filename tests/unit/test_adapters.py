import pytest
from pathlib import Path
from autocub.adapters.registry import AdapterRegistry
from autocub.adapters.booklet_adapter import CbicBookletAdapter
from autocub.adapters.monthly_pdf_adapter import CbicMonthlyPdfV1Adapter
from autocub.adapters.crawler_adapter import CbicCrawlerAdapter


@pytest.mark.unit
def test_adapter_registry_has_canonical_adapters():
    adapters = AdapterRegistry.list_adapters()
    assert "cbic_monthly_pdf_v1" in adapters
    assert "cbic_crawler_v1" in adapters
    assert "cbic_booklet_v1" in adapters


@pytest.mark.unit
def test_booklet_adapter_extracts_perennial_knowledge():
    adapter = AdapterRegistry.get_adapter("cbic_booklet_v1")
    assert isinstance(adapter, CbicBookletAdapter)

    extracted = adapter.extract(None)
    assert "lote_insumos" in extracted
    assert "itens_excluidos" in extracted
    assert "faq" in extracted
    assert "lei_4591" in extracted
    assert "fatores_area_equivalente" in extracted

    # Validação do lote básico (29 insumos)
    lote = extracted["lote_insumos"]
    assert lote["total_insumos"] == 29
    assert len(lote["insumos"]) == 29

    # Validação das famílias macro
    familias = lote["familias_macro_percentuais"]
    assert "materiais" in familias
    assert "mao_de_obra" in familias
    assert "despesas_administrativas" in familias
    assert "equipamentos" in familias

    # Validação de itens excluídos do CUB
    excluidos = extracted["itens_excluidos"]
    assert len(excluidos) >= 8

    # Validação da Lei 4.591
    lei = extracted["lei_4591"]
    assert "art_54" in lei["artigos"]


@pytest.mark.unit
def test_monthly_pdf_adapter_parses_real_pdf():
    adapter = AdapterRegistry.get_adapter("cbic_monthly_pdf_v1")
    assert isinstance(adapter, CbicMonthlyPdfV1Adapter)

    sample_pdf = Path("autocub_downloads/GO/10/cub_2026_01_sem_desoneracao.pdf")
    if sample_pdf.exists():
        res = adapter.transform(sample_pdf)
        assert res.status == "SUCCESS"
        assert res.records_count == 19
        assert len(res.data.itens) == 19
