# Prompt executável — Apresentação Manim análoga para ONDA QUADRADA (PWM) de 20 kHz

Você é um agente encarregado de **criar uma apresentação Manim nova, análoga à do surto**, porém para
uma **onda quadrada de 20 kHz** aplicada à **mesma bobina** (enrolamento de gerador síncrono, neutro
solidamente aterrado, com capacitância série, **α = 5**). O trabalho do surto
(`manim_presentation.py`, classe `SurgePresentation`) **permanece intacto**; esta é uma peça paralela,
em um **arquivo Python novo** (`manim_square_wave.py`).

A entrega é **um novo arquivo de apresentação** + o suporte mínimo no modelo (uma fonte de onda
quadrada, adicionada de forma aditiva). Nada do caso do surto pode ser perdido ou alterado.

O projeto é de **engenharia elétrica**, com cultura de auditoria e reprodutibilidade. **Rigor físico e
honestidade sobre o que cada curva representa valem mais do que vistosidade.**

---

## A física (por que uma onda quadrada de 20 kHz importa)

Uma onda quadrada de 20 kHz (período **T = 50 µs**) é o sinal de saída de um **inversor PWM** que
alimenta máquinas elétricas. O ponto central:

- **Cada borda da onda quadrada é um mini-surto.** A transição rápida (alto `dv/dt`) contém um espectro
  de alta frequência que enxerga o enrolamento como uma **rede capacitiva** — exatamente como a frente
  do impulso 1,2/50 µs. No instante de cada borda, a tensão se distribui de forma **não uniforme**,
  concentrada na entrada, segundo `v(x)/V_0 = sinh(α(1−x))/sinh(α)` (aterrado), com o mesmo
  `α = √(C_g/C_s) = 5`.
- **A diferença em relação ao surto é a repetição.** O impulso é um evento único; a onda quadrada
  **repete a concentração a cada borda**, 40 000 vezes por segundo (2 bordas por período × 20 kHz).
  Esse estresse **repetitivo** na isolação de entrada é o mecanismo de envelhecimento/falha de
  isolamento em máquinas alimentadas por inversor (problema clássico de `dv/dt`/PWM, agravado por
  reflexão em cabos longos).
- **Conexão didática com o surto:** a resposta a **uma** borda é idêntica à do surto (mesma
  distribuição inicial). A apresentação da onda quadrada acrescenta o **regime repetitivo**: a cada
  semiperíodo a tensão concentra-se na entrada e relaxa para quase uniforme antes da próxima borda
  (T/2 = 25 µs ≫ tempo de propagação ≈ 3,16 µs, então há relaxação visível entre bordas).

Essa é a narrativa: **a mesma bobina, agora sob chaveamento PWM** — cada borda re-concentra a tensão na
entrada; a repetição é o que estressa o isolamento de drives.

---

## Decisões já tomadas (não re-perguntar)

1. **Mesma bobina/caso do gerador:** escada Pi `N = 20`, neutro **aterrado**, **com** capacitância
   série (`C_series_total = 40 pF`), **α = 5**. Reusar `config/gerador_aterrado.json` como base.
2. **Idioma da apresentação:** **inglês** (igual ao surto). Comentários de código e este prompt em
   português.
3. **Onda quadrada:** **unipolar** 0 → `V_amplitude` (1 kV), frequência **20 kHz**, com **tempo de
   borda finito** `t_rise` (forma trapezoidal) para `dv/dt` realista e estabilidade numérica.
   Excursão por borda Δv = 1 kV — comparável ao pico do surto.
4. **Arquivo novo:** `manim_square_wave.py`, classe `SquareWavePresentation`. **Reutilizar**
   (importar) os utilitários de `manim_presentation.py` (`VisualFactory`, cores, helpers) **sem
   modificá-lo**.
5. **Fonte aditiva:** adicionar `source_type = "square"` ao `ImpulseSource` **sem alterar** o
   comportamento de `double_exp`/`ramp_exp` (regressão preservada bit-a-bit).

---

## Leitura obrigatória antes de editar

- `manim_presentation.py` — `VisualFactory`, `ProjectDataLoader`, a estrutura das 5 cenas e as cenas
  standalone (`InitialDistributionScene`, `GroundedReturnPreview`). É o gabarito de estilo a espelhar.
