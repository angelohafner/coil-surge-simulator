# Auditoria Técnica — Distributed Coil Surge Simulator

**Data da auditoria:** 11/06/2026
**Escopo:** todo o repositório `surto-1` (código Python, deck ATP, configuração, saídas geradas, relatório LaTeX).
**Contexto avaliado:** uso do projeto como ferramenta de **estudos técnicos de engenharia** (transitórios eletromagnéticos em enrolamentos).
**Método:** leitura integral do código-fonte (~2.000 linhas Python), inspeção do deck ATP e dos logs de execução, verificação numérica independente da forma de onda (critérios IEC 60060-1), teste de reprodutibilidade da simulação no ambiente atual, e checagem cruzada das afirmações do relatório LaTeX contra os artefatos reais.
**Nada foi modificado** — esta auditoria apenas documenta achados e recomendações.

---

## 1. Sumário executivo

O projeto tem uma **arquitetura de núcleo bem organizada** (separação clara entre configuração, fonte, modelo, solver, pós-processamento e visualização), um README de boa qualidade técnica e resultados numericamente reprodutíveis. A forma de onda implementada foi verificada nesta auditoria e **atende às tolerâncias da IEC 60060-1** (frente 1,193 µs, desvio −0,6%; cauda 52,7 µs, desvio +5,4%).

Porém, há **um achado crítico que invalida o principal argumento de confiabilidade do projeto**:

> **A "validação por ATP" nunca aconteceu.** O deck `surto_bobina.atp` falha no ATP com erro fatal (KILL code 6) no **primeiro cartão de ramo**, por desalinhamento de colunas — evidência registrada em `atp_stdout.txt`. Nenhum arquivo `.pl4` foi gerado. Os gráficos em `output/atp/` (HTML e PNGs) foram gerados **pelos scripts Python** `simulate_direct.py` e `save_images.py` — o próprio HTML declara "Simulação Python (scipy RK45)". Apesar disso, o relatório LaTeX apresenta essas figuras na seção "Figuras associadas ao caso ATP", com arquivos renomeados com prefixo `atp_`, e afirma que "a convergência conceitual entre os dois aumenta a confiança". Para um estudo de engenharia, isso é uma **validação cruzada fictícia**.

Adicionalmente: o modelo físico está **triplicado** no código (com parâmetros numéricos divergentes entre as cópias), os scripts auxiliares contêm **caminhos absolutos de um disco que não existe mais** (`E:\surto-1`), e a entrada de configuração tem um **risco de erro silencioso** real (`termination` com valor inválido é tratado silenciosamente como terminação resistiva).

### Quadro-resumo dos achados

| # | Achado | Severidade | Categoria |
|---|--------|-----------|-----------|
| A1 | Validação ATP fictícia: deck quebrado, figuras Python rotuladas como ATP | **Crítica** | Rastreabilidade / Integridade |
| A2 | Fonte ATP declarada como tipo 14 (cossenoidal no ATP padrão), não tipo 15 (dupla exponencial) | **Crítica** (latente) | Modelo |
| A3 | Modelo físico triplicado (`src/`, `simulate_direct.py`, `save_images.py`) com tolerâncias e duração divergentes | Alta | Separação de responsabilidades |
| A4 | Caminhos absolutos `E:\` e `C:\ATP\` hard-coded; projeto está em `D:\` | Alta | Reprodutibilidade |
| A5 | `termination` inválida vira "resistive" silenciosamente; sem validação de faixas físicas na configuração | Alta | Erro silencioso |
| A6 | Nenhum teste automatizado (0 testes no projeto) | Alta | Qualidade de software |
| A7 | Saídas sem metadados de procedência (config, versões, commit); cenários low_C/high_C nunca exportados | Média-Alta | Rastreabilidade |
| A8 | `requirements.txt` incompleto (falta `plotly`, `kaleido`); sem pinagem de versões; API matplotlib deprecada | Média | Reprodutibilidade |
| A9 | Nó de saída duplicado no modelo T (gradiente final sempre 0); coluna de corrente fantasma no CSV | Média | Erro silencioso / Semântica |
| A10 | Constantes mágicas espalhadas (A1=1035.1, β=3/T1, rtol/atol, multiplicadores ×0,1/×10) | Média | Manutenibilidade |
| A11 | Colisão de nomenclatura: `alpha`/`beta` = expoentes da onda **e** correntes do modelo T | Média | Nomenclatura |
| A12 | Procedência física dos parâmetros de entrada (L, R, C) não documentada | Média | Rastreabilidade |
| A13 | Repositório com 375 PNGs de frames e PDF compilado versionados (36 MB) | Baixa | Higiene |

---

## 2. Visão geral do que foi auditado

```
main.py                    pipeline principal (4 cenários: Pi, T, low-C, high-C)
config/default_case.json   parâmetros do caso padrão
src/
  models/                  CoilSection, DistributedCoil (EDOs Pi e T)
  solvers/                 TimeDomainSolver (scipy solve_ivp RK45)
  sources/                 ImpulseSource (dupla exponencial / rampa-exp)
  utils/                   SimulationConfig, ResultProcessor
  visualization/           PlotGenerator (PNG), GifGenerator (GIF)
