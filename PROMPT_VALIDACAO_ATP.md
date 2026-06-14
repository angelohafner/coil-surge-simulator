# Prompt executável — Validação cruzada Python × ATP do caso do gerador (neutro solidamente aterrado, com capacitância série)

Você é um agente encarregado de **validar o modelo Python (`src/`) do projeto `surto-1` contra o ATP**
para o caso que a apresentação realmente mostra: o enrolamento de um **gerador síncrono com neutro
solidamente aterrado**, modelado como escada Pi de `N = 20` seções **com capacitância série
turn-to-turn** (`C_s`) além da capacitância shunt para terra (`C_g`).

O fluxo é, **nesta ordem**:

1. **Primeiro rodar o ATP** sobre um deck que represente esse caso (o deck atual ainda **não** o
   representa — ver abaixo);
2. **Depois conferir** o resultado do `src/` contra o `.pl4` real gerado pelo ATP, com métricas
   quantitativas por nó.

O projeto é de **engenharia elétrica** (transitórios), com forte cultura de auditoria e
reprodutibilidade. **Rigor e honestidade sobre o que foi validado valem mais do que um número bonito.**

---

## Contexto técnico — decisões já tomadas (não re-perguntar)

1. **Caso físico:** gerador síncrono, **neutro solidamente aterrado** ⇒ terminação **grounded**
   (`V(N20) = 0`). A distribuição inicial segue `sinh(α(1−x))/sinh(α)`.
2. **Capacitância série incluída.** O modelo Python usa `C_series_total` (capacitância série
   equivalente ponta-a-ponta do enrolamento). A apresentação usa **α = 5**, ou seja
   `C_series_total = C_total / α² = 1e-9 / 25 = 4.0e-11 F = 40 pF`, com
   `α = sqrt(C_g/C_s) = sqrt(C_total / C_series_total) = sqrt(1nF / 40pF) = 5`.
3. **Idioma:** este documento, os comentários do deck e o relatório ficam em **português**.
4. **Não destruir a validação existente.** O deck atual `surto_bobina.atp` valida o caso
   **open / somente-shunt** e está documentado. **Crie um deck novo** (`surto_bobina_gerador.atp`)
   para o caso aterrado-com-série; **não** sobrescreva o deck original.

### Parâmetros numéricos do caso (fixos)

| Grandeza | Valor total | Por seção (N=20) | No deck ATP (XOPT=0→mH, COPT=0→µF) |
|---|---|---|---|
| Indutância série | `L_total = 10 mH` | `L_sec = 0.5 mH` | `0.5` (col 33-38) |
| Resistência série | `R_total = 5 Ω` | `R_sec = 0.25 Ω` | `0.25` (col 27-32) |
| Capacitância shunt p/ terra `C_g` | `C_total = 1 nF` | `50 pF` interno · `25 pF` nos extremos | `5.E-5` · `2.5E-5` (col 39-44) |
| **Capacitância série `C_s`** | `C_series_total = 40 pF` (ponta-a-ponta) | **`C_s,sec = N·C_series_total = 20×40pF = 800 pF`** | **`8.E-4`** (col 39-44) |
| Terminação | **grounded** (`V(N20)=0`) | — | aterrar N20 (ver 1.2) |
| Fonte | dupla-exponencial 1,2/50 µs, pico ~1 kV | — | tipo 15: `A1=1035.1`, `A=-13863`, `B=-2.5E6` |

> **Atenção (armadilha nº 1):** `C_series_total` (40 pF) é a capacitância série **equivalente
> ponta-a-ponta**; o valor de **cada capacitor de ramo entre nós adjacentes** é
> `C_s,sec = N · C_series_total = 800 pF`, porque `N` capacitores em série equivalem a
> `C_series_total`. **Não** lance 40 pF entre cada par de nós — isso daria um α errado. Confirme
> derivando 1/C_eq = Σ(1/C_s,sec) = N/C_s,sec.

---

## Leitura obrigatória antes de tocar em qualquer arquivo

- `surto_bobina.atp` — entender o formato de coluna fixa que **funciona** (use-o como gabarito).
- `run_atp.py` — como o ATP é invocado (`tpbigG.exe`, env `ATP_EXE`), como o `.pl4` é lido
  (`read_pl4`, formato PISA/GNU) e como localizar a saída; aceita `--atp-file` e `--pl4`.
- `scripts/compare_python_atp.py` — a comparação por nó (CSV + PNG); aceita `--config`, `--pl4`,
  `--out`. Note o `NODE_MAP = {0:N0, 5:N5, 10:N10, 15:N15, 20:N20}` e a checagem analítica da fonte.
