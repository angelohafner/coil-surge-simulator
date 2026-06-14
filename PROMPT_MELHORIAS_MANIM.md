# Prompt executável — Apresentação Manim didática: distribuição de tensão em bobina sob surto

Você é um agente encarregado de **elevar a apresentação Manim do projeto `surto-1`** a uma
peça didática rigorosa que ensine **como a tensão se distribui ao longo de uma bobina/enrolamento
quando ele é atingido por um surto** — por que a distribuição é inicialmente não-uniforme, como ela
evolui no tempo e o que isso significa para o estresse dielétrico do isolamento.

O arquivo-alvo é `manim_presentation.py` (classe `SurgePresentation`). O projeto é de **engenharia
elétrica** (transitórios eletromagnéticos), com forte cultura de auditoria e reprodutibilidade
(ver `AUDITORIA_PROJETO.md`, `PROMPT_CORRECAO.md`, `RELATORIO_EXECUCAO_CORRECAO.md`). Rigor técnico
e honestidade sobre o que foi validado valem mais do que vistosidade.

---

## Decisões já tomadas (não re-perguntar)

1. **Idioma da apresentação: inglês.** Títulos, legendas e narração ficam em inglês. Notação e
   símbolos técnicos seguem o padrão (`R`, `L`, `C_g`, `C_s`, `V_s(t)`, `\alpha`). As **instruções
   de commits e o relatório** continuam em português.
2. **Escopo: expandir a narrativa didática.** Reativar/consertar as cenas mortas, montar um
   storyboard completo (distribuição inicial não-uniforme → onda viajante → reflexão/condição de
   contorno → envelope de tensão máxima → estresse local), eliminar código morto e melhorar robustez.
3. **Incluir capacitância série no modelo.** Estender `src/` com capacitância série (entre seções
   adjacentes, análoga à capacitância turn-to-turn/disco-a-disco) para reproduzir a distribuição
   inicial não-uniforme `∝ cosh/sinh(αx)`. Esta é a melhoria que torna o fenômeno central
   **fisicamente visível**, e não apenas narrado.

---

## Leitura obrigatória antes de tocar em qualquer arquivo

- `manim_presentation.py` inteiro (já existe muita infraestrutura reutilizável).
- `README.md` (seções *Physical model*, *Modelling hypotheses*, *Limitations*, *Manim*).
- `AUDITORIA_PROJETO.md` e `PROMPT_CORRECAO.md` — para herdar o tom e as regras invioláveis.
- `src/` inteiro, em especial `models/distributed_coil.py`, `models/coil_section.py`,
  `solvers/time_domain_solver.py`, `sources/impulse_source.py`, `utils/simulation_config.py`.
- `config/default_case.json`.
- `relatorio/sections/03_modelo_eletrico.tex` e `08_animacoes.tex`.
- `surto_bobina.atp` e a seção *ATP cross-validation* do README (para entender o que a validação
  cruzada cobre hoje).
- Rode o baseline e **registre os valores de referência** antes de mudar qualquer física:
  `python main.py` → caso Pi default deve dar `Vpk_in = 1000,0000 V`, `Vpk_out = 2039,3086 V`,
  `transfer_ratio = 2,0393`.

---

## Regras invioláveis

- **Reprodutibilidade numérica.** Com a capacitância série **desligada** (`C_series_total = 0`,
  o default), o caso Pi padrão deve continuar produzindo `Vpk_out = 2039,3086 V` (tolerância
  relativa `1e-6`) e todos os testes de regressão existentes (`tests/test_regression_outputs.py`)
  devem passar **sem alteração de valores esperados**. A capacitância série é estritamente *opt-in*.
- **Nada de resultado fabricado.** Toda curva da apresentação vem de uma simulação real do `src/`
  (ou de uma fórmula analítica claramente rotulada como tal). Curva só pode ser chamada de "ATP" se
  vier de um `.pl4` realmente gerado por execução bem-sucedida do ATP.
