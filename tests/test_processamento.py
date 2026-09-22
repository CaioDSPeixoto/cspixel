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
from modelos import AjustesFoto, AjustesMascara, CamadaMascara  # noqa: E402
from presets import AJUSTES_PADRAO, preset_recomendado  # noqa: E402
from processamento import (  # noqa: E402
    QUALIDADE_JPEG,
    _cena_subexposta,
    aplicar_ajustes,
    aplicar_edicao_completa,
    criar_preview,
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
        self.assertEqual(preset_recomendado(iso=6400), "Redução forte de ruído")
        self.assertEqual(preset_recomendado(iso=3200), "Menos ruído")
        self.assertEqual(preset_recomendado(iso=1600), "Natural")
        self.assertEqual(preset_recomendado(iso=400), "Retrato")

    def test_presets_combinam_cores_vivas_e_reducao_de_ruido(self) -> None:
        """Oferece combinações equilibrada e forte para os ajustes favoritos."""
        equilibrado = AJUSTES_PADRAO["Cores vivas + menos ruído"]
        forte = AJUSTES_PADRAO["Cores vivas + redução forte"]
        self.assertGreater(equilibrado.saturacao, 0)
        self.assertGreaterEqual(equilibrado.reducao_ruido, 55)
        self.assertGreater(forte.saturacao, 0)
        self.assertGreaterEqual(forte.reducao_ruido, 90)
        self.assertLess(equilibrado.reducao_ruido, forte.reducao_ruido - 20)
        self.assertGreater(equilibrado.nitidez, forte.nitidez)

    def test_deteccao_de_cena_subexposta_ignora_realces_isolados(self) -> None:
        """Clareia uma cena escura mesmo quando há poucos pontos muito claros."""
        mosaico = np.full((80, 80), 2500, dtype=np.uint16)
        mosaico[:4, :] = 15360
        self.assertTrue(
            _cena_subexposta(
                mosaico=mosaico,
                nivel_preto=2047,
                nivel_branco=15360,
            )
        )

    def test_deteccao_de_cena_clara_preserva_realces(self) -> None:
        """Evita compensação automática quando a cena já contém muita luz."""
        mosaico = np.full((80, 80), 9000, dtype=np.uint16)
        self.assertFalse(
            _cena_subexposta(
                mosaico=mosaico,
                nivel_preto=2047,
                nivel_branco=15360,
            )
        )

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

    def test_reducao_de_ruido_preserva_borda_e_limpa_areas_planas(self) -> None:
        """Suaviza o grão sem apagar a separação entre áreas distintas."""
        gerador = np.random.default_rng(seed=123)
        base = np.zeros((128, 128, 3), dtype=np.float32)
        base[:, :64] = 50
        base[:, 64:] = 180
        matriz = np.clip(
            base + gerador.normal(loc=0, scale=22, size=base.shape),
            0,
            255,
        ).astype(np.uint8)
        imagem = Image.fromarray(matriz, mode="RGB")
        ajustes = AJUSTES_PADRAO["Sem ajustes"].copiar(reducao_ruido=96)
        resultado = np.asarray(
            aplicar_ajustes(imagem=imagem, ajustes=ajustes, iso=6400),
            dtype=np.float32,
        )
        ruido_antes = float(np.std(matriz[:, 8:56]))
        ruido_depois = float(np.std(resultado[:, 8:56]))
        borda_antes = float(np.mean(matriz[:, 72:120]) - np.mean(matriz[:, 8:56]))
        borda_depois = float(
            np.mean(resultado[:, 72:120]) - np.mean(resultado[:, 8:56])
        )
        self.assertLess(ruido_depois, ruido_antes * 0.45)
        self.assertGreater(borda_depois, borda_antes * 0.90)

    def test_controle_de_ruido_aumenta_o_efeito_progressivamente(self) -> None:
        """Mantém o slider proporcional entre a redução leve e a forte."""
        gerador = np.random.default_rng(seed=321)
        matriz = np.clip(
            90 + gerador.normal(loc=0, scale=24, size=(96, 96, 3)),
            0,
            255,
        ).astype(np.uint8)
        imagem = Image.fromarray(matriz, mode="RGB")
        leve = aplicar_ajustes(
            imagem=imagem,
            ajustes=AJUSTES_PADRAO["Sem ajustes"].copiar(reducao_ruido=20),
            iso=6400,
        )
        forte = aplicar_ajustes(
            imagem=imagem,
            ajustes=AJUSTES_PADRAO["Sem ajustes"].copiar(reducao_ruido=90),
            iso=6400,
        )
        self.assertGreater(
            float(np.std(np.asarray(leve))),
            float(np.std(np.asarray(forte))),
        )

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

    def test_criar_preview_aplica_ajustes_no_tamanho_visivel(self) -> None:
        """Evita processar filtros em pixels que não serão exibidos."""
        imagem = Image.new("RGB", (4000, 3000), color=(100, 100, 100))
        with patch("processamento.revelar_raw", return_value=imagem):
            original, editada = criar_preview(
                caminho=Path("IMG_0100.CR2"),
                ajustes=AJUSTES_PADRAO["Natural"],
                iso=800,
                tamanho_maximo=(400, 300),
            )
        self.assertEqual(original.size, (400, 300))
        self.assertEqual(editada.size, (400, 300))

    def test_brilho_altera_luminancia_sem_mudar_dimensoes(self) -> None:
        """Clareia ou escurece a foto sem alterar seu tamanho."""
        imagem = Image.new("RGB", (60, 40), color=(100, 100, 100))
        escura = aplicar_ajustes(
            imagem=imagem,
            ajustes=AjustesFoto(
                preset="Personalizado",
                brilho=-40,
                contraste=0,
                realces=0,
                sombras=0,
                saturacao=0,
                reducao_ruido=0,
                nitidez=0,
            ),
            iso=400,
        )
        clara = aplicar_ajustes(
            imagem=imagem,
            ajustes=AjustesFoto(
                preset="Personalizado",
                brilho=40,
                contraste=0,
                realces=0,
                sombras=0,
                saturacao=0,
                reducao_ruido=0,
                nitidez=0,
            ),
            iso=400,
        )
        self.assertEqual(escura.size, imagem.size)
        self.assertEqual(clara.size, imagem.size)
        self.assertLess(int(np.asarray(escura)[20, 20, 0]), 100)
        self.assertGreater(int(np.asarray(clara)[20, 20, 0]), 100)

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
        matriz_resultado = np.asarray(resultado)
        pixel_selecionado = matriz_resultado[20, 10]
        pixel_fundo = matriz_resultado[20, 70]
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
        matriz_resultado = np.asarray(resultado)
        pixel_esquerdo = matriz_resultado[20, 10]
        pixel_direito = matriz_resultado[20, 70]
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