- `src/sources/impulse_source.py` — `__call__`, `derivative`, `evaluate_array`, `peak_time`,
  `source_type`. A onda quadrada entra aqui.
- `src/models/distributed_coil.py` — `initial_voltage_distribution` (a distribuição por borda) e como a
  capacitância série usa `source.derivative(t)`.
- `src/solvers/time_domain_solver.py` — como a fonte é chamada no tempo.
- `src/utils/simulation_config.py` — onde adicionar o parâmetro de frequência.
- `CLAUDE.md` — convenções (idiomas, validação real, commits sem acento).

---

## Regras invioláveis

- **Surto intacto.** Não modificar `manim_presentation.py`, `config/default_case.json`,
  `surto_bobina*.atp`, nem quebrar a regressão (`Vpk_out = 2039.3086 V`). A fonte nova é **aditiva**.
- **Nada de resultado fabricado.** Todas as curvas vêm do solver real (`src/`) ou de fórmula analítica
  rotulada.
- **Importar, não duplicar.** `manim_square_wave.py` importa `VisualFactory`/helpers de
  `manim_presentation.py`. Importar o módulo **não** pode disparar render (ele só define classes; as
  cenas rodam via CLI do Manim) — confirme.
- **Caminhos relativos**; reutilize o asset `assets/tikz_ladder_grounded_circuit.png` para o circuito.
- **Commits pequenos e temáticos**, mensagens **sem acentuação** (padrão do projeto). Sugestão: (1)
  fonte square + teste; (2) apresentação `manim_square_wave.py`.

---

## Parte 1 — Fonte de onda quadrada (`src/sources/impulse_source.py`)

Adicione `source_type = "square"` de forma aditiva. Parâmetros: amplitude, **frequência** (novo;
default 20 kHz) e **tempo de borda** `t_rise` (reutilize `t_front` como `t_rise`). Forma trapezoidal
unipolar, começando a subir em `t = 0`:

```
T  = 1 / frequency           # 50 us @ 20 kHz
tl = t mod T                 # tempo dentro do período
       __call__(t)                              derivative(t)
tl < t_rise        : A * tl / t_rise            +A / t_rise   (borda de subida)
t_rise <= tl < T/2 : A                           0            (plato alto)
T/2 <= tl < T/2+tr : A * (1 - (tl-T/2)/t_rise)  -A / t_rise   (borda de descida)
senao              : 0                            0            (plato baixo)
```

Requisitos:
- Estender `__init__` com `frequency` (default `20000.0`), usado **apenas** quando
  `source_type == "square"`; manter a assinatura compatível para os tipos existentes.
- Implementar `__call__`, `derivative` (analítica, como acima), `evaluate_array` (vetorizado) e
  `peak_time` (defina como `t_rise`, instante em que atinge `A` pela primeira vez) para o tipo square.
- Adicionar `"square"` à validação de `source_type`.
- **Config:** adicionar `f_square` (Hz, default `20000`) a `SimulationConfig` (validado `> 0`) e
  encaminhar à `ImpulseSource` quando `source_type == "square"`.
- **Teste novo** `tests/test_square_source.py`: período correto (50 µs @ 20 kHz); amplitude atingida;
  bordas com `dv/dt = ±A/t_rise`; platôs com derivada nula; periodicidade (`v(t) == v(t+T)`); e um
  **teste de regressão** garantindo que `double_exp` e `ramp_exp` permanecem idênticos (mesmos valores
  de antes em alguns instantes).

---

## Parte 2 — Apresentação Manim (`manim_square_wave.py`)

Espelhe a estrutura de `SurgePresentation`. Importe o que puder de `manim_presentation` (cores,
`VisualFactory`, e — se conveniente — adapte um carregador que simule o caso **com a fonte square**,
mantendo `termination="grounded"` e `C_series_total` para `α = 5`). Janela de simulação ≥ **2–3
períodos** (≥ 100–150 µs) com `dt` que **resolva `t_rise`** (≥ ~10–20 passos por borda; se ficar stiff,
use `solver_method="Radau"`).

Cenas (em inglês), análogas às do surto:

1. **Title** — a PWM square wave (20 kHz) hitting the same winding.
2. **Source** — a onda quadrada 20 kHz: período, bordas rápidas, `dv/dt = A/t_rise`. Contraste com o
   impulso único do surto ("um evento" × "um trem de bordas"). Opcional: ilustrar o conteúdo
   harmônico (bordas ⇒ altas frequências).
