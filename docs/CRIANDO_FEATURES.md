# Processo para criar funcionalidades

## Objetivo

Este é o processo padrão para acrescentar uma funcionalidade sem aumentar acoplamento ou quebrar a edição não destrutiva.

## 1. Descrever o comportamento

Antes de programar, registre:

- problema que será resolvido;
- quem utilizará a funcionalidade;
- entradas e resultado esperado;
- comportamento no preview;
- comportamento na exportação;
- risco para o arquivo original;
- critérios de aceite verificáveis.

Modelo curto:

```markdown
## Funcionalidade

Problema:
Resultado esperado:
Arquivos afetados:
Critérios de aceite:
- [ ] ...
- [ ] ...
```

## 2. Escolher o módulo responsável

| Tipo de mudança | Local principal |
|---|---|
| Novo dado compartilhado | `modelos.py` |
| Novo preset ou recomendação | `presets.py` |
| Novo efeito local | `efeitos.py`, implementação em `processamento.py` |
| Nova ferramenta de máscara | `editor_mascara.py` |
| Algoritmo de imagem ou exportação | `processamento.py` |
| Botão, controle ou navegação | `app.py` |
| Versão do produto | `versao.py` |
| Build e release | `build.ps1` e `docs/BUILD_E_RELEASE.md` |

Quando uma feature precisar de mais de uma camada, implemente primeiro o núcleo testável e conecte a interface por último.

## 3. Implementar em fatias pequenas

1. Adicione ou altere o modelo.
2. Implemente a regra sem interface.
3. Crie testes com imagens sintéticas sempre que possível.
4. Conecte a regra à interface.
5. Teste com um RAW real em preview.
6. Teste uma exportação em resolução total.

Funções públicas devem ter type hints e docstrings em português. Caminhos usam `pathlib.Path`. Presets devem continuar declarativos.

## 4. Testar

Execute:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\tests -v
```

Para mudanças no processamento, valide no mínimo:

- tamanho e modo da imagem preservados;
- valores limitados ao intervalo válido;
- RAW original com tamanho e data de modificação inalterados;
- nome de saída sem sobrescrita;
- preview e exportação visualmente coerentes.

Para mudanças na interface, valide:

- janela continua respondendo durante o processamento;
- troca rápida de foto não mostra preview antigo;
- seleção múltipla não altera fotos fora da seleção;
- cancelamento termina após a foto em andamento.

## 5. Atualizar documentação e versão

- Corrija a documentação afetada; evite duplicar explicações.
- Registre a mudança em `CHANGELOG.md`.
- Atualize `VERSAO_APLICATIVO` em `versao.py` conforme o impacto:
  - correção: `0.1.0` → `0.1.1`;
  - funcionalidade compatível: `0.1.0` → `0.2.0`;
  - mudança incompatível: `0.x` → próxima versão principal quando o produto estabilizar.

## 6. Gerar e verificar o release

Siga [BUILD_E_RELEASE.md](BUILD_E_RELEASE.md). O build só é válido quando sintaxe, testes, empacotamento e teste de abertura passarem.

## Definição de pronto

- [ ] Critérios de aceite atendidos.
- [ ] Código na camada correta.
- [ ] Testes automatizados aprovados.
- [ ] Preview testado com RAW real.
- [ ] Exportação testada sem alterar o original.
- [ ] Documentação e changelog atualizados.
- [ ] Novo executável gerado.
- [ ] `build-info.txt` contém versão e SHA-256 do executável.
