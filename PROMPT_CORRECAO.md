# Prompt executável — Correção do projeto surto-1

Você é um agente encarregado de **corrigir o projeto de simulação de surto em bobina distribuída** localizado na raiz deste repositório, seguindo as recomendações da auditoria técnica registrada em `AUDITORIA_PROJETO.md`.

O projeto é usado para **estudos técnicos de engenharia elétrica** (transitórios eletromagnéticos). Correção aqui significa restaurar a integridade técnica dos resultados, não apenas limpar código.

## Antes de começar (obrigatório)

1. Leia `AUDITORIA_PROJETO.md` por inteiro. Ele contém os achados A1–A13, as recomendações R1–R18 com prioridades P0–P3 e as evidências (arquivo:linha).
2. Leia `README.md`, `main.py`, `config/default_case.json`, todo o pacote `src/`, `run_atp.py`, `simulate_direct.py`, `save_images.py`, `surto_bobina.atp` e `atp_stdout.txt`.
3. Confirme os valores de referência antes de alterar qualquer coisa: rode o caso Pi padrão e registre `Vpk_in`, `Vpk_out` e `transfer_ratio` (valores esperados: 1000,0000 V / 2039,3086 V / 2,0393).

## Regras invioláveis

- **Não fabrique resultados ATP.** Curvas só podem ser apresentadas como "ATP" se vierem de um `.pl4` realmente gerado por uma execução bem-sucedida do ATP. Se o ATP não puder ser executado, o relatório deve dizer isso explicitamente.
- **Preserve a evidência da falha:** não apague `atp_stdout.txt`, `atp_stderr.txt`, `debug1.lis`, `surto_bobina.dbg` nem os `.tmp` da raiz antes de o deck estar corrigido e reexecutado. Ao concluir a correção do deck, mova esses arquivos para `docs/evidencias_atp_falha/` (ou pasta equivalente) em vez de deletá-los.
- **Preserve a reprodutibilidade numérica:** após qualquer refatoração, o caso Pi padrão deve continuar produzindo `Vpk_out = 2039,3086 V` (tolerância relativa 1e-6). Se alguma correção física legítima alterar esse valor, pare, documente a causa raiz e registre o novo valor de referência com justificativa — nunca altere resultados silenciosamente.
- **Não invente comportamento de ATP de memória sem verificar:** a auditoria aponta que o cartão de fonte tipo 14 é cossenoidal no ATP padrão e que a dupla exponencial é o tipo 15 com expoentes negativos. Confirme no ATP Rule Book (ou na interpretação ecoada no `.lis` de um teste) antes de fixar o cartão.
- Trabalhe em commits pequenos e temáticos (um grupo de recomendações por commit), com mensagens claras. Não faça um commit único gigante.
- Ambiente: Windows 11, Python 3.13, ATP em `C:\ATP\ATP\GNUATP\tpbigG.exe` (verifique se existe antes de usar). O projeto está em `D:\surto-1` — nenhum caminho absoluto pode sobrar no código.

## Fase 0 — Baseline (antes de tocar em qualquer arquivo)

1. Execute `python main.py` e guarde uma cópia de `output/` como referência de comparação (fora do repositório ou em pasta temporária).
2. Anote versões: `python --version`, `pip freeze` das bibliotecas usadas.

## Fase 1 — P0 (bloqueadores)

### R1 — Restaurar a verdade sobre a validação ATP

1. Corrija `surto_bobina.atp`:
   - Realinhe os cartões de ramo ao formato de colunas fixas do ATP (BUS1 cols 3–8, BUS2 cols 9–14, BUS3/BUS4 cols 15–26, R a partir da col 27, L e C nos campos seguintes). Corrija também a régua de colunas comentada no deck, que hoje está errada e induziu o erro original.
   - Revise o cartão de fonte: troque para o tipo correto de dupla exponencial (provavelmente tipo 15, com A2/A3 negativos), mantendo A1=1035.1, |A2|=13863, |A3|=2.5e6, Tstop=2e-4.
