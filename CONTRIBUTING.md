# Como contribuir com o Editor RAW

O projeto usa uma arquitetura modular pequena. Antes de alterar o código, leia:

- [Arquitetura](docs/ARQUITETURA.md)
- [Processo para criar funcionalidades](docs/CRIANDO_FEATURES.md)
- [Build e publicação](docs/BUILD_E_RELEASE.md)
- [ADR da arquitetura](docs/adr/0001-monolito-modular.md)

## Regra principal

Uma funcionalidade deve ficar na camada responsável por ela. A interface coleta entradas e mostra resultados; regras fotográficas ficam em `processamento.py`; estruturas de dados ficam em `modelos.py`; presets ficam em `presets.py`.

## Validação mínima

Antes de gerar um executável:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\tests -v
```

O `build.ps1` repete automaticamente a validação de sintaxe e os testes. Se qualquer etapa falhar, nenhum release deve ser considerado válido.
