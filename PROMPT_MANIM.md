# Prompt: Animação Manim — Efeito de Surto em Bobina de Gerador

## Objetivo

Gere um script Python completo usando a biblioteca **Manim (Community Edition)** que
anime o efeito de uma onda de surto atmosférico (impulso 1,2/50 µs) se propagando ao
longo de uma bobina de gerador modelada como escada LC distribuída, mostrando
**lado a lado** o comportamento **sem capacitor de surto** e **com capacitor de surto**.
A animação deve ser autocontida (sem arquivos externos) e tecnicamente precisa.

---

## 1. Física e modelo numérico a reproduzir

### 1.1 Modelo de escada LC (seção Pi)

A bobina é representada por **N = 20 seções Pi** em cascata. Cada seção contém:

| Elemento | Símbolo | Valor (caso base) |
|----------|---------|-------------------|
| Indutância por seção | L_sec | 0,5 mH |
| Resistência por seção | R_sec | 0,25 Ω |
| Capacitância por seção (shunt) | C_sec | 50 pF |

**Topologia Pi:** cada seção tem C_sec/2 no nó de entrada e C_sec/2 no nó de saída
(os meios capacitores de seções adjacentes se somam em C_sec nos nós internos).
O último nó (saída) fica em **circuito aberto**.

**Equações de estado** (vetor x = [V₁…V_N, I₁…I_N]):

```
KCL nó interno k:   C_sec · dVk/dt = I_k − I_{k+1}
KCL nó saída N:     (C_sec/2) · dV_N/dt = I_N
KVL seção k:        L_sec · dI_k/dt = V_{k−1} − V_k − R_sec · I_k
                    (V₀ = V_src(t))
```

### 1.2 Fonte de impulso duplo-exponencial (IEC 60060-1, 1,2/50 µs)

```
V(t) = V_pk · K · (e^{−α·t} − e^{−β·t})

α = ln(2) / T₂  =  13 863 s⁻¹    (T₂ = 50 µs)
β = 3,0  / T₁   =  2,5×10⁶ s⁻¹  (T₁ = 1,2 µs)
V_pk = 1 000 V
K   = normalization so that max(V) = V_pk
```

### 1.3 Dois cenários a comparar

| Cenário | Capacitância total da bobina | Significado físico |
|---------|-----------------------------|--------------------|
| **Sem capacitor de surto** | C_total = 0,1 nF → C_sec = 5 pF | distribuição capacitiva pequena, frente de onda abrupta, alto gradiente de tensão nas espiras iniciais |
| **Com capacitor de surto** | C_total = 10 nF → C_sec = 500 pF | capacitor externo adiciona capacitância distribuída, frente de onda suavizada, distribuição de tensão mais uniforme |

### 1.4 Parâmetros derivados (para exibir na animação)

```
Impedância de surto  Z₀ = sqrt(L_total / C_total)
   sem cap:  Z₀ ≈ 10 000 Ω
   com cap:  Z₀ ≈ 1 000 Ω

Tempo de propagação  T_travel = sqrt(L_total · C_total)
   sem cap:  T_travel ≈ 1,0 µs
   com cap:  T_travel ≈ 10 µs
```

### 1.5 Solver numérico a embutir no script

Use **`scipy.integrate.solve_ivp`** com `method='RK45'` para integrar as equações de
estado de t = 0 até t_end = 100 µs com `max_step = 10 ns`.

---

## 2. Estrutura das cenas Manim

Implemente **uma única classe `SurgeScene(Scene)`** com os seguintes blocos sequenciais.
Use `self.play(...)` e `self.wait(...)` para controlar o tempo. Duração total alvo: ~90 s.

---

### Cena 1 — Título e contexto (≈ 5 s)

- Texto grande centralizado: **"Surto em Bobina de Gerador"**
- Subtítulo: *"Impulso 1,2/50 µs — Modelo de Escada LC Distribuída"*
- Fade-out para a cena 2.

---

### Cena 2 — Diagrama esquemático da bobina (≈ 10 s)

Desenhe o circuito da escada Pi para **5 seções** (representativo):

```
V_src ──┬──[R/2]──[L]──[R/2]──┬──[R/2]──[L]──[R/2]──┬── … ──┬─── (aberto)
        │                      │                      │       │
       [C/2]                  [C]                    [C]    [C/2]
        │                      │                      │       │
       GND                    GND                    GND     GND
```

- Use `Line`, `Rectangle` (indutor) e `Arc`/`Circle` (capacitor) ou VGroup com labels.
- Marque os nós numerados: **0, 1, 2, … N** (posição 0% a 100% da bobina).
- Destaque em amarelo o nó de **entrada** (0%) e em vermelho o nó de **saída** (100%).
- Exiba abaixo do diagrama a fórmula da fonte: `V(t) = V_pk · K · (e^{−αt} − e^{−βt})`.
- Anima a construção seção por seção (Write/Create).

---

### Cena 3 — Forma de onda da fonte (≈ 8 s)

