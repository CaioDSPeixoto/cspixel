# Histórico de versões

Este projeto segue [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## 0.6.0 — 2026-09-20

### Adicionado

- Tela modal durante a exportação com fotografia atual, contador e barra de progresso.
- Cancelamento como única ação disponível enquanto o lote é processado.

### Alterado

- JPEG elevado para qualidade máxima 100, mantendo cores 4:4:4 e perfil sRGB.
- Fechamento do aplicativo bloqueado até a exportação terminar ou ser cancelada.

## 0.5.0 — 2026-09-20

### Adicionado

- Perfil de cor sRGB incorporado às exportações JPEG e PNG.
- Ruff e mypy integrados ao processo obrigatório de build.
- Testes de exportação real, integridade de pixels, perfil de cor e formatos.

### Alterado

- Zoom da máscara renderiza somente a área visível para reduzir o uso de memória.
- Exportação usa uma fotografia imutável dos ajustes e bloqueia execuções simultâneas.
- Previews pendentes são cancelados quando substituídos por uma solicitação nova.
- Interface dividida em componentes menores para facilitar manutenção.
- Preset **Sem ajustes** agora preserva os pixels sem aplicar filtros ocultos.
- Mensagens de erro não expõem detalhes internos da aplicação.

## 0.4.0 — 2026-09-20

### Adicionado

- Múltiplas camadas locais independentes por fotografia.
- Lista de camadas com criação, seleção e edição individual.
- Renomeação e exclusão individual de camadas.
- Aplicação sequencial de todas as camadas no preview e na exportação.

## 0.3.0 — 2026-09-20

### Adicionado

- Indicador de carregamento enquanto o preview ainda está desatualizado.
- Zoom de até 400%, barras de rolagem e movimentação no editor de máscara.

### Alterado

- Área de preview ampliada e atualizada ao redimensionar a janela.
- Nomes dos presets simplificados.
- Rolagem dos ajustes habilitada com a roda do mouse.
- Descrição da exportação adaptada ao formato JPEG ou PNG.
- Título da janela simplificado.

## 0.2.0 — 2026-09-20

### Adicionado

- Editor de máscara não destrutiva por fotografia.
- Pincel para adicionar e borracha para remover áreas.
- Seleção por contorno com preenchimento poligonal.
- Inversão, limpeza, seleção total e suavização de bordas.
- Preview do efeito antes da confirmação.
- Destaque colorido com fundo P&B, P&B local, saturação local e desfoque de fundo.

## 0.1.1 — 2026-09-20

### Alterado

- Removido o controle de qualidade da interface.
- Exportação JPEG fixada em qualidade 98 com subamostragem 4:4:4.
- PNG continua sendo exportado sem perdas.

## 0.1.0 — 2026-09-20

### Adicionado

- Importação múltipla de RAWs.
- Agrupamento por faixa de ISO.
- Presets com recomendação automática.
- Preview lado a lado sem alterar o arquivo original.
- Controles manuais por fotografia.
- Cópia de ajustes para seleção ou lote completo.
- Exportação segura em JPEG e PNG.
- Redução de ruído adaptativa para sombras e ISO alto.
- Build reproduzível para Windows com PyInstaller.
- Documentação de arquitetura, features e release.