- `src/models/distributed_coil.py` — confirme a relação `C_s,sec = N·C_series_total` no docstring e
  como a terminação `grounded` fixa `V(N20)=0`.
- `config/default_case.json` — gabarito de config (tem `termination:"open"`, `C_series_total:0.0`).

---

## Regras invioláveis

- **Nada de resultado fabricado.** Uma curva só pode ser chamada de "ATP" se vier de um `.pl4`
  realmente gerado por uma execução **bem-sucedida** do ATP. Se o ATP não rodar (executável ausente,
  KILL, etc.), **pare e relate o erro** — não invente números nem rotule Python como ATP.
- **Consistência total de parâmetros** entre o deck ATP e o config Python usado na comparação:
  mesmos `R/L/C_g/C_s` por seção, mesma terminação, mesma fonte, mesma janela de tempo. Qualquer
  divergência invalida a comparação.
- **Formato de coluna fixa** do ATP é sagrado (ver Parte 1.3). O deck original já abortou com
  `KILL = 6` por um campo fora de coluna; não repita o erro.
- **Sem caminhos absolutos** em código versionado; o executável do ATP vem de `--atp-exe` ou da env
  `ATP_EXE` (já suportado por `run_atp.py`).
- **Não alterar** `config/default_case.json` nem o deck `surto_bobina.atp` (preservam a regressão e a
  validação open/shunt-only existentes). Crie arquivos **novos**.
- **Commits pequenos e temáticos**, em português (ex.: 1 commit do deck novo, 1 do config + execução
  da comparação, 1 do relatório).

---

## Parte 1 — Criar o deck ATP do caso do gerador  (`surto_bobina_gerador.atp`)

Copie `surto_bobina.atp` como ponto de partida e faça **três** mudanças. Mantenha o cartão misc.
(`dT=1.E-8`, `Tmax=2.E-4`, `XOPT=0`, `COPT=0`, `ICAT=1`, `IPLOT=1`) e a fonte tipo 15 **inalterados**.

### 1.1 — Adicionar a capacitância série `C_s` entre nós adjacentes

Há **20** ramos capacitivos série (um por seção), entre `N0–N1`, `N1–N2`, …, `N19–N20`, cada um com
`C = 8.E-4` µF (= 800 pF). São **ramos entre dois nós** (BUS1 **e** BUS2 preenchidos), com `R` e `L`
em branco e `C` nas colunas 39-44.

### 1.2 — Aterrar o neutro (`V(N20) = 0`)

Imponha `V(N20) = 0` da forma mais robusta no ATP. Opção recomendada: um **ramo de aterramento de
impedância desprezível** de `N20` à referência (BUS2 em branco), p.ex. `R = 1.E-6` ohm. Alternativa:
levar o último ramo R-L de `N19` diretamente à referência (eliminando o nó N20). Em qualquer caso,
**confirme no `.pl4`** que `V(N20) ≈ 0` (poucos volts no máximo). O shunt de 25 pF em N20 fica
curto-circuitado e torna-se irrelevante — pode mantê-lo por simetria.

### 1.3 — Respeitar o formato de coluna fixa (CRÍTICO)

```
C  Régua de colunas (igual ao deck que funciona):
C  1234567890123456789012345678901234567890123456
C    BUS1  BUS2  <--- ref 15-26 --->R[ohm]L[mH] C[uF]
C  --- exemplo de ramo R-L série (já existe no deck) ---
  N0    N1                  0.25   0.5
C  --- exemplo de capacitor SÉRIE entre nós (NOVO): C em col 39-44 ---
  N0    N1                              8.E-4
C  --- exemplo de capacitor SHUNT p/ terra (BUS2 vazio, já existe) ---
  N1                                   5.E-5
```

- BUS1 → colunas **3-8**; BUS2 → **9-14**; R → **27-32**; L → **33-38**; C → **39-44**.
- Confira cada cartão novo contra a régua. Um caractere fora de coluna ⇒ `KILL`.

---

## Parte 2 — Rodar o ATP

```
python run_atp.py --atp-file surto_bobina_gerador.atp --out output/atp
```

- Defina o executável via env `ATP_EXE` ou `--atp-exe "C:\...\tpbigG.exe"` se não estiver no caminho
  default.
- O `run_atp.py` aborta com mensagem clara em caso de `KILL` ou se o `.pl4` não for gerado
  (verifique `ICAT=1`). O `.pl4` esperado é `surto_bobina_gerador.pl4`.
