# Relatório de execução — Correção pós-auditoria do projeto surto-1

**Data:** 12/06/2026
**Plano executado:** `PROMPT_CORRECAO.md` (fases 0–4, recomendações R1–R18 de `AUDITORIA_PROJETO.md`)
**Baseline preservado em:** `D:\surto-1-baseline\` (output pré-existente, output da Fase 0 e versões do ambiente)

---

## 1. Recomendações concluídas × pendentes

| Rec. | Status | Entrega |
|------|--------|---------|
| R1 (P0) | **Concluída** | Deck ATP corrigido, executado de verdade; comparação quantitativa Python×ATP gerada |
| R2 (P0) | **Concluída** | Relatório LaTeX corrigido (seções 02/05/06/07/09, build_notes, macros) e recompilado (24 págs., 0 erros) |
| R3 (P0) | **Concluída** | Validação completa da configuração na construção; typo em `termination` agora é erro ruidoso |
| R4 (P1) | **Concluída** | `scripts/plot_plotly.py` substitui `simulate_direct.py`/`save_images.py`; física única em `src/` |
| R5 (P1) | **Concluída** | Zero caminhos absolutos no código; ATP via `--atp-exe`/env `ATP_EXE` (default documentado) |
| R6 (P1) | **Concluída** | 34 testes pytest (IEC, regressão, energia, convergência, terminação casada, config, CSVs) |
| R7 (P1) | **Concluída** | `run_metadata.json` (config+commit+versões+data) e CSVs para os 4 cenários, incl. low_c/high_c |
| R8 (P2) | **Concluída** | `requirements.txt` completo (plotly, kaleido) e pinado; `matplotlib.colormaps` substitui API deprecada |
| R9 (P2) | **Concluída** | Vão estrutural do T-aberto reportado vazio (não 0,0) e omitido do gráfico com anotação; coluna `I_out` honesta |
| R10 (P2) | **Concluída** | `summary_nodes.csv` + `summary_scalars.csv` (CSV puro); dicionário de dados no README |
| R11 (P2) | **Concluída** | Correntes do modelo T renomeadas `alpha`/`beta` → `i_junction`/`i_out` (código, docstrings, README) |
| R12 (P2) | **Concluída** | `solver_method`/`rtol`/`atol` e `c_scenario_multipliers` na config JSON; `FRONT_COEFF` nomeada; guarda `1e-30` eliminada |
| R13 (P2) | **Concluída** | README "Modelling hypotheses": fonte ideal, T₂ efetivo +5,4%, razão >2 esperada, nó duplicado do T, Radau p/ casos rígidos |
| R14 (P2) | **Concluída** | Procedência declarada: caso didático ilustrativo (README "Input data provenance") |
| R15 (P3) | **Parcial** | `pyproject.toml` (metadados, requires-python, config pytest) e `LICENSE` criados. **Pendente:** instalação editável exigiria renomear `src/`→pacote próprio (decisão de churn adiada, nota no pyproject); texto definitivo da LICENSE é decisão do proprietário (placeholder conservador "todos os direitos reservados") |
| R16 (P3) | **Concluída** | 375 frames PNG + `relatorio.pdf` des-versionados (regeneráveis; comandos documentados); repo sem blobs novos |
| R17 (P3) | **Concluída** | README reescrito: estrutura, fluxo ATP com pré-requisitos e histórico, reprodução das figuras do relatório |
| R18 (P3) | **Parcial** | Casamento de nós por igualdade exata em `run_atp.py` ✔. **Pendente:** conversão `print`→`logging` (mecânica, adiada deliberadamente após a suíte ficar verde — P3 opcional; prints atuais são linhas curtas de progresso) |

---

## 2. Validação ATP — executada de fato

O deck `surto_bobina.atp` foi **corrigido e executado** pelo `tpbigG.exe` em 12/06/2026 (não é mais a validação fictícia do achado A1). Três defeitos corrigidos:

1. **Colunas** dos cartões de ramo realinhadas ao formato fixo (causa do KILL=6 original);
2. **Unidade de L**: com `XOPT=0` o ATP lê **mH** — o valor antigo (`5.E-4` pretendendo H) seria lido 1000× menor; corrigido para `0.5`;
3. **Fonte**: tipo 14 (cosseno) → **tipo 15** (surto dupla exponencial) com expoentes negativos; além de `ICAT=1` (sem ele o GNU ATP descarta o `.pl4` — comportamento observado e documentado) e `IPLOT=1` (grade do `.pl4` = grade do Python).

A interpretação do cartão tipo 15 foi **comprovada** por duas vias independentes: eco do `.lis` (`Source. 1.04E+03 -1.39E+04 -2.50E+06`) e V(N0) do `.pl4` coincidindo com a expressão analítica (desvio máx. 0,0 V). Foi necessário também escrever um parser para o formato **PISA/C-like** do GNU ATP (`run_atp.py::_attempt_pisa`), validado por tamanho de arquivo e uniformidade do eixo de tempo.

### Comparação quantitativa (janela 200 µs, nós N0–N20)

| Nó | Pico Python [V] | Pico ATP [V] | Dif. pico | max\|err\| 0–30 µs | max\|err\| 0–200 µs |
|----|----------------:|-------------:|----------:|-------------------:|--------------------:|
| N0 (0%) | 1000,00 | 999,97 | +0,003 % | 0,03 V | 0,03 V |
| N5 (25%) | 1952,70 | 1953,25 | −0,028 % | 8,26 V | 53,4 V |
| N10 (50%) | 1995,65 | 1995,50 | +0,008 % | 8,22 V | 61,6 V |
| N15 (75%) | 2025,79 | 2026,06 | −0,013 % | 10,77 V | 57,3 V |
| N20 (100%) | 2039,31 | 2039,43 | −0,006 % | 10,78 V | 90,7 V |

RMS (janela completa): 0,01–18,9 V conforme o nó. **Leitura de engenharia:** picos (grandeza de coordenação de isolamento) concordam em ≤ 0,03 %; o erro pontual na janela dielétrica (0–30 µs) é ≤ 1,1 % de 1 kV; as diferenças tardias são deriva de fase trapezoidal (ATP) × RK45 adaptativo, não divergência de modelo. Artefatos: `output/atp/comparacao_python_atp.{csv,png}`, reproduzíveis com `python scripts/compare_python_atp.py`; figura e tabela incorporadas à Seção 6 do relatório LaTeX.

Evidências (falha original de abril + execução bem-sucedida) preservadas e versionadas em `docs/evidencias_atp_falha/`.

---

## 3. Regressão numérica — antes × depois

| Grandeza | Baseline (Fase 0) | Final | Verificação |
|----------|------------------:|------:|-------------|
| Vpk_in (Pi) | 1000,0000 V | 1000,0000 V | idêntico |
| Vpk_out (Pi) | 2039,3086 V | 2039,3086 V | idêntico (diff binário dos escalares vazio) |
| transfer_ratio | 2,039309 | 2,039309 | idêntico |
| Vpk_out (T) | 2039,3090 V | 2039,3090 V | fixado em teste de regressão |

Nenhuma correção alterou a física do caso padrão — conforme o guardrail, nada foi alterado silenciosamente.

---

## 4. Verificação final

| Item | Resultado |
|------|-----------|
| `python -m pytest` | **34 passed** (7,4 s) |
| `python main.py` | exit 0, **zero warnings/deprecações**, 4 cenários com CSV+metadados |
| `scripts/plot_plotly.py` | HTML+2 PNGs com rótulo de procedência "simulação Python" |
| `run_atp.py` (ponta a ponta) | ATP executado, `.pl4` lido (PISA), HTML "resultados ATP" gerado |
| `scripts/compare_python_atp.py` | CSV+figura da validação cruzada |
| LaTeX | `latexmk -pdf` OK — 24 páginas, 0 erros, 0 referências indefinidas |
| Caminhos absolutos em `.py` | apenas o default documentado/sobrescritível de `run_atp.py` |
| `git status` | árvore limpa |

---

## 5. Commits criados (10)

```
e1e5cb7 R1: corrige deck ATP (colunas, L em mH, fonte tipo 15) e valida Python x ATP
18519cb Adiciona auditoria tecnica e prompt executavel de correcao
1f5367a R2: relatorio reflete deck ATP corrigido e validacao quantitativa real
6a24e22 R3: valida configuracao na construcao (elimina erro silencioso A5)
204395a R4+R5: deduplica modelo (scripts consomem src/) e elimina caminhos absolutos
4cfcb68 R8-R10: dependencias pinadas, API matplotlib atual, CSVs com semantica honesta
8d79234 R6: suite pytest (34 testes)
9722188 R7+R11+R12: procedencia das saidas, renomeia correntes do modelo T, constante nomeada
611aac4 R13+R14+R17: README — hipoteses explicitas, procedencia, dicionario de dados
bed28ab R15+R16: pyproject/LICENSE e remove 375 frames PNG do versionamento
```

**Sem push** — revisão do proprietário antes de publicar, conforme o guardrail.

---

## 6. Desvios em relação ao prompt (com justificativa)

1. **Ordem R8–R10 antes do commit de R6**: os testes de CSV asseram o formato novo do summary; implementar R10 antes manteve cada commit com a suíte verde. Conteúdo integral entregue.
2. **`relatorio.pdf` des-versionado já no commit R2** (antecipando parte do R16) para não gravar um segundo blob de 18 MB no histórico.
3. **R15 parcial**: instalação editável adiada — empacotar um pacote chamado `src` é má prática e renomeá-lo agora churnaria todos os imports; registrado como melhoria futura no próprio `pyproject.toml`. LICENSE como placeholder conservador (decisão jurídica é do proprietário).
4. **R18 parcial**: `print`→`logging` adiado (P3 opcional) para não introduzir risco depois da suíte verde; o item de risco real do R18 (casamento de nós por substring) foi corrigido.
5. **Descoberta não prevista no prompt**: além dos 3 defeitos conhecidos do deck, o GNU ATP exige `ICAT=1` para persistir o `.pl4` e emite a listagem no stdout (sem arquivo `.lis`) — ambos tratados e documentados; e o `.pl4` deste build usa o formato PISA/C-like, para o qual foi escrito parser próprio.

## 7. Recomendações de seguimento (fora do escopo desta execução)

- Escolher a licença definitiva (substituir o placeholder).
- Renomear `src/` → `surto_bobina/` + instalação editável (remove o bootstrap de `sys.path`).
- Converter `print` → `logging` com níveis.
- Opcional: CI (GitHub Actions) rodando `pytest` a cada push.