- **Não quebrar nem mascarar a validação ATP existente.** A validação cruzada Python×ATP atual
  cobre o caso **somente-shunt**. Se você **não** estender o deck ATP para incluir capacitância
  série (ver Parte A.6, que é opcional), a apresentação **não pode** rotular o caso com capacitância
  série como "validado por ATP". Use a validação analítica (Parte A.5) para o caso novo e seja
  explícito sobre o escopo de cada validação.
- **Sem caminhos absolutos.** Tudo derivado de `Path(__file__).resolve().parent`.
- **Commits pequenos e temáticos** (um grupo coerente por commit), mensagens claras em português.
  Nada de um commit gigante.
- **Ambiente:** Windows 11, Python 3.13, Manim Community. Confirme a versão do Manim instalada e
  use a API correspondente (a base de código usa `manim import *`, `always_redraw`, `ValueTracker`,
  `MathTex`, `ImageMobject`).

---

## Estado atual — diagnóstico (não precisa redescobrir)

- `SurgePresentation.construct()` (≈ linha 504) roda **apenas 4 cenas**:
  `opening_scene` → `source_scene` → `model_scene(termination="grounded")` →
  `grounded_return_scene(clear_after=False)`. O foco hoje é só o caso aterrado.
- Há **7 cenas definidas e nunca chamadas**: `problem_scene`, `travelling_wave_scene`,
  `reflection_scene`, `pi_t_scene`, `python_atp_scene`, `limitations_scene`, `closing_scene`.
- **Código morto que quebraria se chamado:** `pi_t_scene` e `python_atp_scene` (e partes de
  `reflection_scene`/`travelling_wave_scene`) referenciam `self.data.t_nodes`, `self.data.t_scalars`
  e `self.data.atp_rows`, que **não existem** no dataclass `ProjectData` atual (só tem `config`,
  `pi_nodes`, `grounded_nodes`, `pi_scalars`, `grounded_scalars`). Chamá-las hoje gera
  `AttributeError`.
- O `ProjectDataLoader` tem métodos **mortos** (`_read_node_voltages`, `_read_scalars`,
  `_read_atp_comparison`): a apresentação hoje **re-simula** em `_simulate_manim_case` em vez de ler
  os CSVs de `output/`. Há, portanto, duas fontes de dados concorrentes e só uma em uso.
- O modelo físico só tem **capacitância shunt para terra** (`C_node` diagonal em
  `_deriv_pi`, ≈ linha 188 de `distributed_coil.py`). Por isso a **concentração inicial de tensão
  nas primeiras seções não aparece** — é exatamente o que a Parte A corrige.

---

## Parte A — Estender o modelo físico (pré-requisito da narrativa) — `src/`

> Objetivo: permitir que a apresentação mostre a distribuição inicial não-uniforme **a partir de
> dados simulados reais**, não de um desenho. Mantenha tudo *opt-in* e retrocompatível.

**A.1 — Configuração.** Em `src/utils/simulation_config.py`:
- Adicione o campo `C_series_total: float = 0.0` (capacitância série equivalente ponta-a-ponta do
  enrolamento, em F). Semântica: `0.0` = **sem** capacitância série (modelo atual, idêntico).
- Valide em `__post_init__`: `C_series_total >= 0` (mensagem em português, no mesmo estilo das
  demais). **Não** o inclua na lista que exige `> 0`.
- Como `from_json` **rejeita chaves desconhecidas**, adicionar o campo ao dataclass é obrigatório;
  JSONs antigos sem a chave continuam válidos (cairão no warning de "chave ausente assumiu default",
  comportamento já existente). Acrescente a chave (comentada/documentada) na tabela do README e,
  opcionalmente, em `config/default_case.json` com valor `0.0`.

