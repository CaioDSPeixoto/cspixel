# Arquitetura do Editor RAW

## Objetivo

Manter o aplicativo simples para desenvolvimento individual, sem misturar interface, regras fotográficas e empacotamento. A arquitetura deve permitir adicionar presets, controles e formatos sem reescrever o programa.

## Visão geral

```text
Usuário
  │
  ▼
app.py ─────────── interface, estado da sessão e tarefas de fundo
  │
  ├── editor_mascara.py ─ ferramentas visuais de seleção local
  ├── efeitos.py ─ nomes estáveis dos efeitos locais
  ├── modelos.py ─ objetos imutáveis compartilhados
  ├── presets.py ─ catálogo declarativo e recomendação por ISO
  └── processamento.py
        ├── leitura de metadados
        ├── revelação RAW
        ├── pipeline de ajustes
        └── exportação segura

build.ps1 ─────── testes, empacotamento e metadados do release
```

## Responsabilidades

| Arquivo | Responsabilidade | Não deve conter |
|---|---|---|
| `app.py` | Componentes visuais, eventos, navegação e coordenação de tarefas | Fórmulas de tratamento de imagem |
| `editor_mascara.py` | Pincel, borracha, contorno e preview da máscara | Revelação RAW e exportação |
| `efeitos.py` | Catálogo estável de efeitos locais | Implementação dos filtros |
| `modelos.py` | Dados imutáveis compartilhados | Acesso a arquivos ou interface |
| `presets.py` | Valores declarativos e recomendação inicial | Código de interface |
| `processamento.py` | Revelação, filtros, exportação e nomes seguros | Widgets ou caixas de diálogo |
| `versao.py` | Versão única do aplicativo | Regras de negócio |
| `build.ps1` | Ambiente, testes, build e metadados | Alterações no código-fonte |

## Fluxo de dados

1. A interface recebe caminhos escolhidos pelo usuário.
2. `processamento.obter_iso()` lê os metadados.
3. `presets.preset_recomendado()` define o ponto de partida.
4. A interface guarda um `AjustesFoto` para cada `FotoProjeto`.
5. O preview revela o RAW em meia resolução e aplica os ajustes em memória.
6. Cada `CamadaMascara` é redimensionada e aplicada na ordem exibida na interface.
7. Cada camada mantém nome, seleção e efeito próprios.
8. A exportação revela novamente em resolução total e reaplica todas as camadas.
9. `nome_destino_seguro()` impede a substituição de uma exportação existente.
10. O RAW nunca é aberto para escrita.

## Concorrência

Revelação e exportação não executam na thread da interface. O `ThreadPoolExecutor` realiza o trabalho pesado e uma fila entrega os resultados à thread principal do Tkinter. Nenhuma tarefa de fundo acessa widgets diretamente. Previews obsoletos são cancelados quando possível. A exportação recebe `ItemExportacao` imutável, evitando que alterações posteriores da interface mudem um lote em andamento.

No editor de máscara, o zoom mantém uma região virtual completa, mas só amplia os pixels visíveis no canvas. Isso evita criar bitmaps gigantes em ampliações de 400%.

## Pontos de extensão

- Novo preset: adicionar uma entrada em `AJUSTES_PADRAO`, em `presets.py`.
- Novo parâmetro fotográfico: adicionar o campo em `AjustesFoto`, implementar a transformação em `processamento.py` e expor o controle em `app.py`.
- Novo formato de exportação: ampliar `exportar_foto()` e o seletor da interface.
- Novo formato RAW: validar suporte do LibRaw e adicionar a extensão em `EXTENSOES_SUPORTADAS`.
- Persistência de projeto: criar um módulo próprio que serialize `FotoProjeto` e `AjustesFoto`; não colocar JSON diretamente em `app.py`.

## Requisitos não funcionais

- Não destrutivo: nunca escrever no arquivo de entrada.
- Responsivo: operações de imagem sempre fora da thread visual.
- Reproduzível: dependências fixadas por versão.
- Testável: regras sem dependência de Tkinter ficam fora da interface.
- Compatível: release atual direcionado a Windows 64 bits e Python 3.12.

## Decisões relacionadas

- [ADR-0001: monólito modular para o aplicativo desktop](adr/0001-monolito-modular.md)
