"""
Schemas Pydantic v2 para validação de saída do chatbot.

CKP01 exige: BaseModel com ≥4 campos tipados validando ao menos 1 saída.
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class AnaliseConsulta(BaseModel):
    """Schema para análise estruturada de uma consulta do consumidor."""

    categoria: Literal[
        "vício_produto",
        "vício_serviço",
        "prática_abusiva",
        "garantia",
        "arrependimento",
        "cobrança_indevida",
        "contrato",
        "fora_escopo",
    ] = Field(
        description="Categoria da consulta conforme classificação do CDC"
    )

    artigos_relevantes: list[str] = Field(
        description="Lista de artigos do CDC relevantes para o caso (ex: ['Art. 18', 'Art. 26'])",
        default_factory=list,
    )

    urgencia: Literal["baixa", "média", "alta"] = Field(
        description="Nível de urgência da situação relatada"
    )

    prazo_aplicavel: Optional[str] = Field(
        default=None,
        description="Prazo legal aplicável, se houver (ex: '7 dias - Art. 49')",
    )

    resumo_tecnico: str = Field(
        description="Resumo técnico-jurídico em até 300 caracteres",
        min_length=20,
        max_length=300,
    )

    @field_validator("artigos_relevantes")
    @classmethod
    def artigos_validos(cls, v: list[str]) -> list[str]:
        """Valida que cada artigo segue o formato 'Art. XX'."""
        for artigo in v:
            if not artigo.startswith("Art."):
                raise ValueError(f"Artigo '{artigo}' não segue o formato 'Art. XX'")
        return v

    @field_validator("resumo_tecnico")
    @classmethod
    def resumo_nao_vazio(cls, v: str) -> str:
        """Garante que o resumo é substantivo."""
        if len(v.strip()) < 20:
            raise ValueError("Resumo técnico muito curto — mínimo 20 caracteres")
        return v.strip()


class RelatorioSessao(BaseModel):
    """Schema para relatório de uma sessão de consultas."""

    total_consultas: int = Field(description="Número total de consultas na sessão", ge=0)
    categorias_identificadas: dict[str, int] = Field(
        description="Contagem de consultas por categoria",
        default_factory=dict,
    )
    artigos_mais_citados: list[str] = Field(
        description="Top 5 artigos mais referenciados na sessão",
        default_factory=list,
    )
    data_relatorio: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"),
        description="Data de geração do relatório",
    )
