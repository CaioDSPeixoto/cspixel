"""Interface gráfica do Editor RAW não destrutivo."""

from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
import logging
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from PIL import Image, ImageTk

from editor_mascara import EditorMascara
from modelos import AjustesFoto, AjustesMascara, FotoProjeto
from presets import AJUSTES_PADRAO, preset_recomendado
from processamento import (
    EXTENSOES_SUPORTADAS,
    aplicar_edicao_completa,
    exportar_foto,
    faixa_iso,
    obter_iso,
    revelar_raw,
)
from versao import VERSAO_APLICATIVO


logger = logging.getLogger(__name__)


class AplicativoEditorRaw(tk.Tk):
    """Aplicativo desktop para revelar e editar arquivos RAW."""

    COR_FUNDO = "#17191d"
    COR_PAINEL = "#22252b"
    COR_CAMPO = "#2d3139"
    COR_TEXTO = "#f2f3f5"
    COR_SECUNDARIA = "#aeb4bf"
    COR_DESTAQUE = "#5b8cff"

    def __init__(self) -> None:
        super().__init__()
        self.title(
            f"Editor RAW {VERSAO_APLICATIVO} — edição não destrutiva",
        )
        self.geometry("1480x900")
        self.minsize(1180, 720)
        try:
            self.state("zoomed")
        except tk.TclError:
            pass

        self._executor = ThreadPoolExecutor(max_workers=2)
        self._fotos: dict[Path, FotoProjeto] = {}
        self._ajustes: dict[Path, AjustesFoto] = {}
        self._mascaras: dict[Path, Image.Image] = {}
        self._ajustes_mascara: dict[Path, AjustesMascara] = {}
        self._item_para_caminho: dict[str, Path] = {}
        self._foto_atual: Path | None = None
        self._cache_preview: OrderedDict[Path, Image.Image] = OrderedDict()
        self._imagem_tk_original: ImageTk.PhotoImage | None = None
        self._imagem_tk_editada: ImageTk.PhotoImage | None = None
        self._geracao_preview = 0
        self._temporizador_preview: str | None = None
        self._carregando_controles = False
        self._cancelar_exportacao = threading.Event()
        self._fila_interface: queue.Queue[
            tuple[Callable[..., None], tuple[object, ...]]
        ] = queue.Queue()
        self._encerrando = False
        self._pasta_base_saida: Path | None = None
        self._pasta_sessao_saida: Path | None = None

        self._criar_variaveis()
        self._configurar_estilo()
        self._criar_interface()
        self.after(50, self._processar_fila_interface)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

    def _enfileirar_interface(
        self,
        funcao: Callable[..., None],
        *argumentos: object,
    ) -> None:
        """Agenda uma operação para execução segura na thread da interface."""
        self._fila_interface.put((funcao, argumentos))

    def _processar_fila_interface(self) -> None:
        """Executa retornos das tarefas de fundo na thread principal."""
        while True:
            try:
                funcao, argumentos = self._fila_interface.get_nowait()
            except queue.Empty:
                break
            funcao(*argumentos)
        if not self._encerrando:
            self.after(50, self._processar_fila_interface)

    def _criar_variaveis(self) -> None:
        """Inicializa as variáveis vinculadas aos controles."""
        self.var_preset = tk.StringVar(value="Natural equilibrado")
        self.var_exposicao = tk.DoubleVar(value=0.0)
        self.var_contraste = tk.IntVar(value=6)
        self.var_realces = tk.IntVar(value=-12)
        self.var_sombras = tk.IntVar(value=10)
        self.var_saturacao = tk.IntVar(value=6)
        self.var_temperatura = tk.IntVar(value=0)
        self.var_ruido = tk.IntVar(value=52)
        self.var_nitidez = tk.IntVar(value=38)
        self.var_formato = tk.StringVar(value="JPEG")
        self.var_status = tk.StringVar(
            value="Selecione arquivos RAW para começar.",
        )
        self.var_saida = tk.StringVar(value="Pasta de saída ainda não escolhida")
        self.var_contagem = tk.StringVar(value="0 fotos")
        self.var_status_mascara = tk.StringVar(value="Nenhuma máscara nesta foto")

    def _configurar_estilo(self) -> None:
        """Aplica um tema escuro e legível aos componentes."""
        self.configure(bg=self.COR_FUNDO)
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure(".", font=("Segoe UI", 10))
        estilo.configure(
            "TFrame",
            background=self.COR_FUNDO,
        )
        estilo.configure(
            "Painel.TFrame",
            background=self.COR_PAINEL,
        )
        estilo.configure(
            "TLabel",
            background=self.COR_FUNDO,
            foreground=self.COR_TEXTO,
        )
        estilo.configure(
            "Painel.TLabel",
            background=self.COR_PAINEL,
            foreground=self.COR_TEXTO,
        )
        estilo.configure(
            "Secundario.TLabel",
            background=self.COR_PAINEL,
            foreground=self.COR_SECUNDARIA,
        )
        estilo.configure(
            "Titulo.TLabel",
            background=self.COR_PAINEL,
            foreground=self.COR_TEXTO,
            font=("Segoe UI Semibold", 12),
        )
        estilo.configure(
            "TButton",
            padding=(10, 7),
            background=self.COR_CAMPO,
            foreground=self.COR_TEXTO,
        )
        estilo.map("TButton", background=[("active", "#3a404b")])
        estilo.configure(
            "Destaque.TButton",
            background=self.COR_DESTAQUE,
            foreground="white",
        )
        estilo.map(
            "Destaque.TButton",
            background=[("active", "#78a0ff")],
        )
        estilo.configure(
            "Treeview",
            background=self.COR_CAMPO,
            fieldbackground=self.COR_CAMPO,
            foreground=self.COR_TEXTO,
            rowheight=26,
            borderwidth=0,
        )
        estilo.configure(
            "Treeview.Heading",
            background=self.COR_PAINEL,
            foreground=self.COR_TEXTO,
        )
        estilo.map(
            "Treeview",
            background=[("selected", self.COR_DESTAQUE)],
        )
        estilo.configure(
            "TCombobox",
            fieldbackground=self.COR_CAMPO,
            background=self.COR_CAMPO,
            foreground=self.COR_TEXTO,
            arrowcolor=self.COR_TEXTO,
        )
        estilo.configure(
            "Horizontal.TProgressbar",
            background=self.COR_DESTAQUE,
            troughcolor=self.COR_CAMPO,
        )

    def _criar_interface(self) -> None:
        """Monta os três painéis principais do aplicativo."""
        barra = ttk.Frame(self, style="Painel.TFrame", padding=10)
        barra.pack(fill="x")
        ttk.Button(
            barra,
            text="Selecionar RAWs",
            style="Destaque.TButton",
            command=self._selecionar_arquivos,
        ).pack(side="left")
        ttk.Button(
            barra,
            text="Adicionar pasta",
            command=self._selecionar_pasta,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            barra,
            text="Escolher saída",
            command=self._escolher_saida,
        ).pack(side="left", padx=(8, 0))
        ttk.Label(
            barra,
            textvariable=self.var_saida,
            style="Secundario.TLabel",
        ).pack(side="left", padx=16)
        ttk.Label(
            barra,
            textvariable=self.var_contagem,
            style="Painel.TLabel",
        ).pack(side="right")

        principal = ttk.Panedwindow(self, orient="horizontal")
        principal.pack(fill="both", expand=True, padx=10, pady=10)

        painel_arquivos = ttk.Frame(principal, style="Painel.TFrame", padding=10)
        painel_preview = ttk.Frame(principal, style="Painel.TFrame", padding=10)
        painel_ajustes = ttk.Frame(principal, style="Painel.TFrame", padding=10)
        principal.add(painel_arquivos, weight=1)
        principal.add(painel_preview, weight=4)
        principal.add(painel_ajustes, weight=2)
        self._criar_painel_arquivos(painel=painel_arquivos)
        self._criar_painel_preview(painel=painel_preview)
        self._criar_painel_ajustes(painel=painel_ajustes)

        rodape = ttk.Frame(self, style="Painel.TFrame", padding=(10, 7))
        rodape.pack(fill="x")
        self.barra_progresso = ttk.Progressbar(rodape, mode="determinate")
        self.barra_progresso.pack(side="right", fill="x", expand=False, ipadx=130)
        ttk.Label(
            rodape,
            textvariable=self.var_status,
            style="Painel.TLabel",
        ).pack(side="left", fill="x", expand=True)

    def _criar_painel_arquivos(self, painel: ttk.Frame) -> None:
        """Cria a lista agrupada por ISO."""
        ttk.Label(
            painel,
            text="FOTOS POR ISO",
            style="Titulo.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        quadro = ttk.Frame(painel, style="Painel.TFrame")
        quadro.pack(fill="both", expand=True)
        self.arvore = ttk.Treeview(
            quadro,
            columns=("iso",),
            displaycolumns=("iso",),
            selectmode="extended",
        )
        self.arvore.heading("#0", text="Arquivo")
        self.arvore.heading("iso", text="ISO")
        self.arvore.column("#0", width=190, minwidth=130)
        self.arvore.column("iso", width=65, anchor="center")
        rolagem = ttk.Scrollbar(
            quadro,
            orient="vertical",
            command=self.arvore.yview,
        )
        self.arvore.configure(yscrollcommand=rolagem.set)
        self.arvore.pack(side="left", fill="both", expand=True)
        rolagem.pack(side="right", fill="y")
        self.arvore.bind("<<TreeviewSelect>>", self._selecionar_na_arvore)
        ttk.Button(
            painel,
            text="Remover selecionadas",
            command=self._remover_selecionadas,
        ).pack(fill="x", pady=(8, 0))

    def _criar_painel_preview(self, painel: ttk.Frame) -> None:
        """Cria a comparação lado a lado do preview."""
        cabecalho = ttk.Frame(painel, style="Painel.TFrame")
        cabecalho.pack(fill="x", pady=(0, 8))
        self.rotulo_arquivo = ttk.Label(
            cabecalho,
            text="Nenhuma foto selecionada",
            style="Titulo.TLabel",
        )
        self.rotulo_arquivo.pack(side="left")
        self.rotulo_iso = ttk.Label(
            cabecalho,
            text="",
            style="Secundario.TLabel",
        )
        self.rotulo_iso.pack(side="right")

        comparacao = ttk.Panedwindow(painel, orient="horizontal")
        comparacao.pack(fill="both", expand=True)
        quadro_original = ttk.Frame(comparacao, style="Painel.TFrame")
        quadro_editada = ttk.Frame(comparacao, style="Painel.TFrame")
        comparacao.add(quadro_original, weight=1)
        comparacao.add(quadro_editada, weight=1)
        ttk.Label(
            quadro_original,
            text="ORIGINAL REVELADO",
            style="Secundario.TLabel",
        ).pack(pady=(0, 6))
        ttk.Label(
            quadro_editada,
            text="PREVIEW DOS AJUSTES",
            style="Secundario.TLabel",
        ).pack(pady=(0, 6))
        self.preview_original = tk.Label(
            quadro_original,
            bg="#0d0e10",
            fg=self.COR_SECUNDARIA,
            text="Selecione uma foto",
        )
        self.preview_original.pack(fill="both", expand=True, padx=(0, 4))
        self.preview_editada = tk.Label(
            quadro_editada,
            bg="#0d0e10",
            fg=self.COR_SECUNDARIA,
            text="Os ajustes aparecerão aqui",
        )
        self.preview_editada.pack(fill="both", expand=True, padx=(4, 0))

        navegacao = ttk.Frame(painel, style="Painel.TFrame")
        navegacao.pack(fill="x", pady=(8, 0))
        ttk.Button(
            navegacao,
            text="← Anterior",
            command=lambda: self._navegar(delta=-1),
        ).pack(side="left")
        ttk.Button(
            navegacao,
            text="Próxima →",
            command=lambda: self._navegar(delta=1),
        ).pack(side="left", padx=8)
        ttk.Button(
            navegacao,
            text="Atualizar preview",
            command=self._agendar_preview_imediato,
        ).pack(side="right")

    def _criar_painel_ajustes(self, painel: ttk.Frame) -> None:
        """Cria presets, controles manuais e opções de exportação."""
        canvas = tk.Canvas(
            painel,
            bg=self.COR_PAINEL,
            highlightthickness=0,
        )
        rolagem = ttk.Scrollbar(painel, orient="vertical", command=canvas.yview)
        conteudo = ttk.Frame(canvas, style="Painel.TFrame")
        conteudo.bind(
            "<Configure>",
            lambda evento: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        janela = canvas.create_window((0, 0), window=conteudo, anchor="nw")
        canvas.bind(
            "<Configure>",
            lambda evento: canvas.itemconfigure(janela, width=evento.width),
        )
        canvas.configure(yscrollcommand=rolagem.set)
        canvas.pack(side="left", fill="both", expand=True)
        rolagem.pack(side="right", fill="y")

        ttk.Label(conteudo, text="PRESETS", style="Titulo.TLabel").pack(anchor="w")
        seletor = ttk.Combobox(
            conteudo,
            textvariable=self.var_preset,
            values=list(AJUSTES_PADRAO),
            state="readonly",
        )
        seletor.pack(fill="x", pady=(7, 12))
        seletor.bind("<<ComboboxSelected>>", self._preset_alterado)

        ttk.Label(
            conteudo,
            text="AJUSTES MANUAIS",
            style="Titulo.TLabel",
        ).pack(anchor="w", pady=(0, 5))
        self._criar_controle(
            painel=conteudo,
            titulo="Exposição",
            variavel=self.var_exposicao,
            minimo=-2.0,
            maximo=2.0,
            resolucao=0.05,
        )
        for titulo, variavel, minimo, maximo in (
            ("Contraste", self.var_contraste, -50, 50),
            ("Realces", self.var_realces, -100, 100),
            ("Sombras", self.var_sombras, -100, 100),
            ("Saturação", self.var_saturacao, -100, 100),
            ("Temperatura", self.var_temperatura, -100, 100),
            ("Redução de ruído", self.var_ruido, 0, 100),
            ("Nitidez", self.var_nitidez, 0, 100),
        ):
            self._criar_controle(
                painel=conteudo,
                titulo=titulo,
                variavel=variavel,
                minimo=minimo,
                maximo=maximo,
                resolucao=1,
            )

        ttk.Button(
            conteudo,
            text="Restaurar preset desta foto",
            command=self._restaurar_preset,
        ).pack(fill="x", pady=(8, 4))
        ttk.Button(
            conteudo,
            text="Copiar para fotos selecionadas",
            command=self._copiar_para_selecionadas,
        ).pack(fill="x", pady=4)
        ttk.Button(
            conteudo,
            text="Aplicar estes ajustes a todas",
            command=self._copiar_para_todas,
        ).pack(fill="x", pady=4)

        ttk.Separator(conteudo).pack(fill="x", pady=14)
        ttk.Label(
            conteudo,
            text="MÁSCARA LOCAL",
            style="Titulo.TLabel",
        ).pack(anchor="w")
        ttk.Label(
            conteudo,
            textvariable=self.var_status_mascara,
            style="Secundario.TLabel",
            wraplength=270,
        ).pack(fill="x", pady=(5, 7))
        ttk.Button(
            conteudo,
            text="Editar máscara com pincel ou contorno",
            command=self._abrir_editor_mascara,
        ).pack(fill="x", pady=3)
        ttk.Button(
            conteudo,
            text="Remover máscara desta foto",
            command=self._remover_mascara_atual,
        ).pack(fill="x", pady=3)

        ttk.Separator(conteudo).pack(fill="x", pady=14)
        ttk.Label(
            conteudo,
            text="EXPORTAÇÃO",
            style="Titulo.TLabel",
        ).pack(anchor="w")
        linha_formato = ttk.Frame(conteudo, style="Painel.TFrame")
        linha_formato.pack(fill="x", pady=(8, 3))
        ttk.Label(
            linha_formato,
            text="Formato",
            style="Painel.TLabel",
        ).pack(side="left")
        ttk.Combobox(
            linha_formato,
            textvariable=self.var_formato,
            values=("JPEG", "PNG"),
            state="readonly",
            width=8,
        ).pack(side="right")
        ttk.Label(
            conteudo,
            text="JPEG sempre em qualidade excelente (98, cores 4:4:4).",
            style="Secundario.TLabel",
            wraplength=270,
        ).pack(fill="x", pady=(6, 2))
        ttk.Button(
            conteudo,
            text="Exportar selecionadas",
            command=self._exportar_selecionadas,
        ).pack(fill="x", pady=(10, 4))
        ttk.Button(
            conteudo,
            text="Exportar todas",
            style="Destaque.TButton",
            command=self._exportar_todas,
        ).pack(fill="x", pady=4)
        ttk.Button(
            conteudo,
            text="Cancelar exportação",
            command=self._solicitar_cancelamento,
        ).pack(fill="x", pady=4)

    def _criar_controle(
        self,
        painel: ttk.Frame,
        titulo: str,
        variavel: tk.Variable,
        minimo: float,
        maximo: float,
        resolucao: float,
        altera_preview: bool = True,
    ) -> None:
        """Cria um controle deslizante com valor numérico."""
        linha = ttk.Frame(painel, style="Painel.TFrame")
        linha.pack(fill="x", pady=3)
        ttk.Label(linha, text=titulo, style="Painel.TLabel").pack(anchor="w")
        escala = tk.Scale(
            linha,
            variable=variavel,
            from_=minimo,
            to=maximo,
            resolution=resolucao,
            orient="horizontal",
            showvalue=True,
            bg=self.COR_PAINEL,
            fg=self.COR_TEXTO,
            activebackground=self.COR_DESTAQUE,
            highlightthickness=0,
            troughcolor=self.COR_CAMPO,
            command=(
                self._controle_alterado
                if altera_preview
                else None
            ),
        )
        escala.pack(fill="x")

    def _selecionar_arquivos(self) -> None:
        """Abre a seleção de múltiplos arquivos RAW."""
        formatos = " ".join(f"*{extensao}" for extensao in EXTENSOES_SUPORTADAS)
        nomes = filedialog.askopenfilenames(
            title="Selecione os arquivos RAW",
            filetypes=(("Arquivos RAW", formatos), ("Todos os arquivos", "*.*")),
        )
        if nomes:
            self._analisar_arquivos(caminhos=[Path(nome) for nome in nomes])

    def _selecionar_pasta(self) -> None:
        """Carrega todos os RAWs de uma pasta escolhida."""
        nome = filedialog.askdirectory(title="Selecione uma pasta com arquivos RAW")
        if not nome:
            return
        pasta = Path(nome)
        caminhos = sorted(
            caminho
            for caminho in pasta.iterdir()
            if caminho.is_file() and caminho.suffix.lower() in EXTENSOES_SUPORTADAS
        )
        if not caminhos:
            messagebox.showinfo("Editor RAW", "Nenhum arquivo RAW foi encontrado.")
            return
        self._analisar_arquivos(caminhos=caminhos)

    def _analisar_arquivos(self, caminhos: list[Path]) -> None:
        """Lê o ISO dos arquivos em segundo plano."""
        novos = [caminho for caminho in caminhos if caminho not in self._fotos]
        if not novos:
            self.var_status.set("Essas fotos já estão no projeto.")
            return
        self.var_status.set(f"Analisando {len(novos)} arquivo(s)…")

        def trabalho() -> list[FotoProjeto]:
            return [
                FotoProjeto(caminho=caminho, iso=obter_iso(caminho=caminho))
                for caminho in novos
            ]

        futuro = self._executor.submit(trabalho)
        futuro.add_done_callback(
            lambda tarefa: self._enfileirar_interface(
                self._analise_concluida,
                tarefa,
            ),
        )

    def _analise_concluida(self, futuro: Future[list[FotoProjeto]]) -> None:
        """Adiciona à interface as fotos analisadas."""
        try:
            fotos = futuro.result()
        except Exception as excecao:
            logger.exception("[IMPORTACAO] Falha ao analisar arquivos")
            messagebox.showerror("Falha ao importar", str(excecao))
            self.var_status.set("Falha ao analisar os arquivos.")
            return
        for foto in fotos:
            self._fotos[foto.caminho] = foto
            nome_preset = preset_recomendado(iso=foto.iso)
            self._ajustes[foto.caminho] = AJUSTES_PADRAO[nome_preset]
        self._reconstruir_arvore()
        self.var_contagem.set(f"{len(self._fotos)} fotos")
        self.var_status.set(
            f"{len(fotos)} foto(s) adicionada(s). Selecione uma para editar.",
        )
        if self._foto_atual is None and fotos:
            self._selecionar_caminho(caminho=fotos[0].caminho)

    def _reconstruir_arvore(self) -> None:
        """Recria a árvore mantendo o agrupamento por faixa de ISO."""
        for item in self.arvore.get_children():
            self.arvore.delete(item)
        self._item_para_caminho.clear()
        ordem = (
            "ISO baixo (até 800)",
            "ISO médio (801–1600)",
            "ISO alto (1601–3200)",
            "ISO muito alto (acima de 3200)",
            "ISO não identificado",
        )
        grupos: dict[str, list[FotoProjeto]] = {nome: [] for nome in ordem}
        for foto in self._fotos.values():
            grupos[faixa_iso(iso=foto.iso)].append(foto)
        for nome_grupo in ordem:
            fotos = sorted(grupos[nome_grupo], key=lambda item: item.caminho.name.lower())
            if not fotos:
                continue
            grupo = self.arvore.insert(
                "",
                "end",
                text=f"{nome_grupo} ({len(fotos)})",
                values=("",),
                open=True,
            )
            for foto in fotos:
                item = self.arvore.insert(
                    grupo,
                    "end",
                    text=foto.caminho.name,
                    values=(foto.iso or "—",),
                )
                self._item_para_caminho[item] = foto.caminho

    def _selecionar_na_arvore(self, _evento: tk.Event[tk.Misc]) -> None:
        """Carrega a primeira foto real da seleção."""
        for item in self.arvore.selection():
            caminho = self._item_para_caminho.get(item)
            if caminho is not None and caminho != self._foto_atual:
                self._abrir_foto(caminho=caminho)
                return

    def _selecionar_caminho(self, caminho: Path) -> None:
        """Seleciona visualmente uma foto pelo caminho."""
        for item, caminho_item in self._item_para_caminho.items():
            if caminho_item == caminho:
                self.arvore.selection_set(item)
                self.arvore.focus(item)
                self.arvore.see(item)
                self._abrir_foto(caminho=caminho)
                return

    def _abrir_foto(self, caminho: Path) -> None:
        """Torna uma foto atual e carrega seus ajustes."""
        self._foto_atual = caminho
        foto = self._fotos[caminho]
        self.rotulo_arquivo.configure(text=caminho.name)
        self.rotulo_iso.configure(
            text=f"ISO {foto.iso or 'não identificado'} · {faixa_iso(iso=foto.iso)}",
        )
        self._carregar_controles(ajustes=self._ajustes[caminho])
        self._atualizar_status_mascara()
        self._agendar_preview_imediato()

    def _carregar_controles(self, ajustes: AjustesFoto) -> None:
        """Preenche os controles sem disparar previews intermediários."""
        self._carregando_controles = True
        self.var_preset.set(ajustes.preset)
        self.var_exposicao.set(ajustes.exposicao)
        self.var_contraste.set(ajustes.contraste)
        self.var_realces.set(ajustes.realces)
        self.var_sombras.set(ajustes.sombras)
        self.var_saturacao.set(ajustes.saturacao)
        self.var_temperatura.set(ajustes.temperatura)
        self.var_ruido.set(ajustes.reducao_ruido)
        self.var_nitidez.set(ajustes.nitidez)
        self._carregando_controles = False

    def _ler_controles(self) -> AjustesFoto:
        """Converte os valores da interface em ajustes imutáveis."""
        return AjustesFoto(
            preset=self.var_preset.get(),
            exposicao=float(self.var_exposicao.get()),
            contraste=int(self.var_contraste.get()),
            realces=int(self.var_realces.get()),
            sombras=int(self.var_sombras.get()),
            saturacao=int(self.var_saturacao.get()),
            temperatura=int(self.var_temperatura.get()),
            reducao_ruido=int(self.var_ruido.get()),
            nitidez=int(self.var_nitidez.get()),
        )

    def _preset_alterado(self, _evento: tk.Event[tk.Misc]) -> None:
        """Aplica o preset escolhido somente à foto atual."""
        nome = self.var_preset.get()
        ajustes = AJUSTES_PADRAO[nome]
        self._carregar_controles(ajustes=ajustes)
        if self._foto_atual is not None:
            self._ajustes[self._foto_atual] = ajustes
            self._agendar_preview()

    def _controle_alterado(self, _valor: str) -> None:
        """Registra um ajuste manual e agenda um novo preview."""
        if self._carregando_controles or self._foto_atual is None:
            return
        ajustes = self._ler_controles().copiar(preset="Personalizado")
        self.var_preset.set("Personalizado")
        self._ajustes[self._foto_atual] = ajustes
        self._agendar_preview()

    def _restaurar_preset(self) -> None:
        """Restaura o preset sugerido para a foto atual."""
        if self._foto_atual is None:
            return
        iso = self._fotos[self._foto_atual].iso
        nome = preset_recomendado(iso=iso)
        ajustes = AJUSTES_PADRAO[nome]
        self._ajustes[self._foto_atual] = ajustes
        self._carregar_controles(ajustes=ajustes)
        self._agendar_preview_imediato()

    def _abrir_editor_mascara(self) -> None:
        """Abre o editor de máscara para a fotografia atual."""
        if self._foto_atual is None:
            messagebox.showinfo("Máscara local", "Selecione uma foto primeiro.")
            return
        imagem = self._cache_preview.get(self._foto_atual)
        if imagem is None:
            self.var_status.set("Aguarde o preview terminar antes de editar a máscara.")
            self._agendar_preview_imediato()
            return
        ajustes = self._ajustes_mascara.get(
            self._foto_atual,
            AjustesMascara(),
        )
        EditorMascara(
            parent=self,
            imagem=imagem,
            mascara=self._mascaras.get(self._foto_atual),
            ajustes=ajustes,
            ao_confirmar=self._salvar_mascara_atual,
        )

    def _salvar_mascara_atual(
        self,
        mascara: Image.Image,
        ajustes: AjustesMascara,
    ) -> None:
        """Guarda a máscara da foto atual e atualiza o preview."""
        if self._foto_atual is None:
            return
        self._mascaras[self._foto_atual] = mascara
        self._ajustes_mascara[self._foto_atual] = ajustes
        self._atualizar_status_mascara()
        self._agendar_preview_imediato()

    def _remover_mascara_atual(self) -> None:
        """Desativa e remove a máscara da fotografia atual."""
        if self._foto_atual is None:
            return
        self._mascaras.pop(self._foto_atual, None)
        self._ajustes_mascara.pop(self._foto_atual, None)
        self._atualizar_status_mascara()
        self._agendar_preview_imediato()

    def _atualizar_status_mascara(self) -> None:
        """Mostra se a foto atual possui efeito local."""
        if self._foto_atual is None or self._foto_atual not in self._mascaras:
            self.var_status_mascara.set("Nenhuma máscara nesta foto")
            return
        ajustes = self._ajustes_mascara[self._foto_atual]
        self.var_status_mascara.set(f"Ativa: {ajustes.efeito}")

    def _agendar_preview(self) -> None:
        """Evita recalcular enquanto o usuário ainda move um controle."""
        if self._temporizador_preview is not None:
            self.after_cancel(self._temporizador_preview)
        self._temporizador_preview = self.after(320, self._iniciar_preview)

    def _agendar_preview_imediato(self) -> None:
        """Solicita atualização imediata do preview."""
        if self._temporizador_preview is not None:
            self.after_cancel(self._temporizador_preview)
        self._temporizador_preview = None
        self._iniciar_preview()

    def _iniciar_preview(self) -> None:
        """Processa o preview atual fora da interface."""
        self._temporizador_preview = None
        if self._foto_atual is None:
            return
        caminho = self._foto_atual
        foto = self._fotos[caminho]
        ajustes = self._ajustes[caminho]
        mascara = self._mascaras.get(caminho)
        mascara_trabalho = mascara.copy() if mascara is not None else None
        ajustes_mascara = self._ajustes_mascara.get(caminho)
        self._geracao_preview += 1
        geracao = self._geracao_preview
        self.var_status.set(f"Gerando preview de {caminho.name}…")
        base_cache = self._cache_preview.get(caminho)
        tamanho_preview = self._tamanho_preview()

        def trabalho() -> tuple[Image.Image, Image.Image, Image.Image]:
            base = (
                base_cache.copy()
                if base_cache is not None
                else revelar_raw(caminho=caminho, iso=foto.iso, preview=True)
            )
            editada = aplicar_edicao_completa(
                imagem=base,
                ajustes=ajustes,
                iso=foto.iso,
                mascara=mascara_trabalho,
                ajustes_mascara=ajustes_mascara,
            )
            original_exibicao = base.copy()
            editada_exibicao = editada.copy()
            original_exibicao.thumbnail(tamanho_preview, Image.Resampling.LANCZOS)
            editada_exibicao.thumbnail(tamanho_preview, Image.Resampling.LANCZOS)
            return base, original_exibicao, editada_exibicao

        futuro = self._executor.submit(trabalho)
        futuro.add_done_callback(
            lambda tarefa: self._enfileirar_interface(
                self._preview_concluido,
                tarefa,
                caminho,
                geracao,
            ),
        )

    def _tamanho_preview(self) -> tuple[int, int]:
        """Calcula um tamanho seguro para cada lado da comparação."""
        largura = max(360, self.preview_editada.winfo_width() - 16)
        altura = max(460, self.preview_editada.winfo_height() - 16)
        return largura, altura

    def _preview_concluido(
        self,
        futuro: Future[tuple[Image.Image, Image.Image, Image.Image]],
        caminho: Path,
        geracao: int,
    ) -> None:
        """Mostra o preview se ele ainda corresponde à foto atual."""
        try:
            base, original, editada = futuro.result()
        except Exception as excecao:
            logger.exception("[PREVIEW] Falha ao processar %s", caminho.name)
            if caminho == self._foto_atual:
                self.var_status.set(f"Falha no preview: {excecao}")
            return
        self._guardar_cache(caminho=caminho, imagem=base)
        if caminho != self._foto_atual or geracao != self._geracao_preview:
            return
        self._imagem_tk_original = ImageTk.PhotoImage(original)
        self._imagem_tk_editada = ImageTk.PhotoImage(editada)
        self.preview_original.configure(image=self._imagem_tk_original, text="")
        self.preview_editada.configure(image=self._imagem_tk_editada, text="")
        self.var_status.set("Preview atualizado. Nenhuma alteração foi salva no RAW.")

    def _guardar_cache(self, caminho: Path, imagem: Image.Image) -> None:
        """Mantém poucas revelações recentes em memória."""
        self._cache_preview[caminho] = imagem
        self._cache_preview.move_to_end(caminho)
        while len(self._cache_preview) > 4:
            self._cache_preview.popitem(last=False)

    def _caminhos_selecionados(self) -> list[Path]:
        """Retorna somente fotos reais selecionadas na árvore."""
        return [
            self._item_para_caminho[item]
            for item in self.arvore.selection()
            if item in self._item_para_caminho
        ]

    def _copiar_para_selecionadas(self) -> None:
        """Copia os ajustes atuais para a seleção múltipla."""
        if self._foto_atual is None:
            return
        caminhos = self._caminhos_selecionados()
        if not caminhos:
            caminhos = [self._foto_atual]
        ajustes = self._ajustes[self._foto_atual]
        for caminho in caminhos:
            self._ajustes[caminho] = ajustes
        self.var_status.set(f"Ajustes copiados para {len(caminhos)} foto(s).")

    def _copiar_para_todas(self) -> None:
        """Copia os ajustes atuais para todas as fotos carregadas."""
        if self._foto_atual is None or not self._fotos:
            return
        ajustes = self._ajustes[self._foto_atual]
        for caminho in self._fotos:
            self._ajustes[caminho] = ajustes
        self.var_status.set(f"Ajustes copiados para todas as {len(self._fotos)} fotos.")

    def _navegar(self, delta: int) -> None:
        """Vai para a foto anterior ou seguinte."""
        if not self._fotos:
            return
        caminhos = sorted(self._fotos, key=lambda item: item.name.lower())
        if self._foto_atual not in caminhos:
            indice = 0
        else:
            indice = (caminhos.index(self._foto_atual) + delta) % len(caminhos)
        self._selecionar_caminho(caminho=caminhos[indice])

    def _remover_selecionadas(self) -> None:
        """Remove fotos do projeto sem apagar arquivos do computador."""
        caminhos = self._caminhos_selecionados()
        if not caminhos:
            return
        for caminho in caminhos:
            self._fotos.pop(caminho, None)
            self._ajustes.pop(caminho, None)
            self._mascaras.pop(caminho, None)
            self._ajustes_mascara.pop(caminho, None)
            self._cache_preview.pop(caminho, None)
        if self._foto_atual in caminhos:
            self._foto_atual = None
            self.preview_original.configure(image="", text="Selecione uma foto")
            self.preview_editada.configure(image="", text="Os ajustes aparecerão aqui")
        self._reconstruir_arvore()
        self.var_contagem.set(f"{len(self._fotos)} fotos")
        self.var_status.set(
            f"{len(caminhos)} foto(s) removida(s) do projeto; nenhum arquivo foi apagado.",
        )

    def _escolher_saida(self) -> None:
        """Escolhe a pasta que receberá uma subpasta de exportação."""
        nome = filedialog.askdirectory(title="Escolha onde criar a pasta de exportação")
        if not nome:
            return
        self._pasta_base_saida = Path(nome)
        self._pasta_sessao_saida = None
        self.var_saida.set(f"Saída: {self._pasta_base_saida}")

    def _obter_pasta_sessao(self) -> Path | None:
        """Cria uma pasta exclusiva para a sessão de exportação."""
        if self._pasta_base_saida is None:
            self._escolher_saida()
        if self._pasta_base_saida is None:
            return None
        if self._pasta_sessao_saida is None:
            horario = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._pasta_sessao_saida = self._pasta_base_saida / f"EditorRAW_{horario}"
            self._pasta_sessao_saida.mkdir(parents=True, exist_ok=True)
            self.var_saida.set(f"Saída: {self._pasta_sessao_saida}")
        return self._pasta_sessao_saida

    def _exportar_selecionadas(self) -> None:
        """Exporta somente as fotos selecionadas."""
        caminhos = self._caminhos_selecionados()
        if not caminhos and self._foto_atual is not None:
            caminhos = [self._foto_atual]
        self._iniciar_exportacao(caminhos=caminhos)

    def _exportar_todas(self) -> None:
        """Exporta todas as fotos carregadas."""
        self._iniciar_exportacao(
            caminhos=sorted(self._fotos, key=lambda item: item.name.lower()),
        )

    def _iniciar_exportacao(self, caminhos: list[Path]) -> None:
        """Inicia exportação sequencial em segundo plano."""
        if not caminhos:
            messagebox.showinfo("Editor RAW", "Nenhuma foto foi selecionada.")
            return
        pasta = self._obter_pasta_sessao()
        if pasta is None:
            return
        formato = self.var_formato.get()
        self._cancelar_exportacao.clear()
        self.barra_progresso.configure(maximum=len(caminhos), value=0)
        self.var_status.set(f"Exportando 0 de {len(caminhos)}…")

        def trabalho() -> tuple[list[Path], list[tuple[Path, str]], bool]:
            concluidas: list[Path] = []
            falhas: list[tuple[Path, str]] = []
            for indice, caminho in enumerate(caminhos, start=1):
                if self._cancelar_exportacao.is_set():
                    return concluidas, falhas, True
                try:
                    destino = exportar_foto(
                        origem=caminho,
                        pasta_destino=pasta,
                        ajustes=self._ajustes[caminho],
                        iso=self._fotos[caminho].iso,
                        formato=formato,
                        mascara=self._mascaras.get(caminho),
                        ajustes_mascara=self._ajustes_mascara.get(caminho),
                    )
                    concluidas.append(destino)
                except Exception as excecao:
                    logger.exception("[EXPORTACAO] Falha em %s", caminho.name)
                    falhas.append((caminho, str(excecao)))
                self._enfileirar_interface(
                    self._atualizar_progresso,
                    indice,
                    len(caminhos),
                    caminho.name,
                )
            return concluidas, falhas, False

        futuro = self._executor.submit(trabalho)
        futuro.add_done_callback(
            lambda tarefa: self._enfileirar_interface(
                self._exportacao_concluida,
                tarefa,
                pasta,
            ),
        )

    def _atualizar_progresso(self, atual: int, total: int, nome: str) -> None:
        """Atualiza a barra durante a exportação."""
        self.barra_progresso.configure(value=atual)
        self.var_status.set(f"Exportando {atual} de {total}: {nome}")

    def _exportacao_concluida(
        self,
        futuro: Future[tuple[list[Path], list[tuple[Path, str]], bool]],
        pasta: Path,
    ) -> None:
        """Informa o resultado da exportação."""
        try:
            concluidas, falhas, cancelada = futuro.result()
        except Exception as excecao:
            logger.exception("[EXPORTACAO] Falha geral")
            messagebox.showerror("Falha na exportação", str(excecao))
            return
        if cancelada:
            self.var_status.set(
                f"Exportação cancelada após {len(concluidas)} arquivo(s).",
            )
            return
        self.var_status.set(
            f"Exportação concluída: {len(concluidas)} arquivo(s), {len(falhas)} falha(s).",
        )
        mensagem = f"{len(concluidas)} foto(s) salva(s) em:\n{pasta}"
        if falhas:
            mensagem += f"\n\n{len(falhas)} arquivo(s) apresentaram erro."
        messagebox.showinfo("Exportação concluída", mensagem)

    def _solicitar_cancelamento(self) -> None:
        """Solicita o encerramento seguro da exportação atual."""
        self._cancelar_exportacao.set()
        self.var_status.set("Cancelamento solicitado; terminando a foto atual…")

    def _fechar(self) -> None:
        """Encerra tarefas e fecha o aplicativo."""
        self._encerrando = True
        self._cancelar_exportacao.set()
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def main() -> None:
    """Inicia o Editor RAW."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(message)s",
    )
    aplicativo = AplicativoEditorRaw()
    aplicativo.mainloop()


if __name__ == "__main__":
    main()
