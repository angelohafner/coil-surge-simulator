# Prompt executável — Reescrever o relatório LaTeX para focar no comportamento da bobina (alinhado à apresentação Manim)

Você é um agente encarregado de **reescrever o subprojeto LaTeX em `relatorio/`** para que o PDF conte
**apenas a história física do comportamento de uma bobina sob surto**, exatamente como a apresentação
Manim (`manim_presentation.py`, classe `SurgePresentation`): o enrolamento de um **gerador síncrono com
neutro solidamente aterrado**, modelado como escada com **capacitância série turn-to-turn** além da
shunt, em que a tensão **começa concentrada na entrada (t=0⁺) e relaxa para uma distribuição quase
uniforme**. O PDF deve trazer **animações**, inclusive **trechos da própria apresentação Manim**
convertidos para frames/GIF embutíveis.

O documento atual é um **relatório de projeto** (arquitetura do código Python, deck ATP, correspondência
Python×ATP, modelo T, caso de saída aberta com pico ~2039 V). **Quase tudo isso sai** ou vira nota curta:
o novo documento é sobre **o fenômeno físico**, não sobre a engenharia de software nem sobre a validação
numérica.

O projeto é de **engenharia elétrica**, com cultura de auditoria e reprodutibilidade. **Rigor e
honestidade sobre o que cada figura representa valem mais do que vistosidade.**

---

## Contexto e decisões já tomadas (não re-perguntar)

1. **Caso físico central:** gerador síncrono, **neutro solidamente aterrado** (terminação *grounded*,
   `V(N20)=0`), escada Pi `N=20`, **com capacitância série** `C_s` (turn-to-turn) além da shunt `C_g`.
   Parâmetro de distribuição **α = √(C_g/C_s) = 5** (`C_total = 1 nF`, `C_series_total = 40 pF`).
2. **Idioma do corpo do relatório:** **português** (como hoje). As **animações são trechos do Manim**,
   cujas legendas internas estão em inglês — isso é aceitável (é material da apresentação); o texto do
   relatório e as *captions* em volta explicam, em português, o que se vê.
3. **O caso de saída aberta (pico ~2039 V) deixa de ser o caso central.** Pode sobreviver, no máximo,
   como uma frase de contraste de condição de contorno (aberto × aterrado). A narrativa principal é a
   do gerador aterrado.
4. **A validação ATP não é o tema.** Vira, no máximo, **uma nota curta de credibilidade** (um parágrafo
   + uma figura), apontando para `RELATORIO_VALIDACAO_ATP_GERADOR.md`. Nada de seções de deck/coluna fixa.
5. **Infra de animação já existe e deve ser reutilizada:** pacote `animate` (`\animategraphics`) +
   extração de frames com `ffmpeg`, com os PNGs em `relatorio/frames/<nome>/frame-N.png` e
   `\graphicspath` já incluindo `frames/`.

---

## Leitura obrigatória antes de editar

- `relatorio/relatorio.tex`, `relatorio/preamble.tex`, `relatorio/macros.tex` — estrutura, pacotes
  (já tem `animate`, `circuitikz`, `siunitx`, `booktabs`), macros (`\Nsec`, `\Zsurge`, `\Ttravel`, …).
- `relatorio/build_notes.tex` — o fluxo `ffmpeg` que **já funciona** (fps 5, largura 720, 75 frames,
  numeração `frame-1`..`frame-75`). Use-o como gabarito.
- `relatorio/sections/08_animacoes.tex` — como `\animategraphics` já é usado (controls, loop, autoplay).
- `relatorio/sections/03_modelo_eletrico.tex` e `figures/circuito_tikz.tex` — o circuito atual
  (shunt-only). Precisará de `C_s` (ver Parte 3).
- `manim_presentation.py` — a narrativa das 5 cenas e, em especial, as **cenas standalone**
  `InitialDistributionScene` (≈ linha 1680) e `GroundedReturnPreview` (≈ linha 1696), que renderizam
  isoladamente os dois trechos que viram animação no PDF.