**A.2 — Modelo (Pi).** Em `src/models/distributed_coil.py`, no caminho Pi:
- Hoje a KCL é `C_node · dV_k/dt = I_k − I_{k+1}` com `C_node` **diagonal**. A capacitância série
  `C_s` entre nós adjacentes injeta corrente `C_s · d(V_{k−1} − V_k)/dt`, acoplando os nós. Isso
  transforma a relação em `**C** · dV/dt = (correntes dos indutores e fontes)`, onde `**C**` é uma
  **matriz tridiagonal** constante (shunt na diagonal, `−C_s` nas off-diagonais).
- Monte `**C**` uma única vez no `__init__` (ela é constante). No `derivatives`, resolva
  `dV/dt = C⁻¹ · b` aplicando uma **fatoração pré-computada** (ex.: `scipy.linalg.lu_factor`/
  `lu_solve`, ou Cholesky via `cho_factor` já que `**C**` é simétrica positiva-definida). Não
  inverta a matriz a cada passo.
- A capacitância série por seção decorre de `C_series_total`: `N` capacitores série em cascata
  equivalem a `C_series_total` ponta-a-ponta ⇒ `C_s,sec = N · C_series_total`. **Derive e documente**
  essa relação no docstring; não chute. Confirme com um caso-limite (ver A.5).
- Quando `C_series_total == 0`, **pule** todo o acoplamento e use exatamente o caminho atual (a
  matriz vira diagonal e o resultado deve ser bit-idêntico ao de hoje). Garanta isso com um teste.
- O modelo **T** pode ficar fora do escopo da capacitância série nesta primeira rodada (documente a
  limitação); a narrativa central usa o Pi. Se incluir no T, mantenha a mesma disciplina.

**A.3 — Quantidades derivadas.** Exponha no `summary()`/resultados o **parâmetro de distribuição**
`α = sqrt(C_g / C_s)`, onde `C_g = C_total` (shunt total para terra) e `C_s = C_series_total`
(série equivalente). Trate `C_s → 0` (α → ∞, sem capacitância série efetiva entre espiras) e
`C_s → ∞` (α → 0, distribuição uniforme) de forma numericamente segura.

**A.4 — Distribuição inicial (eletrostática, t = 0⁺).** Implemente uma função que devolva a
distribuição **inicial** de tensão resolvendo a rede **puramente capacitiva** (indutores como
circuito aberto: corrente zero). Resolva o sistema linear capacitivo para `V(x)` dadas as condições
de contorno (`grounded`: neutro a 0; `open`/isolado: neutro flutuante). Isto produz a curva "initial
distribution" usada na cena nova, **sem** depender de extrair t≈0 de uma simulação transitória.

**A.5 — Validação analítica (teste novo, independente do ATP).** Adicione um teste que compare a
distribuição inicial **numérica** (A.4) com a **solução analítica clássica** da teoria de surtos em
enrolamentos (Greenwood, *Electrical Transients in Power Systems*; Blume & Boyajian):

- Neutro **aterrado**: `V(x)/V0 = sinh(α(1−x)) / sinh(α)`, com `x ∈ [0,1]`, `x = 0` na entrada.
- Neutro **isolado/aberto**: `V(x)/V0 = cosh(α(1−x)) / cosh(α)`.
- Fator de concentração na entrada: `α·coth(α)` (aterrado) e `α·tanh(α)` (isolado).

**Confirme a convenção** (origem de `x`, condição de contorno) contra a sua montagem antes de fixar
tolerâncias; o teste deve casar dentro de uma tolerância apertada para `N` grande (ex.: `N = 200`) e
convergir à medida que `N` cresce. Use este resultado também para sanar a relação `C_s,sec` de A.2.

**A.6 — ATP (opcional, P2).** Estender `surto_bobina.atp` com capacitância série entre nós e
revalidar é trabalho real e **opcional** nesta rodada. Se fizer, valide de verdade e siga as regras
invioláveis. Se **não** fizer, deixe explícito (no README e na cena de validação) que a validação
ATP cobre o caso somente-shunt, e que o caso com capacitância série é validado **analiticamente**
(A.5). Nunca apresente Python como ATP.