2. Execute o ATP via `run_atp.py` (depois de corrigir os caminhos — ver R5, que pode ser antecipado aqui). Confirme no `.lis` que **todos** os cartões foram aceitos e que o `.pl4` foi gerado.
3. Gere uma **comparação quantitativa Python × ATP**: para os nós N0, N5, N10, N15, N20, calcule erro máximo absoluto e erro RMS entre as curvas (interpolando para a mesma base de tempo), salve em `output/atp/comparacao_python_atp.csv` e produza uma figura sobreposta Python vs. ATP por nó.
4. **Fallback:** se o executável do ATP não estiver disponível nesta máquina, faça tudo que não depende da execução (corrigir o deck, corrigir rótulos e textos) e registre no relatório e no README, de forma destacada, que a validação ATP está **pendente de execução**, com instruções de como concluí-la.
5. Em qualquer um dos casos: renomeie/reorganize `output/atp/` e os artefatos com prefixo `atp_` para que nada gerado por Python seja apresentado como saída do ATP. O HTML gerado por `simulate_direct.py` deve deixar claro, no título e no nome do arquivo, que é simulação Python.

### R2 — Corrigir o relatório LaTeX

Em `relatorio/`:
- Seção 05: corrigir a descrição do tipo de fonte; remover ou condicionar a afirmação de "referência independente" à existência de resultados ATP reais; corrigir a nota sobre passo de gravação (IPLOT=10→11, saída a cada ~1,1e-7 s, não 1e-8 s).
- Seção 06: corrigir a linha "passo de amostragem" da tabela; adicionar linha distinguindo "deck definido" de "deck executado e comparado".
- Seção 07: re-rotular a subseção "Figuras associadas ao caso ATP" conforme a procedência real das figuras; se a comparação quantitativa de R1 existir, adicionar as figuras e a tabela de erros.
- Recompilar o PDF (`latexmk` ou `pdflatex`+`bibtex`) e corrigir erros de compilação que estejam sob seu controle.

### R3 — Validação da configuração

Em `src/utils/simulation_config.py`, adicione validação na construção (`__post_init__`):
- `termination ∈ {"open", "resistive"}` com `ValueError` ruidoso (elimina o erro silencioso A5);
- `n_sections ≥ 1` inteiro; `L_total, C_total, t_front, t_tail, dt, t_total, V_amplitude > 0`; `R_total ≥ 0`; `R_term > 0` quando `termination == "resistive"`; `dt < t_total`;
- ao carregar de JSON, emitir aviso listando as chaves ausentes que assumiram valor default.

## Fase 2 — P1 (alta prioridade)

### R4 — Eliminar a triplicação do modelo
Reescreva `simulate_direct.py` e `save_images.py` para consumirem `src/` e `config/default_case.json` (ou funda os dois em um único script `scripts/plot_plotly.py`). Deve restar **uma única** implementação da EDO e **uma única** definição da fonte. Duração e tolerâncias devem vir da configuração, não de constantes locais.

### R5 — Remover caminhos absolutos
Todos os caminhos derivados de `pathlib.Path(__file__).resolve().parent` ou de argumentos CLI. O caminho do executável ATP vira argumento `--atp-exe`, variável de ambiente `ATP_EXE`, ou entrada no JSON de configuração — com mensagem de erro clara quando não encontrado.

### R6 — Suíte de testes (pytest, diretório `tests/`)
No mínimo:
1. Forma de onda dentro das tolerâncias IEC 60060-1: T₁ = 1,67·(t₉₀−t₃₀) em 1,2 µs ±30%, T₂ (da origem virtual ao meio-valor) em 50 µs ±20%; pico = `V_amplitude` em ~2,09 µs.
2. Regressão: caso Pi padrão → `Vpk_out = 2039,3086 V` (rel. 1e-6); caso T padrão → mesmo valor de pico.
3. Convergência Pi vs. T: diferença de pico de saída decresce com N crescente (ex.: N=10, 20, 40).
4. Conservação: com `R_total = 0` e fonte zerada após carga inicial, energia total (Σ½CV² + Σ½LI²) constante dentro da tolerância do integrador.
5. Validação de configuração: entradas inválidas (termination com typo, dt>t_total, L negativo, n_sections=0) levantam `ValueError`.
6. `ResultProcessor`: CSVs gerados são relíveis programaticamente (ver R10).
Todos os testes devem passar com `python -m pytest`.

