# Editor RAW

Aplicativo Windows para revelar, comparar, ajustar e exportar fotografias RAW sem alterar os arquivos originais.

## Início rápido

Se você recebeu o pacote pronto, abra `dist\EditorRAW.exe`. O executável contém as dependências e não exige uma instalação separada do Python.

Ao baixar o código-fonte pelo GitHub, gere o executável com `build.ps1` conforme a seção **Gerar novamente o executável**.

## O que ele faz

- Abre vários arquivos RAW de uma vez (`CR2`, `CR3`, `NEF`, `ARW`, `DNG`, `ORF`, `RW2` e `RAF`).
- Agrupa as fotos automaticamente por faixa de ISO.
- Sugere um preset inicial conforme o ISO.
- Exibe o original revelado e o resultado editado lado a lado.
- Permite alterar exposição, contraste, realces, sombras, saturação, temperatura, redução de ruído e nitidez.
- Mantém ajustes individuais para cada foto.
- Permite criar máscaras por pincel, borracha ou contorno.
- Aplica preto e branco, saturação ou desfoque somente dentro ou fora da seleção.
- Copia os ajustes da foto atual para uma seleção ou para todas as fotos.
- Exporta em JPEG ou PNG, sempre para uma pasta nova.
- Exporta JPEG sempre em qualidade 98 e cores 4:4:4; PNG permanece sem perdas.
- Nunca altera ou substitui o RAW original.

## Uso

1. Abra `EditorRAW.exe`.
2. Clique em **Selecionar RAWs** ou **Adicionar pasta**.
3. Escolha uma foto na lista à esquerda.
4. Selecione um preset e use os controles manuais.
5. Confira o resultado no painel **Preview dos ajustes**.
6. Use **Copiar para fotos selecionadas** ou **Aplicar estes ajustes a todas**, se desejar.
7. Escolha a pasta de saída.
8. Exporte as fotos selecionadas ou todas.

O programa cria automaticamente uma subpasta com nome semelhante a `EditorRAW_20260920_153000`. Se um nome de imagem já existir, ele acrescenta uma numeração em vez de substituir o arquivo.

## Presets incluídos

- Natural equilibrado
- Retrato suave
- ISO alto — Limpo
- Noite e palco
- Cores vivas
- Preto e branco
- Neutro

## Desenvolvimento

O código segue um monólito modular pequeno:

```text
app.py             interface e coordenação
editor_mascara.py  pincel, borracha e seleção por contorno
efeitos.py         catálogo de efeitos locais
modelos.py         dados compartilhados
presets.py         catálogo de presets
processamento.py   revelação, filtros e exportação
versao.py          versão do produto
tests/             testes automatizados
docs/              decisões e processos
```

Documentos para manutenção:

- [Como contribuir](CONTRIBUTING.md)
- [Arquitetura](docs/ARQUITETURA.md)
- [Criando funcionalidades](docs/CRIANDO_FEATURES.md)
- [Build e release](docs/BUILD_E_RELEASE.md)
- [Histórico de versões](CHANGELOG.md)

## Gerar novamente o executável

Em uma janela do PowerShell aberta nesta pasta, execute:

```powershell
.\build.ps1
```

O script valida sintaxe, executa os testes, gera o executável e registra versão e SHA-256. Os artefatos ficam em `dist\`.

## Observações

- O preview usa meia resolução para responder mais rápido.
- A exportação sempre revela o RAW novamente em resolução total.
- Fotografias de ISO muito alto podem manter alguma granulação para preservar detalhes naturais.