- Plote `V_src(t)` de 0 a 10 µs usando **`Axes`** do Manim.
- Eixo X: tempo em µs, eixo Y: tensão em V (0 a 1 100 V).
- Curva laranja com label "Impulso 1,2/50 µs".
- Marque com seta o ponto de pico (~1,2 µs) e a meia-cauda (~50 µs).
- Use `Create(curve)` animado.

---

### Cena 4 — Propagação da onda: painel duplo (≈ 40 s — cena principal)

**Layout:** dois `Axes` lado a lado, ocupando a maior parte do frame.

```
┌─────────────────────────────────────────────────────────┐
│  SEM capacitor de surto   │   COM capacitor de surto    │
│  C_total = 0,1 nF         │   C_total = 10 nF           │
│                           │                             │
│  [gráfico de V vs posição]│  [gráfico de V vs posição]  │
│                           │                             │
│  Tempo: XX,X µs ←──── cursor de tempo compartilhado    │
└─────────────────────────────────────────────────────────┘
```

**Para cada frame da animação:**

1. Calcule previamente (fora do Manim, antes da cena) os arrays `V_nodes_lowC[t_idx, node]`
   e `V_nodes_highC[t_idx, node]` para todos os instantes.
2. Use `ValueTracker` para o índice de tempo.
3. Atualize as curvas com `always_redraw` ou `add_updater`:
   - Eixo X: posição ao longo da bobina (0 a 100%, representando os N+1 nós).
   - Eixo Y: tensão instantânea em V (−500 a 2 500 V para cobrir reflexão).
   - Curva esquerda: **vermelho** (sem cap).
   - Curva direita: **azul** (com cap).
4. Linha vertical tracejada cinza marcando a **frente de onda** (primeiro nó com |V| > 50 V).
5. Label dinâmico no topo: `"t = {:.1f} µs"`.
6. Faça o tempo avançar de **0 a 20 µs** com `tracker.animate.set_value(...)` em ~30 s.

**Efeitos visuais a destacar:**

- Quando a frente chega ao nó N (saída aberta), mostre um **flash vermelho** no lado
  sem cap e um **flash azul suave** no lado com cap, acompanhado de texto:
  `"Reflexão: V_saída ≈ 2 × V_entrada"` (sem cap) e
  `"Frente suavizada — menor sobretensão"` (com cap).
- Sempre que a tensão num nó ultrapassar 1 500 V (só no caso sem cap), pinte aquele
  segmento da curva em **amarelo** para indicar estresse dielétrico crítico.

---

### Cena 5 — Distribuição de picos (bar chart) (≈ 10 s)

Após a simulação, exiba um **`BarChart`** lado a lado (dois grupos de barras):

- Eixo X: posição do nó (0%, 25%, 50%, 75%, 100%).
- Eixo Y: tensão de pico máxima [V].
- Grupo 1 (vermelho, hachurado): sem cap → mostra gradiente acentuado perto do nó 0
  e pico ~2 000 V no nó N.
- Grupo 2 (azul): com cap → distribuição quase uniforme, pico ~1 200 V no nó N.
- Anota cada barra com o valor numérico (`.to_edge` ou `next_to`).
- Título: `"Tensão de Pico por Posição na Bobina"`.

---

### Cena 6 — Gradiente de tensão entre espiras (≈ 10 s)

- **`BarChart`** do gradiente de pico |ΔV| entre nós adjacentes.
- Eixo X: intervalo entre nós (1–2, 2–3, …, N−1–N).
- Grupo vermelho (sem cap): alto gradiente nos primeiros intervalos (~800–1 200 V).
- Grupo azul (com cap): gradiente distribuído uniformemente (~100–200 V).
- Legenda explicando: `"Alto gradiente → risco de ruptura de isolamento entre espiras"`.

---

### Cena 7 — Conclusão (≈ 7 s)

Quadro de texto com três pontos em sequência (Write animado):

1. `"Sem capacitor: frente abrupta → pico ~2× V_entrada, gradiente elevado nas primeiras espiras"`
2. `"Com capacitor de surto: frente suavizada → tensão distribuída uniformemente"`
3. `"Capacitor de surto protege o isolamento entre espiras contra sobretensões impulsivas"`

Fade-out final.

---

## 3. Requisitos técnicos do código

### 3.1 Dependências

```python
# Instalar antes de executar:
# pip install manim scipy numpy
```

### 3.2 Estrutura do arquivo

```
surge_animation.py
└── SurgeScene(Scene)
    ├── construct(self)          # orquestra todas as cenas
    ├── _run_simulation(C_total) # integra ODE com scipy e retorna array [n_time, n_nodes+1]
    ├── _build_circuit_diagram() # retorna VGroup com o esquemático
    ├── _source_curve_mobject()  # retorna a curva V_src(t) como ParametricFunction
    ├── _make_voltage_axes(label)# retorna Axes configurado para tensão vs posição
    └── _make_bar_chart(data, colors, title) # retorna BarChart
```

