"""Janela de edição manual de máscaras locais."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from efeitos import EFEITOS_MASCARA
from modelos import AjustesMascara
from processamento import aplicar_mascara_local

__all__ = ["EditorMascara"]


class EditorMascara(tk.Toplevel):
    """Permite criar uma máscara com pincel, borracha ou contorno."""

    def __init__(
        self,
        parent: tk.Misc,
        imagem: Image.Image,
        mascara: Image.Image | None,
        ajustes: AjustesMascara,
        ao_confirmar: Callable[[Image.Image, AjustesMascara], None],
    ) -> None:
        super().__init__(parent)
        self.title("Editor de máscara local")
        self.geometry("1180x820")
        self.minsize(900, 650)
        self.configure(bg="#17191d")
        self.transient(parent)
        self.grab_set()

        self._imagem = imagem.convert("RGB").copy()
        self._mascara = (
            mascara.convert("L").resize(self._imagem.size, Image.Resampling.BILINEAR)
            if mascara is not None
            else Image.new("L", self._imagem.size, color=0)
        )
        self._ao_confirmar = ao_confirmar
        self._foto_tk: ImageTk.PhotoImage | None = None
        self._escala = 1.0
        self._deslocamento_x = 0
        self._deslocamento_y = 0
        self._ultimo_ponto: tuple[int, int] | None = None
        self._pontos_poligono: list[tuple[int, int]] = []

        self.var_ferramenta = tk.StringVar(value="Pincel +")
        self.var_tamanho = tk.IntVar(value=70)
        self.var_efeito = tk.StringVar(value=ajustes.efeito)
        self.var_intensidade = tk.IntVar(value=ajustes.intensidade)
        self.var_suavizacao = tk.IntVar(value=ajustes.suavizacao)
        self.var_visualizar = tk.BooleanVar(value=False)

        self._criar_interface()
        self.bind("<Escape>", lambda _evento: self.destroy())
        self.bind("<Return>", lambda _evento: self._finalizar_poligono())
        self.after(80, self._renderizar)

    def _criar_interface(self) -> None:
        """Monta ferramentas, área de desenho e opções de efeito."""
        barra = ttk.Frame(self, padding=8)
        barra.pack(fill="x")
        ttk.Label(barra, text="Ferramenta:").pack(side="left")
        for nome in ("Pincel +", "Borracha", "Contorno"):
            ttk.Radiobutton(
                barra,
                text=nome,
                value=nome,
                variable=self.var_ferramenta,
                command=self._ferramenta_alterada,
            ).pack(side="left", padx=(6, 0))
        ttk.Label(barra, text="Tamanho:").pack(side="left", padx=(18, 4))
        tk.Scale(
            barra,
            variable=self.var_tamanho,
            from_=8,
            to=300,
            orient="horizontal",
            showvalue=True,
            length=180,
        ).pack(side="left")
        ttk.Button(barra, text="Inverter", command=self._inverter).pack(
            side="right",
            padx=4,
        )
        ttk.Button(barra, text="Selecionar tudo", command=self._selecionar_tudo).pack(
            side="right",
            padx=4,
        )
        ttk.Button(barra, text="Limpar", command=self._limpar).pack(
            side="right",
            padx=4,
        )

        self.canvas = tk.Canvas(
            self,
            bg="#0d0e10",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True, padx=8)
        self.canvas.bind("<Configure>", lambda _evento: self._renderizar())
        self.canvas.bind("<Button-1>", self._pressionar)
        self.canvas.bind("<B1-Motion>", self._arrastar)
        self.canvas.bind("<ButtonRelease-1>", self._soltar)
        self.canvas.bind("<Double-Button-1>", lambda _evento: self._finalizar_poligono())
        self.canvas.bind("<Button-3>", lambda _evento: self._cancelar_poligono())

        opcoes = ttk.Frame(self, padding=8)
        opcoes.pack(fill="x")
        ttk.Label(opcoes, text="Efeito:").grid(row=0, column=0, sticky="w")
        seletor = ttk.Combobox(
            opcoes,
            textvariable=self.var_efeito,
            values=EFEITOS_MASCARA,
            state="readonly",
            width=36,
        )
        seletor.grid(row=0, column=1, sticky="ew", padx=6)
        seletor.bind("<<ComboboxSelected>>", lambda _evento: self._renderizar())
        ttk.Label(opcoes, text="Intensidade:").grid(row=0, column=2, padx=(12, 2))
        tk.Scale(
            opcoes,
            variable=self.var_intensidade,
            from_=0,
            to=100,
            orient="horizontal",
            length=150,
            command=lambda _valor: self._renderizar_se_visualizando(),
        ).grid(row=0, column=3)
        ttk.Label(opcoes, text="Suavizar borda:").grid(
            row=0,
            column=4,
            padx=(12, 2),
        )
        tk.Scale(
            opcoes,
            variable=self.var_suavizacao,
            from_=0,
            to=40,
            orient="horizontal",
            length=150,
            command=lambda _valor: self._renderizar_se_visualizando(),
        ).grid(row=0, column=5)
        ttk.Checkbutton(
            opcoes,
            text="Visualizar efeito",
            variable=self.var_visualizar,
            command=self._renderizar,
        ).grid(row=0, column=6, padx=(12, 0))
        opcoes.columnconfigure(1, weight=1)

        rodape = ttk.Frame(self, padding=(8, 0, 8, 8))
        rodape.pack(fill="x")
        ttk.Label(
            rodape,
            text=(
                "Pincel adiciona; Borracha remove; Contorno usa cliques e "
                "finaliza com Enter ou clique duplo. Botão direito cancela o contorno."
            ),
        ).pack(side="left")
        ttk.Button(rodape, text="Cancelar", command=self.destroy).pack(
            side="right",
            padx=4,
        )
        ttk.Button(
            rodape,
            text="Aplicar máscara",
            command=self._confirmar,
        ).pack(side="right", padx=4)

    def _ajustes_atuais(self) -> AjustesMascara:
        """Lê as opções locais da janela."""
        return AjustesMascara(
            efeito=self.var_efeito.get(),
            intensidade=int(self.var_intensidade.get()),
            suavizacao=int(self.var_suavizacao.get()),
        )

    def _renderizar_se_visualizando(self) -> None:
        """Atualiza a tela quando o modo de efeito está ativo."""
        if self.var_visualizar.get():
            self._renderizar()

    def _renderizar(self) -> None:
        """Exibe a foto, a máscara ou o efeito local calculado."""
        largura_canvas = max(200, self.canvas.winfo_width())
        altura_canvas = max(200, self.canvas.winfo_height())
        escala = min(
            largura_canvas / self._imagem.width,
            altura_canvas / self._imagem.height,
        )
        self._escala = max(escala, 0.01)
        largura = max(1, int(self._imagem.width * self._escala))
        altura = max(1, int(self._imagem.height * self._escala))
        self._deslocamento_x = (largura_canvas - largura) // 2
        self._deslocamento_y = (altura_canvas - altura) // 2

        if self.var_visualizar.get():
            exibicao = aplicar_mascara_local(
                imagem=self._imagem,
                mascara=self._mascara,
                ajustes=self._ajustes_atuais(),
            )
        else:
            exibicao = self._sobrepor_mascara()
        exibicao = exibicao.resize((largura, altura), Image.Resampling.LANCZOS)
        self._foto_tk = ImageTk.PhotoImage(exibicao)
        self.canvas.delete("all")
        self.canvas.create_image(
            self._deslocamento_x,
            self._deslocamento_y,
            image=self._foto_tk,
            anchor="nw",
        )
        self._desenhar_poligono_temporario()

    def _sobrepor_mascara(self) -> Image.Image:
        """Sobrepõe vermelho translúcido à região selecionada."""
        base = self._imagem.convert("RGBA")
        camada = Image.new("RGBA", self._imagem.size, color=(255, 55, 45, 0))
        alpha = self._mascara.point(lambda valor: int(valor * 0.48))
        camada.putalpha(alpha)
        return Image.alpha_composite(base, camada).convert("RGB")

    def _canvas_para_imagem(self, x: int, y: int) -> tuple[int, int] | None:
        """Converte coordenadas do canvas para coordenadas da imagem."""
        imagem_x = int((x - self._deslocamento_x) / self._escala)
        imagem_y = int((y - self._deslocamento_y) / self._escala)
        if not (0 <= imagem_x < self._imagem.width):
            return None
        if not (0 <= imagem_y < self._imagem.height):
            return None
        return imagem_x, imagem_y

    def _pressionar(self, evento: tk.Event[tk.Canvas]) -> None:
        """Inicia uma pincelada ou adiciona um vértice ao contorno."""
        ponto = self._canvas_para_imagem(x=evento.x, y=evento.y)
        if ponto is None:
            return
        if self.var_ferramenta.get() == "Contorno":
            self._pontos_poligono.append(ponto)
            self._renderizar()
            return
        self._ultimo_ponto = ponto
        self._pintar(inicio=ponto, fim=ponto)

    def _arrastar(self, evento: tk.Event[tk.Canvas]) -> None:
        """Continua uma pincelada enquanto o mouse se move."""
        if self.var_ferramenta.get() == "Contorno":
            return
        ponto = self._canvas_para_imagem(x=evento.x, y=evento.y)
        if ponto is None or self._ultimo_ponto is None:
            return
        self._pintar(inicio=self._ultimo_ponto, fim=ponto)
        self._ultimo_ponto = ponto

    def _soltar(self, _evento: tk.Event[tk.Canvas]) -> None:
        """Finaliza a pincelada atual."""
        self._ultimo_ponto = None

    def _pintar(self, inicio: tuple[int, int], fim: tuple[int, int]) -> None:
        """Desenha na máscara com a ferramenta selecionada."""
        cor = 0 if self.var_ferramenta.get() == "Borracha" else 255
        largura = int(self.var_tamanho.get())
        desenho = ImageDraw.Draw(self._mascara)
        desenho.line((inicio, fim), fill=cor, width=largura)
        raio = largura // 2
        desenho.ellipse(
            (fim[0] - raio, fim[1] - raio, fim[0] + raio, fim[1] + raio),
            fill=cor,
        )
        self._renderizar()

    def _desenhar_poligono_temporario(self) -> None:
        """Mostra os segmentos do contorno ainda não confirmado."""
        if not self._pontos_poligono:
            return
        pontos_canvas = [
            (
                int(x * self._escala + self._deslocamento_x),
                int(y * self._escala + self._deslocamento_y),
            )
            for x, y in self._pontos_poligono
        ]
        for x, y in pontos_canvas:
            self.canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#ffd84a")
        if len(pontos_canvas) >= 2:
            self.canvas.create_line(*pontos_canvas, fill="#ffd84a", width=2)

    def _finalizar_poligono(self) -> None:
        """Preenche o contorno quando ele possui ao menos três vértices."""
        if len(self._pontos_poligono) < 3:
            return
        desenho = ImageDraw.Draw(self._mascara)
        desenho.polygon(self._pontos_poligono, fill=255)
        self._pontos_poligono.clear()
        self._renderizar()

    def _cancelar_poligono(self) -> None:
        """Descarta o contorno ainda não confirmado."""
        self._pontos_poligono.clear()
        self._renderizar()

    def _ferramenta_alterada(self) -> None:
        """Cancela vértices pendentes ao trocar de ferramenta."""
        if self.var_ferramenta.get() != "Contorno":
            self._pontos_poligono.clear()
        self._renderizar()

    def _limpar(self) -> None:
        """Remove toda a seleção."""
        self._mascara = Image.new("L", self._imagem.size, color=0)
        self._pontos_poligono.clear()
        self._renderizar()

    def _selecionar_tudo(self) -> None:
        """Seleciona a fotografia inteira."""
        self._mascara = Image.new("L", self._imagem.size, color=255)
        self._pontos_poligono.clear()
        self._renderizar()

    def _inverter(self) -> None:
        """Inverte áreas selecionadas e não selecionadas."""
        self._mascara = self._mascara.point(lambda valor: 255 - valor)
        self._renderizar()

    def _confirmar(self) -> None:
        """Entrega uma cópia da máscara e fecha a janela."""
        self._ao_confirmar(self._mascara.copy(), self._ajustes_atuais())
        self.destroy()
