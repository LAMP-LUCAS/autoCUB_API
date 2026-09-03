from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class StandardEtlResult(BaseModel):
    adapter_id: str
    source_identifier: str
    status: str  # 'SUCCESS', 'EMPTY', 'ERROR'
    records_count: int
    data: Any
    metadata: Dict[str, Any] = {}


class BaseEtlAdapter(ABC):
    """
    Interface base (Port) para adaptadores de ETL no AutoCUB.
    Garante que novos formatos de relatórios, documentações perenes ou
    fontes externas possam ser incorporados ou atualizados sem quebrar a API.
    """
    adapter_id: str
    version: str = "1.0"

    @abstractmethod
    def can_handle(self, source_type: str, source_reference: Any) -> bool:
        """Verifica se este adaptador é capaz de processar a fonte indicada."""
        pass

    @abstractmethod
    def extract(self, source_reference: Any, **kwargs) -> Any:
        """Extrai o conteúdo bruto da fonte de dados."""
        pass

    @abstractmethod
    def transform(self, raw_content: Any, **kwargs) -> StandardEtlResult:
        """Transforma o conteúdo bruto no modelo canônico do domínio."""
        pass
