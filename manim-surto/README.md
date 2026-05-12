# manim-surto

Animação Manim do efeito de surto atmosférico em bobina de gerador.

## O que a animação mostra

Comparação lado a lado do impulso 1,2/50 µs (IEC 60060-1) propagando-se por uma
bobina modelada como escada LC distribuída (20 seções Pi):

| Cena | Conteúdo |
|------|----------|
| 1 | Título e legenda |
| 2 | Diagrama esquemático da escada Pi |
| 3 | Forma de onda da fonte impulso |
| **4** | **Propagação da onda ao longo dos nós — painel duplo animado** |
| 5 | Bar chart de tensão de pico por posição |
| 6 | Bar chart de gradiente de tensão entre espiras |
| 7 | Conclusões |

## Parâmetros do modelo

| Parâmetro | Sem capacitor | Com capacitor |
|-----------|--------------|---------------|
| C_total | 0,1 nF | 10 nF |
| L_total | 10 mH | 10 mH |
| R_total | 5 Ω | 5 Ω |
| N_sections | 20 | 20 |
| Impulso | 1,2/50 µs, 1 000 V | idem |

## Instalação

```bash
pip install -r requirements.txt
```

> **Windows:** o Manim requer também o [MiKTeX](https://miktex.org/) (LaTeX),
> o [FFmpeg](https://ffmpeg.org/) e o [Cairo](https://www.cairographics.org/).
> A forma mais fácil é instalar via Chocolatey:
> ```
> choco install manim
> ```

## Renderização

```bash
# Qualidade alta (1080p 60fps) — recomendado para apresentação
manim -pqh surge_animation.py SurgeScene

# Preview rápido (480p)
manim -pql surge_animation.py SurgeScene

# Sem abrir automaticamente, salva em media/
manim -qh surge_animation.py SurgeScene
```

O vídeo é salvo em `media/videos/surge_animation/1080p60/SurgeScene.mp4`.

## Estrutura do código

```
SurgeScene(Scene)
├── construct()                  # orquestra as 7 cenas
├── _pre_compute_simulations()   # roda scipy.solve_ivp antes de animar
├── _run_simulation(C_total)     # integra ODE — modelo Pi N seções
├── _cena1_titulo()
├── _cena2_esquematico()
├── _build_circuit_diagram(n)
├── _cena3_forma_de_onda()
├── _cena4_propagacao()          # cena principal com ValueTracker + always_redraw
├── _cena5_picos()               # BarChart tensão de pico
├── _cena6_gradiente()           # BarChart gradiente entre nós
├── _cena7_conclusao()
├── _pill()                      # helper para legendas
├── _mensagem()                  # helper para textos pedagógicos
└── _t_to_idx()                  # helper tempo → índice
```