- `PROMPT_MELHORIAS_MANIM.md` — o storyboard físico (use a mesma ordem narrativa).
- `RELATORIO_VALIDACAO_ATP_GERADOR.md` — números da validação (pico N5 ≈ 1108 V, erros ≤0,011 %).
- `assets/tikz_ladder_grounded_circuit.png` — diagrama da escada **com `C_s` e `C_g`** já pronto
  (reutilizável como figura).

---

## Regras invioláveis

- **Nada de resultado fabricado.** Toda figura/animação vem de uma simulação real (`src/` ou cenas
  Manim) ou de fórmula analítica claramente rotulada. Curva só é "ATP" se vier de `.pl4` real.
- **Caso central = grounded + série (α=5).** Não reintroduza o caso aberto como protagonista.
- **O PDF deve compilar** com `latexmk -pdf relatorio.tex` (pdfLaTeX) **sem erros**; o pacote `animate`
  embute os frames (funciona em pdfLaTeX, sem `--shell-escape`).
- **Controle o tamanho do PDF.** `animate` embute **cada frame** como imagem. Limite o número de frames
  e a resolução (ver Parte 2); o PDF final não deve ficar absurdo (mire em ≲ 20–25 MB).
- **Caminhos relativos** e `\graphicspath` preservado. Sem caminhos absolutos.
- **Português no corpo**, com acentuação (o preâmbulo usa `inputenc utf8`). Mantenha o estilo
  `siunitx` para grandezas.
- **Commits pequenos e temáticos** em português (ex.: 1 commit da reestruturação do `.tex`, 1 commit
  dos frames/animações + `build_notes`).

---

## Parte 1 — Nova estrutura do documento (enxuta, espelhando o Manim)

Reescreva `relatorio.tex` para a sequência abaixo. Para cada seção atual, o destino:

| Seção atual | Destino |
|---|---|
| `00_resumo` | **Reescrever** — resumo físico (o que acontece com a tensão num surto), não de projeto. |
| `01_visao_geral` | **Reescrever** como *"O problema"* — gancho + expectativa ingênua (se dividisse igual, cada seção veria `V/N`). |
| `02_arquitetura_python` | **Remover** (no máximo, 1 frase no apêndice dizendo que as curvas vêm de um solver em `src/`). |
| `03_modelo_eletrico` | **Reescrever** — escada com `R, L, C_g (shunt), C_s (série)`; introduzir **α = √(C_g/C_s)**; **remover** modelo T e o foco no caso aberto/2039 V. |
| `04_fonte_surto` | **Manter/refinar** — impulso 1,2/50 µs (front, cauda, pico). |
| `05_modelo_atp` | **Remover** do corpo. |
| `06_correspondencia_python_atp` | **Condensar** numa nota curta de credibilidade (1 parágrafo + figura `comparacao_python_atp.png`), apontando o relatório de validação. |
| `07_resultados_figuras` | **Reescrever** em duas seções físicas novas (ver abaixo, itens 5 e 6). |
| `08_animacoes` | **Reescrever** para usar os trechos do Manim (Parte 2). |
| `09_conclusao` | **Reescrever** — implicações para o **isolamento de entrada** do gerador. |
| `build_notes` (apêndice) | **Atualizar** com o novo fluxo Manim→frames. |

**Sequência final proposta (em `relatorio.tex`):**

1. **Resumo** — físico.
2. **O problema: como a tensão se distribui num enrolamento sob surto?** (gancho + expectativa ingênua).
3. **A fonte de surto (1,2/50 µs)**.
4. **O modelo em escada** — `R, L, C_g, C_s`, e **α = √(C_g/C_s)** como "o número que controla quão
   desigual é a distribuição inicial". Inclua o circuito **com `C_s`** (Parte 3).