3. **Circuit** — o mesmo ladder aterrado com `C_s`/`C_g` (reutilize
   `assets/tikz_ladder_grounded_circuit.png`).
4. **One edge = one surge** — cada borda reproduz a distribuição inicial `sinh(α(1−x))/sinh(α)`
   (reutilize `DistributedCoil.initial_voltage_distribution`); destaque que é **idêntica** à do surto,
   com `α = 5`.
5. **Time evolution under the pulse train** — *animação principal*: a tensão de entrada chaveia em
   20 kHz; a distribuição ao longo do enrolamento **concentra-se na entrada a cada borda e relaxa**
   antes da próxima. Mostre o caráter **repetitivo** (várias bordas) e o envelope de `ΔV` por seção.
6. **Conclusion** — estresse **repetitivo** de isolamento em máquinas alimentadas por inversor: o
   `dv/dt` de cada borda concentra a tensão na entrada, 40 000×/s; daí filtros `dv/dt`, cabos curtos e
   isolamento reforçado de entrada. Conecte de volta ao surto (mesmo mecanismo, agora repetido).

Inclua **classes standalone** para preview rápido (ex.: `SquareSourceScene`,
`SquareEvolutionPreview`), no espírito de `InitialDistributionScene`/`GroundedReturnPreview`.

---

## Parte 3 — Render e validação

```bash
# previa rapida de uma cena
python -m manim render -ql manim_square_wave.py SquareWavePresentation
# entrega (manim.cfg ja fixa 1080p60)
python -m manim render manim_square_wave.py SquareWavePresentation
python -m pytest tests/test_square_source.py   # e a suite completa para a regressao
```

- **Sanidade física:** confirme que a tensão de entrada é a onda quadrada 20 kHz (período 50 µs,
  bordas `t_rise`) e que a distribuição no instante de cada borda bate com `sinh(α(1−x))/sinh(α)` —
  **a mesma** do surto (conexão entre as duas apresentações).
- **Regressão:** `python -m pytest` deve continuar passando, inclusive a regressão do surto
  (`Vpk_out = 2039.3086 V`) e os testes de `double_exp`/`ramp_exp`.

---

## Critérios de aceitação

1. `manim_square_wave.py` renderiza `SquareWavePresentation` **sem erros**.
2. `ImpulseSource` ganha `source_type="square"` (20 kHz, bordas `t_rise`, unipolar 0→1 kV) com
   `derivative` analítica; `double_exp`/`ramp_exp` **inalterados** (teste de regressão).
3. **Surto intacto:** `manim_presentation.py`, `config/default_case.json`, decks ATP e a regressão
   2039 V não foram tocados.
4. Narrativa **análoga e fisicamente correta**: cada borda = surto; distribuição inicial `sinh`
   idêntica; ênfase no estresse **repetitivo** de PWM e `dv/dt`.
5. A apresentação **reutiliza** utilitários de `manim_presentation.py` **sem modificá-lo**; importar o
   módulo não dispara render.
6. `tests/test_square_source.py` cobre período, amplitude, bordas, periodicidade e regressão.

---

## Armadilhas conhecidas

- **Não quebrar a regressão:** a fonte é aditiva; o `__init__` não pode exigir `frequency` para os
  tipos antigos (use default).
- **Bordas íngremes ⇒ rigidez numérica:** `t_rise` finito (não zero) e `dt` resolvendo a borda; se o
  RK45 sofrer, troque para `Radau`.
- **Janela curta demais:** simule ≥ 2–3 períodos (≥ 100–150 µs) para o regime repetitivo aparecer; a
  relaxação entre bordas só é visível porque T/2 = 25 µs ≫ 3,16 µs de propagação.
- **Acoplamento ao surto:** importar `manim_presentation` para reusar helpers é desejável, mas garanta
  que o import seja barato e sem efeitos colaterais (sem render no nível de módulo).
- **`peak_time` da square:** defina-o (ex.: `t_rise`) para não quebrar código da apresentação que
  marca o "pico" da fonte.
- **Idioma:** apresentação em inglês; não traduzir os rótulos internos das cenas.
```