- **Sanidade imediata:** abra o HTML/`.pl4` e confirme (a) `V(N0)` é a dupla-exponencial 1,2/50 µs;
  (b) `V(N20) ≈ 0` (terminação aterrada); (c) os nós internos mostram a frente e a relaxação.

---

## Parte 3 — Alinhar o lado Python e comparar

### 3.1 — Config Python espelhando o deck

Crie `config/gerador_aterrado.json` idêntico ao `default_case.json`, **exceto**:

```json
"termination": "grounded",
"C_series_total": 4e-11
```

(`4e-11 F = 40 pF` ponta-a-ponta ⇒ α = 5; o solver deriva `C_s,sec = N·C_series_total` internamente.)

### 3.2 — Rodar a comparação

```
python scripts/compare_python_atp.py --config config/gerador_aterrado.json \
       --pl4 surto_bobina_gerador.pl4 --out output/atp
```

- O script já: confere `V(N0)` do ATP contra a dupla-exponencial analítica (sanidade da fonte);
  re-simula o Python na **mesma janela** do `.pl4`; e calcula, por nó, diferença de pico, erro máximo
  e RMS na janela completa e na janela inicial (frente + 1ª reflexão).
- Saídas: `output/atp/comparacao_python_atp.{csv,png}`. **Considere** renomear/`--out` para não
  sobrescrever a comparação do caso open existente (p.ex. `output/atp_gerador/`).
- Como `V(N20)=0` nos dois lados, a linha de N20 terá erro ~0 — isso é esperado e correto, não um
  bug.

---

## Parte 4 — Conferir e relatar

Produza um relatório curto (`RELATORIO_VALIDACAO_ATP_GERADOR.md`) com:

1. **Tabela por nó** (do CSV): pico Python × pico ATP, diferença de pico (%), erro máx e RMS
   (em V e em % de 1 kV), na janela completa e na inicial.
2. **Veredito honesto.** Espera-se concordância apertada (o método numérico ATP=trapezoidal e
   Python=RK45 sobre a **mesma** rede), na mesma ordem da validação open/shunt-only já existente
   (picos com diferença de ordem ~0,01–0,1 %). Há uma diferença **sistemática** de ~0,003 % porque a
   fonte do deck usa `A1=1035.1` (pico ~999,97 V) e o Python normaliza para 1000,0 V exatos — declare
   isso. Se algum nó destoar muito, **investigue** (alinhamento de coluna, valor de `C_s,sec`,
   terminação) antes de aceitar.
3. **Escopo do que foi validado.** Deixe explícito: este resultado valida o caso **grounded + série
   (α=5)**; a validação **open / somente-shunt** continua coberta pelo deck `surto_bobina.atp`
   original. Nada de generalizar além disso.
4. **Figura** `comparacao_python_atp.png` (Python × ATP por nó) anexada/citada.

---

## Armadilhas conhecidas

- **`C_s,sec = N·C_series_total = 800 pF`**, não 40 pF, entre cada par de nós (armadilha nº 1, acima).
- **Coluna fixa**: R/L/C têm posições rígidas (27-32 / 33-38 / 39-44). Capacitor série tem BUS1 **e**
  BUS2; capacitor shunt tem só BUS1 (BUS2 vazio = terra).
- **XOPT=0 ⇒ L em mH** (0,5 e não 5.E-4) e **COPT=0 ⇒ C em µF** (800 pF = `8.E-4`, 50 pF = `5.E-5`).
- **Aterramento de N20**: confirme `V(N20)≈0` no `.pl4`; um R de aterramento grande demais deixaria
  resíduo de tensão e falsearia a comparação.
- **Janela de tempo**: o Python deve simular até o `t_max` do `.pl4` (o `compare_*` já faz isso a
  partir de `t_atp[-1]`); não compare janelas diferentes.
- **Não confundir** este caso (grounded + série) com o caso open/shunt-only do deck antigo: são
  duas validações distintas, cada uma com seu deck e seu CSV.

---

## Critérios de aceitação

1. `surto_bobina_gerador.atp` roda no ATP **sem KILL** e gera `surto_bobina_gerador.pl4` com
   `V(N0)` = dupla-exponencial e `V(N20) ≈ 0`.
2. `config/gerador_aterrado.json` espelha exatamente o deck (grounded, `C_series_total=4e-11`).
3. `compare_python_atp.py` roda e produz CSV + PNG do caso do gerador, com diferença de pico por nó
   na mesma ordem de grandeza da validação existente.
4. Relatório com tabela, veredito honesto e escopo claro; nenhum dado Python rotulado como ATP.
5. Deck e config originais **intactos**; commits pequenos e temáticos em português.