### R7 — Procedência das saídas
Ao final de cada cenário em `main.py`, gravar `run_metadata.json` na pasta do cenário com: configuração completa, hash do commit (`git rev-parse HEAD`, com fallback se não houver git), data/hora ISO, versões de Python/numpy/scipy/matplotlib. Exportar CSVs também para `low_c` e `high_c` (hoje só viram GIF).

## Fase 3 — P2 (média prioridade)

- **R8:** adicionar `plotly` e `kaleido` ao `requirements.txt`; pinar versões testadas (ou criar `pyproject.toml` com `requires-python`); substituir `cm.get_cmap(...)` por `matplotlib.colormaps[...]` em `plot_generator.py`.
- **R9:** modelo T aberto — não duplicar o nó de saída em `node_voltages()` (ou excluir o último vão do gradiente e documentar); remover ou renomear a coluna de corrente constante-zero `I_sec_N` do CSV.
- **R10:** dividir `summary.csv` em `summary_nodes.csv` (tabela por nó) e `summary_scalars.csv` (escalares), ambos CSV puro; documentar o dicionário de dados no README.
- **R11:** renomear as correntes `alpha`/`beta` do modelo T (ex.: `i_junction`, `i_out`) em código, comentários e README, eliminando a colisão com os expoentes da fonte.
- **R12:** expor `rtol`, `atol`, `method` do solver e os multiplicadores de cenário (0.1/10) na configuração JSON; nomear constantes restantes (`FRONT_COEFF = 3.0` com referência bibliográfica, guarda `1e-30`).
- **R13:** documentar no README as hipóteses implícitas: fonte ideal (capacitor C/2 de entrada não modelado no Python, presente no deck ATP), T₂ efetivo ≈ 52,7 µs (+5,4%) decorrente de α=ln2/T₂, razão de transferência >2 esperada em escada discreta, alternativa `method="Radau"` para casos rígidos (C alto / N grande).
- **R14:** declarar a procedência dos parâmetros do caso padrão (referência real ou rótulo explícito de "caso didático ilustrativo").

## Fase 4 — P3 (baixa prioridade — fazer se houver tempo)

- **R15:** `pyproject.toml` + instalação editável, removendo o hack `sys.path.insert` de `main.py`; adicionar `LICENSE`; estrutura final com `tests/` e, se viável, CI mínima.
- **R16:** remover `relatorio/frames/` (375 PNGs) e `relatorio.pdf` do versionamento (`git rm --cached` + `.gitignore`), mantendo o comando ffmpeg de regeneração documentado em `build_notes.tex`.
- **R17:** atualizar o README: scripts da raiz/`scripts/`, fluxo ATP (pré-requisitos, como executar, estado), como reproduzir as figuras do relatório.
- **R18:** trocar `print` por `logging`; corrigir o casamento de nós por substring em `run_atp.py` (comparação exata após normalização do nome).

## Verificação final (obrigatória)

1. `python -m pytest` — todos os testes passam.
2. `python main.py` — pipeline completo executa sem erros nem warnings de deprecação; comparar `summary` com o baseline da Fase 0 (idêntico, salvo mudanças documentadas).
3. Script Plotly unificado executa e gera HTML/PNG com rótulos de procedência corretos.
4. Se o ATP estiver disponível: `run_atp.py` executa, `.pl4` é lido, comparação quantitativa gerada.
5. Relatório LaTeX recompila sem erros; nenhuma afirmação de validação ATP sem resultado ATP real.
6. `git status` limpo, commits temáticos, nenhum caminho absoluto restante (`grep -rn "E:\\\\|C:\\\\ATP" --include="*.py"` vazio, exceto valores default documentados de CLI).

## Entrega final esperada

Ao terminar, informe:
- quais recomendações (R1–R18) foram concluídas, quais ficaram pendentes e por quê;
- se a validação ATP foi executada de fato (com erro máximo e RMS por nó) ou se ficou registrada como pendente;
- confirmação dos valores de regressão (`Vpk_out` Pi e T) antes e depois;
- lista de commits criados;
- qualquer desvio em relação a este prompt, com justificativa.
