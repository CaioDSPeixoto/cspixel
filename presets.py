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
    "Retrato suave": AjustesFoto(
        preset="Retrato suave",
        contraste=-4,
        realces=-24,
        sombras=18,
        saturacao=2,
        temperatura=6,
        reducao_ruido=68,
        nitidez=18,
    ),
    "Clarear foto escura": AjustesFoto(
        preset="Clarear foto escura",
        exposicao=0.35,
        brilho=8,
        contraste=3,
        realces=-35,
        sombras=28,
        saturacao=5,
        temperatura=2,
        reducao_ruido=70,
        nitidez=25,
    ),
    "Recuperar áreas claras": AjustesFoto(
        preset="Recuperar áreas claras",
        exposicao=-0.2,
        brilho=-5,
        contraste=2,
        realces=-70,
        sombras=20,
        saturacao=3,
        reducao_ruido=55,
        nitidez=32,
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
    "Redução forte de ruído": AjustesFoto(
        preset="Redução forte de ruído",
        contraste=3,
        realces=-18,
        sombras=8,
        reducao_ruido=96,
        nitidez=12,
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
    "Cores vivas + menos ruído": AjustesFoto(
        preset="Cores vivas + menos ruído",
        contraste=10,
        realces=-18,
        sombras=8,
        saturacao=16,
        temperatura=2,
        reducao_ruido=82,
        nitidez=25,
    ),
    "Cores vivas + redução forte": AjustesFoto(
        preset="Cores vivas + redução forte",
        contraste=8,
        realces=-24,
        sombras=8,
        saturacao=14,
        temperatura=2,
        reducao_ruido=96,
        nitidez=12,
    ),
    "Personagem em destaque": AjustesFoto(
        preset="Personagem em destaque",
        contraste=15,
        realces=-22,
        sombras=8,
        saturacao=22,
        temperatura=3,
        reducao_ruido=60,
        nitidez=42,
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
    "Preto e branco forte": AjustesFoto(
        preset="Preto e branco forte",
        contraste=28,
        realces=-35,
        sombras=2,
        saturacao=-100,
        reducao_ruido=68,
        nitidez=32,
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
    if iso >= 6400:
        return "Redução forte de ruído"
    if iso >= 3200:
        return "Menos ruído"
    if iso >= 1600:
        return "Natural"
    return "Retrato"