5. **Distribuição inicial (t = 0⁺)** — *núcleo*. `V(x)/V_0 = sinh(α(1−x))/sinh(α)` (aterrado); fator de
   concentração na entrada `α·coth α`; sobreponha a curva analítica como prova. **[animação opcional:
   varredura de α]**
6. **Evolução temporal no gerador aterrado** — a tensão parte do perfil concentrado e relaxa para
   quase uniforme; pico interno (o ATP dá **N5 ≈ 1108 V > 1 kV** de entrada). **[ANIMAÇÃO principal]**
7. **(curto) Confiança no resultado** — validação analítica (item 5) + nota da validação cruzada ATP.
8. **Conclusão** — a distribuição inicial não-uniforme dimensiona o **isolamento de entrada**; por isso
   máquinas levam para-raios/capacitor de surto no terminal.
- **Apêndice:** notas de construção (animações).

---

## Parte 2 — Animações a partir da apresentação Manim (o ponto central do pedido)

Use **as cenas standalone** já existentes no Manim como fonte dos trechos:

- `InitialDistributionScene` → animação da **distribuição inicial** (varredura de α).
- `GroundedReturnPreview` → animação da **evolução temporal** no caso aterrado (animação principal).

**Fluxo recomendado (Manim → mp4 → frames PNG → `\animategraphics`):**

```bash
# 1. Renderizar as cenas isoladas (qualidade média basta para o PDF)
manim -qm manim_presentation.py InitialDistributionScene
manim -qm manim_presentation.py GroundedReturnPreview

# 2. Extrair frames AMOSTRADOS do mp4 (escolha o fps de extração para obter
#    ~60-120 frames no total — ver armadilha de tamanho). Ex. para uma cena de
#    ~20 s, fps=5 -> ~100 frames; largura 900 px:
ffmpeg -y -i media/videos/manim_presentation/720p30/GroundedReturnPreview.mp4 \
  -vf "fps=5,scale=900:-1:flags=lanczos" relatorio/frames/manim_grounded/frame-%03d.png
```

- A cena temporal tem `run_time` longo (120 s na configuração atual). **Não** extraia a 30 fps (seriam
  milhares de frames). Escolha **um trecho representativo** (ex.: os primeiros ~15–20 s, onde ocorre a
  relaxação principal, via `-ss 0 -to 20`) e/ou um **fps baixo** (4–6) para ficar em ~60–120 frames.
- **Numeração dos frames:** `\animategraphics{fps}{frames/<nome>/frame-}{1}{N}` espera a sequência
  contígua `frame-1`..`frame-N`. O `ffmpeg` gera `frame-001`..`frame-NNN`; o pacote `animate` lida com
  o zero-padding desde que o intervalo `{1}{N}` cubra exatamente os arquivos. Confirme que o último
  índice `N` bate com o número de PNGs gerados (foi a fonte de bug do fluxo antigo — ver `build_notes`).
- **Incorporação** (espelhe `08_animacoes.tex`):

```latex
\animategraphics[controls,loop,autoplay,width=0.92\linewidth]{5}{frames/manim_grounded/frame-}{1}{100}
```

- **Idioma:** as legendas dentro do vídeo Manim estão em inglês — aceitável. A `\caption` e o texto ao
  redor ficam em português e explicam o que observar.
- **Fallback estático:** em leitores sem suporte a animação, o `\animategraphics` mostra o primeiro
  frame. Garanta que o **frame 1 seja informativo** (ou adicione, ao lado, uma figura estática de um
  instante-chave — ex.: o perfil inicial concentrado).

**Alternativa** (se preferir não embutir centenas de PNGs): exportar GIF do Manim
(`manim -qm --format=gif ...`) e extrair frames do GIF — mesmo fluxo do `build_notes` atual. Mantém a
escolha de `animate` (não use `media9/\movie`, que depende de player externo e é menos portátil).

---

## Parte 3 — Conteúdo físico a alinhar

