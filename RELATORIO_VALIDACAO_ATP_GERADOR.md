# Relatório — Validação cruzada Python × ATP do caso do gerador (neutro aterrado, com capacitância série)

**Data:** 14/06/2026 · **Deck:** `surto_bobina_gerador.atp` · **Config Python:** `config/gerador_aterrado.json`
· **PL4:** `surto_bobina_gerador.pl4` (20001 passos, 0–200 µs) · **ATP:** `tpbigG.exe` (GNU)

## Caso validado

Enrolamento de **gerador síncrono com neutro solidamente aterrado**, escada Pi `N = 20`, **com
capacitância série turn-to-turn**:

| Parâmetro | Valor |
|---|---|
| `L_total` / `R_total` / `C_total` (shunt) | 10 mH / 5 Ω / 1 nF |
| `C_series_total` (ponta-a-ponta) | 40 pF ⇒ **α = √(C_g/C_s) = 5** |
| `C_s,sec` por ramo (deck ATP) | `N·C_series_total` = 800 pF = `8.E-4` µF |
| Terminação | grounded (`V(N20) = 0`) |
| Fonte | dupla-exponencial 1,2/50 µs, ~1 kV |

## Resultados por nó

| Nó | Pos. | Pico Python (V) | Pico ATP (V) | Dif. pico | máx\|err\| (V) | máx\|err\| (% 1 kV) | RMS (V) | máx\|err\| 0–30 µs (V) |
|---|---|---|---|---|---|---|---|---|
| N0 | 0 % | 1000,00 | 999,97 | +0,003 % | 0,030 | 0,003 % | 0,014 | 0,030 |
| N5 | 25 % | 1108,39 | 1108,35 | +0,003 % | 0,693 | 0,069 % | 0,197 | 0,077 |
| N10 | 50 % | 949,43 | 949,40 | +0,003 % | 0,609 | 0,061 % | 0,194 | 0,096 |
| N15 | 75 % | 617,66 | 617,64 | +0,003 % | 0,689 | 0,069 % | 0,198 | 0,110 |
| N20 | 100 % | 0,000 | 0,000 | — (¹) | 0,000 | 0,000 % | 0,000 | 0,000 |

(¹) O CSV registra `-100 %` em N20: é um artefato de `(0−0)/0` (o ATP retorna ~µV de ruído numérico,
o Python fixa exatamente 0). Sem significado físico — `máx|err| = 0,000 V`. Ver painel N20 da figura,
em escala de 10⁻⁶ V.

**Figura:** `output/atp_gerador/comparacao_python_atp.png` (Python × ATP por nó) ·
**CSV:** `output/atp_gerador/comparacao_python_atp.csv`

## Veredito

**Validação confirmada.** O modelo Python (`src/`, RK45) e o ATP (trapezoidal) sobre a **mesma** rede
concordam dentro de:

- **diferença de pico sistemática de +0,003 %** em todos os nós internos — não é erro de modelo, e
  sim a fonte: o deck usa `A1 = 1035.1` (pico ~999,97 V) e o Python normaliza para 1000,0 V exatos;
- **erro pontual ≤ 0,11 V (0,011 % de 1 kV) na janela de interesse dielétrico (0–30 µs)**, onde ocorrem
  a frente de onda e as primeiras reflexões;
- erro pontual ≤ 0,69 V (0,069 %) na janela completa de 200 µs — o leve aumento vem da **dispersão
  numérica** diferente entre trapezoidal e RK45 acumulada ao longo das oscilações sustentadas; é
  benigno e não afeta picos nem a janela inicial.

Isso está na **mesma ordem de grandeza** da validação cruzada open/somente-shunt já existente.

O resultado também confirma a física do caso do gerador: o pico em **N5 (25 %) chega a 1108 V > 1 kV
de entrada** — a sobretensão de **concentração na entrada** que a capacitância série (α = 5) produz e
que justifica a proteção de surto nos terminais da máquina.

## Escopo (o que esta validação cobre e o que não cobre)

- **Cobre:** caso **grounded + capacitância série (α = 5)**, `N = 20`, impulso 1,2/50 µs, nós
  N0/N5/N10/N15/N20.
- **Não cobre / permanece separado:** a validação **open / somente-shunt** continua coberta pelo deck
  original `surto_bobina.atp` e por `output/atp/` — **intactos**. Não foi alterado o `default_case.json`
  nem o deck original.
- Toda curva "ATP" provém do `.pl4` real gerado por execução bem-sucedida do `tpbigG.exe`; nenhum dado
  Python é rotulado como ATP.

## Como reproduzir

```bash
python scripts/gen_deck_gerador.py                      # gera o deck (coluna fixa)
python run_atp.py --atp-file surto_bobina_gerador.atp --out output/atp_gerador
python scripts/compare_python_atp.py \
       --config config/gerador_aterrado.json \
       --pl4 surto_bobina_gerador.pl4 --out output/atp_gerador
```