### 3.3 Parâmetros globais (definir no topo do arquivo)

```python
N_SECTIONS   = 20
L_TOTAL      = 10e-3       # H
R_TOTAL      = 5.0         # Ω
V_PK         = 1000.0      # V
T_FRONT      = 1.2e-6      # s
T_TAIL       = 50e-6       # s
T_END        = 100e-6      # s
DT           = 10e-9       # s
C_LOW        = 0.1e-9      # F  (sem cap surto)
C_HIGH       = 10e-9       # F  (com cap surto)
FPS_ANIM     = 15          # frames por segundo da animação Manim
```

### 3.4 Implementação do solver (embutir no script)

```python
def _run_simulation(self, C_total):
    """Integra modelo Pi de N seções e retorna V_nodes[t_idx, node_0..N]."""
    import numpy as np
    from scipy.integrate import solve_ivp

    N = N_SECTIONS
    L = L_TOTAL / N
    R = R_TOTAL / N
    C = C_total / N

    alpha = np.log(2) / T_TAIL
    beta  = 3.0 / T_FRONT
    t_dummy = np.linspace(0, T_FRONT * 3, 10000)
    raw     = np.exp(-alpha * t_dummy) - np.exp(-beta * t_dummy)
    K       = V_PK / raw.max()

    def v_src(t):
        return K * (np.exp(-alpha * t) - np.exp(-beta * t))

    # Estado: x[0..N-1] = V_1..V_N (tensões nos nós 1 a N)
    #         x[N..2N-1] = I_1..I_N (correntes nas seções)
    def derivatives(t, x):
        V = x[:N]
        I = x[N:]
        dV = np.zeros(N)
        dI = np.zeros(N)

        # KCL
        for k in range(N - 1):
            C_k = C  # nó interno
            dV[k] = (I[k] - I[k + 1]) / C_k
        dV[N - 1] = I[N - 1] / (C / 2)  # nó de saída (aberto)

        # KVL
        V_prev = np.concatenate([[v_src(t)], V[:-1]])
        dI = (V_prev - V - R * I) / L

        return np.concatenate([dV, dI])

    t_eval = np.arange(0, T_END + DT, DT)
    sol = solve_ivp(derivatives, [0, T_END], np.zeros(2 * N),
                    method='RK45', t_eval=t_eval, max_step=DT * 10,
                    rtol=1e-6, atol=1e-9)

    # Reconstruir V_node_0 = V_src(t)
    V_src_arr = np.array([v_src(t) for t in sol.t])
    V_nodes   = np.column_stack([V_src_arr, sol.y[:N].T])  # shape (n_time, N+1)
    return sol.t, V_nodes
```

### 3.5 Comando de renderização

```bash
manim -pqh surge_animation.py SurgeScene
# -p  abre o vídeo automaticamente
# -qh qualidade alta (1080p)
# Para preview rápido use -ql (480p)
```

---

## 4. Diretrizes de estilo visual

| Elemento | Cor / estilo |
|----------|-------------|
| Fundo da cena | `BLACK` ou `#0d1117` |
| Curva sem capacitor | `RED` (#e63946) |
| Curva com capacitor | `BLUE` (#4895ef) |
| Frente de onda (marker) | `YELLOW`, linha tracejada |
| Zona de estresse crítico (V > 1500 V) | `YELLOW` sólido na curva |
| Eixos e labels | `WHITE` |
| Diagrama do circuito | `WHITE` com inductores em `GREEN` e capacitores em `CYAN` |
| Texto de conclusão | `WHITE`, fonte tamanho 28–32 |

---

## 5. Mensagens pedagógicas a incluir na animação

Insira `Text` ou `MathTex` nos momentos indicados:

1. **Antes de a onda chegar** (t < 1 µs):
   `"Bobina em repouso — distribuição de tensão nula"`

2. **No pico da frente** (t ≈ 1,2 µs, só no caso sem cap):
   `"Frente abrupta: alto dV/dt → concentração de tensão nas primeiras espiras"`

3. **Na reflexão** (t ≈ T_travel, nó N):
   `"Circuito aberto: coeficiente de reflexão = +1 → V_saída → 2 × V_fonte"`

4. **Após suavização** (com cap):
   `"Capacitor de surto redistribui a frente → menor gradiente entre espiras"`

5. **No gráfico de pico:**
   `"Tensão de pico 40–60 % menor com proteção capacitiva"`

---

## 6. Critérios de aceitação do código gerado

- [ ] Executa sem erros com `manim -pqh surge_animation.py SurgeScene`.
- [ ] Mostra os dois casos lado a lado na cena 4, animados sincronicamente.
- [ ] Os valores numéricos (picos, tempos de viagem) são consistentes com o modelo acima.
- [ ] A animação dura entre 80 s e 110 s.
- [ ] Não usa arquivos externos (CSV, PNG) — toda a simulação é autocontida.
- [ ] O código segue a estrutura de métodos descrita em 3.2.
- [ ] Comentários em português explicam cada bloco.
