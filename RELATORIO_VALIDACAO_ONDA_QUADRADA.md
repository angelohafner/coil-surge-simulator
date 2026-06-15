# Validação da resposta à onda quadrada (PWM 20 kHz) — validação composta

**Data:** 15/06/2026 · **Caso:** bobina do gerador (neutro aterrado, com capacitância série,
α = √(C_g/C_s) = 5) sob **onda quadrada trapezoidal 0→1000 V, 20 kHz, borda t_rise = 0,2 µs**.

## Por que não há uma rodada ATP direta deste caso

O ATP/EMTP **não possui uma fonte de onda quadrada analítica** (os tipos 11–15 cobrem degrau, rampa,
senoide e dupla-exponencial). A única forma de uma onda quadrada periódica trapezoidal é via **TACS**
(fonte tipo 60 controlada por uma expressão FORTRAN). A montagem do cartão TACS em **formato de coluna
fixa**, sem o ATPDraw (que geraria o deck automaticamente) nem o rule book completo, foi rejeitada pelo
ATP (`FREFIX: Illegal data in column 3`). Como a rede subjacente já está cross-validada com ATP
(abaixo), optou-se pela **validação composta** em vez de insistir no formato TACS.

## A resposta é a convolução determinística (rede × fonte) — e ambos os fatores estão validados

A tensão em cada nó é a resposta da rede linear à fonte aplicada. Os **dois fatores independentes**
estão validados separadamente:

### 1. A rede — validada com ATP (cross-validação independente)

A rede é **exatamente a mesma do caso do gerador**: escada Pi N = 20, ramos R–L, capacitância série
`C_s` entre nós, capacitância shunt `C_g`, neutro solidamente aterrado, α = 5. Essa rede foi
confrontada nó a nó com o ATP no impulso 1,2/50 µs (ver
[RELATORIO_VALIDACAO_ATP_GERADOR.md](RELATORIO_VALIDACAO_ATP_GERADOR.md)):

| Métrica | Resultado |
|---|---|
| Diferença de pico por nó | +0,003 % (sistemática, da fonte) |
| Erro pontual (janela 0–30 µs) | ≤ 0,011 % de 1 kV |
| V(N20), neutro aterrado | 0 V nos dois solvers |

**A onda quadrada não altera a rede — só troca a forma de onda da fonte.**

### 2. A fonte — validada analiticamente

A fonte `source_type="square"` ([src/sources/impulse_source.py](src/sources/impulse_source.py)) é
verificada em [tests/test_square_source.py](tests/test_square_source.py): período (50 µs), amplitude
(1 kV), bordas trapezoidais e `dv/dt = ±V/t_r` nas subidas/descidas, periodicidade, equivalência
`evaluate_array` × chamada escalar, e **regressão** (as fontes `double_exp`/`ramp_exp` permanecem
bit-idênticas).

### 3. A distribuição inicial a cada borda — validada contra a teoria clássica

Cada borda da onda quadrada impõe, no limite capacitivo, a distribuição
`v(x)/V₀ = sinh(α(1−x))/sinh(α)`, validada em
[tests/test_initial_distribution.py](tests/test_initial_distribution.py) contra a solução analítica
clássica de surtos em enrolamentos (erro < 5×10⁻³).

## Verificação direta de convergência numérica (N = 20 vs N = 40)

Como métrica concreta deste caso, a onda quadrada foi simulada com **20 e 40 seções** (duas
discretizações da mesma bobina física). Os picos por posição convergem:

| Posição | Pico N = 20 | Pico N = 40 | Diferença |
|---|---|---|---|
| N0 (0 %) | 1000,0 V | 1000,0 V | 0,00 % |
| 25 % | 1484,0 V | 1488,8 V | −0,32 % |
| 50 % | 1550,4 V | 1555,9 V | −0,35 % |
| 75 % | 1061,2 V | 1073,2 V | −1,12 % |
| N20 (100 %) | 0,0 V | 0,0 V | — (aterrado) |

A discretização está **convergida** (≤ 1,1 %); a solução de N = 20 (a da apresentação) é confiável.

## O que a simulação mostra (física)

Os picos internos da onda quadrada (≈ **1550 V no meio do enrolamento**, > 1,5× a entrada de 1 kV)
são **maiores que os do impulso único** (N5 ≈ 1108 V): o trem de pulsos repetitivo (2 bordas por
período × 20 kHz) reexcita as ressonâncias da rede a cada borda, acumulando estresse. É exatamente o
mecanismo de envelhecimento do isolamento de entrada em máquinas alimentadas por inversor que a
apresentação `manim_square_wave.py` ilustra.

## Escopo e limitação (honestidade sobre o que foi validado)

- Esta é uma **validação composta**: a rede está validada por ATP (caso impulso) e a fonte por testes
  analíticos. **Não** é uma validação ATP *direta* da forma de onda quadrada.
- O efeito de **superposição entre bordas** (quando uma borda chega antes da relaxação completa da
  anterior) não foi cross-validado diretamente com ATP. Como T/2 = 25 µs ≫ tempo de propagação
  ≈ 3,16 µs, a rede quase relaxa entre bordas e a superposição é de segunda ordem — mas isso é um
  argumento físico, não uma medida ATP.
- **Para uma validação ATP direta no futuro:** gerar o deck TACS no **ATPDraw** (que produz o formato
  de coluna fixa correto da fonte tipo 60 + expressão FORTRAN) e rodá-lo com `run_atp.py`, comparando
  com `simulate_square()` via um script análogo ao `compare_python_atp.py`.
