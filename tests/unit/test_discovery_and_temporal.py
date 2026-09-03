from datetime import date
import pytest
from autocub.core.temporal import get_max_published_period, sanitize_etl_range
from autocub.downloader.discovery import cbic_discovery


@pytest.mark.unit
def test_get_max_published_period_normal_month():
    ref = date(2026, 9, 3)
    ano, mes = get_max_published_period(ref)
    assert ano == 2026
    assert mes == 8  # Setembro só tem dados de Agosto


@pytest.mark.unit
def test_get_max_published_period_january():
    ref = date(2026, 1, 15)
    ano, mes = get_max_published_period(ref)
    assert ano == 2025
    assert mes == 12  # Janeiro só tem dados de Dezembro do ano anterior


@pytest.mark.unit
def test_sanitize_etl_range_rejects_future():
    with pytest.raises(ValueError) as exc:
        sanitize_etl_range(2030, 2030)
    assert "futuro" in str(exc.value).lower()


@pytest.mark.unit
def test_sanitize_etl_range_rejects_inverted():
    with pytest.raises(ValueError) as exc:
        sanitize_etl_range(2025, 2024)
    assert "superior" in str(exc.value).lower()


@pytest.mark.unit
def test_discovery_service_identifies_unsupported_sp():
    is_sup = cbic_discovery.is_uf_supported("SP")
    assert is_sup is False


@pytest.mark.unit
def test_discovery_service_identifies_supported_go():
    is_sup = cbic_discovery.is_uf_supported("GO")
    assert is_sup is True
    ids = cbic_discovery.get_active_sinduscon_ids("GO")
    assert 10 in ids


@pytest.mark.unit
def test_discovery_service_auto_resolves_rj_id():
    # RJ tem apenas o ID 20 na CBIC
    resolved = cbic_discovery.validate_or_resolve_sinduscon_id("RJ", requested_id=3)
    assert resolved == 20
