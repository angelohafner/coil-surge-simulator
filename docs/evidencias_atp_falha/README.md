# Evidências — falha e correção da execução ATP

Esta pasta preserva a evidência documental de que a execução original do ATP
(abril/2026) **falhou** e de que o deck corrigido (junho/2026) **executou com
sucesso**. Contexto completo em `AUDITORIA_PROJETO.md` (achados A1/A2) na raiz
do repositório.

| Arquivo | Origem | O que prova |
|---------|--------|-------------|
| `2026-04-26_atp_stdout_KILL6.txt` | stdout do tpbigG.exe em 26/04/2026 (era `atp_stdout.txt` na raiz) | O deck original morreu com **KILL = 6** no primeiro cartão de ramo (`N0 N1`): o valor de R (0,25 Ω) caiu nas colunas 15–26 (campos de ramo de referência). Nenhum `.pl4` foi gerado. |
| `2026-04-26_atp_stderr.txt` | stderr da mesma execução | Vazio (sem mensagens). |
| `2026-04-24_debug1_lis.txt` | `debug1.lis` da raiz | Arquivo de diagnóstico RFUNL1 da época das tentativas. |
| `2026-04-24_63336514_tmp.txt` / `2026-04-24_63346162_tmp.txt` | temporários do ATP na raiz | Conexão do arquivo de diagnóstico nas tentativas de abril (uma por convocação). |
| `2026-06-12_atp_stdout_sucesso.txt` | stdout do tpbigG.exe em 12/06/2026, deck corrigido | Caso completo: 22 nós, 41 ramos, fonte tipo 15 interpretada como `1.04E+03 -1.39E+04 -2.50E+06`, loop de integração até 200 µs, `.pl4` gravado (ICAT=1). |

Correções aplicadas ao `surto_bobina.atp` (ver histórico git do arquivo):

1. **Colunas dos cartões de ramo** realinhadas ao formato fixo (R em 27–32,
   L em 33–38, C em 39–44).
2. **Unidade de L**: com `XOPT = 0` o ATP lê indutância em **mH** — o deck
   original declarava H no comentário e o valor `5.E-4` teria sido lido como
   0,5 µH (1000× menor). Corrigido para `0.5` (mH).
3. **Tipo da fonte**: cartão tipo 14 (cossenoidal no ATP) trocado por
   **tipo 15** (surto dupla exponencial), com expoentes **negativos**
   (`-13863.`, `-2.5E6`). Interpretação confirmada pelo eco do `.lis` e por
   `V(N0)` do `.pl4` coincidir com a expressão analítica (desvio máx. 0,0 V).
4. **ICAT = 1** no cartão inteiro de misc. data — sem ele o GNU ATP descarta
   o `.pl4` ao final da execução (comportamento observado em 12/06/2026).

A comparação quantitativa Python × ATP é gerada por
`scripts/compare_python_atp.py` e gravada em
`output/atp/comparacao_python_atp.{csv,png}`.