- **Circuito com `C_s`.** O `figures/circuito_tikz.tex` é shunt-only. Duas opções: (a) **reutilizar**
  `assets/tikz_ladder_grounded_circuit.png` (já tem `C_s` roxo + `C_g` + neutro aterrado) como figura;
  ou (b) estender o `circuitikz` para incluir os capacitores série. Prefira (a) pela consistência visual
  com a apresentação.
- **Equações-chave** (com `siunitx`/`amsmath`): `α = √(C_g/C_s)`, distribuição inicial
  `sinh(α(1−x))/sinh(α)` (aterrado) e `cosh(α(1−x))/cosh(α)` (aberto, como contraste), fator de
  concentração na entrada `α·coth α`. Cite a teoria clássica (Greenwood; Blume & Boyajian — já em
  `references.bib`/`10_referencias`).
- **Figuras estáticas** podem ser frames-chave das cenas Manim (perfil inicial para alguns α; instante
  inicial × final da evolução) e/ou as figuras do simulador em `output/` que correspondam ao caso
  **aterrado** (não as do caso aberto).
- **Números honestos:** α=5; pico interno N5 ≈ 1108 V (do ATP); erros de validação ≤0,011 % de 1 kV.

---

## Parte 4 — Build e validação

- `cd relatorio && latexmk -pdf relatorio.tex` compila **sem erros** (rode `latexmk -C` antes se houver
  artefatos antigos). Resolva referências quebradas (`\ref`, `\cite`) das seções removidas.
- Abra o PDF no Adobe Acrobat e **confirme que as animações tocam**; verifique o fallback estático em
  um leitor simples.
- **Atualize `build_notes.tex`**: novo fluxo Manim→frames (comandos, fps, largura, nº de frames) e o
  tamanho final do PDF.
- Verifique o **tamanho do PDF** (≲ 20–25 MB); se estourar, reduza frames/resolução ou otimize os PNGs.
- Atualize `\tableofcontents`/`\listoffigures` implicitamente (recompilação dupla via latexmk).

---

## Armadilhas conhecidas

- **PDF gigante:** `animate` embute cada frame. Muitos frames em alta resolução incham o arquivo — fps
  baixo (4–6), largura ≤ 960 px, ≤ ~120 frames por animação.
- **Numeração de frames** `{1}{N}` × `frame-%03d` do ffmpeg: garanta que `N` = nº de PNGs e que não há
  buracos na sequência (foi o bug do fluxo anterior).
- **Cena temporal longa (120 s):** extrair tudo gera frames demais; use trecho/fps baixo.
- **Idioma misto:** animações em inglês dentro de relatório PT — declarado e aceitável; não traduza o
  vídeo, traduza a explicação ao redor.
- **Referências órfãs:** ao remover seções (Python/ATP/T), apague `\ref`/`\cite`/labels que apontavam
  para elas, senão o latexmk acusa.
- **Não** reintroduzir o caso aberto (2039 V) como protagonista — ele é, no máximo, contraste de uma
  frase.

---

## Critérios de aceitação

1. PDF compila com `latexmk -pdf` sem erros e sem referências quebradas.
2. A narrativa segue a do Manim: problema → fonte → modelo (R, L, C_g, C_s, α) → distribuição inicial
   não-uniforme → evolução temporal no gerador aterrado → confiança → conclusão de isolamento.
3. Há **pelo menos uma animação** vinda de um **trecho real do Manim** (cena temporal aterrada),
   tocável no Acrobat, com fallback estático informativo.
4. O circuito mostrado inclui `C_s` (série) e `C_g` (shunt) e a terminação aterrada.
5. Conteúdo de arquitetura Python / deck ATP / modelo T / caso aberto **removido** do corpo (ATP no
   máximo como nota curta de credibilidade).
6. `build_notes.tex` atualizado; tamanho do PDF sob controle; nenhum dado Python rotulado como ATP.
