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
        parent: tk.Tk | tk.Toplevel,
        imagem: Image.Image,
        mascara: Image.Image | None,
        ajustes: AjustesMascara,
        ao_confirmar: Callable[[Image.Image, AjustesMascara], None],
        nome_camada: str = "Camada",
    ) -> None:
        super().__init__(parent)
        self.title(f"Editor de camada — {nome_camada}")
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
        self._zoom = 1.0
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
        self.var_zoom = tk.StringVar(value="100%")

        self._criar_interface()
        self.bind("<Escape>", lambda _evento: self.destroy())
        self.bind("<Return>", lambda _evento: self._finalizar_poligono())
        self.after(80, self._renderizar)

    def _criar_interface(self) -> None:
        """Monta ferramentas, área de desenho e opções de efeito."""
        self._criar_barra_ferramentas()
        self._criar_area_desenho()
        self._criar_opcoes_efeito()
        self._criar_rodape()

    def _criar_barra_ferramentas(self) -> None:
        """Cria ferramentas de seleção, pincel e zoom."""
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
        ttk.Button(
            barra,
            text="−",
            width=3,
            command=lambda: self._alterar_zoom(fator=0.8),
        ).pack(side="left", padx=(16, 2))
        ttk.Label(barra, textvariable=self.var_zoom, width=6).pack(side="left")
        ttk.Button(
            barra,
            text="+",
            width=3,
            command=lambda: self._alterar_zoom(fator=1.25),
        ).pack(side="left", padx=2)
        ttk.Button(
            barra,
            text="Ajustar",
            command=self._ajustar_zoom,
        ).pack(side="left", padx=(2, 0))
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

    def _criar_area_desenho(self) -> None:
        """Cria o canvas navegável e seus eventos de edição."""
        quadro_canvas = ttk.Frame(self)
        quadro_canvas.pack(fill="both", expand=True, padx=8)
        self.canvas = tk.Canvas(
            quadro_canvas,
            bg="#0d0e10",
            highlightthickness=0,
            cursor="crosshair",
        )
        rolagem_vertical = ttk.Scrollbar(
            quadro_canvas,
            orient="vertical",
            command=self._rolar_barra_vertical,
        )
        rolagem_horizontal = ttk.Scrollbar(
            quadro_canvas,
            orient="horizontal",
            command=self._rolar_barra_horizontal,
        )
        self.canvas.configure(
            xscrollcommand=rolagem_horizontal.set,
            yscrollcommand=rolagem_vertical.set,
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        rolagem_vertical.grid(row=0, column=1, sticky="ns")
        rolagem_horizontal.grid(row=1, column=0, sticky="ew")
        quadro_canvas.rowconfigure(0, weight=1)
        quadro_canvas.columnconfigure(0, weight=1)
        self.canvas.bind("<Configure>", lambda _evento: self._renderizar())
        self.canvas.bind("<Button-1>", self._pressionar)
        self.canvas.bind("<B1-Motion>", self._arrastar)
        self.canvas.bind("<ButtonRelease-1>", self._soltar)
        self.canvas.bind(
            "<Double-Button-1>", lambda _evento: self._finalizar_poligono()
        )
        self.canvas.bind("<Button-3>", lambda _evento: self._cancelar_poligono())
        self.canvas.bind("<Control-MouseWheel>", self._zoom_com_roda)
        self.canvas.bind("<MouseWheel>", self._rolar_verticalmente)
        self.canvas.bind("<Shift-MouseWheel>", self._rolar_horizontalmente)
        self.canvas.bind("<ButtonPress-2>", self._iniciar_movimento)
        self.canvas.bind("<B2-Motion>", self._mover_imagem)

    def _criar_opcoes_efeito(self) -> None:
        """Cria os controles do efeito aplicado à camada."""
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

    def _criar_rodape(self) -> None:
        """Cria instruções e ações de confirmação da camada."""
        rodape = ttk.Frame(self, padding=(8, 0, 8, 8))
        rodape.pack(fill="x")
        ttk.Label(
            rodape,
            text=(
                "Pincel adiciona; Borracha remove; Contorno usa cliques e "
                "finaliza com Enter ou clique duplo. Ctrl + roda aplica zoom; "
                "botão do meio move a foto."
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
        largura_canvas, altura_canvas, largura, altura = self._preparar_geometria()
        exibicao = (
            aplicar_mascara_local(
                imagem=self._imagem,
                mascara=self._mascara,
                ajustes=self._ajustes_atuais(),
            )
            if self.var_visualizar.get()
            else self._sobrepor_mascara()
        )
        recorte = self._recortar_area_visivel(
            exibicao=exibicao,
            largura_canvas=largura_canvas,
            altura_canvas=altura_canvas,
            largura_imagem=largura,
            altura_imagem=altura,
        )
        if recorte is None:
            return
        imagem_visivel, posicao_x, posicao_y = recorte
        self._foto_tk = ImageTk.PhotoImage(imagem_visivel)
        self.canvas.delete("all")
        self.canvas.create_image(
            posicao_x,
            posicao_y,
            image=self._foto_tk,
            anchor="nw",
        )
        self._desenhar_poligono_temporario()

    def _preparar_geometria(self) -> tuple[int, int, int, int]:
        """Calcula escala, deslocamento e região navegável da imagem."""
        largura_canvas = max(200, self.canvas.winfo_width())
        altura_canvas = max(200, self.canvas.winfo_height())
        escala_encaixe = min(
            largura_canvas / self._imagem.width,
            altura_canvas / self._imagem.height,
        )
        self._escala = max(escala_encaixe * self._zoom, 0.01)
        largura = max(1, int(self._imagem.width * self._escala))
        altura = max(1, int(self._imagem.height * self._escala))
        self._deslocamento_x = max((largura_canvas - largura) // 2, 0)
        self._deslocamento_y = max((altura_canvas - altura) // 2, 0)
        self.canvas.configure(
            scrollregion=(
                0,
                0,
                max(largura_canvas, largura),
                max(altura_canvas, altura),
            ),
        )
        return largura_canvas, altura_canvas, largura, altura

    def _recortar_area_visivel(
        self,
        exibicao: Image.Image,
        largura_canvas: int,
        altura_canvas: int,
        largura_imagem: int,
        altura_imagem: int,
    ) -> tuple[Image.Image, int, int] | None:
        """Amplia somente os pixels visíveis para limitar o uso de memória."""
        inicio_visivel_x = max(
            self._deslocamento_x,
            int(self.canvas.canvasx(0)),
        )
        inicio_visivel_y = max(
            self._deslocamento_y,
            int(self.canvas.canvasy(0)),
        )
        fim_visivel_x = min(
            self._deslocamento_x + largura_imagem,
            int(self.canvas.canvasx(largura_canvas)) + 1,
        )
        fim_visivel_y = min(
            self._deslocamento_y + altura_imagem,
            int(self.canvas.canvasy(altura_canvas)) + 1,
        )
        origem_x = max(
            0,
            int((inicio_visivel_x - self._deslocamento_x) / self._escala),
        )
        origem_y = max(
            0,
            int((inicio_visivel_y - self._deslocamento_y) / self._escala),
        )
        fim_x = min(
            self._imagem.width,
            int((fim_visivel_x - self._deslocamento_x) / self._escala) + 2,
        )
        fim_y = min(
            self._imagem.height,
            int((fim_visivel_y - self._deslocamento_y) / self._escala) + 2,
        )
        if fim_x <= origem_x or fim_y <= origem_y:
            return None
        recorte = exibicao.crop((origem_x, origem_y, fim_x, fim_y))
        largura_recorte = max(1, int(recorte.width * self._escala))
        altura_recorte = max(1, int(recorte.height * self._escala))
        recorte = recorte.resize(
            (largura_recorte, altura_recorte),
            Image.Resampling.LANCZOS,
        )
        return (
            recorte,
            self._deslocamento_x + int(origem_x * self._escala),
            self._deslocamento_y + int(origem_y * self._escala),
        )

    def _sobrepor_mascara(self) -> Image.Image:
        """Sobrepõe vermelho translúcido à região selecionada."""
        base = self._imagem.convert("RGBA")
        camada = Image.new("RGBA", self._imagem.size, color=(255, 55, 45, 0))
        alpha = self._mascara.point(lambda valor: int(valor * 0.48))
        camada.putalpha(alpha)
        return Image.alpha_composite(base, camada).convert("RGB")

    def _canvas_para_imagem(self, x: int, y: int) -> tuple[int, int] | None:
        """Converte coordenadas do canvas para coordenadas da imagem."""
        x_canvas = self.canvas.canvasx(x)
        y_canvas = self.canvas.canvasy(y)
        imagem_x = int((x_canvas - self._deslocamento_x) / self._escala)
        imagem_y = int((y_canvas - self._deslocamento_y) / self._escala)
        if not (0 <= imagem_x < self._imagem.width):
            return None
        if not (0 <= imagem_y < self._imagem.height):
            return None
        return imagem_x, imagem_y

    def _alterar_zoom(self, fator: float) -> None:
        """Altera o zoom preservando o centro visível da fotografia."""
        largura_canvas = max(1, self.canvas.winfo_width())
        altura_canvas = max(1, self.canvas.winfo_height())
        centro = self._canvas_para_imagem(
            x=largura_canvas // 2,
            y=altura_canvas // 2,
        )
        if centro is None:
            centro = (self._imagem.width // 2, self._imagem.height // 2)
        novo_zoom = max(1.0, min(4.0, self._zoom * fator))
        if abs(novo_zoom - self._zoom) < 0.001:
            return
        self._zoom = novo_zoom
        self.var_zoom.set(f"{round(self._zoom * 100)}%")
        self._renderizar()
        largura_total = max(largura_canvas, int(self._imagem.width * self._escala))
        altura_total = max(altura_canvas, int(self._imagem.height * self._escala))
        destino_x = centro[0] * self._escala - largura_canvas / 2
        destino_y = centro[1] * self._escala - altura_canvas / 2
        self.canvas.xview_moveto(max(0.0, destino_x / largura_total))
        self.canvas.yview_moveto(max(0.0, destino_y / altura_total))
        self._renderizar()

    def _ajustar_zoom(self) -> None:
        """Retorna à visualização completa da fotografia."""
        self._zoom = 1.0
        self.var_zoom.set("100%")
        self._renderizar()
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)
        self._renderizar()

    def _zoom_com_roda(self, evento: tk.Event[tk.Misc]) -> str:
        """Aplica zoom usando Ctrl e a roda do mouse."""
        fator = 1.25 if evento.delta > 0 else 0.8
        self._alterar_zoom(fator=fator)
        return "break"

    def _rolar_verticalmente(self, evento: tk.Event[tk.Misc]) -> str:
        """Move verticalmente uma fotografia ampliada."""
        unidades = -1 if evento.delta > 0 else 1
        self.canvas.yview_scroll(unidades, "units")
        self._renderizar()
        return "break"

    def _rolar_horizontalmente(self, evento: tk.Event[tk.Misc]) -> str:
        """Move horizontalmente uma fotografia ampliada."""
        unidades = -1 if evento.delta > 0 else 1
        self.canvas.xview_scroll(unidades, "units")
        self._renderizar()
        return "break"

    def _rolar_barra_vertical(self, *argumentos: str) -> None:
        """Move a visualização pela barra vertical e redesenha o recorte."""
        self.canvas.yview(*argumentos)
        self._renderizar()

    def _rolar_barra_horizontal(self, *argumentos: str) -> None:
        """Move a visualização pela barra horizontal e redesenha o recorte."""
        self.canvas.xview(*argumentos)
        self._renderizar()

    def _iniciar_movimento(self, evento: tk.Event[tk.Misc]) -> None:
        """Marca o ponto inicial para arrastar a fotografia ampliada."""
        self.canvas.scan_mark(evento.x, evento.y)

    def _mover_imagem(self, evento: tk.Event[tk.Misc]) -> None:
        """Move a área visível com o botão central pressionado."""
        self.canvas.scan_dragto(evento.x, evento.y, gain=1)
        self._renderizar()

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
