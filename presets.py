"""Catálogo declarativo de presets do Editor RAW."""

from typing import Final

from modelos import AjustesFoto

__all__ = ["AJUSTES_PADRAO", "preset_recomendado"]


AJUSTES_PADRAO: Final[dict[str, AjustesFoto]] = {
    "Natural": AjustesFoto(preset="Natural"),
    "Retrato": AjustesFoto(
        preset="Retrato",
        contraste=2,
        realces=-18,
        sombras=14,
        saturacao=3,
        temperatura=5,
        reducao_ruido=60,
        nitidez=25,
    ),
    "Menos ruído": AjustesFoto(
        preset="Menos ruído",
        contraste=4,
        realces=-14,
        sombras=6,
        saturacao=2,
        reducao_ruido=82,
        nitidez=20,
    ),
    "Fotos noturnas": AjustesFoto(
        preset="Fotos noturnas",
        contraste=9,
        realces=-28,
        sombras=8,
        saturacao=7,
        temperatura=-3,
        reducao_ruido=75,
        nitidez=28,
    ),
    "Cores vivas": AjustesFoto(
        preset="Cores vivas",
        contraste=12,
        realces=-10,
        sombras=8,
        saturacao=18,
        temperatura=2,
        reducao_ruido=48,
        nitidez=45,
    ),
    "Preto e branco": AjustesFoto(
        preset="Preto e branco",
        contraste=18,
        realces=-20,
        sombras=5,
        saturacao=-100,
        reducao_ruido=65,
        nitidez=35,
    ),
    "Sem ajustes": AjustesFoto(
        preset="Sem ajustes",
        contraste=0,
        realces=0,
        sombras=0,
        saturacao=0,
        reducao_ruido=0,
        nitidez=0,
    ),
}


def preset_recomendado(iso: int) -> str:
    """Sugere um preset inicial a partir do ISO."""
    if iso >= 3200:
        return "Menos ruído"
    if iso >= 1600:
        return "Natural"
    return "Retrato"
