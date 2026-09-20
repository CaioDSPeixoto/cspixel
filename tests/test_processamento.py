"""Testes unitários do núcleo do Editor RAW."""

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

PASTA_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PASTA_PROJETO))

from presets import AJUSTES_PADRAO, preset_recomendado
from modelos import AjustesMascara
from processamento import (
    QUALIDADE_JPEG,
    aplicar_ajustes,
    aplicar_edicao_completa,
    faixa_iso,
    nome_destino_seguro,
)


class TesteProcessamento(unittest.TestCase):
    """Valida regras que não dependem de um arquivo RAW real."""

    def test_faixa_iso_classifica_limites(self) -> None:
        """Classifica corretamente os limites de cada faixa."""
        casos = (
            (0, "ISO não identificado"),
            (800, "ISO baixo (até 800)"),
            (801, "ISO médio (801–1600)"),
            (1600, "ISO médio (801–1600)"),
            (1601, "ISO alto (1601–3200)"),
            (3200, "ISO alto (1601–3200)"),
            (3201, "ISO muito alto (acima de 3200)"),
        )
        for iso, esperado in casos:
            with self.subTest(iso=iso):
                self.assertEqual(faixa_iso(iso=iso), esperado)

    def test_preset_recomendado_considera_iso(self) -> None:
        """Recomenda redução mais forte para ISO elevado."""
        self.assertEqual(preset_recomendado(iso=6400), "ISO alto — Limpo")
        self.assertEqual(preset_recomendado(iso=1600), "Natural equilibrado")
        self.assertEqual(preset_recomendado(iso=400), "Retrato suave")

    def test_qualidade_jpeg_e_alta_e_fixa(self) -> None:
        """Mantém a exportação JPEG em nível visualmente excelente."""
        self.assertGreaterEqual(QUALIDADE_JPEG, 98)

    def test_nome_destino_seguro_nao_sobrescreve(self) -> None:
        """Acrescenta numeração quando o primeiro destino já existe."""
        with tempfile.TemporaryDirectory() as nome_pasta:
            pasta = Path(nome_pasta)
            origem = Path("IMG_0001.CR2")
            primeiro = pasta / "IMG_0001_editada.jpg"
            primeiro.touch()
            destino = nome_destino_seguro(
                pasta=pasta,
                origem=origem,
                extensao=".jpg",
            )
            self.assertEqual(destino.name, "IMG_0001_editada_2.jpg")

    def test_aplicar_ajustes_preserva_dimensoes(self) -> None:
        """Mantém as dimensões e o modo RGB da imagem."""
        matriz = np.full((80, 120, 3), 96, dtype=np.uint8)
        imagem = Image.fromarray(matriz, mode="RGB")
        resultado = aplicar_ajustes(
            imagem=imagem,
            ajustes=AJUSTES_PADRAO["ISO alto — Limpo"],
            iso=6400,
        )
        self.assertEqual(resultado.size, imagem.size)
        self.assertEqual(resultado.mode, "RGB")

    def test_mascara_mantem_selecao_colorida_e_fundo_pb(self) -> None:
        """Preserva cor apenas onde a máscara está branca."""
        matriz = np.zeros((40, 80, 3), dtype=np.uint8)
        matriz[:, :, 0] = 180
        matriz[:, :, 1] = 70
        matriz[:, :, 2] = 25
        imagem = Image.fromarray(matriz, mode="RGB")
        mascara = Image.new("L", imagem.size, color=0)
        mascara.paste(255, (0, 0, 40, 40))
        resultado = aplicar_edicao_completa(
            imagem=imagem,
            ajustes=AJUSTES_PADRAO["Preto e branco"],
            iso=400,
            mascara=mascara,
            ajustes_mascara=AjustesMascara(suavizacao=0),
        )
        pixel_selecionado = resultado.getpixel((10, 20))
        pixel_fundo = resultado.getpixel((70, 20))
        self.assertNotEqual(pixel_selecionado[0], pixel_selecionado[1])
        self.assertEqual(pixel_fundo[0], pixel_fundo[1])
        self.assertEqual(pixel_fundo[1], pixel_fundo[2])


if __name__ == "__main__":
    unittest.main()