---

## Parte B — Saneamento de `manim_presentation.py`

**B.1 — Eliminar código morto / referências quebradas.** Decida, para cada cena hoje não usada:
*reativar e consertar* (entra no storyboard da Parte C) ou *remover*. Ao final **não pode existir**
nenhum método que referencie atributos inexistentes de `ProjectData`. Se uma cena reativada precisa
de dados (T-model, linhas ATP), **estenda `ProjectData` e o loader** para fornecê-los; caso
contrário, remova a cena. Remova também os métodos `_read_*` do loader se a decisão de fonte de
dados (B.2) for re-simular.

**B.2 — Fonte de dados única e explícita.** Escolha **uma** estratégia e documente no docstring do
módulo:
- (Recomendado) **Re-simular** dentro do Manim via `_simulate_manim_case`, agora parametrizado por
  `C_series_total` e por condição de contorno, para que a apresentação seja autocontida (não exige
  `python main.py` antes). Remova os `_read_*` mortos.
- *Ou* **ler os CSVs** de `output/` (consertando e usando os `_read_*`), assumindo a dependência de
  rodar `main.py` antes.
  Não mantenha as duas vias concorrentes.

**B.3 — Robustez de assets.** `coil()` e `tikz_ladder()` lançam `FileNotFoundError` se o PNG não
existir. Para os diagramas de circuito você precisará de uma variante TikZ **com capacitância série**
(ver C.4). Garanta um *fallback* claro (mensagem acionável com o comando de regeneração do PNG) ou um
desenho vetorial nativo de reserva, para a cena não morrer silenciosamente.

**B.4 — Performance dos updaters.** `always_redraw(make_profile)` recria a curva inteira a cada
frame e `make_dynamic_local_percentage_row` recomputa `segment_local_percentages` a cada frame. Para
janelas longas isso fica caro. Pré-amostre os perfis (matriz tempo×posição) uma vez e, nos updaters,
apenas **interpole/atualize pontos** (`set_points_smoothly`/`become` sobre mobjects existentes) em
vez de reconstruir `VGroup`s. Mantenha o resultado visual equivalente.

**B.5 — Parametrização de layout.** Extraia números mágicos de posição (`shift`, `buff`, larguras)
para constantes nomeadas no topo, como já existe para cores e janelas. Facilita manter o
alinhamento quando novas cenas entram.

**B.6 — Qualidade de render.** O cabeçalho sugere `-pql` (480p). Defina e documente um alvo de
entrega (ex.: `-qh`, 1080p, fps 30/60) e verifique que tudo permanece legível nesse alvo
(tamanhos de fonte, espessuras). Texto explicativo pode seguir em `Text` com fonte de sistema; use
`MathTex`/`Tex` para símbolos e equações.

---

## Parte C — Storyboard didático (em inglês)

> Conte uma história física coerente: **expectativa ingênua → fonte → modelo → distribuição inicial
> não-uniforme → evolução no tempo → condição de contorno → envelope de tensão máxima → estresse
> local → validação → mitigação → conclusões.** Cada cena deve ter uma legenda/narração curta que
> explique *o que olhar* e *por quê*. Mapeie para os métodos existentes onde possível (reaproveite
> `VisualFactory`, `metric_card`, `legend_item`, a régua dinâmica de percentuais etc.).

1. **Title / hook** (`opening_scene`, refinar). *"How does a surge distribute along a winding?"*
   Bobina + pulso entrando. Promete a resposta.

2. **The naive expectation** (`problem_scene`, reescrever). Mostre a hipótese ingênua: *"if it split
   evenly, each of the N sections would see V/N"* (régua uniforme). Encerre com o gancho: *"a fast
   front does not see the coil as one lumped inductor — it sees a capacitive network."*

3. **The impulse source** (`source_scene`, manter/refinar). Forma 1.2/50 µs, pontos notáveis (front,
   tail, peak). Já está polida; só ajuste textos para encaixar na narrativa.

