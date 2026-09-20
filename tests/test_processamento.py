"""Testes unitários do núcleo do Editor RAW."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, JpegImagePlugin

PASTA_PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PASTA_PROJETO))

from efeitos import EFEITO_PB_SELECAO, EFEITO_SATURAR_SELECAO  # noqa: E402
from modelos import AjustesMascara, CamadaMascara  # noqa: E402
from presets import AJUSTES_PADRAO, preset_recomendado  # noqa: E402
from processamento import (  # noqa: E402
    QUALIDADE_JPEG,
    aplicar_ajustes,
    aplicar_edicao_completa,
    exportar_foto,
    faixa_iso,
    nome_destino_seguro,
    obter_iso,
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
        self.assertEqual(preset_recomendado(iso=6400), "Menos ruído")
        self.assertEqual(preset_recomendado(iso=1600), "Natural")
        self.assertEqual(preset_recomendado(iso=400), "Retrato")

    def test_qualidade_jpeg_e_alta_e_fixa(self) -> None:
        """Mantém a exportação JPEG em nível visualmente excelente."""
        self.assertEqual(QUALIDADE_JPEG, 100)

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

    def test_nome_destino_seguro_avanca_ate_um_nome_livre(self) -> None:
        """Ignora todas as exportações anteriores com o mesmo nome."""
        with tempfile.TemporaryDirectory() as nome_pasta:
            pasta = Path(nome_pasta)
            origem = Path("IMG_0001.CR2")
            (pasta / "IMG_0001_editada.jpg").touch()
            (pasta / "IMG_0001_editada_2.jpg").touch()
            destino = nome_destino_seguro(
                pasta=pasta,
                origem=origem,
                extensao=".jpg",
            )
            self.assertEqual(destino.name, "IMG_0001_editada_3.jpg")

    def test_obter_iso_de_arquivo_invalido_retorna_zero(self) -> None:
        """Não interrompe a importação quando o EXIF não pode ser lido."""
        with tempfile.TemporaryDirectory() as nome_pasta:
            caminho = Path(nome_pasta) / "corrompida.cr2"
            caminho.write_bytes(b"arquivo RAW invalido")
            self.assertEqual(obter_iso(caminho=caminho), 0)

    def test_aplicar_ajustes_preserva_dimensoes(self) -> None:
        """Mantém as dimensões e o modo RGB da imagem."""
        matriz = np.full((80, 120, 3), 96, dtype=np.uint8)
        imagem = Image.fromarray(matriz, mode="RGB")
        resultado = aplicar_ajustes(
            imagem=imagem,
            ajustes=AJUSTES_PADRAO["Menos ruído"],
            iso=6400,
        )
        self.assertEqual(resultado.size, imagem.size)
        self.assertEqual(resultado.mode, "RGB")

    def test_aplicar_ajustes_nao_altera_imagem_de_origem(self) -> None:
        """Mantém os pixels da imagem recebida intactos."""
        matriz = np.full((30, 50, 3), 110, dtype=np.uint8)
        imagem = Image.fromarray(matriz, mode="RGB")
        pixels_antes = np.asarray(imagem).copy()
        aplicar_edicao_completa(
            imagem=imagem,
            ajustes=AJUSTES_PADRAO["Cores vivas"],
            iso=800,
        )
        np.testing.assert_array_equal(np.asarray(imagem), pixels_antes)

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

    def test_multiplas_camadas_aplicam_efeitos_independentes(self) -> None:
        """Combina camadas distintas na ordem configurada."""
        matriz = np.zeros((40, 80, 3), dtype=np.uint8)
        matriz[:, :, 0] = 150
        matriz[:, :, 1] = 80
        matriz[:, :, 2] = 35
        imagem = Image.fromarray(matriz, mode="RGB")
        mascara_esquerda = Image.new("L", imagem.size, color=0)
        mascara_esquerda.paste(255, (0, 0, 40, 40))
        mascara_direita = Image.new("L", imagem.size, color=0)
        mascara_direita.paste(255, (40, 0, 80, 40))
        camadas = [
            CamadaMascara(
                nome="Pessoa",
                mascara=mascara_esquerda,
                ajustes=AjustesMascara(
                    efeito=EFEITO_PB_SELECAO,
                    suavizacao=0,
                ),
            ),
            CamadaMascara(
                nome="Fundo",
                mascara=mascara_direita,
                ajustes=AjustesMascara(
                    efeito=EFEITO_SATURAR_SELECAO,
                    suavizacao=0,
                ),
            ),
        ]
        resultado = aplicar_edicao_completa(
            imagem=imagem,
            ajustes=AJUSTES_PADRAO["Sem ajustes"],
            iso=400,
            camadas=camadas,
        )
        pixel_esquerdo = resultado.getpixel((10, 20))
        pixel_direito = resultado.getpixel((70, 20))
        self.assertEqual(pixel_esquerdo[0], pixel_esquerdo[1])
        self.assertEqual(pixel_esquerdo[1], pixel_esquerdo[2])
        self.assertNotEqual(pixel_direito[0], pixel_direito[1])

    def test_exportar_jpeg_embute_srgb_e_usa_cores_444(self) -> None:
        """Gera JPEG com perfil de cor e sem subamostragem cromática."""
        imagem = Image.new("RGB", (64, 48), color=(130, 70, 25))
        with tempfile.TemporaryDirectory() as nome_pasta:
            pasta = Path(nome_pasta)
            with patch("processamento.revelar_raw", return_value=imagem.copy()):
                destino = exportar_foto(
                    origem=Path("IMG_0100.CR2"),
                    pasta_destino=pasta,
                    ajustes=AJUSTES_PADRAO["Sem ajustes"],
                    iso=400,
                    formato="JPEG",
                )
            with Image.open(destino) as exportada:
                self.assertEqual(exportada.format, "JPEG")
                self.assertEqual(exportada.size, imagem.size)
                self.assertTrue(exportada.info.get("icc_profile"))
                self.assertEqual(JpegImagePlugin.get_sampling(exportada), 0)

    def test_exportar_png_embute_srgb_sem_perdas(self) -> None:
        """Gera PNG com pixels e perfil de cor preservados."""
        imagem = Image.new("RGB", (32, 24), color=(20, 90, 170))
        with tempfile.TemporaryDirectory() as nome_pasta:
            pasta = Path(nome_pasta)
            with patch("processamento.revelar_raw", return_value=imagem.copy()):
                destino = exportar_foto(
                    origem=Path("IMG_0101.CR2"),
                    pasta_destino=pasta,
                    ajustes=AJUSTES_PADRAO["Sem ajustes"],
                    iso=400,
                    formato="PNG",
                )
            with Image.open(destino) as exportada:
                self.assertEqual(exportada.format, "PNG")
                self.assertEqual(exportada.getpixel((10, 10)), (20, 90, 170))
                self.assertTrue(exportada.info.get("icc_profile"))

    def test_exportar_rejeita_formato_desconhecido(self) -> None:
        """Evita salvar silenciosamente em um formato diferente do solicitado."""
        with tempfile.TemporaryDirectory() as nome_pasta:
            with self.assertRaises(ValueError):
                exportar_foto(
                    origem=Path("IMG_0102.CR2"),
                    pasta_destino=Path(nome_pasta),
                    ajustes=AJUSTES_PADRAO["Sem ajustes"],
                    iso=400,
                    formato="TIFF",  # type: ignore[arg-type]
                )


if __name__ == "__main__":
    unittest.main()
