# CLAUDE.md

Orientações para o Claude Code ao trabalhar neste repositório. O `README.md` é a
documentação detalhada (em inglês, para humanos); este arquivo dá o panorama e as
convenções que não são óbvias só lendo o código.

## O que é este projeto

`surto-1` estuda **como a tensão de um surto (impulso 1,2/50 µs) se distribui ao longo
de uma bobina/enrolamento** modelado por parâmetros distribuídos (escada de `N=20`
seções Pi ou T, com `R`, `L`, capacitância shunt para terra `C_g` e, opcionalmente,
capacitância série entre espiras `C_s`). O fenômeno central: sob uma frente rápida o
enrolamento se comporta como uma **rede capacitiva**, a tensão **começa concentrada na
entrada** (distribuição inicial não uniforme) e depois **relaxa para um perfil quase
uniforme**.

O projeto tem **quatro produtos** que contam a mesma história:

1. **Simulador Python** (`src/`, `main.py`) — monta a rede em espaço de estados e
   resolve no tempo com `scipy.solve_ivp`; exporta CSV, figuras PNG e GIFs.
2. **Apresentação Manim** (`manim_presentation.py`, classe `SurgePresentation`) —
   apresentação didática que re-simula o modelo na hora; renderizada em 1080p60.
3. **Relatório LaTeX** (`relatorio/`) — documento técnico (em **português**) focado no
   comportamento físico da bobina, com animações embutidas (pacote `animate`).
4. **Deck ATP/EMTP** — o mesmo caso em ATP, para **validação cruzada** independente.

Há ainda uma apresentação **análoga para onda quadrada PWM de 20 kHz**
(`manim_square_wave.py`, `SquareWavePresentation`): cada borda do chaveamento é um
mini-surto que reconcentra a tensão na entrada (mesma `sinh`, α=5) — o estresse
repetitivo de isolamento em máquinas alimentadas por inversor. Reutiliza a
`VisualFactory`/helpers de `manim_presentation.py` (herda `SurgePresentation`) sem
modificá-lo, e usa a fonte `source_type="square"` do `ImpulseSource`. A onda quadrada
**não** tem validação ATP direta (o ATP não tem fonte de onda quadrada nativa — exigiria
TACS); usa-se **validação composta** (rede já validada por ATP no impulso × fonte validada
analiticamente × convergência numérica N=20 vs N=40), documentada em
`RELATORIO_VALIDACAO_ONDA_QUADRADA.md`.

## Dois casos físicos (não confundir)

- **Caso default / regressão** (`config/default_case.json`, `surto_bobina.atp`):
  terminação **aberta**, **somente shunt** (`C_series_total = 0`). É a base de
  regressão — `Vpk_out = 2039.3086 V`. **Não alterar** sem necessidade.
- **Caso do gerador** (foco atual da apresentação e do relatório):
  neutro **solidamente aterrado** (`termination="grounded"`) **com capacitância série**
  (`C_series_total = 40 pF`), parâmetro de distribuição **α = √(C_g/C_s) = 5**.
  Arquivos: `surto_bobina_gerador.atp`, `config/gerador_aterrado.json`.
  Resultado-chave: pico interno em N5 ≈ 1108 V (> 1 kV de entrada).

## Conceitos físicos-chave

- **α = √(C_g/C_s)** controla a desigualdade da distribuição inicial. α grande →
  concentração na entrada; α → 0 → uniforme. O gerador tem `C_g` grande (barra na
  ranhura aterrada), logo α elevado.
- **Distribuição inicial em t=0⁺**: `sinh(α(1−x))/sinh(α)` (aterrado),
  `cosh(α(1−x))/cosh(α)` (aberto). Fator de concentração na entrada `α·coth α`.
- `C_s_sec = N · C_series_total` (N capacitores de ramo em cascata equivalem ao total
  ponta-a-ponta). No deck ATP, isso são 800 pF por ramo.

## Comandos principais

```bash
python main.py                         # simulação do caso default -> output/
python -m pytest                       # suíte de testes (waveform, regressão, física)

# Caso do gerador: ATP + validação cruzada
python scripts/gen_deck_gerador.py     # (re)gera surto_bobina_gerador.atp (coluna fixa)
python run_atp.py --atp-file surto_bobina_gerador.atp --out output/atp_gerador
python scripts/compare_python_atp.py --config config/gerador_aterrado.json \
       --pl4 surto_bobina_gerador.pl4 --out output/atp_gerador

# Apresentações Manim (manim.cfg ja fixa 1080p60; use -ql para previa rapida)
python -m manim render manim_presentation.py SurgePresentation
python -m manim render manim_square_wave.py SquareWavePresentation   # onda quadrada PWM 20 kHz

# Relatório LaTeX (figuras + animações + PDF)
python scripts/gen_figuras_relatorio.py
cd relatorio && latexmk -pdf relatorio.tex
```

## Convenções e cuidados

- **Idioma:** o relatório LaTeX e a comunicação com o usuário são em **português**; a
  apresentação Manim e o `README.md`/código são em **inglês**. As animações do relatório
  são trechos do Manim (legendas em inglês) com captions em português ao redor.
- **Validação ATP é real, nunca fabricada.** Uma curva só é "ATP" se vier de um `.pl4`
  gerado por execução bem-sucedida do `tpbigG.exe` (default
  `C:\ATP\ATP\GNUATP\tpbigG.exe`, ou via `--atp-exe`/`ATP_EXE`). O deck ATP usa
  **formato de coluna fixa** (BUS1 3-8, BUS2 9-14, R 27-32, L 33-38, C 39-44) — um campo
  fora de coluna causa `KILL`. Por isso o deck é gerado por script. A validação cruzada do
  gerador está em `RELATORIO_VALIDACAO_ATP_GERADOR.md` (picos ≤0,03 %); a da onda quadrada,
  por composição, em `RELATORIO_VALIDACAO_ONDA_QUADRADA.md`.
- **Mensagens de commit sem acentuação** (padrão do histórico do projeto).
- **Animações do PDF:** cenas standalone `InitialDistributionScene` e
  `GroundedReturnPreview` (Manim) → mp4 720p → frames PNG (`ffmpeg`, fps baixo) →
  `\animategraphics`. Conferir que o índice final `{1}{N}` bate com o nº de PNGs.
- **Não versionado** (`.gitignore`): `output/`, `media/`, `relatorio/frames/`,
  `relatorio/relatorio.pdf`, `*.pl4`/`*.lis`, `assets/*.pdf`. São regeneráveis.
- Cultura do projeto: **rigor e auditoria** — preferir honestidade sobre o que foi
  validado a um número bonito; commits pequenos e temáticos.

## Onde está o quê

Estrutura completa em `README.md` (seção *Project structure*). Resumo: modelo físico em
`src/models/distributed_coil.py`; solver em `src/solvers/`; fonte de surto em
`src/sources/impulse_source.py`; scripts utilitários em `scripts/`; testes em `tests/`;
relatório em `relatorio/` (seções em `relatorio/sections/`).
