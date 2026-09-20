# Build e release do Editor RAW

## Ambiente suportado

- Windows 64 bits.
- Python 3.12 de 64 bits.
- PowerShell.
- Acesso à internet apenas na primeira instalação das dependências.

As versões das bibliotecas estão fixadas em `requirements.txt` para tornar o resultado reproduzível.

## Build padrão

Abra o PowerShell na pasta do projeto e execute:

```powershell
.\build.ps1
```

Quando `python` não apontar para o Python 3.12:

```powershell
.\build.ps1 -Python "C:\caminho\para\python.exe"
```

## O que o script executa

1. Confirma que o executável anterior não está aberto.
2. Cria `.venv`, se necessário.
3. Instala as versões fixadas em `requirements.txt`.
4. Confirma o uso do Python 3.12.
5. Compila os módulos para validar a sintaxe.
6. Executa todos os testes unitários.
7. Gera um executável único e sem console com PyInstaller.
8. Calcula o SHA-256 do artefato.
9. Copia o README e grava `dist/build-info.txt`.

Qualquer falha interrompe o processo; o script não deve anunciar sucesso após erro.

## Artefatos

```text
dist/
├── EditorRAW.exe
├── README.md
└── build-info.txt
```

O diretório `build/`, o arquivo `EditorRAW.spec` e `.venv/` são materiais locais de desenvolvimento. O usuário final precisa apenas do conteúdo de `dist/`.

## Verificação manual do release

1. Abra `dist/EditorRAW.exe`.
2. Importe pelo menos um RAW de ISO baixo e um de ISO alto.
3. Confirme o agrupamento por ISO.
4. Altere um preset e um controle manual.
5. Confirme a comparação original × preview.
6. Exporte uma imagem JPEG.
7. Confira resolução, cor e abertura do arquivo exportado; JPEG deve usar qualidade 98 e cores 4:4:4.
8. Confirme que tamanho e data de modificação do RAW não mudaram.
9. Feche o programa e confira se não ficou um processo `EditorRAW.exe` aberto.

## Versionamento

A versão fica em `versao.py` e deve ser atualizada antes do build. O histórico fica em `CHANGELOG.md`.

## Problemas comuns

### “Acesso negado” ao gerar o executável

Feche todas as instâncias de `EditorRAW.exe`. O Windows impede que o PyInstaller substitua um executável em uso.

### Aviso do Windows SmartScreen

O executável local não possui assinatura digital. Para distribuição pública, assine o artefato com um certificado de assinatura de código antes de publicá-lo.

### Preview funciona, mas a exportação é lenta

O preview usa meia resolução; a exportação revela e trata todos os pixels do RAW. Esse comportamento é intencional.

### Alteração de dependência

Atualize uma biblioteca por vez, execute os testes e faça o teste manual com RAW real. Depois fixe a nova versão em `requirements.txt` e registre a mudança no changelog.
