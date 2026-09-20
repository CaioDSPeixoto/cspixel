"""Nomes estáveis dos efeitos locais disponíveis."""

from typing import Final

__all__ = [
    "EFEITO_DESFOCAR_FUNDO",
    "EFEITO_DESTAQUE_SUAVE",
    "EFEITO_DESTAQUE_SELETIVO",
    "EFEITO_NENHUM",
    "EFEITO_PB_SELECAO",
    "EFEITO_SATURAR_SELECAO",
    "EFEITOS_MASCARA",
]

EFEITO_NENHUM: Final = "Nenhum"
EFEITO_DESTAQUE_SELETIVO: Final = "Destaque seletivo — fundo P&B"
EFEITO_DESTAQUE_SUAVE: Final = "Destaque — fundo P&B e suave"
EFEITO_PB_SELECAO: Final = "Preto e branco somente na seleção"
EFEITO_SATURAR_SELECAO: Final = "Aumentar saturação da seleção"
EFEITO_DESFOCAR_FUNDO: Final = "Desfocar o fundo"

EFEITOS_MASCARA: Final[tuple[str, ...]] = (
    EFEITO_DESTAQUE_SELETIVO,
    EFEITO_DESTAQUE_SUAVE,
    EFEITO_PB_SELECAO,
    EFEITO_SATURAR_SELECAO,
    EFEITO_DESFOCAR_FUNDO,
    EFEITO_NENHUM,
)
