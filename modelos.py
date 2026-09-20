"""Modelos imutáveis compartilhados pelas camadas do Editor RAW."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image

__all__ = [
    "AjustesFoto",
    "AjustesMascara",
    "CamadaMascara",
    "FotoProjeto",
    "ItemExportacao",
]


@dataclass(frozen=True)
class AjustesFoto:
    """Representa ajustes reversíveis aplicados a uma fotografia."""

    preset: str = "Natural"
    exposicao: float = 0.0
    contraste: int = 6
    realces: int = -12
    sombras: int = 10
    saturacao: int = 6
    temperatura: int = 0
    reducao_ruido: int = 52
    nitidez: int = 38

    def copiar(
        self,
        *,
        preset: str | None = None,
        exposicao: float | None = None,
        contraste: int | None = None,
        realces: int | None = None,
        sombras: int | None = None,
        saturacao: int | None = None,
        temperatura: int | None = None,
        reducao_ruido: int | None = None,
        nitidez: int | None = None,
    ) -> AjustesFoto:
        """Cria uma cópia substituindo somente os campos informados."""
        return replace(
            self,
            preset=self.preset if preset is None else preset,
            exposicao=self.exposicao if exposicao is None else exposicao,
            contraste=self.contraste if contraste is None else contraste,
            realces=self.realces if realces is None else realces,
            sombras=self.sombras if sombras is None else sombras,
            saturacao=self.saturacao if saturacao is None else saturacao,
            temperatura=self.temperatura if temperatura is None else temperatura,
            reducao_ruido=(
                self.reducao_ruido if reducao_ruido is None else reducao_ruido
            ),
            nitidez=self.nitidez if nitidez is None else nitidez,
        )


@dataclass(frozen=True)
class AjustesMascara:
    """Configura o efeito aplicado dentro ou fora de uma máscara."""

    efeito: str = "Destaque seletivo — fundo P&B"
    intensidade: int = 100
    suavizacao: int = 6


@dataclass(frozen=True)
class CamadaMascara:
    """Agrupa nome, seleção e efeito de uma camada local."""

    nome: str
    mascara: Image.Image
    ajustes: AjustesMascara


@dataclass(frozen=True)
class FotoProjeto:
    """Armazena metadados essenciais de uma foto carregada."""

    caminho: Path
    iso: int


@dataclass(frozen=True)
class ItemExportacao:
    """Congela os dados usados por uma fotografia durante a exportação."""

    origem: Path
    ajustes: AjustesFoto
    iso: int
    camadas: tuple[CamadaMascara, ...]
