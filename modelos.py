"""Modelos imutáveis compartilhados pelas camadas do Editor RAW."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

__all__ = ["AjustesFoto", "AjustesMascara", "FotoProjeto"]


@dataclass(frozen=True)
class AjustesFoto:
    """Representa ajustes reversíveis aplicados a uma fotografia."""

    preset: str = "Natural equilibrado"
    exposicao: float = 0.0
    contraste: int = 6
    realces: int = -12
    sombras: int = 10
    saturacao: int = 6
    temperatura: int = 0
    reducao_ruido: int = 52
    nitidez: int = 38

    def copiar(self, **alteracoes: float | int | str) -> AjustesFoto:
        """Cria uma cópia com os campos informados alterados."""
        return replace(self, **alteracoes)


@dataclass(frozen=True)
class AjustesMascara:
    """Configura o efeito aplicado dentro ou fora de uma máscara."""

    efeito: str = "Destaque seletivo — fundo P&B"
    intensidade: int = 100
    suavizacao: int = 6


@dataclass(frozen=True)
class FotoProjeto:
    """Armazena metadados essenciais de uma foto carregada."""

    caminho: Path
    iso: int
