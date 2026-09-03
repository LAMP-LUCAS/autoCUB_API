from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Index
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utc_now():
    return datetime.now(timezone.utc)


class Sinduscon(Base):
    __tablename__ = "sinduscons"

    id = Column(Integer, primary_key=True)
    uf = Column(String(2), nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    regiao = Column(String(20), nullable=False)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


    cotacoes = relationship("CubMensal", back_populates="sinduscon", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Sinduscon(id={self.id}, uf='{self.uf}', nome='{self.nome}')>"


class PadraoProjeto(Base):
    __tablename__ = "padroes_projeto"

    codigo = Column(String(10), primary_key=True)  # ex: 'R1-B', 'R1-N', 'R1-A', 'RP1Q'
    codigo_base = Column(String(10), nullable=False)  # ex: 'R-1', 'PP-4', 'GI'
    nome = Column(String(100), nullable=False)
    categoria = Column(String(30), nullable=False)  # 'RESIDENCIAL', 'COMERCIAL', 'ESPECIAL'
    padrao_acabamento = Column(String(10), nullable=False)  # 'BAIXO', 'NORMAL', 'ALTO', 'UNICO'
    pavimentos = Column(Integer, nullable=True)
    descricao = Column(Text, nullable=True)

    cotacoes = relationship("CubMensal", back_populates="padrao_projeto")

    def __repr__(self) -> str:
        return f"<PadraoProjeto(codigo='{self.codigo}', nome='{self.nome}')>"


class CubMensal(Base):
    __tablename__ = "cub_mensal"

    sinduscon_id = Column(Integer, ForeignKey("sinduscons.id", ondelete="CASCADE"), primary_key=True)
    data_referencia = Column(Date, primary_key=True)  # primeiro dia do mês (ex: 2026-01-01)
    codigo_padrao = Column(String(10), ForeignKey("padroes_projeto.codigo"), primary_key=True)
    desoneracao = Column(String(20), primary_key=True)  # 'SEM_DESONERACAO', 'COM_DESONERACAO'

    valor_m2 = Column(Numeric(12, 2), nullable=False)
    variacao_mensal_pct = Column(Numeric(6, 3), nullable=True)
    data_extracao = Column(DateTime, default=utc_now)

    sinduscon = relationship("Sinduscon", back_populates="cotacoes")
    padrao_projeto = relationship("PadraoProjeto", back_populates="cotacoes")

    __table_args__ = (
        Index("idx_cub_mensal_ref", "data_referencia"),
        Index("idx_cub_mensal_padrao", "codigo_padrao"),
        Index("idx_cub_mensal_sind_data", "sinduscon_id", "data_referencia"),
    )

    def __repr__(self) -> str:
        return (
            f"<CubMensal(sinduscon_id={self.sinduscon_id}, data={self.data_referencia}, "
            f"padrao='{self.codigo_padrao}', valor={self.valor_m2})>"
        )


class EtlExecucao(Base):
    __tablename__ = "etl_execucoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sinduscon_id = Column(Integer, ForeignKey("sinduscons.id", ondelete="SET NULL"), nullable=True)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    desoneracao = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)  # 'SUCESSO', 'FALHA', 'CACHE_LOCAL', 'EM_ANDAMENTO'
    registros_processados = Column(Integer, default=0)
    mensagem_erro = Column(Text, nullable=True)
    duracao_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now)


    def __repr__(self) -> str:
        return f"<EtlExecucao(id={self.id}, status='{self.status}', registros={self.registros_processados})>"