run_atp.py                 executa ATP + parser .pl4 + gráficos Plotly   [fora de src/]
simulate_direct.py         reimplementação independente do modelo Pi    [fora de src/]
save_images.py             cópia de simulate_direct com saída PNG       [fora de src/]
surto_bobina.atp           deck ATP (escada Pi, N=20)
relatorio/                 relatório LaTeX modular (10 seções + TikZ + BibTeX)
output/                    artefatos gerados (não versionados — correto)
```

---

## 3. Achados detalhados

### 3.1. Rastreabilidade dos dados de entrada e dos resultados

**A1 — A cadeia de procedência dos "resultados ATP" está quebrada (CRÍTICO).**

Evidências verificadas nesta auditoria:

1. `atp_stdout.txt` registra execução do ATP em 26/04/2026 que **terminou em erro fatal** antes de montar o circuito:
   ```
   KILL = 6.  The reference branch names of the last data card are illegal...
   the missing branch is supposed to connect node "      " with node " 0.25 ".
   Card: "   N0    N1          0.25     5.E-4"
   ```
   O formato de colunas fixas do cartão de ramo está errado: o valor de R (0,25 Ω) caiu nas colunas 15–26 (campos de ramo de referência BUS3/BUS4), quando R deve iniciar na coluna 27. A régua de colunas comentada no próprio deck ([surto_bobina.atp:31](surto_bobina.atp:31)) está incorreta e induziu o erro.
2. Nenhum `.pl4` existe no projeto — a execução nunca produziu dados.
3. `output/atp/surto_bobina.html` contém literalmente: *"Simulação Python (scipy RK45) — circuito idêntico ao arquivo ATP"* — foi gerado por [simulate_direct.py:178](simulate_direct.py:178), que grava **no mesmo caminho** que `run_atp.py` usaria. `grafico_overlay.png` e `grafico_subplots.png` foram gerados por [save_images.py](save_images.py) (também Python).
4. O relatório LaTeX ([07_resultados_figuras.tex:51](relatorio/sections/07_resultados_figuras.tex:51)) apresenta essas figuras sob o título "Figuras associadas ao caso ATP", renomeadas para `atp_grafico_overlay.png` / `atp_grafico_subplots.png`, e [05_modelo_atp.tex:17](relatorio/sections/05_modelo_atp.tex:17) afirma que o ATP é "uma referência independente" cuja convergência "aumenta a confiança".

**Consequência para uso em engenharia:** qualquer leitor do relatório conclui que houve validação cruzada Python × ATP. Não houve. A comparação numérica entre as duas ferramentas nunca foi executada. A legenda da Fig. do overlay diz "escada Pi equivalente ao ATP" (tecnicamente verdadeiro, mas facilmente lido como resultado ATP).

**A7 — Resultados não carimbados com sua origem.**
- Nenhum CSV/PNG/GIF registra: configuração usada, versão do código (commit), versões de bibliotecas, data/hora. `SimulationConfig.to_json()` existe ([simulation_config.py:41](src/utils/simulation_config.py:41)) mas **nunca é chamado**.
- Os cenários `low_c` e `high_c` são simulados e viram GIFs, mas **nunca são exportados como CSV** ([main.py:110-117](main.py:110) salva apenas Pi e T) — as animações comparativas não têm dados rastreáveis por trás.
- As figuras do relatório são **cópias manuais** de `output/` para `relatorio/figures/output/` (documentado em [build_notes.tex](relatorio/build_notes.tex)); não há registro de qual execução as produziu. Se o código mudar e as figuras não forem recopiadas, o relatório fica silenciosamente desatualizado.
- O número citado no relatório ("a saída chega a cerca de 2039 V", [03_modelo_eletrico.tex:33](relatorio/sections/03_modelo_eletrico.tex:33)) **confere** com `output/csv/summary.csv` (2039,3086 V) — mas esse CSV não é versionado, então a afirmação do relatório não é verificável a partir do repositório.

**A12 — Procedência física dos parâmetros de entrada.**
`L_total = 10 mH`, `R_total = 5 Ω`, `C_total = 1 nF`, `N = 20` não têm justificativa documentada em lugar nenhum (nem README, nem config, nem relatório): não se sabe se representam uma bobina real, valores típicos de literatura ou números didáticos. Para estudo de engenharia, todo parâmetro de entrada precisa de fonte (medição, datasheet, norma, literatura) ou da declaração explícita "caso didático ilustrativo".

### 3.2. Validação de unidades físicas

- **Positivo:** unidades SI consistentes em todo o núcleo; comentários de unidade nos dataclasses ([simulation_config.py:12-30](src/utils/simulation_config.py:12)); tabela de configuração do README com coluna de unidade; conversões de exibição (s→µs, V→kV) corretas; conversões do deck ATP (COPT=0 → µF: `5.E-5 µF = 50 pF`) corretas.
- **Lacuna:** não há **nenhuma validação programática**. O JSON aceita qualquer número: `L_total = -0.01`, `t_front = 0` (→ divisão por zero em `beta = 3.0/t_front`, [impulse_source.py:57](src/sources/impulse_source.py:57)), `n_sections = 0` (→ `ZeroDivisionError` em [distributed_coil.py:70](src/models/distributed_coil.py:70)), `dt > t_total` (→ malha de tempo vazia). Alguns desses falham ruidosamente, outros produzem lixo numérico sem aviso.
- As chaves do JSON não carregam unidade no nome (`L_total` vs. `L_total_H`). Convenção é aceitável quando documentada, mas o arquivo `default_case.json` em si não tem nenhum comentário/metadado de unidade (JSON não permite comentários — ver recomendação R7).

### 3.3. Separação entre dados, modelo, simulação, visualização e relatório

- **Positivo:** o pacote `src/` implementa exatamente a separação pedida: dados (`config/` + `SimulationConfig`) → fonte (`ImpulseSource`) → modelo (`DistributedCoil`) → simulação (`TimeDomainSolver`) → pós-processamento (`ResultProcessor`) → visualização (`PlotGenerator`/`GifGenerator`) → relatório (`relatorio/`). O solver não conhece matplotlib; a visualização não resolve EDOs. Bom desenho.
- **A3 — A separação é violada pelos três scripts da raiz.** `simulate_direct.py` e `save_images.py` reimplementam o modelo Pi inteiro (EDO, fonte, parâmetros) **sem usar `src/`**, e `save_images.py` é ~90% cópia de `simulate_direct.py`. Consequências concretas já presentes:
  - Tolerâncias do solver divergem: `rtol=1e-7, atol=1e-12` no núcleo ([time_domain_solver.py:69](src/solvers/time_domain_solver.py:69)) vs. `rtol=1e-6, atol=1e-10` nos scripts ([simulate_direct.py:96](simulate_direct.py:96)).
  - Duração divergente: 50 µs no pipeline principal vs. 200 µs nos scripts/ATP.
  - Fonte divergente: o núcleo **calcula** a normalização K em tempo de execução; os scripts usam `A1 = 1035.1` fixo (o valor calculado é 1035,16 — diferença pequena, mas duas fontes de verdade).
  - Qualquer correção futura no modelo precisa ser feita em três lugares.
- `main.py` define os cenários de estudo (×0,1 / ×10 em C) em código ([main.py:94-95](main.py:94)), não em dados — um estudo de engenharia deveria poder variar cenários sem editar o programa.
- `ResultProcessor` acumula duas responsabilidades (derivar grandezas + escrever CSV) — aceitável no porte atual, registrado como menor.

### 3.4. Reprodutibilidade dos resultados

- **Verificado nesta auditoria:** reexecutando o cenário Pi em memória no ambiente atual (Python 3.13.5, numpy 2.4.2, scipy 1.17.1), os picos reproduzem **exatamente** os CSVs existentes (Vpk_out = 2039,3086 V). O modelo é determinístico (sem RNG). Bom.
- **A4 — Os três scripts da raiz não rodam mais nesta máquina:** caminhos fixos `E:\surto-1\...` ([run_atp.py:30-31](run_atp.py:30), [simulate_direct.py:40](simulate_direct.py:40), [save_images.py:17](save_images.py:17)) e `C:\ATP\ATP\GNUATP\tpbigG.exe` ([run_atp.py:29](run_atp.py:29)). O projeto hoje está em `D:\surto-1`. Se executados, gravariam em disco errado ou falhariam.
- **A8 — Ambiente não reproduzível a partir do repositório:**
  - `requirements.txt` omite `plotly` (usado por 3 scripts) e `kaleido` (exigido por `fig.write_image` em [save_images.py:69](save_images.py:69)).
  - Versões apenas com piso (`>=`), sem lock file e sem versão de Python declarada.
  - [plot_generator.py:93](src/visualization/plot_generator.py:93) usa `cm.get_cmap(...)`, **deprecado desde matplotlib 3.7 com remoção anunciada para 3.11** (verificado no ambiente: emite `MatplotlibDeprecationWarning` na 3.10.8). Com o requisito aberto `matplotlib>=3.7`, uma instalação futura quebrará o pipeline no meio da geração de figuras.
- A versão exata do ATP usada (build GNU de 16/09/2005, conforme `atp_stdout.txt`) não está documentada em nenhum documento do projeto.

### 3.5. Clareza das hipóteses técnicas

- **Positivo:** o README tem seção explícita de limitações (sem capacitância série espira-espira, modelo linear, aproximação concentrada, relação empírica β=3/T₁ "±10%") e formulação matemática completa dos dois modelos (KCL/KVL). Isso é acima da média.
- **Verificação independente da onda (feita nesta auditoria):** pelos critérios da IEC 60060-1, a onda implementada tem T₁ = 1,193 µs (−0,6%) e T₂ = 52,71 µs (+5,4%) — **dentro das tolerâncias normativas** (±30% frente, ±20% cauda). A hipótese declarada é válida, porém **nenhuma verificação dessas está codificada** — é exatamente o tipo de checagem que deveria ser um teste automatizado.
- **Hipóteses implícitas não declaradas:**
  1. **Fonte ideal (impedância zero):** o capacitor de extremidade C/2 do nó de entrada não entra no modelo de estados (correto para fonte ideal, mas a hipótese não está escrita; o deck ATP, ao contrário, inclui o capacitor em N0).
  2. **α = ln2/T₂** assume que a componente exponencial lenta sozinha decai a 50% em T₂ — a cauda real da onda composta dá 52,7 µs. Disclosed apenas parcialmente (o README menciona aproximação apenas para β).
  3. A razão de transferência observada (2,039 > 2,0) é fisicamente plausível em escada discreta com oscilações, mas o relatório não discute por que excede o dobro ideal — leitor pode suspeitar de erro.
  4. RK45 explícito é adequado para os parâmetros default, mas nada alerta que cenários com C×10 ou N grande podem tornar o sistema rígido (stiff) e degradar o desempenho/precisão.

### 3.6. Constantes mágicas (A10)

| Constante | Local | Observação |
|-----------|-------|------------|
| `beta = 3.0 / t_front` | [impulse_source.py:57](src/sources/impulse_source.py:57) | Documentada (empírica), mas o "3.0" mereceria nome e referência |
| `rtol=1e-7, atol=1e-12` | [time_domain_solver.py:69-70](src/solvers/time_domain_solver.py:69) | Não configuráveis; divergem dos scripts |
| `rtol=1e-6, atol=1e-10` | [simulate_direct.py:96](simulate_direct.py:96), [save_images.py:45](save_images.py:45) | Divergem do núcleo |
| `A1=1035.1; alpha=13863.0; beta=2.5e6` | [simulate_direct.py:32-34](simulate_direct.py:32), [save_images.py:14](save_images.py:14), [surto_bobina.atp:104](surto_bobina.atp:104) | Valores derivados hard-coded em 3 lugares; o núcleo os calcula |
| `C_total*0.1` / `C_total*10.0` | [main.py:94-95](main.py:94) | Definição de cenário de estudo embutida em código |
| `1e-30` (guarda de divisão) | [result_processor.py:49](src/utils/result_processor.py:49) | Sem nome/justificativa |
| `_SUBSAMPLE=20, _FPS=15` | [gif_generator.py:41-42](src/visualization/gif_generator.py:41) | OK (nomeadas), mas não configuráveis |
| Faixas heurísticas do parser .pl4 (`nvar≤500`, `1e-13<del_t<1e-1`) | [run_atp.py:211-216](run_atp.py:211) | Heurísticas de detecção sem justificativa documentada |

### 3.7. Risco de erro silencioso

- **A5 — `termination` não é validada.** `model_type` e `source_type` são validados com `raise ValueError` ([distributed_coil.py:66](src/models/distributed_coil.py:66), [impulse_source.py:42](src/sources/impulse_source.py:42)), mas `termination` segue o padrão `if termination == "open" ... else resistive` ([distributed_coil.py:170-173](src/models/distributed_coil.py:170)). Um typo (`"opne"`, `"Open "` com espaço) converte silenciosamente o estudo para terminação resistiva com R_term = 1 MΩ — resultado *quase* igual ao aberto, ou seja, **o pior tipo de erro: pequeno o bastante para passar despercebido**.
- **A2 — Tipo de fonte ATP.** O deck usa cartão tipo **14** ([surto_bobina.atp:104](surto_bobina.atp:104)) com comentário afirmando ser dupla exponencial. Na documentação padrão do ATP (Rule Book), o tipo 14 é fonte **cossenoidal** (amplitude, frequência, fase); a dupla exponencial de surto é o tipo **15** (com expoentes negativos nos campos A2/A3). Se o erro de colunas (A1) for corrigido sem revisar o tipo da fonte, o ATP injetará uma cossenoide de ~13,9 kHz e o usuário poderá comparar curvas sem perceber que a excitação é outra. *(Verificar contra o Rule Book na correção — a execução atual morre antes de interpretar o cartão, então não há eco no `.lis` para confirmar.)*
- **A9 — Nó de saída duplicado no modelo T (aberto).** Em `node_voltages()` para T aberto, `V_out = V_m[N-1]` é **anexado de novo** como nó extra na posição 1,0 ([distributed_coil.py:114-123](src/models/distributed_coil.py:114)). Confirmado em `output/t_model/csv/summary.csv`: linhas 20 e 21 idênticas (2039,3090 V) e gradiente do último vão **sempre 0,0000**. Em um estudo de solicitação dielétrica, esse zero estrutural pode ser lido como "não há esforço no fim do enrolamento" — interpretação errada de um artefato de visualização. Análogo: a corrente `I_sec_20` do CSV do modelo T aberto é uma coluna constante igual a zero (β fictício, [distributed_coil.py:141-145](src/models/distributed_coil.py:141)) sem aviso.
- **Casamento de nós por substring** em [run_atp.py:305-310](run_atp.py:305): `node.upper() in k.upper()` retorna a primeira chave que contém o texto — pedir `N1` casaria com `N10`/`N15`. Com a lista atual (N0, N5, N10, N15, N20) funciona **por sorte**.
- **Comparação de GIFs sem verificação de base de tempo:** `generate_comparison_animation` documenta "Both results must share the same time array" mas não verifica ([gif_generator.py:198-211](src/visualization/gif_generator.py:198)); bases diferentes produziriam quadros dessincronizados com rótulo de tempo de apenas um dos casos.
- **`summary.csv` com formato misto** (tabela + linhas chave-valor após linha em branco, [result_processor.py:91-108](src/utils/result_processor.py:91)) quebra leitura programática ingênua (`pandas.read_csv`) — risco de pós-processamentos externos descartarem ou corromperem as últimas linhas.
- **Chave ausente no JSON assume default silenciosamente** (dataclass): remover `C_total` do arquivo não gera erro — o estudo roda com 1 nF default sem aviso. (Chave desconhecida, ao contrário, falha ruidosamente — bom.)

### 3.8. Consistência dos nomes de variáveis técnicas

- **A11 — Colisão grave de nomenclatura:** `alpha` e `beta` são os **expoentes da dupla exponencial** em `ImpulseSource` ([impulse_source.py:54-57](src/sources/impulse_source.py:54)) e, simultaneamente, as **correntes de junção** do modelo T em `DistributedCoil` ([distributed_coil.py:192-219](src/models/distributed_coil.py:192)) e no README. Em um projeto de transitórios, α e β têm leitura canônica como expoentes da onda — usar os mesmos símbolos para correntes confunde revisão e manutenção.
- Menores: `V_amplitude` (config) vs. `amplitude` (classe); `n_sections` vs. `n` vs. `N`; rótulos de CSV `V_node_{k}` não distinguem, no modelo T, terminais de pontos médios (o leitor precisa do código para saber que as colunas 1..N são pontos de meia seção); `t_front`/`t_tail` vs. T₁/T₂ vs. A2/A3 (ATP) — mapeados em texto, mas espalhados.
- **Positivo:** dentro do núcleo a notação segue o README (V_k, I_k, C_sec, L_sec, R_sec) com consistência boa entre equações documentadas e código.

### 3.9. Documentação para continuidade por outro engenheiro

- **Positivo:** README com formulação matemática completa, tabela de parâmetros com unidades, interpretação física dos resultados e limitações; docstrings de módulo em todos os arquivos do núcleo; relatório LaTeX modular com bibliografia real (IEEEtran) e até o prompt que o gerou (`PROMPT_RELATORIO.md`) — transparência rara.
- **Lacunas:**
  1. Os três scripts da raiz **não aparecem** na seção de estrutura do README — um engenheiro novo não sabe que existem nem para que servem (apenas o relatório LaTeX os menciona).
  2. Não há documentação do **formato dos CSVs** (semântica das colunas por modelo, formato misto do summary).
  3. Não há instrução de como rodar o fluxo ATP (pré-requisitos, versão, correção de caminhos) nem aviso de que ele está quebrado.
  4. Sem `LICENSE`, sem `pyproject.toml`/empacotamento (depende de hack `sys.path.insert`, [main.py:32](main.py:32)), sem diretório de testes, sem CI.
  5. O relatório LaTeX afirma equivalências não verificadas (ver A1) e repete o erro do tipo 14 ([05_modelo_atp.tex:9-15](relatorio/sections/05_modelo_atp.tex:9)); a tabela de correspondência ([06](relatorio/sections/06_correspondencia_python_atp.tex)) declara "passo de amostragem 1e-8 = 1e-8", mas o deck ATP grava saída a cada 10–11 passos (IPLOT=10, tornado ímpar pelo ATP).

### 3.10. Higiene de repositório (A13)

- 429 arquivos versionados, dos quais **375 são frames PNG** extraídos dos GIFs para o PDF (e `relatorio.pdf` compilado) — `.git` com 36 MB. Os frames são deriváveis por comando ffmpeg já documentado em `build_notes.tex`.
- `.gitignore` correto para `output/`, caches e temporários do ATP (verificado: não estão rastreados).
- Arquivos órfãos na raiz do disco de trabalho: `63336514.tmp`, `63346162.tmp`, `debug1.lis`, `surto_bobina.dbg`, `atp_stdout.txt`, `atp_stderr.txt`. **Atenção:** `atp_stdout.txt` é hoje a única evidência da falha do ATP — preservá-lo até a correção do deck (recomenda-se arquivá-lo junto à correção, não apagá-lo).

---

## 4. Pontos fortes (a preservar)

1. Arquitetura em camadas do `src/` limpa e coerente com a física (dados → fonte → modelo → solver → pós-processamento → visualização).
2. README tecnicamente sólido: equações KCL/KVL dos dois modelos, tabela de parâmetros com unidades, limitações explícitas.
3. Forma de onda dentro das tolerâncias IEC 60060-1 (verificado nesta auditoria).
4. Determinismo e reprodutibilidade local exata dos resultados.
5. Validação ruidosa de `model_type`/`source_type` e do sucesso do solver (`RuntimeError` se `solve_ivp` falhar).
6. Relatório LaTeX modular, com bibliografia real e notas de construção; prompt gerador versionado.
7. Parser `.pl4` defensivo (8 combinações de formato, erros acumulados e reportados).

---

## 5. Recomendações priorizadas

### P0 — Bloqueadores para uso em estudo de engenharia

| # | Recomendação | Esforço |
|---|--------------|---------|
| R1 | **Restaurar a verdade sobre a validação ATP.** Duas opções: (a) corrigir o deck (alinhamento de colunas dos cartões de ramo conforme formato fixo do ATP; revisar tipo da fonte — usar tipo 15/dupla exponencial conforme Rule Book), reexecutar, ler o `.pl4` real e publicar comparação **quantitativa** Python×ATP (erro máximo e RMS por nó); ou (b) se o ATP não for reexecutado, **remover/renomear** tudo que sugira procedência ATP (`output/atp/`, prefixos `atp_` nas figuras, seções 05–07 do relatório) e declarar explicitamente no relatório que a validação ATP está pendente. A opção (a) é a que agrega valor de engenharia. | (a) 0,5–1 dia; (b) 2 h |
| R2 | **Corrigir o texto do relatório LaTeX** após R1: legenda e seção das figuras "ATP", afirmação de "referência independente", equação do tipo 14, nota sobre IPLOT/passo de gravação. | 1–2 h |
| R3 | **Validar a configuração na carga** (`SimulationConfig.__post_init__` ou validador): `termination ∈ {open, resistive}` (erro ruidoso — elimina o erro silencioso A5), positividade de N, L, R, C, t_front, t_tail, dt, `dt < t_total`, e aviso quando chaves esperadas estiverem ausentes do JSON. | 2–3 h |

### P1 — Alta prioridade

| # | Recomendação | Esforço |
|---|--------------|---------|
| R4 | **Eliminar a triplicação do modelo:** reescrever `simulate_direct.py` e `save_images.py` (ou fundi-los em um único script) consumindo `src/` e `config/`; um único conjunto de tolerâncias e de parâmetros da fonte. | 0,5 dia |
| R5 | **Remover caminhos absolutos:** derivar caminhos de `pathlib.Path(__file__).parent` e/ou aceitar CLI args (`--atp-exe`, `--out`); mover `ATP_EXE` para configuração ou variável de ambiente. | 1–2 h |
| R6 | **Criar suíte mínima de testes** (pytest): (i) T₁/T₂ da onda dentro das tolerâncias IEC (o teste já existe em essência — foi o que esta auditoria executou); (ii) pico da fonte = V_amplitude; (iii) regressão dos picos Pi/T contra valores de referência (2039,31 V); (iv) convergência Pi vs. T com N crescente; (v) conservação de carga/energia em caso sem perdas (R=0); (vi) validação de config rejeitando entradas inválidas. | 1 dia |
| R7 | **Carimbar procedência em toda saída:** ao final de cada execução, gravar `output/<cenário>/run_metadata.json` com a config completa (`to_json`), hash do commit, data, versões de Python/numpy/scipy/matplotlib. Exportar CSV também para `low_c`/`high_c`. | 2–3 h |

### P2 — Média prioridade

| # | Recomendação | Esforço |
|---|--------------|---------|
| R8 | Completar e pinar dependências: adicionar `plotly`, `kaleido`; congelar versões testadas (`requirements.lock` ou `pyproject.toml` + `requires-python`); substituir `cm.get_cmap(...)` por `matplotlib.colormaps[...]` antes da remoção na 3.11. | 1–2 h |
| R9 | Corrigir a semântica do modelo T nas saídas: não duplicar o nó de saída no caso aberto (ou documentar e excluir o último vão do gráfico de gradiente); remover a coluna `I_sec_N` constante-zero ou renomeá-la (`I_out`). | 2–4 h |
| R10 | Separar `summary.csv` em dois arquivos (tabela por nó + escalares) ou um único formato tabular consistente. Documentar o dicionário de dados dos CSVs no README. | 1–2 h |
| R11 | Resolver a colisão `alpha`/`beta`: renomear as correntes do modelo T (ex.: `i_junction`, `i_out`) no código e no README. | 1–2 h |
| R12 | Tornar tolerâncias do solver (`rtol`, `atol`, método) e cenários de estudo (multiplicadores de C) configuráveis via JSON; nomear as constantes restantes (`FRONT_COEFF = 3.0` com referência, guarda `1e-30`). | 2–3 h |
| R13 | Documentar hipóteses implícitas no README: fonte ideal (capacitor de entrada não modelado), significado aproximado de α=ln2/T₂ (T₂ efetivo +5,4%), comportamento esperado da razão de transferência >2 em escada discreta, limites de validade do RK45 (rigidez com C alto/N grande — sugerir `method="Radau"` como alternativa). | 2–3 h |
| R14 | Documentar a procedência dos parâmetros do caso padrão (referência de literatura/medição ou rótulo explícito de "caso didático"). | 1 h |

### P3 — Baixa prioridade

| # | Recomendação | Esforço |
|---|--------------|---------|
| R15 | Empacotar (`pyproject.toml`, `pip install -e .`), removendo o hack de `sys.path`; adicionar `LICENSE`; estrutura `tests/`; CI simples (lint + pytest). | 0,5 dia |
| R16 | Reduzir o repositório: remover `relatorio/frames/` (375 PNGs) e `relatorio.pdf` do versionamento (regeneráveis por script documentado); opcionalmente Git LFS para binários remanescentes. | 1–2 h |
| R17 | Atualizar o README com os scripts da raiz, fluxo ATP (pré-requisitos e estado), e seção "como reproduzir as figuras do relatório". | 1–2 h |
| R18 | Trocar `print` por `logging` com níveis; corrigir casamento de nós por substring em `run_atp.py` (comparação exata pós-normalização). | 2–3 h |

---

## 6. Anexo — Verificações executadas nesta auditoria

| Verificação | Método | Resultado |
|-------------|--------|-----------|
| Onda 1,2/50 µs conforme IEC 60060-1 | Avaliação numérica de `ImpulseSource` (2×10⁶ pontos), T₁=1,67·(t₉₀−t₃₀), T₂ da origem virtual ao meio-valor | T₁ = 1,193 µs (−0,6%); T₂ = 52,71 µs (+5,4%) — **dentro das tolerâncias** (±30%/±20%); pico = 1000,00 V em 2,090 µs |
| Reprodutibilidade do cenário Pi | Reexecução em memória (sem gravar) com `config/default_case.json` | Vpk_in = 1000,0000 V; Vpk_out = 2039,3086 V — **idêntico** ao `summary.csv` existente |
| Execução do ATP | Leitura de `atp_stdout.txt`, `debug1.lis`, busca por `.pl4` | **Falha KILL=6** no 1º cartão de ramo (colunas); nenhum `.pl4` existe |
| Procedência de `output/atp/` | Inspeção do HTML e dos scripts geradores | Gerado por `simulate_direct.py`/`save_images.py` (Python), não pelo ATP |
| Artefato duplicado do modelo T | `output/t_model/csv/summary.csv` | Nós 20 e 21 idênticos; gradiente final = 0,0000 (estrutural) |
| API matplotlib deprecada | Chamada de `cm.get_cmap('plasma', 6)` no ambiente (3.10.8) | `MatplotlibDeprecationWarning` — remoção anunciada para 3.11 |
| Rastreamento git de artefatos | `git ls-files` | `output/`, caches e temporários corretamente ignorados; 375 frames PNG + PDF versionados |

*Ambiente da auditoria: Windows 11, Python 3.13.5, numpy 2.4.2, scipy 1.17.1, matplotlib 3.10.8, plotly 6.6.0.*