4. **The ladder model** (`model_scene`, reescrever). Circuito com **capacitância série `C_s` (entre
   seções) e shunt `C_g` (para terra)**, destacando o papel de cada uma. Introduza
   `α = sqrt(C_g / C_s)` como *"the single number that controls how uneven the initial distribution
   is."* Requer o novo TikZ (C.4).

5. **Initial distribution (t = 0⁺)** — **CENA NOVA, núcleo da apresentação.** Plote `V(x)` inicial
   (dados de A.4) para alguns valores de α: `α → 0` (quase uniforme), α moderado e α alto
   (concentração forte na entrada). **Sobreponha a curva analítica** `sinh/cosh` (A.5) como prova de
   correção. Anote o **fator de concentração na entrada** (`α·coth α`). Mensagem: *"at the first
   instant the winding is a capacitive divider; the entrance turns take a disproportionate share."*

6. **Time evolution / travelling wave** (`travelling_wave_scene`, reativar e consertar, agora **com**
   capacitância série). Anime `V(x, t)` saindo do perfil inicial não-uniforme rumo ao perfil final
   (quase linear), com as oscilações no meio do caminho. Use a régua dinâmica de ΔV já existente.

7. **Boundary condition matters** (fundir `reflection_scene` + `grounded_return_scene`). Contraste
   **neutro aterrado** × **neutro isolado/aberto**: como muda a distribuição inicial, a reflexão e o
   pico de saída. Mantenha a honestidade do `transfer_ratio` (ligeiramente acima de 2 no caso aberto,
   ver hipótese 3 do README).

8. **Maximum-voltage envelope** — **CENA NOVA.** Plote o **envelope** `max_t |V(x, t)|` ao longo da
   posição: é isto que dimensiona o isolamento. Marque os *hotspots* (entrada e eventuais picos
   internos por oscilação). Conecte com a engenharia: *"this envelope, not the steady state, sets the
   insulation design."*

9. **Local dielectric stress** (derivar da régua dinâmica existente). Reinterprete o ΔV entre seções
   adjacentes como **estresse dielétrico turn-to-turn/disco-a-disco**. Deixe a métrica intuitiva:
   além do "% relativo à média", mostre o valor em **kV/seção** ou um "fator de sobretensão local".

10. **Validation** (`python_atp_scene`, consertar; adicionar painel analítico). Dois painéis
    honestos: (a) distribuição inicial **numérica × analítica** (A.5) — valida o recurso novo;
    (b) transiente **Python × ATP** — valida o caso somente-shunt já existente. Rotule o escopo de
    cada um sem exagero. Conserte a dependência de `self.data.atp_rows` (estenda o loader ou leia o
    CSV de comparação real).

