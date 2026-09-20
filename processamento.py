"""Núcleo de revelação e edição não destrutiva de fotografias RAW."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal, TypeAlias

import numpy as np
from PIL import ExifTags, Image, ImageCms, ImageEnhance, ImageFilter
import rawpy

from efeitos import (
    EFEITO_DESFOCAR_FUNDO,
    EFEITO_DESTAQUE_SELETIVO,
    EFEITO_DESTAQUE_SUAVE,
    EFEITO_NENHUM,
    EFEITO_PB_SELECAO,
    EFEITO_SATURAR_SELECAO,
)
from modelos import AjustesFoto, AjustesMascara, CamadaMascara

__all__ = [
    "EXTENSOES_SUPORTADAS",
    "FormatoExportacao",
    "QUALIDADE_JPEG",
    "aplicar_ajustes",
    "aplicar_edicao_completa",
    "aplicar_mascara_local",
    "criar_preview",
    "exportar_foto",
    "faixa_iso",
    "nome_destino_seguro",
    "obter_iso",
    "revelar_raw",
]


FormatoExportacao: TypeAlias = Literal["JPEG", "PNG"]
EXTENSOES_SUPORTADAS: Final[tuple[str, ...]] = (
    ".cr2",
    ".cr3",
    ".nef",
    ".arw",
    ".dng",
    ".orf",
    ".rw2",
    ".raf",
)
QUALIDADE_JPEG: Final = 100
PERFIL_SRGB: Final[bytes] = ImageCms.ImageCmsProfile(
    ImageCms.createProfile("sRGB"),
).tobytes()
TAG_EXIF: Final[dict[str, int]] = {
    nome: codigo for codigo, nome in ExifTags.TAGS.items()
}


def obter_iso(caminho: Path) -> int:
    """Lê o ISO do EXIF e retorna um valor seguro quando indisponível."""
    try:
        with Image.open(caminho) as imagem:
            exif_principal = imagem.getexif()
            exif_foto = exif_principal.get_ifd(34665)
            valor = exif_foto.get(TAG_EXIF["ISOSpeedRatings"], 0)
        if isinstance(valor, tuple):
            valor = valor[0]
        return max(0, int(valor))
    except (KeyError, OSError, TypeError, ValueError):
        return 0


def faixa_iso(iso: int) -> str:
    """Classifica o ISO em uma faixa útil para edição."""
    if iso <= 0:
        return "ISO não identificado"
    if iso <= 800:
        return "ISO baixo (até 800)"
    if iso <= 1600:
        return "ISO médio (801–1600)"
    if iso <= 3200:
        return "ISO alto (1601–3200)"
    return "ISO muito alto (acima de 3200)"


def revelar_raw(caminho: Path, iso: int, preview: bool) -> Image.Image:
    """Revela um RAW em sRGB, usando meia resolução no preview."""
    reducao = (
        rawpy.FBDDNoiseReductionMode.Full
        if iso >= 1600
        else rawpy.FBDDNoiseReductionMode.Light
    )
    passagens_mediana = 2 if iso >= 3200 else 1
    with rawpy.imread(str(caminho)) as raw:
        dados = raw.postprocess(
            use_camera_wb=True,
            output_color=rawpy.ColorSpace.sRGB,
            output_bps=8,
            bright=0.98,
            no_auto_bright=False,
            highlight_mode=rawpy.HighlightMode.Blend,
            fbdd_noise_reduction=reducao,
            median_filter_passes=passagens_mediana,
            half_size=preview,
        )
    return Image.fromarray(dados, mode="RGB")


def _aplicar_exposicao(matriz: np.ndarray, valor: float) -> np.ndarray:
    """Aplica compensação de exposição em pontos de luz."""
    return matriz * (2.0**valor)


def _aplicar_temperatura(matriz: np.ndarray, valor: int) -> np.ndarray:
    """Aquece ou esfria o balanço de cor."""
    intensidade = valor / 100.0
    resultado = matriz.copy()
    resultado[:, :, 0] *= 1.0 + 0.16 * intensidade
    resultado[:, :, 2] *= 1.0 - 0.16 * intensidade
    return resultado


def _aplicar_tons(
    matriz: np.ndarray,
    contraste: int,
    realces: int,
    sombras: int,
) -> np.ndarray:
    """Ajusta contraste, realces e sombras em espaço normalizado."""
    normalizada = np.clip(matriz / 255.0, 0.0, 1.0)
    fator_sombras = sombras / 100.0
    fator_realces = realces / 100.0
    normalizada += fator_sombras * 0.32 * (1.0 - normalizada) ** 2
    normalizada += fator_realces * 0.26 * normalizada**2
    fator_contraste = 1.0 + contraste / 100.0
    normalizada = (normalizada - 0.5) * fator_contraste + 0.5
    return np.clip(normalizada * 255.0, 0.0, 255.0)


def _reduzir_pixels_quentes(imagem: Image.Image) -> Image.Image:
    """Remove pontos vermelhos e azuis isolados nas sombras."""
    matriz = np.asarray(imagem, dtype=np.float32)
    mediana = np.asarray(
        imagem.filter(ImageFilter.MedianFilter(size=3)),
        dtype=np.float32,
    )
    luminancia = (
        0.2126 * matriz[:, :, 0] + 0.7152 * matriz[:, :, 1] + 0.0722 * matriz[:, :, 2]
    )
    diferenca = np.max(np.abs(matriz - mediana), axis=2)
    cor_isolada = (matriz[:, :, 0] > mediana[:, :, 0] + 24) | (
        matriz[:, :, 2] > mediana[:, :, 2] + 24
    )
    mascara = (luminancia < 125) & (diferenca > 27) & cor_isolada
    matriz[mascara] = mediana[mascara]
    return Image.fromarray(np.clip(matriz, 0, 255).astype(np.uint8), mode="RGB")


def _reduzir_ruido(
    imagem: Image.Image,
    iso: int,
    intensidade: int,
) -> Image.Image:
    """Reduz ruído preservando bordas e detalhes relevantes."""
    if intensidade <= 0:
        return imagem
    escala = intensidade / 100.0
    raio_cor = 0.7 + 3.4 * escala + min(iso / 6400.0, 1.0) * 0.6
    luminancia, azul, vermelho = imagem.convert("YCbCr").split()
    azul = azul.filter(ImageFilter.GaussianBlur(radius=raio_cor))
    vermelho = vermelho.filter(ImageFilter.GaussianBlur(radius=raio_cor))

    matriz_luminancia = np.asarray(luminancia, dtype=np.float32)
    mediana = np.asarray(
        luminancia.filter(ImageFilter.MedianFilter(size=3)),
        dtype=np.float32,
    )
    raio_luminancia = 0.45 + 0.7 * escala
    suave = np.asarray(
        luminancia.filter(ImageFilter.GaussianBlur(radius=raio_luminancia)),
        dtype=np.float32,
    )
    alvo = mediana * 0.70 + suave * 0.30
    peso_sombra = np.clip((180 - matriz_luminancia) / 130, 0.20, 1.0)
    estrutura = np.asarray(
        luminancia.filter(ImageFilter.GaussianBlur(radius=1.6)),
        dtype=np.float32,
    )
    gradiente_x = np.abs(np.diff(estrutura, axis=1, prepend=estrutura[:, :1]))
    gradiente_y = np.abs(np.diff(estrutura, axis=0, prepend=estrutura[:1, :]))
    preservacao = np.clip(
        1.0 - np.maximum(gradiente_x, gradiente_y) / 34.0,
        0.28,
        1.0,
    )
    peso_iso = 0.72 + min(iso / 6400.0, 1.0) * 0.28
    peso = escala * peso_iso * (0.46 + 0.54 * peso_sombra) * preservacao
    tratada = matriz_luminancia * (1.0 - peso) + alvo * peso
    canal_luminancia = Image.fromarray(
        np.clip(tratada, 0, 255).astype(np.uint8),
        mode="L",
    )
    return Image.merge(
        "YCbCr",
        (canal_luminancia, azul, vermelho),
    ).convert("RGB")


def aplicar_ajustes(
    imagem: Image.Image,
    ajustes: AjustesFoto,
    iso: int,
) -> Image.Image:
    """Aplica os ajustes informados sem modificar a imagem de origem."""
    sem_alteracoes = (
        ajustes.exposicao == 0
        and ajustes.contraste == 0
        and ajustes.realces == 0
        and ajustes.sombras == 0
        and ajustes.saturacao == 0
        and ajustes.temperatura == 0
        and ajustes.reducao_ruido == 0
        and ajustes.nitidez == 0
    )
    if sem_alteracoes:
        return imagem.convert("RGB").copy()
    matriz = np.asarray(imagem, dtype=np.float32)
    matriz = _aplicar_exposicao(matriz=matriz, valor=ajustes.exposicao)
    matriz = _aplicar_temperatura(matriz=matriz, valor=ajustes.temperatura)
    matriz = _aplicar_tons(
        matriz=matriz,
        contraste=ajustes.contraste,
        realces=ajustes.realces,
        sombras=ajustes.sombras,
    )
    resultado = Image.fromarray(
        np.clip(matriz, 0, 255).astype(np.uint8),
        mode="RGB",
    )
    if ajustes.reducao_ruido > 0:
        resultado = _reduzir_pixels_quentes(imagem=resultado)
    resultado = _reduzir_ruido(
        imagem=resultado,
        iso=iso,
        intensidade=ajustes.reducao_ruido,
    )
    fator_cor = max(0.0, 1.0 + ajustes.saturacao / 100.0)
    resultado = ImageEnhance.Color(resultado).enhance(fator_cor)
    if ajustes.nitidez > 0:
        resultado = resultado.filter(
            ImageFilter.UnsharpMask(
                radius=1.0,
                percent=int(ajustes.nitidez * 1.35),
                threshold=7 if iso < 3200 else 11,
            )
        )
    return resultado


def aplicar_mascara_local(
    imagem: Image.Image,
    mascara: Image.Image | None,
    ajustes: AjustesMascara,
) -> Image.Image:
    """Aplica um efeito local usando uma máscara branca como seleção."""
    if mascara is None or ajustes.efeito == EFEITO_NENHUM:
        return imagem
    mascara_ajustada = mascara.convert("L")
    if mascara_ajustada.size != imagem.size:
        mascara_ajustada = mascara_ajustada.resize(
            imagem.size,
            Image.Resampling.BILINEAR,
        )
    if ajustes.suavizacao > 0:
        mascara_ajustada = mascara_ajustada.filter(
            ImageFilter.GaussianBlur(radius=ajustes.suavizacao),
        )
    intensidade = np.clip(ajustes.intensidade / 100.0, 0.0, 1.0)
    if intensidade < 1.0:
        mascara_ajustada = mascara_ajustada.point(
            lambda valor: int(valor * intensidade),
        )

    preto_branco = ImageEnhance.Contrast(
        imagem.convert("L").convert("RGB"),
    ).enhance(1.03)
    match ajustes.efeito:
        case efeito if efeito == EFEITO_DESTAQUE_SELETIVO:
            return Image.composite(imagem, preto_branco, mascara_ajustada)
        case efeito if efeito == EFEITO_DESTAQUE_SUAVE:
            fundo = preto_branco.filter(ImageFilter.GaussianBlur(radius=1.2))
            return Image.composite(imagem, fundo, mascara_ajustada)
        case efeito if efeito == EFEITO_PB_SELECAO:
            return Image.composite(preto_branco, imagem, mascara_ajustada)
        case efeito if efeito == EFEITO_SATURAR_SELECAO:
            saturada = ImageEnhance.Color(imagem).enhance(1.0 + intensidade * 0.65)
            return Image.composite(saturada, imagem, mascara_ajustada)
        case efeito if efeito == EFEITO_DESFOCAR_FUNDO:
            fundo = imagem.filter(
                ImageFilter.GaussianBlur(radius=0.8 + intensidade * 3.2),
            )
            return Image.composite(imagem, fundo, mascara_ajustada)
        case _:
            return imagem


def aplicar_edicao_completa(
    imagem: Image.Image,
    ajustes: AjustesFoto,
    iso: int,
    mascara: Image.Image | None = None,
    ajustes_mascara: AjustesMascara | None = None,
    camadas: list[CamadaMascara] | None = None,
) -> Image.Image:
    """Aplica ajustes globais e as camadas locais em sequência."""
    ajustes_base = ajustes
    efeitos_com_cor = {
        EFEITO_DESTAQUE_SELETIVO,
        EFEITO_DESTAQUE_SUAVE,
        EFEITO_SATURAR_SELECAO,
    }
    ajustes_locais = [camada.ajustes for camada in camadas or []]
    if ajustes_mascara is not None:
        ajustes_locais.append(ajustes_mascara)
    preserva_cor = any(
        ajuste_local.efeito in efeitos_com_cor for ajuste_local in ajustes_locais
    )
    if preserva_cor and ajustes.saturacao < 0:
        ajustes_base = ajustes.copiar(saturacao=0)
    resultado = aplicar_ajustes(
        imagem=imagem,
        ajustes=ajustes_base,
        iso=iso,
    )
    if ajustes_mascara is not None:
        resultado = aplicar_mascara_local(
            imagem=resultado,
            mascara=mascara,
            ajustes=ajustes_mascara,
        )
    for camada in camadas or []:
        resultado = aplicar_mascara_local(
            imagem=resultado,
            mascara=camada.mascara,
            ajustes=camada.ajustes,
        )
    return resultado


def criar_preview(
    caminho: Path,
    ajustes: AjustesFoto,
    iso: int,
    tamanho_maximo: tuple[int, int],
) -> tuple[Image.Image, Image.Image]:
    """Gera os previews original e editado para comparação."""
    original = revelar_raw(caminho=caminho, iso=iso, preview=True)
    editada = aplicar_edicao_completa(imagem=original, ajustes=ajustes, iso=iso)
    original.thumbnail(tamanho_maximo, Image.Resampling.LANCZOS)
    editada.thumbnail(tamanho_maximo, Image.Resampling.LANCZOS)
    return original, editada


def nome_destino_seguro(pasta: Path, origem: Path, extensao: str) -> Path:
    """Cria um nome de saída sem substituir arquivos existentes."""
    base = pasta / f"{origem.stem}_editada{extensao}"
    if not base.exists():
        return base
    contador = 2
    while True:
        candidato = pasta / f"{origem.stem}_editada_{contador}{extensao}"
        if not candidato.exists():
            return candidato
        contador += 1


def exportar_foto(
    origem: Path,
    pasta_destino: Path,
    ajustes: AjustesFoto,
    iso: int,
    formato: FormatoExportacao,
    mascara: Image.Image | None = None,
    ajustes_mascara: AjustesMascara | None = None,
    camadas: list[CamadaMascara] | None = None,
) -> Path:
    """Revela e exporta uma foto em resolução total para uma nova pasta."""
    if formato not in {"JPEG", "PNG"}:
        raise ValueError("Formato de exportação não suportado.")
    pasta_destino.mkdir(parents=True, exist_ok=True)
    imagem = revelar_raw(caminho=origem, iso=iso, preview=False)
    imagem = aplicar_edicao_completa(
        imagem=imagem,
        ajustes=ajustes,
        iso=iso,
        mascara=mascara,
        ajustes_mascara=ajustes_mascara,
        camadas=camadas,
    )
    extensao = ".png" if formato == "PNG" else ".jpg"
    destino = nome_destino_seguro(
        pasta=pasta_destino,
        origem=origem,
        extensao=extensao,
    )
    if formato == "PNG":
        imagem.save(
            destino,
            format="PNG",
            compress_level=4,
            dpi=(300, 300),
            icc_profile=PERFIL_SRGB,
        )
    else:
        imagem.save(
            destino,
            format="JPEG",
            quality=QUALIDADE_JPEG,
            subsampling=0,
            optimize=True,
            dpi=(300, 300),
            icc_profile=PERFIL_SRGB,
        )
    return destino
