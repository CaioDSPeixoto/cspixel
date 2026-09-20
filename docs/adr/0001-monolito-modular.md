# ADR-0001: Monólito modular para o aplicativo desktop

**Status:** Aceito

**Data:** 2026-09-20

**Decisores:** proprietário do projeto e mantenedor do Editor RAW

## Contexto

O Editor RAW é um aplicativo desktop local, inicialmente mantido por uma pessoa. Ele precisa evoluir com novos presets, algoritmos e controles, mas não possui requisitos de servidor, extensões de terceiros ou equipes independentes. O executável deve continuar simples de gerar e distribuir.

## Decisão

Usar um monólito modular em Python, com módulos explícitos para modelos, presets, processamento, interface, versão e build. As dependências seguem em uma direção: a interface usa o núcleo; o núcleo não conhece Tkinter.

## Opções consideradas

### Opção A: Arquivo único

| Dimensão | Avaliação |
|---|---|
| Complexidade inicial | Baixa |
| Manutenção | Baixa após crescimento |
| Testabilidade | Média/baixa |
| Distribuição | Simples |

**Prós:** mínimo número de arquivos e início rápido.

**Contras:** mistura interface, processamento e estado; aumenta o risco de regressões.

### Opção B: Monólito modular

| Dimensão | Avaliação |
|---|---|
| Complexidade inicial | Baixa/média |
| Manutenção | Alta |
| Testabilidade | Alta |
| Distribuição | Simples |

**Prós:** responsabilidades claras, testes rápidos e um único executável.

**Contras:** exige disciplina para manter os limites entre módulos.

### Opção C: Arquitetura de plugins

| Dimensão | Avaliação |
|---|---|
| Complexidade inicial | Alta |
| Manutenção | Média/alta |
| Testabilidade | Alta |
| Distribuição | Mais complexa |

**Prós:** extensões independentes e carregamento dinâmico.

**Contras:** versionamento de API, descoberta de plugins e tratamento de incompatibilidades sem necessidade atual.

## Análise de trade-offs

O arquivo único é atraente no começo, mas já concentra interface e coordenação. Plugins resolveriam um problema futuro e adicionariam custo imediato. O monólito modular oferece o melhor equilíbrio: preserva o executável único e separa as regras que precisam de testes.

## Consequências

- Novos algoritmos podem ser testados sem abrir a interface.
- Presets podem ser acrescentados de forma declarativa.
- O build continua produzindo um único `.exe`.
- A interface ainda coordena o estado da sessão e pode ser dividida em componentes quando crescer.
- Uma arquitetura de plugins só deverá ser reconsiderada se houver extensões externas ou equipes independentes.

## Itens de ação

1. [x] Separar modelos, presets, processamento e versão.
2. [x] Fixar dependências de build.
3. [x] Documentar o processo de features e release.
4. [ ] Avaliar a separação de painéis da interface quando `app.py` superar a capacidade de manutenção prática.