11. **Mitigation** (CENA NOVA, breve — opcional). Uma frase + visual: **reduzir α** (enrolamentos
    entrelaçados/*interleaved*, anéis estáticos/*static shields*) **achata** a distribuição inicial.
    Fecha o ciclo "problema → causa → o que se faz na prática".

12. **Key takeaways** (`closing_scene`, reescrever os bullets para a nova narrativa). Ex.: (1) a um
    surto rápido a bobina responde como rede capacitiva; (2) α governa a não-uniformidade inicial;
    (3) a condição de contorno controla reflexão e pico; (4) o envelope de tensão máxima dimensiona o
    isolamento; (5) resultados validados (analítico para a distribuição inicial; ATP para o caso
    somente-shunt).

> A cena `pi_t_scene` (Pi × T) **não** é central para esta narrativa. Mantenha-a apenas como
> apêndice opcional **se** o loader for estendido para fornecer os dados do T; caso contrário,
> remova-a (regra B.1: nada de código morto que quebra).

---

## Parte D — Qualidade visual e acessibilidade

- **Daltonismo:** hoje vermelho/verde carregam significado semântico (open × grounded; barras de
  estresse). Adicione um segundo canal (rótulo de texto, forma, traço/preenchimento) para não
  depender só da cor.
- **Contraste:** verifique a legibilidade da paleta escura no alvo de render escolhido (B.6).
- **Consistência:** mantenha a paleta e a tipografia já definidas; reuse `VisualFactory`.
- **Ritmo:** transições e `wait()` suficientes para leitura; a cena central (5) e o envelope (8)
  merecem mais tempo de tela.

---

## Parte E — Validação e testes

- `tests/test_regression_outputs.py` passa **sem alterar** os valores esperados (caso default,
  `C_series_total = 0`).
- Novo teste: `C_series_total = 0` ⇒ resultados **bit-idênticos** ao caminho atual (mesma `Vpk_out`).
- Novo teste: distribuição inicial numérica × analítica `sinh/cosh` (A.5), com convergência em `N`.
- Testes de funções puras do Manim que não exigem render (ex.: `segment_local_percentages`,
  a montagem da distribuição inicial), para travar regressões sem depender de render headless.
- **Smoke render:** `manim -ql manim_presentation.py SurgePresentation` conclui **sem erro**; repita
  no alvo de entrega (`-qh`). Anexe a duração e o tamanho final do vídeo no relatório de execução.

---

## Critérios de aceitação

1. A apresentação renderiza ponta a ponta sem erros em `-ql` e no alvo de entrega.
2. Existe uma cena que mostra **claramente** a distribuição inicial não-uniforme a partir de **dados
   simulados reais**, sobreposta à curva analítica, para ≥ 2 valores de α.
3. Nenhum método morto e nenhuma referência a atributo inexistente de `ProjectData`.
4. Caso default (`C_series_total = 0`) reproduz `Vpk_out = 2039,3086 V` (tol. `1e-6`); regressões
   existentes intactas.
5. Toda curva é rastreável a uma simulação real ou a uma fórmula analítica rotulada; nenhum dado é
   apresentado como ATP sem `.pl4` real.
6. Cada cena tem legenda/narração explicativa em inglês; a história física flui na ordem da Parte C.
7. README atualizado: novo campo de config, nova estrutura da apresentação, e o que cada validação
   cobre.

---

## Fluxo de trabalho sugerido (commits temáticos)

1. **Baseline + testes congelados** (rodar `main.py`, registrar referências).
2. **A.1–A.3** capacitância série no config + modelo Pi (com guarda `C_s = 0` ⇒ idêntico).
3. **A.4–A.5** distribuição inicial + validação analítica (teste).
4. **B.1–B.2** remover código morto, fixar fonte de dados única, estender `ProjectData`.
5. **C.4 + assets** novo TikZ com capacitância série + robustez de assets (B.3).
6. **C.5 + C.8** cenas novas (distribuição inicial e envelope).
7. **C.2/C.6/C.7/C.9/C.10/C.12** reativar/consertar e reescrever o restante do storyboard.
8. **B.4–B.6 + D** performance, layout, qualidade de render, acessibilidade.
9. **Docs** README + relatório de execução (anexar smoke render).

---

## Armadilhas conhecidas

- Adicionar `C_series_total` sem incluí-lo no dataclass quebra `from_json` (chaves desconhecidas são
  rejeitadas). Adicione o campo **e** documente.
- A matriz de capacitância tridiagonal deve ser **fatorada uma vez**; invertê-la por passo destrói a
  performance e pode introduzir ruído numérico.
- `α·coth(α)` cresce ~linearmente com α: para α grande a entrada concentra quase toda a tensão —
  cheque a estabilidade numérica e os limites do gráfico nessa faixa.
- Não confunda **distribuição inicial** (capacitiva, não-uniforme) com **distribuição final**
  (indutiva/resistiva, quase linear): a história didática **é** a transição entre as duas.
- Manter a régua dinâmica de ΔV barata por frame (B.4) é o que evita renders longos.
